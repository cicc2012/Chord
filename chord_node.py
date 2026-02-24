# chord_node.py
"""
Base Chord DHT Implementation
Provides core distributed hash table functionality with consistent hashing,
finger tables, and stabilization protocol.
"""

import hashlib
import json
import requests
from flask import Flask, request, jsonify
import threading
import time
import logging

class ChordNode:
    def __init__(self, ip, port, m=8):
        """
        Initialize a Chord node
        
        Args:
            ip: IP address to bind to
            port: Port to listen on
            m: Number of bits in hash space (2^m nodes max)
        """
        self.ip = ip
        self.port = port
        self.m = m
        self.max_nodes = 2 ** m
        
        # Node's position in the ring
        self.id = self._hash(f"{ip}:{port}")
        
        # Successor and predecessor
        self.successor = None
        self.predecessor = None
        
        # Finger table for efficient lookup
        self.finger_table = [None] * m
        
        # Local storage
        self.data = {}
        
        # Metrics
        self.start_time = time.time()
        self.request_count = 0
        self.total_latency = 0
        
        # Flask app for RPC
        self.app = Flask(__name__)
        self.app.logger.setLevel(logging.ERROR)
        self._setup_routes()
        
        # Stabilization running flag
        self.running = True
    
    def _hash(self, key):
        """Hash function to map keys to positions in the ring"""
        return int(hashlib.sha1(key.encode()).hexdigest(), 16) % self.max_nodes
    
    def _in_range(self, key, start, end):
        """
        Check if key is in (start, end] on the ring
        Handles wrap-around for circular ring
        """
        if start < end:
            return start < key <= end
        else:  # Range wraps around
            return key > start or key <= end
    
    def _setup_routes(self):
        """Setup REST API endpoints"""
        
        @self.app.route('/join', methods=['POST'])
        def join():
            """Join existing ring via known node"""
            data = request.json
            known_node = data.get('known_node')
            self._join(known_node)
            return jsonify({"status": "joined", "node_id": self.id})
        
        @self.app.route('/find_successor', methods=['POST'])
        def find_successor():
            """Find successor of a given ID"""
            data = request.json
            target_id = data['id']
            succ = self._find_successor(target_id)
            return jsonify(succ)
        
        @self.app.route('/get_predecessor', methods=['GET'])
        def get_predecessor():
            """Get this node's predecessor"""
            return jsonify(self.predecessor)
        
        @self.app.route('/notify', methods=['POST'])
        def notify():
            """Notification from potential predecessor"""
            data = request.json
            self._notify(data)
            return jsonify({"status": "ok"})
        
        @self.app.route('/store', methods=['POST'])
        def store():
            """Store key-value pair"""
            data = request.json
            key = data['key']
            value = data['value']
            key_id = self._hash(key)
            
            # Find responsible node
            responsible = self._find_successor(key_id)
            
            if responsible['id'] == self.id:
                # This node is responsible
                self.data[key] = value
                return jsonify({"status": "stored", "node": self.id})
            else:
                # Forward to responsible node
                return self._forward_request(responsible, '/store', data)
        
        @self.app.route('/retrieve', methods=['POST'])
        def retrieve():
            """Retrieve value by key"""
            data = request.json
            key = data['key']
            key_id = self._hash(key)
            
            responsible = self._find_successor(key_id)
            
            if responsible['id'] == self.id:
                value = self.data.get(key)
                return jsonify({"value": value, "node": self.id})
            else:
                return self._forward_request(responsible, '/retrieve', data)
        
        @self.app.route('/delete', methods=['POST'])
        def delete():
            """Delete key-value pair"""
            data = request.json
            key = data['key']
            key_id = self._hash(key)
            
            responsible = self._find_successor(key_id)
            
            if responsible['id'] == self.id:
                if key in self.data:
                    del self.data[key]
                    return jsonify({"status": "deleted", "node": self.id})
                return jsonify({"status": "not_found", "node": self.id}), 404
            else:
                return self._forward_request(responsible, '/delete', data)
        
        @self.app.route('/get_keys', methods=['GET'])
        def get_keys():
            """List all keys stored on this node"""
            return jsonify({"keys": list(self.data.keys()), "count": len(self.data)})
        
        @self.app.route('/get_info', methods=['GET'])
        def get_info():
            """Get node information for debugging"""
            return jsonify({
                "id": self.id,
                "ip": self.ip,
                "port": self.port,
                "successor": self.successor,
                "predecessor": self.predecessor,
                "finger_table": self.finger_table,
                "data_keys": list(self.data.keys())
            })
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({
                "status": "healthy",
                "node_id": self.id,
                "uptime": time.time() - self.start_time,
                "has_successor": self.successor is not None,
                "has_predecessor": self.predecessor is not None
            })
        
        @self.app.route('/metrics', methods=['GET'])
        def metrics():
            """Performance metrics"""
            avg_latency = self.total_latency / self.request_count if self.request_count > 0 else 0
            return jsonify({
                "node_id": self.id,
                "stored_items": len(self.data),
                "requests_handled": self.request_count,
                "avg_latency_ms": avg_latency,
                "successor_id": self.successor['id'] if self.successor else None,
                "predecessor_id": self.predecessor['id'] if self.predecessor else None
            })
        
        @self.app.route('/ring_state', methods=['GET'])
        def ring_state():
            """Get entire ring state by walking the ring"""
            nodes = []
            visited = set()
            current = {"id": self.id, "ip": self.ip, "port": self.port}
            
            while current['id'] not in visited:
                visited.add(current['id'])
                try:
                    resp = requests.get(
                        f"http://{current['ip']}:{current['port']}/get_info",
                        timeout=2
                    )
                    info = resp.json()
                    nodes.append({
                        "id": info['id'],
                        "ip": info['ip'],
                        "port": info['port'],
                        "keys_count": len(info['data_keys'])
                    })
                    current = info['successor']
                    if not current:
                        break
                except:
                    break
            
            total_keys = sum(n['keys_count'] for n in nodes)
            return jsonify({
                "nodes": nodes,
                "total_nodes": len(nodes),
                "total_keys": total_keys
            })
        
        @self.app.route('/stabilize', methods=['POST'])
        def stabilize_manual():
            """Trigger stabilization manually"""
            self._stabilize()
            return jsonify({"status": "stabilized"})
        
        @self.app.route('/fix_fingers', methods=['POST'])
        def fix_fingers_manual():
            """Trigger finger table fix manually"""
            self._fix_fingers()
            return jsonify({"status": "fingers_fixed"})
    
    def _find_successor(self, target_id):
        """Find successor node for given ID"""
        if self.successor is None:
            return {"id": self.id, "ip": self.ip, "port": self.port}
        
        # If target is between this node and successor
        if self._in_range(target_id, self.id, self.successor['id']):
            return self.successor
        
        # Use finger table to jump closer
        closest = self._closest_preceding_node(target_id)
        
        if closest['id'] == self.id:
            return self.successor
        
        # Ask the closest node
        try:
            resp = requests.post(
                f"http://{closest['ip']}:{closest['port']}/find_successor",
                json={"id": target_id},
                timeout=2
            )
            return resp.json()
        except:
            return self.successor
    
    def _closest_preceding_node(self, target_id):
        """Find closest finger that precedes target_id"""
        for i in range(self.m - 1, -1, -1):
            finger = self.finger_table[i]
            if finger and self._in_range(finger['id'], self.id, target_id):
                return finger
        return {"id": self.id, "ip": self.ip, "port": self.port}
    
    def _join(self, known_node):
        """Join the Chord ring through a known node"""
        if known_node:
            # Ask known node to find our successor
            try:
                resp = requests.post(
                    f"http://{known_node['ip']}:{known_node['port']}/find_successor",
                    json={"id": self.id},
                    timeout=5
                )
                self.successor = resp.json()
                print(f"Node {self.id}: Joined ring via {known_node['ip']}:{known_node['port']}")
                print(f"Node {self.id}: My successor is {self.successor['id']}")
            except Exception as e:
                print(f"Node {self.id}: Failed to join ring: {e}")
                self.successor = {"id": self.id, "ip": self.ip, "port": self.port}
        else:
            # First node in the ring
            self.successor = {"id": self.id, "ip": self.ip, "port": self.port}
            print(f"Node {self.id}: Created new ring")
        
        # Start stabilization
        self._start_stabilization()
    
    def _notify(self, node):
        """Handle notification from potential predecessor"""
        if self.predecessor is None or \
           self._in_range(node['id'], self.predecessor['id'], self.id):
            self.predecessor = node
    
    def _stabilize(self):
        """Periodically verify successor and update predecessor"""
        if not self.running:
            return
            
        try:
            # Get successor's predecessor
            resp = requests.get(
                f"http://{self.successor['ip']}:{self.successor['port']}/get_predecessor",
                timeout=2
            )
            x = resp.json()
            
            # If x is between us and our successor, x should be our successor
            if x and x['id'] != self.id and \
               self._in_range(x['id'], self.id, self.successor['id']):
                self.successor = x
            
            # Notify successor about us
            requests.post(
                f"http://{self.successor['ip']}:{self.successor['port']}/notify",
                json={"id": self.id, "ip": self.ip, "port": self.port},
                timeout=2
            )
        except Exception as e:
            pass
    
    def _fix_fingers(self):
        """Periodically refresh finger table entries"""
        if not self.running:
            return
            
        for i in range(self.m):
            start = (self.id + 2**i) % self.max_nodes
            try:
                self.finger_table[i] = self._find_successor(start)
            except:
                pass
    
    def _start_stabilization(self):
        """Start background threads for maintenance"""
        def stabilize_loop():
            while self.running:
                self._stabilize()
                time.sleep(5)
        
        def fix_fingers_loop():
            while self.running:
                self._fix_fingers()
                time.sleep(10)
        
        threading.Thread(target=stabilize_loop, daemon=True).start()
        threading.Thread(target=fix_fingers_loop, daemon=True).start()
    
    def _forward_request(self, node, endpoint, data):
        """Forward request to another node"""
        try:
            resp = requests.post(
                f"http://{node['ip']}:{node['port']}{endpoint}",
                json=data,
                timeout=2
            )
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    def stop(self):
        """Stop the node gracefully"""
        self.running = False
    
    def run(self):
        """Start the node server"""
        print(f"Node {self.id} listening on {self.ip}:{self.port}")
        self.app.run(host='0.0.0.0', port=self.port, threaded=True)
        
    def __enter__(self):
        """Context manager entry"""
        print(f"Node {self.id} starting...")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ALWAYS runs on shutdown"""
        print(f"\nNode {self.id} shutting down...")
        
        # Stop background threads
        self.running = False
        
        # Save state
        self._save_state()
        
        # Final stats
        print(f"Final key count: {len(self.data)}")
        
        if exc_type is not None:
            print(f"Shutdown due to exception: {exc_type.__name__}: {exc_val}")
        else:
            print("Clean shutdown")
        
        return False  # Don't suppress exceptions
    
    def run_with_context(self):
        """Run with context manager"""
        with self:
            self.run()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python chord_node.py <ip> <port> [known_node_ip:port]")
        sys.exit(1)
    
    ip = sys.argv[1]
    port = int(sys.argv[2])
    
    node = ChordNode(ip, port)
    
    # Join existing ring if known node provided
    if len(sys.argv) == 4:
        known_ip, known_port = sys.argv[3].split(':')
        known_node = {"ip": known_ip, "port": int(known_port)}
        node._join(known_node)
    else:
        # Bootstrap first node
        node._join(None)
    
    node.run()