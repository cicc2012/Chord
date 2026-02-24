# shared_config.py
"""
Shared Configuration for Chord Ring
This file must be IDENTICAL on all hosts!
Sync via Git, Dropbox, scp, or other method.

IMPORTANT: Update host_ip values with your actual host IPs!
"""

# ==============================================================================
# NODE CONFIGURATION
# Update host_ip values with your actual host machine IPs on the network
# ==============================================================================

CHORD_NODES = {
    # Host 1 nodes
    "node1": {
        "host_machine": "Host1",
        "host_ip": "10.34.11.223",      # ← UPDATE with Host 1's actual IP
        "host_port": 5001,
        "vm_internal_ip": "10.0.2.111",
        "vm_internal_port": 5000
    },
    "node2": {
        "host_machine": "Host1",
        "host_ip": "10.34.11.223",      # ← Same as node1 (same host)
        "host_port": 5002,
        "vm_internal_ip": "10.0.2.112",
        "vm_internal_port": 5000
    },
    
    #Host 2 nodes
    "node3": {
        "host_machine": "Host2",
        "host_ip": "10.34.11.180",      # ← UPDATE with Host 2's actual IP
        "host_port": 5003,
        "vm_internal_ip": "10.0.2.114",    # Can reuse (different host)
        "vm_internal_port": 5000
    }
}

# Bootstrap node (first node to start)
BOOTSTRAP_NODE = {
    "ip": CHORD_NODES["node1"]["host_ip"],
    "port": CHORD_NODES["node1"]["host_port"]
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_node_config(node_name):
    """
    Get configuration for a specific node
    
    Args:
        node_name: Node identifier (e.g., "node1")
    
    Returns:
        dict: Node configuration
    
    Raises:
        ValueError: If node_name not found
    """
    if node_name not in CHORD_NODES:
        raise ValueError(f"Unknown node: {node_name}. Available: {list(CHORD_NODES.keys())}")
    return CHORD_NODES[node_name]


def get_all_nodes():
    """
    Get list of all node addresses (external/public)
    Useful for client connections and testing
    
    Returns:
        list: List of dicts with 'ip' and 'port' keys
    """
    return [
        {
            "ip": cfg["host_ip"],
            "port": cfg["host_port"],
            "name": name
        }
        for name, cfg in CHORD_NODES.items()
    ]


def get_nodes_on_host(host_ip):
    """
    Get all nodes running on a specific host
    
    Args:
        host_ip: IP address of the host machine
    
    Returns:
        list: List of node names on that host
    """
    return [
        name for name, cfg in CHORD_NODES.items()
        if cfg["host_ip"] == host_ip
    ]


def get_bootstrap_node():
    """
    Get bootstrap node configuration
    
    Returns:
        dict: Bootstrap node address
    """
    return BOOTSTRAP_NODE


def print_config_summary():
    """Print a summary of the configuration"""
    print("\n" + "="*70)
    print("CHORD RING CONFIGURATION SUMMARY")
    print("="*70)
    
    # Group by host
    hosts = {}
    for name, cfg in CHORD_NODES.items():
        host = cfg["host_ip"]
        if host not in hosts:
            hosts[host] = []
        hosts[host].append((name, cfg))
    
    for host_ip, nodes in hosts.items():
        print(f"\nHost: {host_ip}")
        print(f"  Machine: {nodes[0][1]['host_machine']}")
        print(f"  Nodes:")
        for name, cfg in nodes:
            bootstrap_marker = " (BOOTSTRAP)" if (cfg['host_ip'] == BOOTSTRAP_NODE['ip'] and 
                                                   cfg['host_port'] == BOOTSTRAP_NODE['port']) else ""
            print(f"    - {name}: {cfg['host_ip']}:{cfg['host_port']}{bootstrap_marker}")
    
    print(f"\nTotal Nodes: {len(CHORD_NODES)}")
    print(f"Total Hosts: {len(hosts)}")
    print(f"Bootstrap Node: {BOOTSTRAP_NODE['ip']}:{BOOTSTRAP_NODE['port']}")
    print("="*70 + "\n")


if __name__ == "__main__":
    # When run directly, print configuration summary
    print_config_summary()
    
    # Validate configuration
    print("Validating configuration...")
    
    # Check for port conflicts
    ports_per_host = {}
    for name, cfg in CHORD_NODES.items():
        key = cfg['host_ip']
        if key not in ports_per_host:
            ports_per_host[key] = []
        ports_per_host[key].append(cfg['host_port'])
    
    conflicts = False
    for host, ports in ports_per_host.items():
        if len(ports) != len(set(ports)):
            print(f"   ERROR: Port conflict on host {host}")
            conflicts = True
    
    if not conflicts:
        print("   No port conflicts")
    
    # Check bootstrap node exists
    bootstrap_found = False
    for cfg in CHORD_NODES.values():
        if cfg['host_ip'] == BOOTSTRAP_NODE['ip'] and cfg['host_port'] == BOOTSTRAP_NODE['port']:
            bootstrap_found = True
            break
    
    if bootstrap_found:
        print("   Bootstrap node is valid")
    else:
        print("   ERROR: Bootstrap node not found in CHORD_NODES")
    
    print("\n Configuration validated\n")