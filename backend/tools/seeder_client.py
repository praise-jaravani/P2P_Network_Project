#!/usr/bin/env python3
"""
Standalone seeder client for P2P file sharing system.

Usage:
    python seeder_client.py --ip 192.168.1.100 --port 8000 --tracker-ip 192.168.1.101 --tracker-port 12345 --files-dir ./my_files

This seeder will:
1. Connect to the specified tracker
2. Watch the specified files directory for any files
3. Make these files available for download by other peers
4. Stay running until manually stopped (Ctrl+C)
"""

import argparse
import sys
import os
import time
import logging
import threading
import colorama
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Initialize colorama
colorama.init()

# Add the parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.p2p_client import P2PClient

# Custom file watcher to detect changes in the files directory
class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, seeder):
        self.seeder = seeder
        
    def on_created(self, event):
        if not event.is_directory and Path(event.src_path).is_file():
            print(f"{colorama.Fore.GREEN}[+] New file detected: {Path(event.src_path).name}{colorama.Style.RESET_ALL}")
            self.seeder.rescan_files()
            
    def on_deleted(self, event):
        if not event.is_directory:
            print(f"{colorama.Fore.RED}[-] File removed: {Path(event.src_path).name}{colorama.Style.RESET_ALL}")
            self.seeder.rescan_files()
            
    def on_modified(self, event):
        if not event.is_directory and Path(event.src_path).is_file():
            print(f"{colorama.Fore.BLUE}[*] File modified: {Path(event.src_path).name}{colorama.Style.RESET_ALL}")
            self.seeder.rescan_files()

def setup_logging(level=logging.INFO):
    """Configure colored logging"""
    class ColorFormatter(logging.Formatter):
        COLORS = {
            'DEBUG': colorama.Fore.CYAN,
            'INFO': colorama.Fore.GREEN,
            'WARNING': colorama.Fore.YELLOW,
            'ERROR': colorama.Fore.RED,
            'CRITICAL': colorama.Fore.RED + colorama.Style.BRIGHT,
        }
        
        def format(self, record):
            msg = super().format(record)
            return f"{self.COLORS.get(record.levelname, '')}{msg}{colorama.Style.RESET_ALL}"
    
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicates
    for hdlr in logger.handlers[:]:
        logger.removeHandler(hdlr)
    
    logger.addHandler(handler)

def print_banner():
    """Print a nice banner for the seeder client"""
    banner = f"""
{colorama.Fore.CYAN}╔════════════════════════════════════════════════════════╗
║                                                        ║
║  {colorama.Fore.GREEN}P2P File Sharing - Seeder Client{colorama.Fore.CYAN}                    ║
║                                                        ║
║  {colorama.Fore.YELLOW}A peer that shares files with the network{colorama.Fore.CYAN}                ║
║  {colorama.Fore.YELLOW}Files placed in the specified directory will be seeded{colorama.Fore.CYAN}   ║
║                                                        ║
╚════════════════════════════════════════════════════════╝{colorama.Style.RESET_ALL}
"""
    print(banner)

def status_monitor(seeder, files_dir):
    """Periodically display status information"""
    while True:
        try:
            # Scan files again to make sure we have the latest
            files = seeder.rescan_files()
            
            print(f"\n{colorama.Fore.CYAN}==== Seeder Status @ {datetime.now().strftime('%H:%M:%S')} ===={colorama.Style.RESET_ALL}")
            
            # Show seeder information
            print(f"{colorama.Fore.WHITE}Seeder address: {seeder.ip}:{seeder.port}")
            print(f"Tracker address: {seeder.tracker_address[0]}:{seeder.tracker_address[1]}")
            print(f"Files directory: {os.path.abspath(files_dir)}")
            
            # Show file information
            if files:
                print(f"\n{colorama.Fore.GREEN}Currently seeding {len(files)} files:{colorama.Style.RESET_ALL}")
                for i, filename in enumerate(sorted(files), 1):
                    file_path = Path(files_dir) / filename
                    file_size = file_path.stat().st_size
                    
                    # Format file size
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    elif file_size < 1024 * 1024 * 1024:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    else:
                        size_str = f"{file_size / (1024 * 1024 * 1024):.1f} GB"
                    
                    print(f"{colorama.Fore.WHITE}{i}. {filename} ({size_str}){colorama.Style.RESET_ALL}")
            else:
                print(f"\n{colorama.Fore.YELLOW}No files currently being seeded.{colorama.Style.RESET_ALL}")
                print(f"{colorama.Fore.WHITE}Place files in {os.path.abspath(files_dir)} to share them.{colorama.Style.RESET_ALL}")
                
            # Instructions
            print(f"\n{colorama.Fore.BLUE}Instructions:{colorama.Style.RESET_ALL}")
            print(f"{colorama.Fore.WHITE}- Add files to {os.path.abspath(files_dir)} to make them available for sharing")
            print(f"- Remove files from the directory to stop sharing them")
            print(f"- Press Ctrl+C to stop the seeder{colorama.Style.RESET_ALL}")
            
        except Exception as e:
            logging.error(f"Error in status monitor: {e}")
            
        time.sleep(30)  # Update every 30 seconds

def main():
    print_banner()
    
    # Setup argument parsing
    parser = argparse.ArgumentParser(description="P2P File Sharing Seeder Client")
    parser.add_argument('--ip', default='0.0.0.0', help='IP address to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to listen on')
    parser.add_argument('--tracker-ip', required=True, help='Tracker server IP address')
    parser.add_argument('--tracker-port', type=int, default=12345, help='Tracker server port')
    parser.add_argument('--files-dir', default='./files', help='Directory containing files to share')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--quiet', action='store_true', help='Reduce output verbosity')
    args = parser.parse_args()
    
    # Configure logging
    setup_logging(level=getattr(logging, args.log_level))
    
    # Ensure files directory exists
    files_dir = os.path.abspath(args.files_dir)
    os.makedirs(files_dir, exist_ok=True)
    
    print(f"{colorama.Fore.GREEN}Starting seeder on {args.ip}:{args.port}{colorama.Style.RESET_ALL}")
    print(f"{colorama.Fore.GREEN}Connecting to tracker at {args.tracker_ip}:{args.tracker_port}{colorama.Style.RESET_ALL}")
    print(f"{colorama.Fore.GREEN}Serving files from {files_dir}{colorama.Style.RESET_ALL}")
    
    try:
        # Create seeder client
        seeder = P2PClient(
            mode="seeder",
            ip=args.ip,
            port=args.port,
            file_directory=files_dir,
            tracker_address=(args.tracker_ip, args.tracker_port)
        )
        
        # Start the seeder
        seeder.start()
        
        # Setup file monitoring
        event_handler = FileChangeHandler(seeder)
        observer = Observer()
        observer.schedule(event_handler, files_dir, recursive=False)
        observer.start()
        
        # Display initial files
        files = seeder.rescan_files()
        if files:
            print(f"\n{colorama.Fore.GREEN}Initially sharing {len(files)} files:{colorama.Style.RESET_ALL}")
            for i, filename in enumerate(sorted(files), 1):
                file_path = Path(files_dir) / filename
                file_size = file_path.stat().st_size
                
                # Format file size
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                elif file_size < 1024 * 1024 * 1024:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{file_size / (1024 * 1024 * 1024):.1f} GB"
                
                print(f"{colorama.Fore.WHITE}{i}. {filename} ({size_str}){colorama.Style.RESET_ALL}")
        else:
            print(f"\n{colorama.Fore.YELLOW}No files found in the specified directory.{colorama.Style.RESET_ALL}")
            print(f"{colorama.Fore.WHITE}Add files to {files_dir} to make them available for sharing.{colorama.Style.RESET_ALL}")
        
        # Start the status monitor thread if not in quiet mode
        if not args.quiet:
            monitor_thread = threading.Thread(target=status_monitor, args=(seeder, files_dir), daemon=True)
            monitor_thread.start()
        
        # Keep seeder running until interrupted
        print(f"\n{colorama.Fore.GREEN}Seeder is running. Press Ctrl+C to stop.{colorama.Style.RESET_ALL}")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n{colorama.Fore.YELLOW}Shutting down seeder...{colorama.Style.RESET_ALL}")
        observer.stop()
        observer.join()
        seeder.stop()
        print(f"{colorama.Fore.GREEN}Seeder stopped successfully.{colorama.Style.RESET_ALL}")
    except Exception as e:
        print(f"{colorama.Fore.RED}Error: {e}{colorama.Style.RESET_ALL}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())