from flask import Flask, request, jsonify
import hashlib
from queue import Queue
from threading import Lock
import os
import time
import sys

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.logger import get_logger
from common.config import TASK_BATCH_SIZE, TASK_TIMEOUT, MASTER_HOST, MASTER_PORT

app = Flask(__name__)
logger = get_logger("Master")

task_queue = Queue()
result_list = []
queue_lock = Lock()
target_hashes = []
active_workers = {}  # worker_id: {last_heartbeat, tasks_completed, passwords_cracked, status}
active_tasks = {}    # task_id: {worker_id, timestamp, task_data}
worker_stats = {}    # worker_id: {total_tasks, total_cracked, avg_time}

# Worker registration and health monitoring
@app.route("/register_worker", methods=["POST"])
def register_worker():
    try:
        data = request.json
        worker_id = data.get("worker_id")
        if worker_id:
            active_workers[worker_id] = {
                'last_heartbeat': time.time(),
                'tasks_completed': 0,
                'passwords_cracked': 0,
                'status': 'active',
                'registered_at': time.time()
            }
            worker_stats[worker_id] = {
                'total_tasks': 0,
                'total_cracked': 0,
                'total_time': 0,
                'avg_time': 0
            }
            logger.info(f"👋 Worker {worker_id} registered and ready")
            return jsonify({"status": "success"})
        return jsonify({"status": "failure", "reason": "worker_id required"})
    except Exception as e:
        logger.error(f"❌ Error in register_worker: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    try:
        data = request.json
        worker_id = data.get("worker_id")
        if worker_id:
            if worker_id in active_workers:
                active_workers[worker_id].update({
                    'last_heartbeat': time.time(),
                    'tasks_completed': data.get('tasks_completed', 0),
                    'passwords_cracked': data.get('passwords_cracked', 0),
                    'status': data.get('status', 'active')
                })
            return jsonify({"status": "success"})
        return jsonify({"status": "failure", "reason": "worker_id required"})
    except Exception as e:
        logger.error(f"❌ Error in heartbeat: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

# Enhanced task timeout and retry logic
def check_task_timeouts():
    current_time = time.time()
    expired_tasks = []
    failed_workers = []
    
    # Check for expired tasks
    for task_id, task_info in active_tasks.items():
        if current_time - task_info['timestamp'] > TASK_TIMEOUT:
            expired_tasks.append(task_id)
            worker_id = task_info['worker_id']
            if worker_id not in failed_workers:
                failed_workers.append(worker_id)
    
    # Handle expired tasks
    for task_id in expired_tasks:
        task_info = active_tasks.pop(task_id)
        task_queue.put(task_info['task_data'])  # Re-queue the task
        logger.warning(f"⏰ Task {task_id} timed out from worker {task_info['worker_id']}, re-queued")
    
    # Check for failed workers (no heartbeat for 2 minutes)
    dead_workers = []
    for worker_id, worker_info in active_workers.items():
        if current_time - worker_info['last_heartbeat'] > 120:  # 2 minutes
            dead_workers.append(worker_id)
    
    # Remove dead workers
    for worker_id in dead_workers:
        del active_workers[worker_id]
        logger.error(f"💀 Worker {worker_id} declared dead (no heartbeat for 2+ minutes)")

# Load hashes and prepare tasks (with proper encoding)
def load_hashes(filepath="data/hashes.txt"):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        logger.warning(f"Hash file {filepath} not found, creating sample data")
        return []
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error reading {filepath}: {e}")
        return []

def prepare_tasks(wordlist_path="data/password.txt"):
    global target_hashes
    target_hashes = load_hashes()
    
    if not target_hashes:
        sample_passwords = ["password123", "admin", "123456", "qwerty"]
        target_hashes = [hashlib.sha256(pwd.encode('utf-8')).hexdigest() for pwd in sample_passwords]
        logger.info("Created sample target hashes")
    
    try:
        with open(wordlist_path, 'r', encoding='utf-8') as file:
            passwords = [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        logger.warning(f"Password file {wordlist_path} not found, creating sample data")
        passwords = ["password123", "admin", "123456", "qwerty", "letmein", "welcome"]
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error reading {wordlist_path}: {e}")
        passwords = ["password123", "admin", "123456", "qwerty", "letmein", "welcome"]
    
    task_id = 0
    for target_hash in target_hashes:
        for i in range(0, len(passwords), TASK_BATCH_SIZE):
            batch = passwords[i:i + TASK_BATCH_SIZE]
            task = {
                "task_id": task_id,
                "target_hash": target_hash,
                "candidates": batch
            }
            task_queue.put(task)
            task_id += 1
    
    logger.info(f"Loaded {task_queue.qsize()} tasks into the queue")

@app.route("/get_task", methods=["GET"])
def get_task():
    check_task_timeouts()  # Check for expired tasks
    
    worker_id = request.args.get('worker_id')
    if not worker_id:
        return jsonify({"status": "failure", "reason": "worker_id required"})
    
    with queue_lock:
        if task_queue.empty():
            return jsonify({"status": "no_tasks"})
        
        task = task_queue.get()
        active_tasks[task['task_id']] = {
            'worker_id': worker_id,
            'timestamp': time.time(),
            'task_data': task
        }
        return jsonify(task)

@app.route("/submit_result", methods=["POST"])
def submit_result():
    try:
        data = request.json
        task_id = data.get("task_id")
        cracked_password = data.get("cracked_password")
        worker_id = data.get("worker_id")
        processing_time = data.get("processing_time", 0)
        
        if task_id is not None:
            # Remove from active tasks
            if task_id in active_tasks:
                del active_tasks[task_id]
            
            # Update worker stats
            if worker_id and worker_id in worker_stats:
                stats = worker_stats[worker_id]
                stats['total_tasks'] += 1
                stats['total_time'] += processing_time
                stats['avg_time'] = stats['total_time'] / stats['total_tasks']
                if cracked_password:
                    stats['total_cracked'] += 1
            
            if cracked_password:
                result_list.append((task_id, cracked_password, worker_id, processing_time))
                logger.info(f"🎯 Password cracked! Task {task_id}: '{cracked_password}' by {worker_id} in {processing_time:.2f}s")
            else:
                logger.debug(f"📝 Task {task_id} completed by {worker_id} (no match found)")
            return jsonify({"status": "success"})
        
        return jsonify({"status": "failure", "reason": "invalid input"})
    except Exception as e:
        logger.error(f"❌ Error in submit_result: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

@app.route("/worker_stats", methods=["GET"])
def get_worker_stats():
    """Get detailed worker statistics"""
    try:
        workers_list = []
        current_time = time.time()
        
        for worker_id, worker_info in active_workers.items():
            worker_data = {
                'worker_id': worker_id,
                'status': worker_info['status'],
                'tasks_completed': worker_info['tasks_completed'],
                'passwords_cracked': worker_info['passwords_cracked'],
                'last_heartbeat': worker_info['last_heartbeat'],
                'avg_processing_time': worker_stats.get(worker_id, {}).get('avg_time', 0)
            }
            workers_list.append(worker_data)
        
        return jsonify({"workers": workers_list})
    
    except Exception as e:
        logger.error(f"❌ Error getting worker stats: {e}")
        return jsonify({"workers": []})

# Add to the existing status endpoint
@app.route("/status", methods=["GET"])
def get_status():
    """Enhanced status endpoint with more metrics"""
    try:
        current_time = time.time()
        
        # Count active workers (heartbeat within last 60 seconds)
        active_count = sum(1 for worker_info in active_workers.values() 
                          if current_time - worker_info['last_heartbeat'] < 60)
        
        # Calculate total metrics
        total_completed = sum(worker_info['tasks_completed'] for worker_info in active_workers.values())
        total_cracked = sum(worker_info['passwords_cracked'] for worker_info in active_workers.values())
        
        status_data = {
            "status": "running" if active_count > 0 else "idle",
            "active_workers": active_count,
            "total_workers": len(active_workers),
            "queue_size": task_queue.qsize(),
            "active_tasks": len(active_tasks),
            "completed_tasks": total_completed,
            "passwords_cracked": total_cracked,
            "uptime": current_time - start_time if 'start_time' in globals() else 0
        }
        
        return jsonify(status_data)
    
    except Exception as e:
        logger.error(f"❌ Error getting status: {e}")
        return jsonify({"status": "error", "message": str(e)})

# Add at the top of the file
start_time = time.time()

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "message": "Password Cracking Simulator Master Node",
        "status": "running",
        "endpoints": ["/status", "/results", "/get_task", "/submit_result"]
    })

# New endpoints for GUI support
@app.route("/add_custom_password", methods=["POST"])
def add_custom_password():
    try:
        data = request.json
        password = data.get("password")
        if not password:
            return jsonify({"status": "failure", "reason": "password required"})
        
        # Hash the password and add to target hashes
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        target_hashes.append(password_hash)
        
        # Create tasks for this new password
        create_tasks_for_hash(password_hash)
        
        logger.info(f"Added custom password for cracking (hash: {password_hash[:16]}...)")
        return jsonify({"status": "success", "hash": password_hash})
    except Exception as e:
        logger.error(f"Error in add_custom_password: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

@app.route("/clear_results", methods=["POST"])
def clear_results():
    try:
        global result_list
        result_list = []
        logger.info("Results cleared")
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error in clear_results: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

@app.route("/reset_tasks", methods=["POST"])
def reset_tasks():
    try:
        global task_queue, active_tasks, target_hashes
        with queue_lock:
            # Clear existing tasks
            while not task_queue.empty():
                task_queue.get()
            active_tasks.clear()
            target_hashes.clear()
        
        # Reload default tasks
        prepare_tasks()
        
        logger.info("Tasks reset to default")
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error in reset_tasks: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

@app.route("/load_demo_tasks", methods=["POST"])
def load_demo_tasks():
    """Load demo tasks from GUI"""
    try:
        data = request.json
        tasks = data.get('tasks', [])
        
        if not tasks:
            return jsonify({"status": "failure", "reason": "no tasks provided"})
        
        # Clear existing tasks
        global task_queue, active_tasks, target_hashes
        with queue_lock:
            while not task_queue.empty():
                task_queue.get()
            active_tasks.clear()
            target_hashes.clear()
        
        # Add demo tasks to queue
        task_count = 0
        for task in tasks:
            target_hash = task.get('target_hash')
            candidates = task.get('candidates', [])
            
            if target_hash and candidates:
                target_hashes.append(target_hash)
                
                # Split candidates into batches
                for i in range(0, len(candidates), TASK_BATCH_SIZE):
                    batch = candidates[i:i + TASK_BATCH_SIZE]
                    task_data = {
                        "task_id": task_count,
                        "target_hash": target_hash,
                        "candidates": batch
                    }
                    task_queue.put(task_data)
                    task_count += 1
        
        logger.info(f"📋 Loaded {task_count} demo tasks into queue")
        return jsonify({"status": "success", "tasks_loaded": task_count})
        
    except Exception as e:
        logger.error(f"❌ Error loading demo tasks: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

@app.route("/load_custom_task", methods=["POST"])
def load_custom_task():
    """Load a single custom task from GUI"""
    try:
        data = request.json
        task = data.get('task')
        
        if not task:
            return jsonify({"status": "failure", "reason": "no task provided"})
        
        target_hash = task.get('target_hash')
        candidates = task.get('candidates', [])
        
        if not target_hash or not candidates:
            return jsonify({"status": "failure", "reason": "invalid task data"})
        
        # Add to target hashes if not already present
        global target_hashes
        if target_hash not in target_hashes:
            target_hashes.append(target_hash)
        
        # Split candidates into batches and add to queue
        task_count = 0
        base_task_id = len(active_tasks) + task_queue.qsize()
        
        with queue_lock:
            for i in range(0, len(candidates), TASK_BATCH_SIZE):
                batch = candidates[i:i + TASK_BATCH_SIZE]
                task_data = {
                    "task_id": base_task_id + task_count,
                    "target_hash": target_hash,
                    "candidates": batch
                }
                task_queue.put(task_data)
                task_count += 1
        
        logger.info(f"📋 Loaded custom task with {task_count} batches into queue")
        return jsonify({"status": "success", "tasks_loaded": task_count})
        
    except Exception as e:
        logger.error(f"❌ Error loading custom task: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

def create_tasks_for_hash(target_hash, wordlist_path="data/password.txt"):
    """Create tasks for a specific hash"""
    try:
        with open(wordlist_path, 'r', encoding='utf-8') as file:
            passwords = [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        passwords = ["password123", "admin", "123456", "qwerty", "letmein", "welcome"]
    
    task_id = len(active_tasks) + task_queue.qsize()
    for i in range(0, len(passwords), TASK_BATCH_SIZE):
        batch = passwords[i:i + TASK_BATCH_SIZE]
        task = {
            "task_id": task_id,
            "target_hash": target_hash,
            "candidates": batch
        }
        task_queue.put(task)
        task_id += 1

@app.route("/results", methods=["GET"])
def get_results():
    """Get all cracking results"""
    try:
        results = []
        for task_id, password, worker_id, processing_time in result_list:
            results.append({
                'task_id': task_id,
                'cracked_password': password,
                'worker_id': worker_id,
                'processing_time': processing_time
            })
        
        return jsonify({"results": results})
        
    except Exception as e:
        logger.error(f"❌ Error getting results: {e}")
        return jsonify({"results": []})

if __name__ == "__main__":
    try:
        logger.info("Initializing Password Cracking Simulator Master Node")
        logger.info(f"Starting on {MASTER_HOST}:{MASTER_PORT}")
        
        # Prepare tasks
        prepare_tasks()
        
        logger.info("Master node ready to accept connections")
        
        # Start Flask app
        app.run(host=MASTER_HOST, port=MASTER_PORT, debug=False, threaded=True)
        
    except Exception as e:
        logger.error(f"Failed to start master node: {e}")
        sys.exit(1)