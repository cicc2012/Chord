# Collaborative Document Metadata Store
Here is an overview of building a Collaborative Document Metadata Store using Chord ring DHT (Distributed Hash Table) on VirtualBox VMs.

The Chord Ring will store document metadata (owner, permissions, version info, etc). Then we will simulate multiple "users" (client programs) that can create/query documents, to demonstrate how Chord can handle concurrent access.

Key features to demonstrate:
- Consistent Hashing: Show how documents are distributed
- Scalability: Add/remove nodes dynamically
- Load Balancing: Show even distribution of data
- Lookup Efficiency: Demonstrate O(log N) lookups


## Big Picture Architecture
We need 3-4 VMs in the same LAN to build such a Chord ring, to support metadata lookup. 

The metadata will be saved on the VMs. We can build a storage web service for the users to interact with the metadata on the VMs. The implementation of the web service can use Chord ring functionalities to fundamentally perform low level operations on the VM level storage. 

NAT network can be used on school network to enable different types of connections, e.g., among VMs, between VM and host/LAN, etc. The architecture for such a deployment can be illustrated later in [multi-host deployment section](#multi-host-deployment-architecture) and [port forwarding over NAT network](#how-nat-network-solves-multi-host). 

The overall architecture can be illustrated as below:

```
┌─────────────────────────────────────────────────────────┐
│              Client Application Layer                   │
│  (Document operations: create, share, query metadata)   │
└────────────┬────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────┐
│               Metadata Storage Layer                    │
│  Key: hash(doc_id) → Value: {metadata JSON}             │
└────────────┬────────────────────────────────────────────┘
             |
┌────────────▼────────────────────────────────────────────┐
│              Chord Ring (VirtualBox VMs)                │
│  ┌──────┐       ┌──────┐      ┌──────┐       ┌──────┐   │
│  │Node 1│       │Node 2│      │Node 3│       │Node 4│   │
│  │ ID:5 │       │ID:15 │      │ID:30 │       │ID:50 │   │
│  └───┬──┘       └───┬──┘      └───┬──┘       └───┬──┘   │
│      │              │             │              │      │
│      └──────────────┴─────────────┴──────────────┘      │
│           (Finger tables for O(log N) lookup)           │
└────────────┬────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────┐
│                    Network Layer (NAT Network)          │
│  Multi-Host Support | Port Forwarding | School Network  │
└─────────────────────────────────────────────────────────┘
```

## Multi-Host Deployment Architecture

To simulate a fully distributed storage, we will build a multi-host environment: VMs can be scattered over these hosts. In the following deployment architecture, we can have 2-3 hosts in the same LAN. 

```
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│   Host Machine 1    │      │   Host Machine 2    │      │   Host Machine 3    │
│  (Your Laptop)      │      │  (Friend's Laptop)  │      │  (Lab Computer)     │
├─────────────────────┤      ├─────────────────────┤      ├─────────────────────┤
│      host 1         │      │      host 2         │      │      host 3         │
│ IP: 192.168.1.101   │      │ IP: 192.168.1.102   │      │ IP: 192.168.1.103   │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
         │                            │                            │
         └────────────────────────────┴────────────────────────────┘
                        Local Network (192.168.1.0/24)
                        or Internet (Public IPs)
```		
			
## How NAT Network Solves Multi-Host
We need to use 3-4 VMs, and we will assign them to 2-3 hosts. The following diagram can depict the layout of the network design. 
```
Host 1 (Your Laptop - 192.168.1.100)          Host 2 (Friend's - 192.168.1.101)
┌────────────────────────────────┐            ┌────────────────────────────────┐
│ NAT Network: "chord-net"       │            │ NAT Network: "chord-net"       │
│                                │            │                                │
│ VM1: 10.0.2.4:5000 ───┐        │            │ VM3: 10.0.2.4:5000 ───┐        │
│                       ├───┐    │            │                       ├───┐    │
│ VM2: 10.0.2.5:5000 ───┘   │    │            │ VM4: 10.0.2.5:5000 ───┘   │    │
│                           ↓    │            │                           ↓    │
│    Port Forwarding:            │            │    Port Forwarding:            │
│    Host:5001 → VM1:5000        │            │    Host:5003 → VM3:5000        │
│    Host:5002 → VM2:5000        │            │    Host:5004 → VM4:5000        │
└────────────┬───────────────────┘            └────────────┬───────────────────┘
             │                                             │
             └──────────────────┬──────────────────────────┘
                                │
                    School/Home Network
                       192.168.1.0/24
```
Port forwarding can enable communication among VMs across multiple hosts. For example, the communication from host 1 to VM3 can be achieved by using "host 2 IP + host port 5003", which will be forwarded to "VM3 IP + VM3 port 5000". 

---



## File Contents & Execution Steps

### **Step 1: Pre-Deployment Setup**
VM Configuration:

OS: Ubuntu Server 22.04 LTS (minimal installation)
Network:  NAT network with port forwarding
Resources per VM: 1GB RAM, 1 CPU core, 10GB disk
Number of VMs: 3-4 nodes for testing

#### **1.1 Configure Node Addresses**

Once the NAT network and port forwarding are ready, then we will put the network info in our configuration that can shared for other programs. 

The example can be found in the included python file [shared_config.py](shared_config.py). Please change the CHORD_NODES and BOOTSTRAP_NODE according to your network and VM settings.
#### **1.2 Create NAT Network **

Please follow the [previous guide for settings of port forwarding](https://github.com/cicc2012/vbox-port-forward). 

Previously the demo shows how to perform port forward by using
```bash
vboxmanage natnetwork modify --netname NatNetwork --port-forward-4 "ssh1:tcp:[]:1021:[10.0.2.101]:22"
```
Access to our host through port 1021 will be directed to port 22 on the guest.

In this project, we will set extra port forwarding rules, illustrated in the [**How NAT Network Solves Multi-Host:**](## How NAT Network Solves Multi-Host) section above. 

We can define VM1 as node 1, VM2 as node 2, VM3 as node 3, and so on so forth. 

**Please make sure the port forwarding rules are consistent with the configuration in [shared_config.py](shared_config.py).**


**Key Points:**
- Update `host_ip` with actual host IPs on your network
- Keep `vm_internal_ip` as your NAT Network addresses
- Nodes: VM1 - node 1, VM2 - node 2, VM3 - node 3, ...
- Host Ports: 5001, 5002, 5003... 
- VM Ports: 5000 

---


### **Step 2: Deploy Chord Nodes**

For an easy implementation, we can have the following key features:
- Consistent Hashing: SHA-1 hash → m-bit identifier space (default m=8, 0-255)
- Finger Table: O(log N) lookup optimization
- Stabilization: Periodic maintenance for correctness
- Successor/Predecessor: Maintain ring structure

#### 2.1 Copy Files to VMs
For the deployment of the project, we need to have the following files copied to each VM:
```python
# List of files to copy
FILES=(
    "shared_config.py"
    "chord_node.py"
    "chord_node_nat_network.py"
    "document_service.py"
	"requirements.txt"
)
```

#### **2.2 Start Chord Nodes**
On **each VM**, run the following command to install prerequisites:
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip
pip3 install -r requirements.txt
```
We assume node 1 is the bootstrap node, and we need to start the deployment on this node. In the terminal of node 1, let's deploy the chord node by:
```bash
python3 chord_node_nat_network.py node1 > node1.log 2>&1
```
This will run the node1 silently without cluttering the terminal. Change node1 accordingly for other VM.

**Key Points:**
- Start node1 FIRST (bootstrap node)
- Wait 5 seconds before starting others
- Nodes join via node1's address
- Check logs for errors

---

### **Step 3: Verify Deployment**

**Network Connectivity Test**

Execute this in the terminal of any host or machine in the same LAN:
```bash
python3 test_nat_network.py
```

**Output should be similar as:**
```
NAT NETWORK CONNECTIVITY TEST
============================================================

Testing node1: http://192.168.1.100:5001/health
   Status: healthy
   Node ID: 42
   Uptime: 15.3s

Testing node2: http://192.168.1.100:5002/health
   Status: healthy
   Node ID: 128
   Uptime: 10.1s

... (similar for node3, node4)

 All nodes are reachable

Waiting 10 seconds for stabilization...

CHORD RING FORMATION TEST
============================================================

node1 (ID: 42)
  Successor: 128
  Predecessor: 200
  Keys stored: 0

node2 (ID: 128)
  Successor: 180
  Predecessor: 42
  Keys stored: 0

...
```

---

### **Step 4: Run Some Tests**

Execute this in the terminal of any host or machine in the same LAN:
```bash
python3 test_chord_comprehensive.py
```
**Expected Output:**
```
=== Testing Data Correctness ===
Storing 20 documents...
Verifying document placement...
 Correct placements: 20/20
 Data integrity: 20/20 documents match

=== Testing QPS Performance (10s) ===
Measuring WRITE QPS...
  Write QPS: 127.34
  Avg Write Latency: 15.23 ms
  P95 Write Latency: 28.45 ms
  P99 Write Latency: 42.12 ms

Measuring READ QPS...
  Read QPS: 283.67
  Avg Read Latency: 8.91 ms
  P95 Read Latency: 18.34 ms
  P99 Read Latency: 25.78 ms

Measuring MIXED QPS (70% read, 30% write)...
  Mixed QPS: 215.43

=== Testing Load Distribution ===
Storing 100 documents...

Data distribution:
  Node  42:  23 docs ███████████
  Node 128:  19 docs █████████
  Node 180:  26 docs █████████████
  Node 200:  32 docs ████████████████

Statistics:
  Average: 25.00 docs/node
  Max: 32 docs
  Min: 19 docs
  Std Dev: 5.12
  Balance Ratio: 0.59

=== Testing Concurrent Correctness (5 threads, 20 ops each) ===
Completed in 8.45 seconds
  Total operations: 200
  Throughput: 23.67 ops/sec
  Successful writes: 100
  Successful reads: 100
  Failed operations: 0
  Data mismatches: 0
  Correctness rate: 100.00%

============================================================
SUMMARY
============================================================
Data Correctness: 100.0%
Data Integrity: 100.0%
Write QPS: 127.34
Read QPS: 283.67
Load Balance: 0.59
Concurrent Correctness: 100.0%

 Full report saved to test_report.json
```

---

## Appendix A: File Set in This Demo

### **Core Files (Must Have)**

| File | Purpose | Lines | Key Points |
|------|---------|-------|------------|
| `shared_config.py` | Node addresses & configuration | ~50 | **Sync across all hosts!** Define all node IPs/ports here |
| `chord_node.py` | Base Chord DHT implementation | ~400 | Core algorithm: hashing, routing, stabilization |
| `chord_node_nat_network.py` | NAT Network adapter for multi-host | ~100 | Handles internal ↔ external address translation |
| `document_service.py` | Document metadata CRUD operations | ~150 | Application layer on top of Chord |
| `requirements.txt` | Python dependencies | ~5 | Install on each VM |

### **Testing & Deployment Files**

| File | Purpose | Lines | Key Points |
|------|---------|-------|------------|
| `test_chord_comprehensive.py` | Full test suite with QPS & correctness | ~500 | Run after all nodes are up |
| `test_nat_network.py` | Network connectivity verification | ~80 | Run first to verify setup |


---
## Appendix B: Explanations of the Files

### B.1 shared_config.py

This is the shared config about the VMs with NAT network and port forwarding. It will be copied to all VMs, and serve as the single source of truth, so that there will be no duplicate IP/port definitions, easy to add/remove nodes, consistent across all test scripts, and less error-prone. 

Just in case you want to use it, you can act like:
```python
from shared_config import get_all_nodes
nodes = get_all_nodes()
```

### B.2 chord_node.py
This file implement the basic ideas about how to maintain a Chord Ring.

```python
class ChordNode:
    - id: int                    # Position in ring (0-255)
    - ip: str                    # Internal IP (10.0.2.x)
    - port: int                  # Internal port (5000)
    - public_ip: str             # External IP (host IP)
    - public_port: int           # External port (forwarded)
    - successor: dict            # Next node in ring
    - predecessor: dict          # Previous node in ring
    - finger_table: list         # Routing table (m entries)
    - data: dict                 # Local key-value storage of the metadata
```

Aligned with our lecture notes, node lookup (O(log N)) can be illustrated as:
```
Ring: N10 → N30 → N50 → N80 → N120 → N200 → N10

Query: Find successor of key=100

N10 (finger table):
  [0] → N30   (N10 + 2^0 = N11 → successor = N30)
  [1] → N30   (N10 + 2^1 = N12 → successor = N30)
  [2] → N30   (N10 + 2^2 = N14 → successor = N30)
  [3] → N50   (N10 + 2^3 = N18 → successor = N50)
  [4] → N50   (N10 + 2^4 = N26 → successor = N50)
  [5] → N80   (N10 + 2^5 = N42 → successor = N80)
  [6] → N120  (N10 + 2^6 = N74 → successor = N120)
  [7] → N200  (N10 + 2^7 = N138 → successor = N200)

Lookup path: N10 → N80 (jump to closest) → N120 (found!)
```

**stabilization** is the mechanism that maintains correct successor/predecessor pointers as nodes join and leave. The basic idea is:
```
    Periodically verify and fix successor/predecessor pointers
    
    Algorithm:
    1. Ask successor: "Who is YOUR predecessor?"
    2. If that node is between me and my successor, it should be my new successor
    3. Notify my successor that I exist (so it can update its predecessor)
```

If we don't have stabilization, we can meet this situation:
```
Initial state:  N10 → N20 → N30 → N10

New node N15 joins:
- N15 finds its successor should be N20
- But N10 doesn't know about N15 yet!
- N10 still points to N20 as successor

Without stabilization:
N10 → N20 → N30 → N10    (N15 is isolated!)
N15 → N20
```

To fix this problem, we can have stabilization:
```
T=0: Initial ring
    N10 → N30
    N10 ← N30

T=1: N20 joins, finds successor = N30
    N10 → N30
    N10 ← N30
    N20 → N30 (isolated)

T=2: N30's stabilize() runs
    - N30 asks successor (N10): who is your predecessor?
    - N10 replies: "My predecessor is N30" (pointing to self)
    - N30's successor is still N10 (no change)
    - N30 notifies N10: "I am your predecessor"
    - N10 updates: predecessor = N30 

T=3: N10's stabilize() runs
    - N10 asks successor (N30): who is your predecessor?
    - N30 replies: "My predecessor is N10"
    - N10's successor is still N30 (no change)
    - But N10 doesn't know about N20 yet!

T=4: N20's stabilize() runs
    - N20 asks successor (N30): who is your predecessor?
    - N30 replies: "My predecessor is N10"
    - N20 checks: Is N10 between me(20) and my successor(30)?
    - No! N10 < N20, so no change
    - N20 notifies N30: "I am your predecessor"
    - N30 updates: predecessor = N20 

T=5: N10's stabilize() runs again
    - N10 asks successor (N30): who is your predecessor?
    - N30 replies: "My predecessor is N20"
    - N10 checks: Is N20 between me(10) and my successor(30)?
    - YES! 10 < 20 < 30
    - N10 updates: successor = N20 
    - N10 notifies N20: "I am your predecessor"
    - N20 updates: predecessor = N10 

T=6: Stabilized!
    N10 → N20 → N30 → N10
    N10 ← N20 ← N30 ← N10
```

### B.3 chord_node_nat_network.py
This is the address translation layer. Because of the NAT network for a safer on-campus networking environment, we need to use port forwarding to enable all types of connections among VMs, host, and LAN. With port forwarding, the access to each VM need to involve the external IP/port and internal IP/port, so we need this layer for manage them correctly: VMs have internal IPs but must be reached via external (host) IPs, in such dual-address system, which is common in production environment.

### B.4 document_service.py
The document data model can be defined as:
```python
document_metadata = {
    "doc_id": "uuid-1234",
    "title": "Project Proposal",
    "owner": "alice",
    "created_at": "2024-02-17T10:30:00Z",
    "modified_at": "2024-02-17T15:45:00Z",
    "content_location": "/docs/proposal.pdf",
    "permissions": {
        "alice": "owner",
        "bob": "read",
        "charlie": "write"
    },
    "version": 2,
    "tags": ["important", "Q1-2024"]
}

# Stored in Chord with:
# key = doc_id
# value = JSON.stringify(metadata)
# Responsible node = successor(hash(doc_id))
```

The basic operations can be explained as such:
```bash
# Create document
doc_id = create_document(owner="alice", title="Report")
→ hash(doc_id) = 142
→ Store at successor(142) = Node 200

# Retrieve document
metadata = get_document_metadata(doc_id)
→ hash(doc_id) = 142
→ Route to successor(142) = Node 200
→ Return metadata

# Share document
share_document(doc_id, owner="alice", target="bob", permission="read")
→ Retrieve metadata
→ Update permissions["bob"] = "read"
→ Store updated metadata

# Update document
update_document(doc_id, user="alice", updates={"tags": ["urgent"]})
→ Retrieve metadata
→ Check permissions (alice is owner)
→ Apply updates
→ Increment version
→ Store updated metadata
```

These operations are supported by REST web services. Here is a brief view of the REST API Design - Comprehensive Table:

| **Category** | **Endpoint** | **Method** | **Request Body** | **Response** | **Description** |
|-------------|-------------|----------|-----------------|-------------|----------------|
| **Node Management** | `/join` | POST | `{"known_node": {"ip": "...", "port": ...}}` | `{"status": "joined", "node_id": 42}` | Join Chord ring via bootstrap node |
| | `/get_info` | GET | - | `{"id": 42, "ip": "...", "successor": {...}, "predecessor": {...}, "finger_table": [...], "data_keys": [...]}` | Get node status and topology info |
| | `/get_predecessor` | GET | - | `{"id": 42, "ip": "...", "port": 5000}` or `null` | Get node's predecessor |
| | `/notify` | POST | `{"id": 42, "ip": "...", "port": 5000}` | `{"status": "ok"}` | Notify node of potential predecessor |
| **Chord Routing** | `/find_successor` | POST | `{"id": 150}` | `{"id": 200, "ip": "...", "port": 5000}` | Find successor node for given ID |
| | `/closest_preceding_finger` | POST | `{"id": 150}` | `{"id": 120, "ip": "...", "port": 5000}` | Find closest preceding finger for ID |
| **Data Operations** | `/store` | POST | `{"key": "doc_123", "value": "..."}` | `{"status": "stored", "node": 42}` | Store key-value pair (routes to responsible node) |
| | `/retrieve` | POST | `{"key": "doc_123"}` | `{"value": "...", "node": 42}` | Retrieve value by key |
| | `/delete` | POST | `{"key": "doc_123"}` | `{"status": "deleted", "node": 42}` | Delete key-value pair |
| | `/get_keys` | GET | - | `{"keys": ["doc_1", "doc_2"]}` | List all keys stored on this node |
| **Document Service** | `/document/create` | POST | `{"owner": "alice", "title": "...", "content_location": "..."}` | `{"doc_id": "uuid", "status": "created"}` | Create document metadata |
| | `/document/get` | GET | `?doc_id=uuid` | `{"doc_id": "...", "title": "...", "owner": "...", ...}` | Get document metadata |
| | `/document/update` | PUT | `{"doc_id": "uuid", "user": "alice", "updates": {...}}` | `{"status": "updated", "version": 2}` | Update document metadata |
| | `/document/share` | POST | `{"doc_id": "uuid", "owner": "alice", "target_user": "bob", "permission": "read"}` | `{"status": "shared"}` | Share document with user |
| | `/document/list` | GET | `?user=alice` | `{"documents": [...]}` | List user's documents |
| | `/document/delete` | DELETE | `{"doc_id": "uuid", "user": "alice"}` | `{"status": "deleted"}` | Delete document |
| **Monitoring** | `/health` | GET | - | `{"status": "healthy", "uptime": 3600}` | Health check endpoint |
| | `/metrics` | GET | - | `{"requests_count": 1000, "avg_latency_ms": 15, "stored_items": 50}` | Performance metrics |
| | `/ring_state` | GET | - | `{"nodes": [...], "total_keys": 200}` | Get entire ring state |
| **Maintenance** | `/stabilize` | POST | - | `{"status": "stabilized"}` | Trigger stabilization manually |
| | `/fix_fingers` | POST | - | `{"status": "fingers_fixed"}` | Trigger finger table fix manually |
| | `/transfer_keys` | POST | `{"target_node": {...}}` | `{"transferred_count": 10}` | Transfer keys to target node |

### B.5 requirements.txt
This file contains the dependencies to support this project.

## Appendix C: Flask
Flask is a Python Flask web server that runs in the foreground (not a system service) to support the REST web services above, by handling the HTTP requests. It is simple  - no service configuration needed.

Here it's running in blocked mode: to terminate, just press Ctrl+C on your keyboard.

The general components of the program on each VM are:
```
┌────────────────────────────────────────────────────────┐
│                    VM: chord-node1                     │
├────────────────────────────────────────────────────────┤
│                                                        │
│  $ python3 chord_node_nat_network.py node1             │
│                                                        │
│  This single Python process contains:                  │
│  ┌────────────────────────────────────────────────┐    │
│  │  Flask Web Server (HTTP Server)                │    │
│  │  Listens on: 0.0.0.0:5000                      │    │
│  │  Handles: /store, /retrieve, /health, etc.     │    │
│  └────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────┐    │
│  │  Chord DHT Logic                               │    │
│  │  - Consistent hashing                          │    │
│  │  - Finger table                                │    │
│  │  - Successor/predecessor pointers              │    │
│  └────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────┐    │
│  │  Background Threads (Daemon)                   │    │
│  │  - Stabilization loop (every 5s)               │    │
│  │  - Fix fingers loop (every 10s)                │    │
│  └────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────┐    │
│  │  Local Data Storage                            │    │
│  │  - In-memory dict: self.data = {}              │    │
│  │  - Keys and values stored here                 │    │
│  └────────────────────────────────────────────────┘    │
│                                                        │
│  Process runs CONTINUOUSLY until killed                │
└────────────────────────────────────────────────────────┘
```
And when it is running, the whole process is:
```
   ┌─────────────────────────────────────────────┐
   │ chord_node_nat_network.py                   │
   │                                             │
   │ main()                                      │
   │   ↓                                         │
   │ node = ChordNodeNATNetwork("node1")         │
   │   ↓                                         │
   │ ChordNode.__init__()                        │
   │   ├─ self.app = Flask(__name__)             │ ← Creates web server
   │   ├─ self._setup_routes()                   │ ← Registers endpoints
   │   └─ self.data = {}                         │ ← Creates storage
   │                                             │
   │ node._join(BOOTSTRAP_NODE)                  │
   │   └─ self._start_stabilization()            │ ← Starts background threads
   │                                             │
   │ node.run()                                  │
   │   └─ self.app.run(host='0.0.0.0', port=5000)│ ← BLOCKS HERE
   └─────────────────────────────────────────────┘
                    │
                    ├─ Thread 1: Flask web server
                    │    Handles HTTP requests on port 5000
                    │    Runs forever
                    │
                    ├─ Thread 2: Stabilization loop
                    │    Every 5 seconds: _stabilize()
                    │    Runs forever
                    │
                    └─ Thread 3: Fix fingers loop
                         Every 10 seconds: _fix_fingers()
                         Runs forever

```