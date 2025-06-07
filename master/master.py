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
active_workers = {}  # worker_id: last_heartbeat
active_tasks = {}    # task_id: {worker_id, timestamp, task_data}

# Worker registration and health monitoring
@app.route("/register_worker", methods=["POST"])
def register_worker():
    try:
        data = request.json
        worker_id = data.get("worker_id")
        if worker_id:
            active_workers[worker_id] = time.time()
            logger.info(f"Worker {worker_id} registered")
            return jsonify({"status": "success"})
        return jsonify({"status": "failure", "reason": "worker_id required"})
    except Exception as e:
        logger.error(f"Error in register_worker: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    try:
        data = request.json
        worker_id = data.get("worker_id")
        if worker_id:
            active_workers[worker_id] = time.time()
            return jsonify({"status": "success"})
        return jsonify({"status": "failure", "reason": "worker_id required"})
    except Exception as e:
        logger.error(f"Error in heartbeat: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

# Task timeout and retry logic
def check_task_timeouts():
    current_time = time.time()
    expired_tasks = []
    
    for task_id, task_info in active_tasks.items():
        if current_time - task_info['timestamp'] > TASK_TIMEOUT:
            expired_tasks.append(task_id)
    
    for task_id in expired_tasks:
        task_info = active_tasks.pop(task_id)
        task_queue.put(task_info['task_data'])  # Re-queue the task
        logger.warning(f"Task {task_id} timed out, re-queued")

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
        
        if task_id is not None:
            # Remove from active tasks
            if task_id in active_tasks:
                del active_tasks[task_id]
            
            if cracked_password:
                result_list.append((task_id, cracked_password))
                logger.info(f"Password cracked for task {task_id}: {cracked_password}")
            else:
                logger.info(f"No password found for task {task_id}")
            return jsonify({"status": "success"})
        
        return jsonify({"status": "failure", "reason": "invalid input"})
    except Exception as e:
        logger.error(f"Error in submit_result: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

@app.route("/results", methods=["GET"])
def get_results():
    try:
        return jsonify({"results": result_list})
    except Exception as e:
        logger.error(f"Error in get_results: {e}")
        return jsonify({"results": [], "error": str(e)})

@app.route("/status", methods=["GET"])
def get_status():
    try:
        return jsonify({
            "active_workers": len(active_workers),
            "pending_tasks": task_queue.qsize(),
            "active_tasks": len(active_tasks),
            "completed_results": len(result_list)
        })
    except Exception as e:
        logger.error(f"Error in get_status: {e}")
        return jsonify({
            "active_workers": 0,
            "pending_tasks": 0,
            "active_tasks": 0,
            "completed_results": 0,
            "error": str(e)
        })

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