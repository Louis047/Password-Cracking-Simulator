import pytest
import hashlib
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.worker import PasswordCrackingWorker

class TestWorker:
    @pytest.fixture
    def worker(self):
        return PasswordCrackingWorker()
    
    def test_hash_password(self, worker):
        """Test password hashing function"""
        password = "test123"
        expected_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        assert worker.hash_password(password) == expected_hash
    
    def test_crack_password_success(self, worker):
        """Test successful password cracking"""
        # Create a test task
        test_password = "secret"
        test_hash = worker.hash_password(test_password)
        
        task = {
            "task_id": "test_task_1",
            "target_hash": test_hash,
            "candidates": ["wrong1", "wrong2", test_password, "wrong3"]
        }
        
        result = worker.crack_password(task)
        assert result == test_password
    
    def test_crack_password_failure(self, worker):
        """Test password cracking with no match"""
        test_hash = worker.hash_password("notinlist")
        
        task = {
            "task_id": "test_task_2",
            "target_hash": test_hash,
            "candidates": ["wrong1", "wrong2", "wrong3"]
        }
        
        result = worker.crack_password(task)
        assert result is None
    
    @patch('requests.post')
    def test_register_with_master(self, mock_post, worker):
        """Test worker registration with master"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = worker.register_with_master()
        assert result is True
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_send_heartbeat(self, mock_post, worker):
        """Test heartbeat sending"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        worker.send_heartbeat()
        mock_post.assert_called_once()