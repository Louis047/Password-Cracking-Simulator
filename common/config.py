# Master Configuration
MASTER_URL = 'http://localhost:5000'
MASTER_HOST = 'localhost'  # Changed from '0.0.0.0' to 'localhost'
MASTER_PORT = 5000

# Task Configuration
TASK_FETCH_INTERVAL = 5  # seconds
TASK_BATCH_SIZE = 10
TASK_TIMEOUT = 300  # 5 minutes

# Worker Configuration
WORKER_HEARTBEAT_INTERVAL = 30  # seconds
WORKER_RETRY_ATTEMPTS = 3
WORKER_RETRY_DELAY = 5  # seconds

# Logging Configuration
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Hash Configuration
HASH_ALGORITHM = 'sha256'
SALT_LENGTH = 16
