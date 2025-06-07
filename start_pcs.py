#!/usr/bin/env python3
import subprocess
import time
import sys
import os
import threading
import requests
from common.logger import get_logger
from common.config import MASTER_URL, MASTER_PORT

logger = get_logger("PCS_Launcher")

class PCSLauncher:
    def __init__(self):
        self.master_process = None
        self.worker_processes = []
        self.running = False
        # Get the project root directory
        self.project_root = os.path.dirname(os.path.abspath(__file__))
    
    def start_master(self):
        """Start the master node"""
        logger.info("Starting Master Node...")
        try:
            master_script = os.path.join(self.project_root, "master", "master.py")
            self.master_process = subprocess.Popen(
                [sys.executable, master_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.project_root,  # Set working directory
                env=dict(os.environ, PYTHONPATH=self.project_root)  # Add to Python path
            )
            time.sleep(5)  # Give master more time to start
            
            # Check if the process is still running
            if self.master_process.poll() is not None:
                # Process has terminated, get the error output
                stdout, stderr = self.master_process.communicate()
                logger.error("Master process terminated unexpectedly")
                logger.error(f"Master stdout: {stdout}")
                logger.error(f"Master stderr: {stderr}")
                logger.error("Failed to start master node - aborting demo")
                return False
            
            # Check if master is responding
            max_retries = 6
            for attempt in range(max_retries):
                try:
                    response = requests.get(f"{MASTER_URL}/status", timeout=5)
                    if response.status_code == 200:
                        logger.info("✅ Master Node started successfully")
                        return True
                    else:
                        logger.warning(f"Master responded with status code: {response.status_code}")
                except requests.exceptions.ConnectionError:
                    if attempt < max_retries - 1:
                        logger.info(f"Waiting for master to start... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(2)
                    else:
                        logger.error("Cannot connect to master - it may not be listening on the expected port")
                except requests.exceptions.Timeout:
                    logger.error("Timeout connecting to master")
                except Exception as e:
                    logger.error(f"Error connecting to master: {e}")
            
            # If we get here, master didn't start properly
            if self.master_process.poll() is None:
                # Process is still running but not responding
                try:
                    stdout, stderr = self.master_process.communicate(timeout=2)
                    logger.error(f"Master process output: {stdout}")
                    logger.error(f"Master process errors: {stderr}")
                except subprocess.TimeoutExpired:
                    logger.error("Master process is running but not responding")
            
            logger.error("❌ Master Node failed to start")
            return False
        except Exception as e:
            logger.error(f"Failed to start master: {e}")
            return False
    
    def start_workers(self, num_workers=2):
        """Start worker nodes"""
        logger.info(f"Starting {num_workers} Worker Nodes...")
        
        for i in range(num_workers):
            try:
                worker_script = os.path.join(self.project_root, "worker", "worker.py")
                worker_process = subprocess.Popen(
                    [sys.executable, worker_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=self.project_root,  # Set working directory
                    env=dict(os.environ, PYTHONPATH=self.project_root)  # Add to Python path
                )
                self.worker_processes.append(worker_process)
                logger.info(f"✅ Worker {i+1} started successfully")
                time.sleep(1)  # Stagger worker starts
            except Exception as e:
                logger.error(f"Failed to start worker {i+1}: {e}")
    
    def monitor_system(self):
        """Monitor system status and display logs"""
        logger.info("🔍 Starting system monitoring...")
        
        while self.running:
            try:
                response = requests.get(f"{MASTER_URL}/status", timeout=5)
                if response.status_code == 200:
                    status = response.json()
                    logger.info(f"📊 System Status - Workers: {status['active_workers']}, "
                              f"Pending Tasks: {status['pending_tasks']}, "
                              f"Active Tasks: {status['active_tasks']}, "
                              f"Completed Results: {status['completed_results']}")
                    
                    # Check for results
                    results_response = requests.get(f"{MASTER_URL}/results", timeout=5)
                    if results_response.status_code == 200:
                        results = results_response.json().get('results', [])
                        if results:
                            logger.info("🎯 Cracked Passwords:")
                            for task_id, password in results:
                                logger.info(f"   Task {task_id}: '{password}'")
                
            except Exception as e:
                logger.warning(f"Monitoring error: {e}")
            
            time.sleep(10)  # Check every 10 seconds
    
    def stop_all(self):
        """Stop all processes"""
        logger.info("🛑 Stopping all processes...")
        self.running = False
        
        # Stop workers
        for i, worker in enumerate(self.worker_processes):
            try:
                worker.terminate()
                worker.wait(timeout=5)
                logger.info(f"✅ Worker {i+1} stopped successfully")
            except subprocess.TimeoutExpired:
                worker.kill()
                logger.warning(f"⚠️ Worker {i+1} force killed")
            except Exception as e:
                logger.error(f"Error stopping worker {i+1}: {e}")
        
        # Stop master
        if self.master_process:
            try:
                self.master_process.terminate()
                self.master_process.wait(timeout=5)
                logger.info("✅ Master Node stopped successfully")
            except subprocess.TimeoutExpired:
                self.master_process.kill()
                logger.warning("⚠️ Master Node force killed")
            except Exception as e:
                logger.error(f"Error stopping master: {e}")
    
    def run_demo(self, num_workers=2):
        """Run the complete demo"""
        logger.info("🚀 Starting Password Cracking Simulator Demo")
        logger.info("=" * 50)
        
        try:
            # Start master
            if not self.start_master():
                return
            
            # Start workers
            self.start_workers(num_workers)
            
            # Start monitoring
            self.running = True
            monitor_thread = threading.Thread(target=self.monitor_system)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            logger.info("\n🎮 Demo is now running! Press Ctrl+C to stop")
            logger.info(f"📊 Web interface available at: http://localhost:{MASTER_PORT}/status")
            logger.info("=" * 50)
            
            # Keep running until interrupted
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n👋 Demo interrupted by user")
        except Exception as e:
            logger.error(f"Demo error: {e}")
        finally:
            self.stop_all()
            logger.info("🏁 Demo completed")

def main():
    print("Password Cracking Simulator (PCS) Launcher")
    print("==========================================\n")
    
    launcher = PCSLauncher()
    
    if len(sys.argv) > 1:
        try:
            num_workers = int(sys.argv[1])
        except ValueError:
            num_workers = 2
            print(f"Invalid worker count, using default: {num_workers}")
    else:
        num_workers = 2
    
    print(f"Starting demo with {num_workers} workers...\n")
    launcher.run_demo(num_workers)

if __name__ == "__main__":
    main()