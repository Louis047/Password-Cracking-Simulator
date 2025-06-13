import os
from pathlib import Path

# Base Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

# Ensure directories exist
LOG_DIR.mkdir(exist_ok=True)

# Master Configuration
MASTER_HOST = os.getenv('MASTER_HOST', 'localhost')
MASTER_PORT = int(os.getenv('MASTER_PORT', 5000))
MASTER_URL = f'http://{MASTER_HOST}:{MASTER_PORT}'

# Task Configuration
TASK_FETCH_INTERVAL = int(os.getenv('TASK_FETCH_INTERVAL', 2))  # Reduced from 5
TASK_BATCH_SIZE = int(os.getenv('TASK_BATCH_SIZE', 20))  # Increased from 10
TASK_TIMEOUT = int(os.getenv('TASK_TIMEOUT', 180))  # Reduced from 300

# Worker Configuration
WORKER_HEARTBEAT_INTERVAL = int(os.getenv('WORKER_HEARTBEAT_INTERVAL', 15))  # Reduced from 30
WORKER_RETRY_ATTEMPTS = int(os.getenv('WORKER_RETRY_ATTEMPTS', 3))
WORKER_RETRY_DELAY = int(os.getenv('WORKER_RETRY_DELAY', 5))
MAX_WORKERS = int(os.getenv('MAX_WORKERS', 10))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = LOG_DIR / 'pcs.log'
1
# Security Configuration
HASH_ALGORITHM = 'sha256'
SALT_LENGTH = 16
MAX_PASSWORD_LENGTH = 128

# Data Files
HASHES_FILE = DATA_DIR / 'hashes.txt'
PASSWORDS_FILE = DATA_DIR / 'password.txt'

# Performance Configuration
CHUNK_SIZE = 1000  # For processing large password lists
MEMORY_LIMIT_MB = 512  # Memory limit per worker
