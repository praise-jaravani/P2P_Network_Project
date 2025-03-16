#!/usr/bin/env python3
"""
Network resilience test for P2P file sharing system.
This test evaluates how the system handles network failures and recovers from them.

Tests performed:
1. Tracker failure and recovery
2. Seeder disconnection during downloads
3. Leecher reconnection after network interruption
4. Ability to resume partial downloads

Usage:
    python network_resilience_test.py
"""

import os
import sys
import time
import signal
import random
import shutil
import socket
import threading
import subprocess
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ResilienceTest")

# Default configuration
DEFAULT_TRACKER_IP = "127.0.0.1"
DEFAULT_TRACKER_PORT = 12345
SEEDER_PORT = 8000
LEECHER_PORT = 9000
TEST_FILE_SIZE = 5120  # 5MB in KB

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_FILES_DIR = os.path.join(BASE_DIR, "resilience_test_files")
SEEDER_FILES_DIR = os.path.join(BASE_DIR, "resilience_seeder_files")
LEECHER_FILES_DIR = os.path.join(BASE_DIR, "resilience_leecher_files")


def generate_test_file(size_kb):
    """Generate a test file of specified size with random content."""
    os.makedirs(TEST_FILES_DIR, exist_ok=True)
    filename = f"resilience_test_{size_kb}KB.dat"
    filepath = os.path.join(TEST_FILES_DIR, filename)
    
    # Check if file already exists
    if os.path.exists(filepath) and os.path.getsize(filepath) >= size_kb * 1024:
        logger.info(f"Using existing test file: {filepath}")
        return filepath
    
    logger.info(f"Generating {size_kb}KB test file...")
    
    # Generate file with random data
    with open(filepath, 'wb') as f:
        chunk_size = 1024  # 1KB chunks
        for _ in range(size_kb):
            # Generate random chunk
            chunk = os.urandom(chunk_size)
            f.write(chunk)
    
    logger.info(f"Generated test file: {filepath}")
    return filepath


def setup_environment():
    """Set up the test environment."""
    # Create directories
    for directory in [TEST_FILES_DIR, SEEDER_FILES_DIR, LEECHER_FILES_DIR]:
        os.makedirs(directory, exist_ok=True)
        # Clean existing files
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
    
    # Generate test file
    test_file = generate_test_file(TEST_FILE_SIZE)
    
    # Copy to seeder directory
    shutil.copy(test_file, SEEDER_FILES_DIR)
    
    return os.path.basename(test_file)


def start_tracker():
    """Start the tracker server."""
    tracker_cmd = [
        sys.executable, 
        os.path.join(BASE_DIR, "tracker_server.py"),
        "--ip", DEFAULT_TRACKER_IP, 
        "--port", str(DEFAULT_TRACKER_PORT)
    ]
    
    logger.info(f"Starting tracker at {DEFAULT_TRACKER_IP}:{DEFAULT_TRACKER_PORT}")
    tracker_process = subprocess.Popen(
        tracker_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    
    # Wait for tracker to start
    time.sleep(3)
    
    # Check if tracker is responsive
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        sock.sendto(b"TIME:", (DEFAULT_TRACKER_IP, DEFAULT_TRACKER_PORT))
        response, _ = sock.recvfrom(1024)
        logger.info(f"Tracker responded: {response.decode('utf-8')}")
        sock.close()
    except Exception as e:
        logger.error(f"Failed to check tracker: {e}")
        tracker_process.terminate()
        raise
    
    return tracker_process


def start_seeder():
    """Start a seeder process."""
    seeder_cmd = [
        sys.executable, 
        os.path.join(BASE_DIR, "seeder_client.py"),
        "--ip", DEFAULT_TRACKER_IP, 
        "--port", str(SEEDER_PORT),
        "--tracker-ip", DEFAULT_TRACKER_IP, 
        "--tracker-port", str(DEFAULT_TRACKER_PORT),
        "--files-dir", SEEDER_FILES_DIR,
        "--quiet"
    ]
    
    logger.info(f"Starting seeder at {DEFAULT_TRACKER_IP}:{SEEDER_PORT}")
    seeder_process = subprocess.Popen(
        seeder_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    
    # Wait for seeder to register with tracker
    time.sleep(3)
    
    return seeder_process


def start_leecher(test_file):
    """Start a leecher process that will download the specified file."""
    leecher_cmd = [
        sys.executable, 
        os.path.join(BASE_DIR, "leecher_client.py"),
        "--ip", DEFAULT_TRACKER_IP, 
        "--port", str(LEECHER_PORT),
        "--tracker-ip", DEFAULT_TRACKER_IP, 
        "--tracker-port", str(DEFAULT_TRACKER_PORT),
        "--files-dir", LEECHER_FILES_DIR,
        "--file", test_file
    ]
    
    logger.info(f"Starting leecher at {DEFAULT_TRACKER_IP}:{LEECHER_PORT}")
    leecher_process = subprocess.Popen(
        leecher_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    
    return leecher_process


def test_tracker_resilience(test_file):
    """Test the system's resilience to tracker failures."""
    logger.info("=== TESTING TRACKER RESILIENCE ===")
    
    # Start tracker
    tracker_process = start_tracker()
    
    # Start seeder
    seeder_process = start_seeder()
    
    # Start leecher and let it begin downloading
    leecher_process = start_leecher(test_file)
    
    # Give the leecher time to connect and start downloading
    logger.info("Waiting for download to start...")
    time.sleep(10)
    
    # Kill the tracker to simulate failure
    logger.info("Simulating tracker failure by terminating tracker process...")
    tracker_process.terminate()
    tracker_process.wait()
    
    # Wait a bit
    time.sleep(5)
    
    # Check if leecher and seeder are still running (they should be)
    if leecher_process.poll() is not None:
        logger.error("Leecher process terminated after tracker failure!")
    else:
        logger.info("Leecher process still running after tracker failure - Good!")
    
    if seeder_process.poll() is not None:
        logger.error("Seeder process terminated after tracker failure!")
    else:
        logger.info("Seeder process still running after tracker failure - Good!")
    
    # Restart the tracker
    logger.info("Restarting tracker...")
    new_tracker_process = start_tracker()
    
    # Give time for processes to reconnect
    time.sleep(10)
    
    # Check if download continues
    download_file_path = os.path.join(LEECHER_FILES_DIR, test_file)
    orig_file_path = os.path.join(SEEDER_FILES_DIR, test_file)
    
    # Wait for a while to see if download completes
    max_wait = 60  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        if os.path.exists(download_file_path):
            # File exists, check if it's the right size
            if os.path.getsize(download_file_path) == os.path.getsize(orig_file_path):
                logger.info("Download completed successfully after tracker restart!")
                break
        time.sleep(2)
    else:
        logger.error(f"Download did not complete within {max_wait} seconds after tracker restart")
    
    # Clean up
    for process in [leecher_process, seeder_process, new_tracker_process]:
        if process.poll() is None:  # Process is still running
            process.terminate()
            process.wait()
    
    # Remove downloaded file to prepare for next test
    if os.path.exists(download_file_path):
        os.remove(download_file_path)


def test_seeder_resilience(test_file):
    """Test the system's resilience to seeder failures."""
    logger.info("=== TESTING SEEDER RESILIENCE ===")
    
    # Start tracker
    tracker_process = start_tracker()
    
    # Start seeder
    seeder_process = start_seeder()
    
    # Start leecher
    leecher_process = start_leecher(test_file)
    
    # Give the leecher time to connect and start downloading
    logger.info("Waiting for download to start...")
    time.sleep(10)
    
    # Kill the seeder
    logger.info("Simulating seeder failure by terminating seeder process...")
    seeder_process.terminate()
    seeder_process.wait()
    
    # Wait a bit
    time.sleep(5)
    
    # Restart the seeder
    logger.info("Restarting seeder...")
    new_seeder_process = start_seeder()
    
    # Check if download continues
    download_file_path = os.path.join(LEECHER_FILES_DIR, test_file)
    orig_file_path = os.path.join(SEEDER_FILES_DIR, test_file)
    
    # Wait for download to complete
    max_wait = 60  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        if os.path.exists(download_file_path):
            if os.path.getsize(download_file_path) == os.path.getsize(orig_file_path):
                logger.info("Download completed successfully after seeder restart!")
                break
        time.sleep(2)
    else:
        logger.error(f"Download did not complete within {max_wait} seconds after seeder restart")
    
    # Clean up
    for process in [leecher_process, new_seeder_process, tracker_process]:
        if process.poll() is None:
            process.terminate()
            process.wait()
    
    # Remove downloaded file to prepare for next test
    if os.path.exists(download_file_path):
        os.remove(download_file_path)


def test_leecher_resilience(test_file):
    """Test the system's resilience to leecher failures."""
    logger.info("=== TESTING LEECHER RESILIENCE ===")
    
    # Start tracker
    tracker_process = start_tracker()
    
    # Start seeder
    seeder_process = start_seeder()
    
    # Start leecher
    leecher_process = start_leecher(test_file)
    
    # Give the leecher time to connect and start downloading
    logger.info("Waiting for download to start...")
    time.sleep(10)
    
    # Kill the leecher
    logger.info("Simulating leecher failure by terminating leecher process...")
    leecher_process.terminate()
    leecher_process.wait()
    
    # Wait a bit
    time.sleep(5)
    
    # Restart the leecher
    logger.info("Restarting leecher...")
    new_leecher_process = start_leecher(test_file)
    
    # Check if download continues and completes
    download_file_path = os.path.join(LEECHER_FILES_DIR, test_file)
    orig_file_path = os.path.join(SEEDER_FILES_DIR, test_file)
    
    # Wait for download to complete
    max_wait = 60  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        if os.path.exists(download_file_path):
            if os.path.getsize(download_file_path) == os.path.getsize(orig_file_path):
                logger.info("Download completed successfully after leecher restart!")
                break
        time.sleep(2)
    else:
        logger.error(f"Download did not complete within {max_wait} seconds after leecher restart")
    
    # Clean up
    for process in [new_leecher_process, seeder_process, tracker_process]:
        if process.poll() is None:
            process.terminate()
            process.wait()


def test_resume_download(test_file):
    """Test the ability to resume a partial download."""
    logger.info("=== TESTING DOWNLOAD RESUME FUNCTIONALITY ===")
    
    # Start tracker
    tracker_process = start_tracker()
    
    # Start seeder
    seeder_process = start_seeder()
    
    # Start leecher
    leecher_process = start_leecher(test_file)
    
    # Give the leecher time to download part of the file
    logger.info("Waiting for partial download...")
    time.sleep(15)
    
    # Kill the leecher
    logger.info("Terminating leecher during download...")
    leecher_process.terminate()
    leecher_process.wait()
    
    # Verify partial download exists
    download_file_path = os.path.join(LEECHER_FILES_DIR, test_file)
    orig_file_path = os.path.join(SEEDER_FILES_DIR, test_file)
    
    if not os.path.exists(download_file_path):
        logger.error("No partial download file found!")
        return
    
    partial_size = os.path.getsize(download_file_path)
    orig_size = os.path.getsize(orig_file_path)
    
    logger.info(f"Partial download: {partial_size} bytes / {orig_size} bytes ({partial_size/orig_size*100:.1f}%)")
    
    # Restart leecher
    logger.info("Restarting leecher to resume download...")
    new_leecher_process = start_leecher(test_file)
    
    # Wait for download to complete
    max_wait = 60  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        if os.path.exists(download_file_path):
            current_size = os.path.getsize(download_file_path)
            if current_size == orig_size:
                logger.info("Download completed successfully after resume!")
                
                # Verify file integrity
                with open(download_file_path, 'rb') as f1, open(orig_file_path, 'rb') as f2:
                    data1 = f1.read()
                    data2 = f2.read()
                    if data1 == data2:
                        logger.info("Downloaded file matches the original - integrity verified!")
                    else:
                        logger.error("Downloaded file does not match the original - integrity check failed!")
                
                break
        time.sleep(2)
    else:
        logger.error(f"Download resume did not complete within {max_wait} seconds")
    
    # Clean up
    for process in [new_leecher_process, seeder_process, tracker_process]:
        if process.poll() is None:
            process.terminate()
            process.wait()


def run_all_tests():
    """Run all resilience tests."""
    test_file = setup_environment()
    
    tests = [
        test_tracker_resilience,
        test_seeder_resilience,
        test_leecher_resilience,
        test_resume_download
    ]
    
    for test_func in tests:
        try:
            test_func(test_file)
            # Add a delay between tests to ensure processes are cleaned up
            time.sleep(3)
        except Exception as e:
            logger.error(f"Test {test_func.__name__} failed: {e}")
    
    logger.info("All resilience tests completed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Network resilience tests for P2P file sharing system")
    parser.add_argument("--test", choices=["tracker", "seeder", "leecher", "resume", "all"], 
                        default="all", help="Specific test to run")
    
    args = parser.parse_args()
    
    # Set up the test environment
    test_file = setup_environment()
    
    if args.test == "tracker":
        test_tracker_resilience(test_file)
    elif args.test == "seeder":
        test_seeder_resilience(test_file)
    elif args.test == "leecher":
        test_leecher_resilience(test_file)
    elif args.test == "resume":
        test_resume_download(test_file)
    else:  # "all"
        run_all_tests()