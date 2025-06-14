from flask import Flask, request, jsonify
import hashlib
from queue import Queue
from threading import Lock, Thread
import os
import time
import sys
from waitress import serve
from collections import deque
from threading import RLock
import signal

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.logger import get_logger
from common.config import TASK_BATCH_SIZE, TASK_TIMEOUT, MASTER_HOST, MASTER_PORT

app = Flask(__name__)
logger = get_logger("Master")

task_queue = deque()
result_list = []
queue_lock = RLock()
target_hashes = []
active_workers = {}  # worker_id: {last_heartbeat, tasks_completed, passwords_cracked, status}
active_tasks = {}    # task_id: {worker_id, timestamp, task_data}
worker_stats = {}    # worker_id: {total_tasks, total_cracked, avg_time}

# Add new global variables
is_initialized = False
initialization_lock = RLock()

# Add initialization function
def initialize_master():
    """Initialize the master node without loading tasks"""
    global is_initialized, task_queue, result_list, queue_lock, target_hashes, active_workers, active_tasks, worker_stats, start_time
    
    with initialization_lock:
        if is_initialized:
            return
        
        # Initialize all state
        task_queue = deque()
        result_list = []
        queue_lock = RLock()
        target_hashes = []
        active_workers = {}
        active_tasks = {}
        worker_stats = {}
        start_time = time.time()
        
        is_initialized = True
        logger.info("Master node initialized (no tasks loaded)")

# Worker registration and health monitoring
@app.route("/register_worker", methods=["POST"])
def register_worker():
    """Register a new worker"""
    # Ensure master is initialized
    initialize_master()
    
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
    """Update worker heartbeat"""
    # Ensure master is initialized
    initialize_master()
    
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
        task_queue.append(task_info['task_data'])  # Re-queue the task
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
    """Prepare initial tasks - only used for normal mode"""
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
        # Use larger batches for better performance
        batch_size = min(TASK_BATCH_SIZE, 200)  # Increased batch size
        for i in range(0, len(passwords), batch_size):
            batch = passwords[i:i + batch_size]
            task = {
                "task_id": task_id,
                "target_hash": target_hash,
                "candidates": batch
            }
            add_task_to_queue(task)
            task_id += 1
    
    logger.info(f"Loaded {len(task_queue)} tasks into the queue")

# Add new task management functions
def add_task_to_queue(task):
    """Add a task to the queue with minimal locking"""
    with queue_lock:
        task_queue.append(task)

def get_task_from_queue():
    """Get a task from the queue with minimal locking"""
    with queue_lock:
        if not task_queue:
            return None
        return task_queue.popleft()

def clear_task_queue():
    """Clear the task queue with minimal locking"""
    with queue_lock:
        task_queue.clear()

# Modify the get_task endpoint to use the new functions
@app.route("/get_task", methods=["GET"])
def get_task():
    """Get a task for a worker"""
    # Ensure master is initialized
    initialize_master()
    
    check_task_timeouts()  # Check for expired tasks
    
    worker_id = request.args.get('worker_id')
    if not worker_id:
        return jsonify({"status": "failure", "reason": "worker_id required"})
    
    task = get_task_from_queue()
    if not task:
        return jsonify({"status": "no_tasks"})
    
    # Track active task without holding the queue lock
    active_tasks[task['task_id']] = {
        'worker_id': worker_id,
        'timestamp': time.time(),
        'task_data': task
    }
    return jsonify(task)

@app.route("/submit_result", methods=["POST"])
def submit_result():
    """Submit a task result"""
    # Ensure master is initialized
    initialize_master()
    
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
        logger.error(f"❌ Error submitting result: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

@app.route("/worker_stats", methods=["GET"])
def get_worker_stats():
    """Get worker statistics"""
    # Ensure master is initialized
    initialize_master()
    
    try:
        workers_list = []
        current_time = time.time()
        
        for worker_id, worker_info in active_workers.items():
            if worker_id in worker_stats:
                worker_data = {
                    'worker_id': worker_id,
                    'status': worker_info['status'],
                    'tasks_completed': worker_info['tasks_completed'],
                    'passwords_cracked': worker_info['passwords_cracked'],
                    'last_heartbeat': worker_info['last_heartbeat'],
                    'avg_processing_time': worker_stats[worker_id]['avg_time']
                }
                workers_list.append(worker_data)
        
        return jsonify({"workers": workers_list})
    except Exception as e:
        logger.error(f"❌ Error getting worker stats: {e}")
        return jsonify({"workers": []})

# Add to the existing status endpoint
@app.route("/status", methods=["GET"])
def get_status():
    """Get system status"""
    # Ensure master is initialized
    initialize_master()
    
    try:
        active_count = sum(1 for w in active_workers.values() if w['status'] == 'active')
        total_completed = sum(w['tasks_completed'] for w in active_workers.values())
        total_cracked = sum(w['passwords_cracked'] for w in active_workers.values())
        
        return jsonify({
            "status": "running",
            "uptime": time.time() - start_time,
            "active_workers": active_count,
            "total_workers": len(active_workers),
            "queue_size": len(task_queue),
            "active_tasks": len(active_tasks),
            "completed_tasks": total_completed,
            "cracked_passwords": total_cracked
        })
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

# Modify reset_tasks to use the new functions
@app.route("/reset_tasks", methods=["POST"])
def reset_tasks():
    try:
        global active_tasks, target_hashes
        # Clear state without holding locks
        active_tasks.clear()
        target_hashes.clear()
        clear_task_queue()
        
        # Reload default tasks
        prepare_tasks()
        
        logger.info("Tasks reset to default")
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error in reset_tasks: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

# Modify the load_demo_tasks endpoint to ensure initialization
@app.route("/load_demo_tasks", methods=["POST"])
def load_demo_tasks():
    """Load demo tasks from GUI"""
    try:
        # Ensure master is initialized
        initialize_master()
        
        data = request.json
        tasks = data.get('tasks', [])
        
        if not tasks:
            return jsonify({"status": "failure", "reason": "no tasks provided"})
        
        # Clear existing tasks and reset state
        global active_tasks, target_hashes, result_list
        
        # Clear state without holding locks
        active_tasks.clear()
        target_hashes.clear()
        result_list.clear()
        clear_task_queue()
        
        # Add demo tasks to queue with minimal locking
        task_count = 0
        for task in tasks:
            target_hash = task.get('target_hash')
            candidates = task.get('candidates', [])
            
            if target_hash and candidates:
                target_hashes.append(target_hash)
                
                # Use larger batches for better performance
                batch_size = min(TASK_BATCH_SIZE, 200)  # Increased batch size
                for i in range(0, len(candidates), batch_size):
                    batch = candidates[i:i + batch_size]
                    task_data = {
                        "task_id": task_count,
                        "target_hash": target_hash,
                        "candidates": batch
                    }
                    add_task_to_queue(task_data)
                    task_count += 1
        
        logger.info(f"📋 Loaded {task_count} demo tasks into queue")
        return jsonify({"status": "success", "tasks_loaded": task_count})
        
    except Exception as e:
        logger.error(f"❌ Error loading demo tasks: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

# Modify the load_custom_task endpoint to ensure initialization
@app.route("/load_custom_task", methods=["POST"])
def load_custom_task():
    """Load a single custom task from GUI"""
    try:
        # Ensure master is initialized
        initialize_master()
        
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
        base_task_id = len(active_tasks) + len(task_queue)
        
        # Use larger batches for better performance
        batch_size = min(TASK_BATCH_SIZE, 200)  # Increased batch size
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i + batch_size]
            task_data = {
                "task_id": base_task_id + task_count,
                "target_hash": target_hash,
                "candidates": batch
            }
            add_task_to_queue(task_data)
            task_count += 1
        
        logger.info(f"📋 Loaded custom task with {task_count} batches into queue")
        return jsonify({"status": "success", "tasks_loaded": task_count})
        
    except Exception as e:
        logger.error(f"❌ Error loading custom task: {e}")
        return jsonify({"status": "failure", "reason": str(e)})

# Modify create_tasks_for_hash to use the new functions
def create_tasks_for_hash(target_hash, wordlist_path="data/password.txt"):
    """Create tasks for a specific hash"""
    try:
        with open(wordlist_path, 'r', encoding='utf-8') as file:
            passwords = [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        passwords = ["password123", "admin", "123456", "qwerty", "letmein", "welcome"]
    
    task_id = len(active_tasks) + len(task_queue)
    # Use larger batches for better performance
    batch_size = min(TASK_BATCH_SIZE, 200)  # Increased batch size
    for i in range(0, len(passwords), batch_size):
        batch = passwords[i:i + batch_size]
        task = {
            "task_id": task_id,
            "target_hash": target_hash,
            "candidates": batch
        }
        add_task_to_queue(task)
        task_id += 1

@app.route("/results", methods=["GET"])
def get_results():
    """Get all cracking results"""
    # Ensure master is initialized
    initialize_master()
    
    try:
        return jsonify({"results": result_list})
    except Exception as e:
        logger.error(f"❌ Error getting results: {e}")
        return jsonify({"results": []})

def start_server():
    """Start the Flask server using Waitress"""
    logger.info(f"Starting on {MASTER_HOST}:{MASTER_PORT}")
    serve(app, host=MASTER_HOST, port=MASTER_PORT, threads=8)

if __name__ == "__main__":
    logger.info("Initializing Password Cracking Simulator Master Node")
    initialize_master()  # Initialize without loading tasks
    start_server()  # Start the server

# Add signal handler for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Received shutdown signal, stopping server...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)