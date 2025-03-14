#!/usr/bin/env python3
"""
Standalone leecher client for P2P file sharing system.

Usage:
    python leecher_client.py --ip 192.168.1.102 --port 9000 --tracker-ip 192.168.1.101 --tracker-port 12345 --files-dir ./downloads
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
    parser = argparse.ArgumentParser(description="P2P File Sharing Leecher Client")
    parser.add_argument('--ip', default='0.0.0.0', help='IP address to bind to')
    parser.add_argument('--port', type=int, default=9000, help='Port to listen on')
    parser.add_argument('--tracker-ip', required=True, help='Tracker server IP address')
    parser.add_argument('--tracker-port', type=int, default=12345, help='Tracker server port')
    parser.add_argument('--files-dir', default='./downloads', help='Directory to save downloaded files')
    parser.add_argument('--become-seeder', action='store_true', help='Become a seeder after downloading')
    parser.add_argument('--file', help='Optional: Immediately download this file')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ensure download directory exists
    os.makedirs(args.files_dir, exist_ok=True)
    
    # Create leecher client
    leecher = P2PClient(
        mode="leecher",
        ip=args.ip,
        port=args.port,
        file_directory=args.files_dir,
        tracker_address=(args.tracker_ip, args.tracker_port),
        become_seeder_after_download=args.become_seeder
    )
    
    print(f"Starting leecher on {args.ip}:{args.port}")
    print(f"Connecting to tracker at {args.tracker_ip}:{args.tracker_port}")
    print(f"Downloads will be saved to {os.path.abspath(args.files_dir)}")
    
    try:
        # Start the leecher
        leecher.start()
        
        # If a file was specified, download it
        if args.file:
            print(f"\nRequesting download of {args.file}...")
            success = leecher.request_file(args.file)
            
            if success:
                print(f"Download of {args.file} initiated.")
            else:
                print(f"Failed to initiate download of {args.file}.")
        
        # Interactive loop for user commands
        print("\nLeecher is running. Type 'help' for available commands.")
        while True:
            cmd = input("> ").strip().lower()
            
            if cmd == "quit" or cmd == "exit":
                break
            elif cmd == "help":
                print("Available commands:")
                print("  list      - List available files from tracker")
                print("  download  - Download a file")
                print("  status    - Show download status")
                print("  files     - Show downloaded files")
                print("  exit/quit - Exit the program")
            elif cmd == "list":
                # Request list of files from tracker
                print("Requesting available files from tracker...")
                # This would need to be implemented in p2p_client.py
                files = leecher.get_available_files()
                if files:
                    print(f"\nAvailable files ({len(files)}):")
                    for i, filename in enumerate(sorted(files), 1):
                        print(f"{i}. {filename}")
                else:
                    print("No files available for download.")
            elif cmd == "download":
                # Get list of files first
                files = leecher.get_available_files()
                if not files:
                    print("No files available for download.")
                    continue
                
                print("\nAvailable files:")
                for i, filename in enumerate(sorted(files), 1):
                    print(f"{i}. {filename}")
                
                file_choice = input("\nEnter the number of the file to download (or 0 to cancel): ")
                try:
                    file_index = int(file_choice) - 1
                    if file_index < 0:
                        continue
                    
                    filename = sorted(files)[file_index]
                    print(f"\nRequesting download of {filename}...")
                    success = leecher.request_file(filename)
                    
                    if success:
                        print(f"Download of {filename} initiated successfully.")
                    else:
                        print(f"Failed to initiate download of {filename}.")
                except (ValueError, IndexError):
                    print("Invalid selection.")
            elif cmd == "status":
                # Show download status
                status = leecher.get_download_status()
                
                print("\nCurrent downloads:")
                if not status["current_downloads"]:
                    print("No active downloads.")
                else:
                    for download in status["current_downloads"]:
                        print(f"- {download['filename']}: {download['progress']} (Seeders: {download['seeders']})")
                
                print("\nCompleted downloads:")
                if not status["completed_downloads"]:
                    print("No completed downloads.")
                else:
                    for filename in status["completed_downloads"]:
                        print(f"- {filename}")
            elif cmd == "files":
                # Show downloaded files
                if not leecher.files:
                    print("No files have been downloaded yet.")
                else:
                    print("\nDownloaded files:")
                    for i, filename in enumerate(sorted(leecher.files), 1):
                        print(f"{i}. {filename}")
            else:
                print(f"Unknown command: {cmd}. Type 'help' for available commands.")
            
    except KeyboardInterrupt:
        print("\nShutting down leecher...")
        leecher.stop()
    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())