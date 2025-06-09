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
from common.logger import get_logger

class PasswordCrackingWorker:
    def __init__(self):
        self.worker_id = f"worker_{socket.gethostname()}_{uuid.uuid4().hex[:8]}"
        self.master_url = MASTER_URL
        self.running = True
        self.logger = get_logger(f"Worker-{self.worker_id[-8:]}")
        self.tasks_completed = 0
        self.passwords_cracked = 0
        
    def register_with_master(self):
        """Register this worker with the master node"""
        try:
            response = requests.post(
                f"{self.master_url}/register_worker",
                json={"worker_id": self.worker_id},
                timeout=5
            )
            if response.status_code == 200:
                self.logger.info(f"✅ Worker {self.worker_id} registered successfully")
                return True
        except Exception as e:
            self.logger.error(f"❌ Failed to register worker: {e}")
        return False
    
    def send_heartbeat(self):
        """Send heartbeat to master with worker stats"""
        try:
            response = requests.post(
                f"{self.master_url}/heartbeat",
                json={
                    "worker_id": self.worker_id,
                    "tasks_completed": self.tasks_completed,
                    "passwords_cracked": self.passwords_cracked,
                    "status": "active"
                },
                timeout=5
            )
            if response.status_code == 200:
                self.logger.debug(f"💓 Heartbeat sent - Tasks: {self.tasks_completed}, Cracked: {self.passwords_cracked}")
        except Exception as e:
            self.logger.warning(f"💔 Heartbeat failed: {e}")
    
    def hash_password(self, password):
        """Returns SHA-256 hash of the password."""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def crack_password(self, task):
        """Try all candidates to find the correct password for the hash."""
        target_hash = task["target_hash"]
        candidates = task["candidates"]
        task_id = task["task_id"]
        
        self.logger.info(f"🔍 Processing task {task_id} with {len(candidates)} candidates")
        
        for i, password in enumerate(candidates):
            if self.hash_password(password) == target_hash:
                self.logger.info(f"🎯 SUCCESS! Found password '{password}' for task {task_id} (candidate {i+1}/{len(candidates)})")
                self.passwords_cracked += 1
                return password
            
            # Log progress every 100 attempts for long tasks
            if (i + 1) % 100 == 0:
                progress = ((i + 1) / len(candidates)) * 100
                self.logger.debug(f"⏳ Task {task_id} progress: {progress:.1f}% ({i+1}/{len(candidates)})")
        
        self.logger.info(f"❌ No match found for task {task_id} after checking {len(candidates)} candidates")
        return None
    
    def fetch_and_crack(self):
        """Main worker loop with enhanced error handling"""
        self.logger.info(f"🚀 Worker {self.worker_id} started and ready for tasks")
        
        if not self.register_with_master():
            self.logger.error("❌ Failed to register with master, exiting...")
            return
        
        last_heartbeat = time.time()
        consecutive_failures = 0
        
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
                    self.logger.warning(f"⚠️ Failed to fetch task (status: {response.status_code})")
                    time.sleep(TASK_FETCH_INTERVAL)
                    continue
                    
                task_data = response.json()
                if task_data.get("status") == "no_tasks":
                    if consecutive_failures == 0:  # Only log first occurrence
                        self.logger.info("😴 No tasks available, waiting...")
                    consecutive_failures += 1
                    time.sleep(TASK_FETCH_INTERVAL)
                    continue
                
                consecutive_failures = 0  # Reset failure counter
                
                # Process the task
                start_time = time.time()
                cracked_password = self.crack_password(task_data)
                processing_time = time.time() - start_time
                
                result = {
                    "task_id": task_data["task_id"],
                    "cracked_password": cracked_password,
                    "worker_id": self.worker_id,
                    "processing_time": processing_time
                }
                
                # Submit result to master
                res = requests.post(
                    f"{self.master_url}/submit_result",
                    json=result,
                    timeout=10
                )
                
                if res.status_code == 200:
                    self.tasks_completed += 1
                    if cracked_password:
                        self.logger.info(f"✅ Task {task_data['task_id']} completed successfully in {processing_time:.2f}s")
                    else:
                        self.logger.info(f"✅ Task {task_data['task_id']} completed (no match) in {processing_time:.2f}s")
                else:
                    self.logger.error(f"❌ Failed to submit result: {res.text}")

            except requests.exceptions.ConnectionError:
                self.logger.error("🔌 Connection lost to master server")
                time.sleep(TASK_FETCH_INTERVAL * 2)
            except requests.exceptions.Timeout:
                self.logger.warning("⏰ Request timeout, retrying...")
                time.sleep(TASK_FETCH_INTERVAL)
            except Exception as e:
                self.logger.error(f"💥 Unexpected error: {e}")
                time.sleep(TASK_FETCH_INTERVAL)

if __name__ == "__main__":
    worker = PasswordCrackingWorker()
    try:
        worker.fetch_and_crack()
    except KeyboardInterrupt:
        worker.logger.info("👋 Worker shutting down gracefully...")
        worker.running = False