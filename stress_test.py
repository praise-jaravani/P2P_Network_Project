#!/usr/bin/env python3
"""
Stress test for the P2P file sharing system.
This script tests the system's performance under heavy load by:
1. Creating multiple large files
2. Running multiple seeders sharing different files
3. Running multiple concurrent leechers that download files simultaneously
4. Measuring download times and system stability

Usage:
    python stress_test.py
"""

import os
import sys
import time
import shutil
import random
import string
import threading
import subprocess
import logging
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("StressTest")

# Default configuration
DEFAULT_TRACKER_IP = "127.0.0.1"
DEFAULT_TRACKER_PORT = 12345
DEFAULT_SEEDERS = 3
DEFAULT_LEECHERS = 5
DEFAULT_FILES_PER_SEEDER = 2
DEFAULT_FILE_SIZES = [1024, 2048, 5120]  # KB (1MB, 2MB, 5MB)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_FILES_DIR = os.path.join(BASE_DIR, "stress_test_files")
SEEDERS_DIR = os.path.join(BASE_DIR, "stress_test_seeders")
LEECHERS_DIR = os.path.join(BASE_DIR, "stress_test_leechers")


def generate_random_file(filename, size_kb):
    """Generate a file with random content of specified size in KB."""
    path = os.path.join(TEST_FILES_DIR, filename)
    with open(path, 'wb') as f:
        # Generate in chunks to avoid memory issues with large files
        chunk_size = 1024  # 1 KB chunks
        remaining = size_kb
        while remaining > 0:
            write_size = min(remaining, chunk_size)
            data = ''.join(random.choices(string.ascii_letters + string.digits, k=write_size)).encode()
            f.write(data)
            remaining -= 1
    
    logger.info(f"Generated test file {filename} ({size_kb} KB)")
    return path


def prepare_test_environment(num_seeders, num_leechers, files_per_seeder, file_sizes):
    """Prepare the test environment by creating files and directories."""
    logger.info("Preparing test environment...")
    
    # Create directories
    os.makedirs(TEST_FILES_DIR, exist_ok=True)
    
    # Clean up existing directories
    if os.path.exists(SEEDERS_DIR):
        shutil.rmtree(SEEDERS_DIR)
    if os.path.exists(LEECHERS_DIR):
        shutil.rmtree(LEECHERS_DIR)
    
    # Create fresh directories
    os.makedirs(SEEDERS_DIR)
    os.makedirs(LEECHERS_DIR)
    
    # Create seeder directories
    seeder_dirs = []
    for i in range(num_seeders):
        seeder_dir = os.path.join(SEEDERS_DIR, f"seeder_{i}")
        os.makedirs(seeder_dir)
        seeder_dirs.append(seeder_dir)
    
    # Create leecher directories
    leecher_dirs = []
    for i in range(num_leechers):
        leecher_dir = os.path.join(LEECHERS_DIR, f"leecher_{i}")
        os.makedirs(leecher_dir)
        leecher_dirs.append(leecher_dir)
    
    # Generate test files
    test_files = []
    total_files = num_seeders * files_per_seeder
    
    for i in range(total_files):
        # Select a random file size from the list
        size_kb = random.choice(file_sizes)
        filename = f"testfile_{i}_{size_kb}KB.dat"
        file_path = generate_random_file(filename, size_kb)
        test_files.append(file_path)
    
    # Distribute files to seeders
    file_distribution = defaultdict(list)
    for i, file_path in enumerate(test_files):
        seeder_idx = i // files_per_seeder
        if seeder_idx < len(seeder_dirs):  # Ensure we don't exceed the number of seeders
            dest_path = os.path.join(seeder_dirs[seeder_idx], os.path.basename(file_path))
            shutil.copy(file_path, dest_path)
            file_distribution[seeder_idx].append(os.path.basename(file_path))
    
    logger.info(f"Created {len(test_files)} test files distributed among {num_seeders} seeders")
    return seeder_dirs, leecher_dirs, file_distribution, test_files


def start_tracker(tracker_ip, tracker_port):
    """Start the tracker server."""
    logger.info(f"Starting tracker at {tracker_ip}:{tracker_port}")
    
    tracker_cmd = [
        sys.executable, 
        os.path.join(BASE_DIR, "tracker_server.py"),
        "--ip", tracker_ip, 
        "--port", str(tracker_port),
        "--log-level", "INFO"
    ]
    
    tracker_process = subprocess.Popen(
        tracker_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    
    # Give tracker time to initialize
    time.sleep(3)
    
    # Test if tracker is running
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    try:
        sock.sendto(b"TIME:", (tracker_ip, tracker_port))
        response, _ = sock.recvfrom(1024)
        logger.info(f"Tracker responded: {response.decode('utf-8')}")
    except Exception as e:
        logger.error(f"Tracker failed to respond: {e}")
        tracker_process.terminate()
        raise
    finally:
        sock.close()
    
    return tracker_process


def start_seeder(idx, seeder_dir, tracker_ip, tracker_port):
    """Start a seeder process."""
    port = 8000 + idx
    logger.info(f"Starting seeder {idx} at port {port} with files in {seeder_dir}")
    
    seeder_cmd = [
        sys.executable, 
        os.path.join(BASE_DIR, "seeder_client.py"),
        "--ip", "0.0.0.0", 
        "--port", str(port),
        "--tracker-ip", tracker_ip, 
        "--tracker-port", str(tracker_port),
        "--files-dir", seeder_dir,
        "--log-level", "INFO",
        "--quiet"  # Suppress verbose output
    ]
    
    seeder_process = subprocess.Popen(
        seeder_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    
    # Wait a bit for registration with tracker
    time.sleep(1)
    
    return port, seeder_process


def download_file(leecher_idx, file_to_download, leecher_dir, tracker_ip, tracker_port):
    """Download a file using a leecher client and measure performance."""
    port = 9000 + leecher_idx
    logger.info(f"Leecher {leecher_idx} (port {port}) starting download of {file_to_download}")
    
    start_time = time.time()
    
    leecher_cmd = [
        sys.executable, 
        os.path.join(BASE_DIR, "leecher_client.py"),
        "--ip", "0.0.0.0", 
        "--port", str(port),
        "--tracker-ip", tracker_ip, 
        "--tracker-port", str(tracker_port),
        "--files-dir", leecher_dir,
        "--file", file_to_download,
        "--log-level", "INFO"
    ]
    
    try:
        leecher_process = subprocess.Popen(
            leecher_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True  # To get string output
        )
        
        # Maximum time to wait for download
        max_wait_time = 300  # 5 minutes
        downloaded_file_path = os.path.join(leecher_dir, file_to_download)
        
        # Monitor the download
        while time.time() - start_time < max_wait_time:
            # Check if file exists and is complete
            if os.path.exists(downloaded_file_path):
                # Read some of the leecher output to check progress
                if leecher_process.poll() is None:  # Process still running
                    time.sleep(1)
                    continue
                
                # Process completed, check if file was downloaded
                end_time = time.time()
                duration = end_time - start_time
                
                # Get file size
                file_size = os.path.getsize(downloaded_file_path) / 1024  # KB
                
                # Verify the file against the original
                original_file_path = os.path.join(TEST_FILES_DIR, file_to_download)
                if os.path.getsize(downloaded_file_path) == os.path.getsize(original_file_path):
                    # Calculate speed
                    speed = file_size / duration  # KB/s
                    logger.info(f"Leecher {leecher_idx} downloaded {file_to_download} "
                               f"({file_size:.2f} KB) in {duration:.2f} s ({speed:.2f} KB/s)")
                    
                    return {
                        "leecher": leecher_idx,
                        "file": file_to_download,
                        "size_kb": file_size,
                        "duration_sec": duration,
                        "speed_kbps": speed,
                        "success": True
                    }
                
                # File exists but is incomplete
                logger.warning(f"Leecher {leecher_idx} download incomplete for {file_to_download}")
                return {
                    "leecher": leecher_idx,
                    "file": file_to_download,
                    "success": False,
                    "reason": "Incomplete download"
                }
            
            # Sleep and check again
            time.sleep(1)
        
        # If we get here, download timed out
        logger.error(f"Leecher {leecher_idx} download timed out for {file_to_download}")
        return {
            "leecher": leecher_idx,
            "file": file_to_download,
            "success": False,
            "reason": "Timeout"
        }
        
    except Exception as e:
        logger.error(f"Error running leecher {leecher_idx}: {e}")
        return {
            "leecher": leecher_idx,
            "file": file_to_download,
            "success": False,
            "reason": str(e)
        }
    finally:
        # Ensure process is terminated
        if 'leecher_process' in locals():
            try:
                leecher_process.terminate()
                leecher_process.wait(timeout=5)
            except:
                pass


def run_stress_test(args):
    """Run the full stress test."""
    try:
        # Prepare test files and directories
        seeder_dirs, leecher_dirs, file_distribution, test_files = prepare_test_environment(
            args.seeders, args.leechers, args.files_per_seeder, args.file_sizes
        )
        
        # Flatten the list of files for random assignment to leechers
        all_files = [os.path.basename(file) for file in test_files]
        
        # Start tracker
        tracker_process = start_tracker(args.tracker_ip, args.tracker_port)
        
        # Start seeders
        seeder_processes = {}
        for i, seeder_dir in enumerate(seeder_dirs):
            port, process = start_seeder(i, seeder_dir, args.tracker_ip, args.tracker_port)
            seeder_processes[i] = {
                "port": port,
                "process": process,
                "dir": seeder_dir
            }
        
        # Give seeders time to fully register with tracker
        logger.info("Waiting for seeders to register with the tracker...")
        time.sleep(5)
        
        # Randomly assign files to leechers for download
        download_tasks = []
        for i, leecher_dir in enumerate(leecher_dirs):
            # Each leecher will download 1-3 random files
            num_files = random.randint(1, min(3, len(all_files)))
            files_to_download = random.sample(all_files, num_files)
            
            for file in files_to_download:
                download_tasks.append((i, file, leecher_dir))
        
        # Perform downloads concurrently
        logger.info(f"Starting {len(download_tasks)} concurrent downloads...")
        results = []
        
        with ThreadPoolExecutor(max_workers=args.leechers) as executor:
            futures = []
            
            for leecher_idx, file, leecher_dir in download_tasks:
                future = executor.submit(
                    download_file, 
                    leecher_idx, 
                    file, 
                    leecher_dir, 
                    args.tracker_ip, 
                    args.tracker_port
                )
                futures.append(future)
            
            # Wait for all downloads to complete
            for future in futures:
                result = future.result()
                results.append(result)
        
        # Calculate and report results
        successful = [r for r in results if r.get("success", False)]
        failed = [r for r in results if not r.get("success", False)]
        
        logger.info("\n===== STRESS TEST RESULTS =====")
        logger.info(f"Total downloads: {len(results)}")
        logger.info(f"Successful: {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
        logger.info(f"Failed: {len(failed)} ({len(failed)/len(results)*100:.1f}%)")
        
        if successful:
            avg_speed = sum(r.get("speed_kbps", 0) for r in successful) / len(successful)
            avg_size = sum(r.get("size_kb", 0) for r in successful) / len(successful)
            avg_duration = sum(r.get("duration_sec", 0) for r in successful) / len(successful)
            
            logger.info(f"Average download speed: {avg_speed:.2f} KB/s")
            logger.info(f"Average file size: {avg_size:.2f} KB")
            logger.info(f"Average download time: {avg_duration:.2f} seconds")
        
        if failed:
            # Group failures by reason
            failures_by_reason = defaultdict(int)
            for f in failed:
                reason = f.get("reason", "Unknown")
                failures_by_reason[reason] += 1
            
            logger.info("Failure reasons:")
            for reason, count in failures_by_reason.items():
                logger.info(f"  - {reason}: {count}")
        
        return {
            "total": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful)/len(results) if results else 0,
            "avg_speed_kbps": avg_speed if successful else 0,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Stress test failed: {e}")
        raise
    finally:
        # Clean up processes
        logger.info("Cleaning up processes...")
        
        # Stop seeders
        if 'seeder_processes' in locals():
            for info in seeder_processes.values():
                try:
                    info["process"].terminate()
                    info["process"].wait(timeout=5)
                except:
                    pass
        
        # Stop tracker
        if 'tracker_process' in locals():
            try:
                tracker_process.terminate()
                tracker_process.wait(timeout=5)
            except:
                pass


def main():
    """Main entry point with command-line argument handling."""
    parser = argparse.ArgumentParser(description="P2P File Sharing System Stress Test")
    
    parser.add_argument("--tracker-ip", default=DEFAULT_TRACKER_IP,
                       help=f"Tracker IP address (default: {DEFAULT_TRACKER_IP})")
    parser.add_argument("--tracker-port", type=int, default=DEFAULT_TRACKER_PORT,
                       help=f"Tracker port (default: {DEFAULT_TRACKER_PORT})")
    parser.add_argument("--seeders", type=int, default=DEFAULT_SEEDERS,
                       help=f"Number of seeders to run (default: {DEFAULT_SEEDERS})")
    parser.add_argument("--leechers", type=int, default=DEFAULT_LEECHERS,
                       help=f"Number of leechers to run (default: {DEFAULT_LEECHERS})")
    parser.add_argument("--files-per-seeder", type=int, default=DEFAULT_FILES_PER_SEEDER,
                       help=f"Number of files per seeder (default: {DEFAULT_FILES_PER_SEEDER})")
    parser.add_argument("--file-sizes", type=int, nargs="+", default=DEFAULT_FILE_SIZES,
                       help=f"File sizes in KB (default: {DEFAULT_FILE_SIZES})")
    
    args = parser.parse_args()
    
    logger.info("Starting stress test with configuration:")
    logger.info(f"  Tracker: {args.tracker_ip}:{args.tracker_port}")
    logger.info(f"  Seeders: {args.seeders}")
    logger.info(f"  Leechers: {args.leechers}")
    logger.info(f"  Files per seeder: {args.files_per_seeder}")
    logger.info(f"  File sizes (KB): {args.file_sizes}")
    
    run_stress_test(args)


if __name__ == "__main__":
    main()