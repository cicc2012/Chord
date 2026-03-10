# test_nat_network.py
import requests
import sys
from shared_config import CHORD_NODES

def test_connectivity():
    """Test that all nodes are reachable"""
    print("="*60)
    print("NAT NETWORK CONNECTIVITY TEST")
    print("="*60)
    
    all_ok = True
    
    for node_name, config in CHORD_NODES.items():
        url = f"http://{config['host_ip']}:{config['host_port']}/health"
        print(f"\nTesting {node_name}: {url}")
        
        try:
            resp = requests.get(url, timeout=2)
            data = resp.json()
            print(f"  Status: {data.get('status')}")
            print(f"  Node ID: {data.get('node_id')}")
            print(f"  Uptime: {data.get('uptime', 0):.1f}s")
        except requests.exceptions.ConnectionError:
            print(f"  Connection failed - is node running?")
            all_ok = False
        except Exception as e:
            print(f"  Error: {e}")
            all_ok = False
    
    return all_ok

def test_ring_formation():
    """Test that nodes have formed a ring"""
    print("\n" + "="*60)
    print("CHORD RING FORMATION TEST")
    print("="*60)
    
    for node_name, config in CHORD_NODES.items():
        url = f"http://{config['host_ip']}:{config['host_port']}/get_info"
        
        try:
            resp = requests.get(url, timeout=2)
            info = resp.json()
            
            print(f"\n{node_name} (ID: {info['id']})")
            print(f"  Successor: {info['successor']['id'] if info['successor'] else 'None'}")
            print(f"  Predecessor: {info['predecessor']['id'] if info['predecessor'] else 'None'}")
            print(f"  Keys stored: {len(info['data_keys'])}")
        except Exception as e:
            print(f"\n{node_name}: Error - {e}")

if __name__ == "__main__":
    print("Make sure all nodes are running!\n")
    input("Press Enter to start tests...")
    
    if test_connectivity():
        print("\n All nodes are reachable")
        print("\nWaiting 10 seconds for stabilization...")
        import time
        time.sleep(10)
        test_ring_formation()
    else:
        print("\n Some nodes are not reachable")
        print("Check:")
        print("  1. VMs are running: node status")
        print("  2. Nodes are started: check logs")
        print("  3. Firewall allows port 500X")
        sys.exit(1)