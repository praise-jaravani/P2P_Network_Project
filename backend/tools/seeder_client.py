#!/usr/bin/env python3
"""
Standalone seeder client for P2P file sharing system.

Usage:
    python seeder_client.py --ip 192.168.1.100 --port 8000 --tracker-ip 192.168.1.101 --tracker-port 12345 --files-dir ./my_files
"""

import argparse
import sys
import os
import time
import logging

# Add the parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.p2p_client import P2PClient

def main():
    # Setup argument parsing
    parser = argparse.ArgumentParser(description="P2P File Sharing Seeder Client")
    parser.add_argument('--ip', default='0.0.0.0', help='IP address to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to listen on')
    parser.add_argument('--tracker-ip', required=True, help='Tracker server IP address')
    parser.add_argument('--tracker-port', type=int, default=12345, help='Tracker server port')
    parser.add_argument('--files-dir', default='./files', help='Directory containing files to share')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ensure files directory exists
    os.makedirs(args.files_dir, exist_ok=True)
    
    # Create seeder client
    seeder = P2PClient(
        mode="seeder",
        ip=args.ip,
        port=args.port,
        file_directory=args.files_dir,
        tracker_address=(args.tracker_ip, args.tracker_port)
    )
    
    print(f"Starting seeder on {args.ip}:{args.port}")
    print(f"Connecting to tracker at {args.tracker_ip}:{args.tracker_port}")
    print(f"Serving files from {os.path.abspath(args.files_dir)}")
    
    try:
        # Start the seeder
        seeder.start()
        
        # Display available files
        files = seeder.rescan_files()
        if files:
            print(f"\nSharing {len(files)} files:")
            for file in files:
                print(f"  - {file}")
        else:
            print("\nNo files found in the specified directory.")
        
        # Keep seeder running until interrupted
        print("\nSeeder is running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down seeder...")
        seeder.stop()
    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())