from flask import Flask, request, jsonify
import hashlib
from queue import Queue
from threading import Lock
import os
import time
from common.logger import get_logger
from common.config import TASK_BATCH_SIZE, TASK_TIMEOUT

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
    data = request.json
    worker_id = data.get("worker_id")
    if worker_id:
        active_workers[worker_id] = time.time()
        logger.info(f"Worker {worker_id} registered")
        return jsonify({"status": "success"})
    return jsonify({"status": "failure"})

@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    data = request.json
    worker_id = data.get("worker_id")
    if worker_id:
        active_workers[worker_id] = time.time()
        return jsonify({"status": "success"})
    return jsonify({"status": "failure"})

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

# Load hashes and prepare tasks (existing logic with improvements)
def load_hashes(filepath="data/hashes.txt"):
    try:
        with open(filepath, 'r') as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        logger.warning(f"Hash file {filepath} not found, creating sample data")
        return []

def prepare_tasks(wordlist_path="data/password.txt"):
    global target_hashes
    target_hashes = load_hashes()
    
    if not target_hashes:
        sample_passwords = ["password123", "admin", "123456", "qwerty"]
        target_hashes = [hashlib.sha256(pwd.encode()).hexdigest() for pwd in sample_passwords]
        logger.info("Created sample target hashes")
    
    try:
        with open(wordlist_path, 'r') as file:
            passwords = [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        logger.warning(f"Password file {wordlist_path} not found, creating sample data")
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

@app.route("/results", methods=["GET"])
def get_results():
    return jsonify({"results": result_list})

@app.route("/status", methods=["GET"])
def get_status():
    return jsonify({
        "active_workers": len(active_workers),
        "pending_tasks": task_queue.qsize(),
        "active_tasks": len(active_tasks),
        "completed_results": len(result_list)
    })

if __name__ == "__main__":
    prepare_tasks()
    app.run(host='0.0.0.0', port=5000, debug=True)