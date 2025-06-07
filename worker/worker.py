import hashlib
import requests
import time
import uuid
import socket
import sys
import os

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.config import MASTER_URL, TASK_FETCH_INTERVAL

class PasswordCrackingWorker:
    def __init__(self):
        self.worker_id = f"worker_{socket.gethostname()}_{uuid.uuid4().hex[:8]}"
        self.master_url = MASTER_URL
        self.running = True
        
    def register_with_master(self):
        """Register this worker with the master node"""
        try:
            response = requests.post(
                f"{self.master_url}/register_worker",
                json={"worker_id": self.worker_id},
                timeout=5
            )
            if response.status_code == 200:
                print(f"Worker {self.worker_id} registered successfully")
                return True
        except Exception as e:
            print(f"Failed to register worker: {e}")
        return False
    
    def send_heartbeat(self):
        """Send heartbeat to master"""
        try:
            requests.post(
                f"{self.master_url}/heartbeat",
                json={"worker_id": self.worker_id},
                timeout=5
            )
        except Exception as e:
            print(f"Heartbeat failed: {e}")
    
    def hash_password(self, password):
        """Returns SHA-256 hash of the password."""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def crack_password(self, task):
        """Try all candidates to find the correct password for the hash."""
        target_hash = task["target_hash"]
        candidates = task["candidates"]
        
        for password in candidates:
            if self.hash_password(password) == target_hash:
                return password
        return None
    
    def fetch_and_crack(self):
        """Main worker loop"""
        print(f"Worker {self.worker_id} started...")
        
        if not self.register_with_master():
            print("Failed to register with master, exiting...")
            return
        
        last_heartbeat = time.time()
        
        while self.running:
            try:
                # Send heartbeat every 30 seconds
                if time.time() - last_heartbeat > 30:
                    self.send_heartbeat()
                    last_heartbeat = time.time()
                
                # Fetch task from master
                response = requests.get(
                    f"{self.master_url}/get_task",
                    params={"worker_id": self.worker_id},
                    timeout=10
                )
                
                if response.status_code != 200:
                    print("Failed to fetch task, sleeping...")
                    time.sleep(TASK_FETCH_INTERVAL)
                    continue
                    
                task_data = response.json()
                if task_data.get("status") == "no_tasks":
                    print("No tasks available, sleeping...")
                    time.sleep(TASK_FETCH_INTERVAL)
                    continue

                print(f"Received task {task_data['task_id']} with {len(task_data['candidates'])} candidates")

                cracked_password = self.crack_password(task_data)
                result = {
                    "task_id": task_data["task_id"],
                    "cracked_password": cracked_password
                }
                
                # Submit result to master
                res = requests.post(
                    f"{self.master_url}/submit_result",
                    json=result,
                    timeout=10
                )
                
                if res.status_code == 200:
                    if cracked_password:
                        print(f"SUCCESS: Found password '{cracked_password}' for task {task_data['task_id']}")
                    else:
                        print(f"No match found for task {task_data['task_id']}")
                else:
                    print(f"Failed to submit result: {res.text}")

            except Exception as e:
                print(f"Error: {e}")
                time.sleep(TASK_FETCH_INTERVAL)

if __name__ == "__main__":
    worker = PasswordCrackingWorker()
    try:
        worker.fetch_and_crack()
    except KeyboardInterrupt:
        print("Worker shutting down...")
        worker.running = False