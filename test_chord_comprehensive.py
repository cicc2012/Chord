# test_chord_comprehensive.py
import requests
import json
import time
import threading
import hashlib
from collections import defaultdict
from datetime import datetime
from shared_config import get_all_nodes

class ComprehensiveChordTester:
    def __init__(self, nodes=None):
        # self.nodes = nodes
        # self.test_results = []
        """
        Initialize tester
        
        Args:
            nodes: List of node dicts. If None, loads from shared_config
        """
        if nodes is None:
            # Load from shared_config automatically
            nodes = get_all_nodes()
            print(f"Loaded {len(nodes)} nodes from shared_config.py")
        
        self.nodes = nodes
        self.test_results = []
    
    def _hash(self, key, m=8):
        """Same hash function as Chord nodes"""
        return int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2 ** m)
    
    def test_data_correctness(self):
        """Verify that data is stored on correct nodes"""
        print("\n=== Testing Data Correctness ===")
        
        # Create test documents
        test_docs = []
        for i in range(20):
            doc_id = f"doc_{i}"
            metadata = {
                "title": f"Document {i}",
                "owner": f"user{i % 5}",
                "created_at": datetime.now().isoformat()
            }
            test_docs.append((doc_id, metadata))
        
        # Store documents
        print("Storing 20 documents...")
        storage_results = {}
        for doc_id, metadata in test_docs:
            node = self.nodes[0]
            resp = requests.post(
                f"http://{node['ip']}:{node['port']}/store",
                json={"key": doc_id, "value": json.dumps(metadata)}
            )
            result = resp.json()
            storage_results[doc_id] = result.get('node')
        
        time.sleep(2)  # Allow stabilization
        
        # Verify each document is on the correct node
        print("\nVerifying document placement...")
        correct_placements = 0
        incorrect_placements = 0
        
        for doc_id, expected_node in storage_results.items():
            # Calculate which node should be responsible
            key_hash = self._hash(doc_id)
            
            # Get actual storage location
            node = self.nodes[0]
            resp = requests.post(
                f"http://{node['ip']}:{node['port']}/retrieve",
                json={"key": doc_id}
            )
            result = resp.json()
            actual_node = result.get('node')
            
            if actual_node == expected_node:
                correct_placements += 1
            else:
                incorrect_placements += 1
                print(f"     {doc_id}: Expected node {expected_node}, got {actual_node}")
        
        print(f"\n Correct placements: {correct_placements}/20")
        print(f" Incorrect placements: {incorrect_placements}/20")
        
        # Verify data integrity
        print("\nVerifying data integrity...")
        integrity_pass = 0
        for doc_id, original_metadata in test_docs:
            node = self.nodes[0]
            resp = requests.post(
                f"http://{node['ip']}:{node['port']}/retrieve",
                json={"key": doc_id}
            )
            result = resp.json()
            retrieved_metadata = json.loads(result.get('value', '{}'))
            
            if retrieved_metadata == original_metadata:
                integrity_pass += 1
            else:
                print(f"     Data mismatch for {doc_id}")
                print(f"     Expected: {original_metadata}")
                print(f"     Got: {retrieved_metadata}")
        
        print(f" Data integrity: {integrity_pass}/20 documents match")
        
        return {
            "correctness": correct_placements / 20,
            "integrity": integrity_pass / 20
        }
    
    def test_qps_performance(self, duration_seconds=10):
        """Measure QPS (Queries Per Second) performance"""
        print(f"\n=== Testing QPS Performance ({duration_seconds}s) ===")
        
        # Pre-populate some data
        print("Populating test data...")
        test_keys = []
        for i in range(100):
            doc_id = f"perf_doc_{i}"
            node = self.nodes[i % len(self.nodes)]
            requests.post(
                f"http://{node['ip']}:{node['port']}/store",
                json={"key": doc_id, "value": f"data_{i}"}
            )
            test_keys.append(doc_id)
        
        time.sleep(2)
        
        # Measure write QPS
        print("\nMeasuring WRITE QPS...")
        write_count = 0
        write_latencies = []
        write_start = time.time()
        
        while time.time() - write_start < duration_seconds:
            doc_id = f"qps_write_{write_count}"
            
            start = time.time()
            node = self.nodes[write_count % len(self.nodes)]
            try:
                requests.post(
                    f"http://{node['ip']}:{node['port']}/store",
                    json={"key": doc_id, "value": f"data_{write_count}"},
                    timeout=2
                )
                latency = (time.time() - start) * 1000  # Convert to ms
                write_latencies.append(latency)
                write_count += 1
            except:
                pass
        
        write_qps = write_count / duration_seconds
        avg_write_latency = sum(write_latencies) / len(write_latencies) if write_latencies else 0
        p95_write_latency = sorted(write_latencies)[int(len(write_latencies) * 0.95)] if write_latencies else 0
        p99_write_latency = sorted(write_latencies)[int(len(write_latencies) * 0.99)] if write_latencies else 0
        
        print(f"  Write QPS: {write_qps:.2f}")
        print(f"  Avg Write Latency: {avg_write_latency:.2f} ms")
        print(f"  P95 Write Latency: {p95_write_latency:.2f} ms")
        print(f"  P99 Write Latency: {p99_write_latency:.2f} ms")
        
        # Measure read QPS
        print("\nMeasuring READ QPS...")
        read_count = 0
        read_latencies = []
        read_start = time.time()
        
        while time.time() - read_start < duration_seconds:
            doc_id = test_keys[read_count % len(test_keys)]
            
            start = time.time()
            node = self.nodes[read_count % len(self.nodes)]
            try:
                requests.post(
                    f"http://{node['ip']}:{node['port']}/retrieve",
                    json={"key": doc_id},
                    timeout=2
                )
                latency = (time.time() - start) * 1000
                read_latencies.append(latency)
                read_count += 1
            except:
                pass
        
        read_qps = read_count / duration_seconds
        avg_read_latency = sum(read_latencies) / len(read_latencies) if read_latencies else 0
        p95_read_latency = sorted(read_latencies)[int(len(read_latencies) * 0.95)] if read_latencies else 0
        p99_read_latency = sorted(read_latencies)[int(len(read_latencies) * 0.99)] if read_latencies else 0
        
        print(f"  Read QPS: {read_qps:.2f}")
        print(f"  Avg Read Latency: {avg_read_latency:.2f} ms")
        print(f"  P95 Read Latency: {p95_read_latency:.2f} ms")
        print(f"  P99 Read Latency: {p99_read_latency:.2f} ms")
        
        # Mixed workload QPS
        print("\nMeasuring MIXED QPS (70% read, 30% write)...")
        mixed_count = 0
        mixed_start = time.time()
        
        while time.time() - mixed_start < duration_seconds:
            import random
            if random.random() < 0.7:  # 70% reads
                doc_id = test_keys[mixed_count % len(test_keys)]
                node = self.nodes[mixed_count % len(self.nodes)]
                try:
                    requests.post(
                        f"http://{node['ip']}:{node['port']}/retrieve",
                        json={"key": doc_id},
                        timeout=2
                    )
                    mixed_count += 1
                except:
                    pass
            else:  # 30% writes
                doc_id = f"mixed_{mixed_count}"
                node = self.nodes[mixed_count % len(self.nodes)]
                try:
                    requests.post(
                        f"http://{node['ip']}:{node['port']}/store",
                        json={"key": doc_id, "value": f"data_{mixed_count}"},
                        timeout=2
                    )
                    mixed_count += 1
                except:
                    pass
        
        mixed_qps = mixed_count / duration_seconds
        print(f"  Mixed QPS: {mixed_qps:.2f}")
        
        return {
            "write_qps": write_qps,
            "read_qps": read_qps,
            "mixed_qps": mixed_qps,
            "avg_write_latency_ms": avg_write_latency,
            "avg_read_latency_ms": avg_read_latency,
            "p95_write_latency_ms": p95_write_latency,
            "p99_write_latency_ms": p99_write_latency,
            "p95_read_latency_ms": p95_read_latency,
            "p99_read_latency_ms": p99_read_latency
        }
    
    def test_load_distribution(self):
        """Verify even distribution of data across nodes"""
        print("\n=== Testing Load Distribution ===")
        
        # Store 100 documents
        print("Storing 100 documents...")
        for i in range(100):
            doc_id = f"dist_doc_{i}"
            node = self.nodes[0]
            requests.post(
                f"http://{node['ip']}:{node['port']}/store",
                json={"key": doc_id, "value": f"data_{i}"}
            )
        
        time.sleep(2)
        
        # Check distribution across nodes
        distribution = {}
        for node in self.nodes:
            resp = requests.get(f"http://{node['ip']}:{node['port']}/get_info")
            info = resp.json()
            distribution[info['id']] = len(info['data_keys'])
        
        print("\nData distribution:")
        for node_id, count in sorted(distribution.items()):
            bar = "█" * (count // 2)
            print(f"  Node {node_id:3d}: {count:3d} docs {bar}")
        
        # Calculate distribution metrics
        counts = list(distribution.values())
        avg_count = sum(counts) / len(counts)
        max_count = max(counts)
        min_count = min(counts)
        std_dev = (sum((c - avg_count) ** 2 for c in counts) / len(counts)) ** 0.5
        
        print(f"\nStatistics:")
        print(f"  Average: {avg_count:.2f} docs/node")
        print(f"  Max: {max_count} docs")
        print(f"  Min: {min_count} docs")
        print(f"  Std Dev: {std_dev:.2f}")
        print(f"  Balance Ratio: {min_count/max_count:.2f} (closer to 1.0 is better)")
        
        return {
            "balance_ratio": min_count / max_count if max_count > 0 else 0,
            "std_dev": std_dev,
            "distribution": distribution
        }
    
    def test_concurrent_correctness(self, num_threads=10, ops_per_thread=50):
        """Test correctness under concurrent operations"""
        print(f"\n=== Testing Concurrent Correctness ({num_threads} threads, {ops_per_thread} ops each) ===")
        
        results = {
            "successful_writes": 0,
            "successful_reads": 0,
            "failed_operations": 0,
            "data_mismatches": 0
        }
        results_lock = threading.Lock()
        written_docs = {}
        written_lock = threading.Lock()
        
        def worker(thread_id):
            for i in range(ops_per_thread):
                doc_id = f"concurrent_{thread_id}_{i}"
                expected_value = f"thread{thread_id}_op{i}_data"
                
                # Write
                try:
                    node = self.nodes[thread_id % len(self.nodes)]
                    resp = requests.post(
                        f"http://{node['ip']}:{node['port']}/store",
                        json={"key": doc_id, "value": expected_value},
                        timeout=2
                    )
                    
                    if resp.status_code == 200:
                        with results_lock:
                            results["successful_writes"] += 1
                        with written_lock:
                            written_docs[doc_id] = expected_value
                except:
                    with results_lock:
                        results["failed_operations"] += 1
                
                # Read back immediately
                try:
                    time.sleep(0.1)  # Small delay
                    node = self.nodes[(thread_id + 1) % len(self.nodes)]
                    resp = requests.post(
                        f"http://{node['ip']}:{node['port']}/retrieve",
                        json={"key": doc_id},
                        timeout=2
                    )
                    
                    if resp.status_code == 200:
                        with results_lock:
                            results["successful_reads"] += 1
                        
                        actual_value = resp.json().get('value')
                        if actual_value != expected_value:
                            with results_lock:
                                results["data_mismatches"] += 1
                            print(f"   Mismatch: {doc_id} expected '{expected_value}', got '{actual_value}'")
                except:
                    with results_lock:
                        results["failed_operations"] += 1
        
        # Run concurrent workers
        threads = []
        start_time = time.time()
        
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        elapsed = time.time() - start_time
        total_ops = num_threads * ops_per_thread * 2  # writes + reads
        
        print(f"\nCompleted in {elapsed:.2f} seconds")
        print(f"  Total operations: {total_ops}")
        print(f"  Throughput: {total_ops/elapsed:.2f} ops/sec")
        print(f"  Successful writes: {results['successful_writes']}")
        print(f"  Successful reads: {results['successful_reads']}")
        print(f"  Failed operations: {results['failed_operations']}")
        print(f"  Data mismatches: {results['data_mismatches']}")
        
        correctness_rate = (results['successful_writes'] + results['successful_reads'] - results['data_mismatches']) / total_ops
        print(f"  Correctness rate: {correctness_rate*100:.2f}%")
        
        return results
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("COMPREHENSIVE TEST REPORT")
        print("="*60)
        
        # Run all tests
        correctness = self.test_data_correctness()
        performance = self.test_qps_performance(duration_seconds=10)
        distribution = self.test_load_distribution()
        concurrency = self.test_concurrent_correctness(num_threads=5, ops_per_thread=20)
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Data Correctness: {correctness['correctness']*100:.1f}%")
        print(f"Data Integrity: {correctness['integrity']*100:.1f}%")
        print(f"Write QPS: {performance['write_qps']:.2f}")
        print(f"Read QPS: {performance['read_qps']:.2f}")
        print(f"Load Balance: {distribution['balance_ratio']:.2f}")
        print(f"Concurrent Correctness: {(1 - concurrency['data_mismatches']/(concurrency['successful_writes']+concurrency['successful_reads']))*100:.1f}%" if concurrency['successful_writes']+concurrency['successful_reads'] > 0 else "N/A")
        
        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "correctness": correctness,
            "performance": performance,
            "distribution": distribution,
            "concurrency": concurrency
        }
        
        with open('test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n Full report saved to test_report.json")

if __name__ == "__main__":
    # Optional: Override with specific nodes (if needed)
    # nodes = [
        # {"ip": "10.34.11.223", "port": 5001},
        # {"ip": "10.34.11.223", "port": 5002},
        # {"ip": "10.34.11.180", "port": 5003},
    # ]
    
    # tester = ComprehensiveChordTester(nodes)
    
    tester = ComprehensiveChordTester()
    tester.generate_report()