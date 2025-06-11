import pytest
import requests
import time
import threading
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from master.master import app
from common.config import MASTER_PORT

class TestMaster:
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_worker_registration(self, client):
        """Test worker registration endpoint"""
        response = client.post('/register_worker', 
                             json={'worker_id': 'test_worker_1'})
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_heartbeat(self, client):
        """Test worker heartbeat endpoint"""
        # First register a worker
        client.post('/register_worker', json={'worker_id': 'test_worker_1'})
        
        # Send heartbeat
        response = client.post('/heartbeat', 
                             json={
                                 'worker_id': 'test_worker_1',
                                 'tasks_completed': 5,
                                 'passwords_cracked': 2,
                                 'status': 'active'
                             })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
    
    def test_task_assignment(self, client):
        """Test task assignment to workers"""
        # Register worker
        client.post('/register_worker', json={'worker_id': 'test_worker_1'})
        
        # Load tasks first
        client.post('/load_tasks')
        
        # Request task
        response = client.post('/get_task', json={'worker_id': 'test_worker_1'})
        assert response.status_code == 200
        data = response.get_json()
        assert 'task' in data or data.get('status') == 'no_tasks'
    
    def test_status_endpoint(self, client):
        """Test master status endpoint"""
        response = client.get('/status')
        assert response.status_code == 200
        data = response.get_json()
        assert 'status' in data
        assert 'active_workers' in data
        assert 'queue_size' in data