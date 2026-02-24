# chord_node_nat_network.py
"""
NAT Network Adapter for Chord Node
Handles address translation between internal VM IPs and external host IPs
for multi-host deployment with NAT Network mode.
"""

import sys
import os
from chord_node import ChordNode
from shared_config import get_node_config, BOOTSTRAP_NODE

class ChordNodeNATNetwork(ChordNode):
    def __init__(self, node_name):
        """
        Initialize Chord node for NAT Network deployment
        
        Args:
            node_name: Node identifier from shared_config.py
        """
        config = get_node_config(node_name)
        
        # Node binds to internal IP (inside VM)
        internal_ip = config['vm_internal_ip']
        internal_port = config['vm_internal_port']
        
        # But advertises external address (host IP + forwarded port)
        self.public_ip = config['host_ip']
        self.public_port = config['host_port']
        self.node_name = node_name
        self.host_machine = config['host_machine']
        
        # Initialize with internal address for binding
        super().__init__(internal_ip, internal_port)
        
        print(f"\n{'='*60}")
        print(f"Node {node_name} initialized")
        print(f"{'='*60}")
        print(f"  Host Machine: {self.host_machine}")
        print(f"  Internal Address: {internal_ip}:{internal_port} (listening)")
        print(f"  External Address: {self.public_ip}:{self.public_port} (advertised)")
        print(f"  Chord ID: {self.id}")
        print(f"{'='*60}\n")
    
    def _get_self_info(self):
        """Return info with public address for other nodes to reach us"""
        return {
            "id": self.id,
            "ip": self.public_ip,      # Use public IP for routing
            "port": self.public_port   # Use public port
        }
    
    def _join(self, known_node):
        """Override join to use public addresses"""
        if known_node:
            print(f"Node {self.node_name}: Joining ring via {known_node['ip']}:{known_node['port']}")
        else:
            print(f"Node {self.node_name}: Creating new ring (bootstrap node)")
        
        super()._join(known_node)
    
    def _notify(self, node):
        """Override to ensure we store public addresses"""
        # Node info already contains public addresses from other nodes
        super()._notify(node)
    
    def _stabilize(self):
        """Override stabilize to use public address in notifications"""
        if not self.running:
            return
            
        try:
            # Get successor's predecessor
            resp = self.app.test_client().get(
                f"http://{self.successor['ip']}:{self.successor['port']}/get_predecessor"
            ) if self.successor['id'] == self.id else \
                requests.get(
                    f"http://{self.successor['ip']}:{self.successor['port']}/get_predecessor",
                    timeout=2
                )
            
            if self.successor['id'] != self.id:
                x = resp.json()
            else:
                x = None
            
            # If x is between us and our successor, x should be our successor
            if x and x['id'] != self.id and \
               self._in_range(x['id'], self.id, self.successor['id']):
                self.successor = x
            
            # Notify successor about us with PUBLIC address
            self_info = self._get_self_info()
            
            if self.successor['id'] != self.id:
                requests.post(
                    f"http://{self.successor['ip']}:{self.successor['port']}/notify",
                    json=self_info,
                    timeout=2
                )
        except Exception as e:
            pass


def main():
    if len(sys.argv) < 2:
        print("Usage: python chord_node_nat_network.py <node_name>")
        print("Example: python chord_node_nat_network.py node1")
        print("\nAvailable nodes from shared_config.py:")
        from shared_config import CHORD_NODES
        for name in CHORD_NODES.keys():
            print(f"  - {name}")
        sys.exit(1)
    
    node_name = sys.argv[1]
    
    try:
        config = get_node_config(node_name)
    except ValueError as e:
        print(f"Error: {e}")
        print("\nAvailable nodes:")
        from shared_config import CHORD_NODES
        for name in CHORD_NODES.keys():
            print(f"  - {name}")
        sys.exit(1)
    
    # Create node
    node = ChordNodeNATNetwork(node_name)
    
    # Determine if this is the bootstrap node
    is_bootstrap = (config['host_ip'] == BOOTSTRAP_NODE['ip'] and 
                   config['host_port'] == BOOTSTRAP_NODE['port'])
    
    # Use context manager
    try:
        with node:
            if is_bootstrap:
                node._join(None)
            else:
                node._join(BOOTSTRAP_NODE)
            
            node.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        raise
        
    # if is_bootstrap:
        # print(f">>> This is the BOOTSTRAP node <<<\n")
        # node._join(None)
    # else:
        # print(f">>> Joining via bootstrap node {BOOTSTRAP_NODE['ip']}:{BOOTSTRAP_NODE['port']} <<<\n")
        # node._join(BOOTSTRAP_NODE)
    
    # # Run the node
    # try:
        # node.run()
    # except KeyboardInterrupt:
        # print(f"\nNode {node_name} shutting down...")
        # node.stop()


if __name__ == "__main__":
    main()