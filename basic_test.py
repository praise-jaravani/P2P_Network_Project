#!/usr/bin/env python3
"""
Basic test suite for the P2P file sharing system.
This test validates basic functionality across tracker, seeder, and leecher components.

Usage:
    python basic_test.py
"""

import os
import sys
import time
import socket
import shutil
import threading
import subprocess
import unittest
import logging
import random
import string

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TestSuite")

# Configuration
TRACKER_IP = "127.0.0.1"
TRACKER_PORT = 12345
SEEDER_PORT_BASE = 8000  # Will increment for multiple seeders
LEECHER_PORT_BASE = 9000  # Will increment for multiple leechers

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_FILES_DIR = os.path.join(BASE_DIR, "test_files")
SEEDER_FILES_DIR = os.path.join(BASE_DIR, "seeder_files")
LEECHER_FILES_DIR = os.path.join(BASE_DIR, "leecher_files")

# Create test directories
os.makedirs(TEST_FILES_DIR, exist_ok=True)
os.makedirs(SEEDER_FILES_DIR, exist_ok=True)
os.makedirs(LEECHER_FILES_DIR, exist_ok=True)

def generate_random_file(filename, size_kb):
    """Generate a file with random content of specified size in KB."""
    path = os.path.join(TEST_FILES_DIR, filename)
    with open(path, 'wb') as f:
        # Generate random content in chunks to avoid memory issues with large files
        chunk_size = 1024  # 1 KB chunks
        remaining = size_kb
        while remaining > 0:
            write_size = min(remaining, chunk_size)
            data = ''.join(random.choices(string.ascii_letters + string.digits, k=write_size)).encode()
            f.write(data)
            remaining -= 1
    
    logger.info(f"Generated test file {filename} ({size_kb} KB)")
    return path

class P2PTestCase(unittest.TestCase):
    """Test case for P2P file sharing functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the test environment before running tests."""
        # Create test files
        cls.test_files = [
            generate_random_file("small_file.txt", 10),  # 10 KB
            generate_random_file("medium_file.dat", 1024),  # 1 MB
            generate_random_file("large_file.bin", 5120),  # 5 MB
        ]
        
        # Start tracker process
        tracker_cmd = [
            sys.executable, 
            os.path.join(BASE_DIR, "tracker_server.py"),
            "--ip", TRACKER_IP, 
            "--port", str(TRACKER_PORT),
            "--log-level", "INFO"
        ]
        cls.tracker_process = subprocess.Popen(
            tracker_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        logger.info(f"Started tracker at {TRACKER_IP}:{TRACKER_PORT}")
        
        # Wait for tracker to initialize
        time.sleep(3)
        
        # Copy test files to seeder directory
        for file_path in cls.test_files:
            shutil.copy(file_path, SEEDER_FILES_DIR)
        
        # Start seeder process
        seeder_cmd = [
            sys.executable, 
            os.path.join(BASE_DIR, "seeder_client.py"),
            "--ip", TRACKER_IP, 
            "--port", str(SEEDER_PORT_BASE),
            "--tracker-ip", TRACKER_IP, 
            "--tracker-port", str(TRACKER_PORT),
            "--files-dir", SEEDER_FILES_DIR,
            "--log-level", "INFO",
            "--quiet"  # Suppress verbose output
        ]
        cls.seeder_process = subprocess.Popen(
            seeder_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        logger.info(f"Started seeder at {TRACKER_IP}:{SEEDER_PORT_BASE}")
        
        # Wait for seeder to register with tracker
        time.sleep(3)

    @classmethod
    def tearDownClass(cls):
        """Clean up resources after tests."""
        # Terminate processes
        if hasattr(cls, 'tracker_process'):
            cls.tracker_process.terminate()
            cls.tracker_process.wait()
            logger.info("Terminated tracker process")
        
        if hasattr(cls, 'seeder_process'):
            cls.seeder_process.terminate()
            cls.seeder_process.wait()
            logger.info("Terminated seeder process")
        
        # Clean up test directories
        for dir_path in [SEEDER_FILES_DIR, LEECHER_FILES_DIR]:
            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    logger.debug(f"Removed file: {file_path}")
    
    def test_udp_tracker_connection(self):
        """Test basic connection to the UDP tracker server."""
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        
        try:
            # Send a simple message to the tracker
            message = "TIME:"
            sock.sendto(message.encode('utf-8'), (TRACKER_IP, TRACKER_PORT))
            
            # Wait for response
            response, _ = sock.recvfrom(1024)
            response = response.decode('utf-8')
            
            # Check response
            self.assertTrue(response.startswith("Current time:"), 
                           f"Unexpected response from tracker: {response}")
            logger.info(f"Tracker response: {response}")
        finally:
            sock.close()
    
    def test_list_files(self):
        """Test listing available files from the tracker."""
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        
        try:
            # Send ListFiles request
            message = "ListFiles:"
            sock.sendto(message.encode('utf-8'), (TRACKER_IP, TRACKER_PORT))
            
            # Wait for response
            response, _ = sock.recvfrom(4096)  # Larger buffer for file lists
            response = response.decode('utf-8')
            
            # Check response
            self.assertTrue(response.startswith("FilesList:"), 
                           f"Unexpected response format: {response}")
            
            # Extract file list
            import ast
            file_list = ast.literal_eval(response[len("FilesList:"):])
            logger.info(f"Available files: {file_list}")
            
            # Verify at least one of our test files is listed
            test_file_names = [os.path.basename(path) for path in self.test_files]
            found = False
            for test_file in test_file_names:
                if test_file in file_list:
                    found = True
                    break
            
            self.assertTrue(found, "No test files found in tracker file list")
        finally:
            sock.close()
    
    def test_file_download(self):
        """Test downloading a file via leecher client."""
        # Get the smallest test file for quicker testing
        test_file_name = os.path.basename(self.test_files[0])  # small_file.txt
        
        # Start leecher process to download the file
        leecher_cmd = [
            sys.executable, 
            os.path.join(BASE_DIR, "leecher_client.py"),
            "--ip", TRACKER_IP, 
            "--port", str(LEECHER_PORT_BASE),
            "--tracker-ip", TRACKER_IP, 
            "--tracker-port", str(TRACKER_PORT),
            "--files-dir", LEECHER_FILES_DIR,
            "--become-seeder",
            "--file", test_file_name,
            "--log-level", "INFO"
        ]
        
        try:
            leecher_process = subprocess.Popen(
                leecher_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            logger.info(f"Started leecher to download {test_file_name}")
            
            # Wait a bit for download to complete (adjust timeout as needed)
            timeout = 30  # seconds
            start_time = time.time()
            
            downloaded_file_path = os.path.join(LEECHER_FILES_DIR, test_file_name)
            original_file_path = os.path.join(SEEDER_FILES_DIR, test_file_name)
            
            while time.time() - start_time < timeout:
                if os.path.exists(downloaded_file_path):
                    # Check if file sizes match to determine if download is complete
                    if os.path.getsize(downloaded_file_path) == os.path.getsize(original_file_path):
                        logger.info(f"File {test_file_name} successfully downloaded")
                        
                        # Verify file contents
                        with open(original_file_path, 'rb') as f1, open(downloaded_file_path, 'rb') as f2:
                            original_content = f1.read()
                            downloaded_content = f2.read()
                            self.assertEqual(original_content, downloaded_content, 
                                           "Downloaded file content doesn't match original")
                        
                        return  # Test passed
                time.sleep(1)
            
            # If we get here, the download didn't complete in time
            self.fail(f"File download did not complete within {timeout} seconds")
            
        finally:
            # Terminate leecher process if still running
            if 'leecher_process' in locals():
                leecher_process.terminate()
                leecher_process.wait()
                logger.info("Terminated leecher process")


if __name__ == "__main__":
    unittest.main()
