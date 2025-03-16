#!/usr/bin/env python3
"""
Standalone tracker server for P2P file sharing system.

Usage:
    python tracker_server.py --ip 0.0.0.0 --port 12345
"""

import argparse
import sys
import os
import logging
import time
import socket
import requests
import threading
import colorama
from datetime import datetime
from typing import List, Tuple

# Initialize colorama for cross-platform colored terminal output
colorama.init()

# Add the parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import tracker, udp_server, tracker_handlers

# Configure colored logging
class ColorFormatter(logging.Formatter):
    """Custom formatter with colored output"""
    
    COLORS = {
        'DEBUG': colorama.Fore.CYAN,
        'INFO': colorama.Fore.GREEN,
        'WARNING': colorama.Fore.YELLOW,
        'ERROR': colorama.Fore.RED,
        'CRITICAL': colorama.Fore.RED + colorama.Style.BRIGHT,
    }
    
    def format(self, record):
        # Get the original formatted message
        msg = super().format(record)
        # Add color based on log level
        return f"{self.COLORS.get(record.levelname, '')}{msg}{colorama.Style.RESET_ALL}"

def setup_logging(level=logging.INFO):
    """Setup logging with colors and formatting"""
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    logger = logging.getLogger()
    logger.setLevel(level)
    logger.addHandler(handler)
    
    # Set format for existing handlers
    for handler in logger.handlers:
        handler.setFormatter(ColorFormatter('%(asctime)s - %(levelname)s - %(message)s'))

def get_ip_addresses() -> List[Tuple[str, str]]:
    """Get all local IP addresses with their interface names."""
    ips = []
    try:
        # Get hostname
        hostname = socket.gethostname()
        # Get local IP by hostname
        local_ip = socket.gethostbyname(hostname)
        ips.append(("Hostname", f"{hostname} ({local_ip})"))
        
        # Get all network interfaces
        try:
            import netifaces
            for interface in netifaces.interfaces():
                try:
                    addresses = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in addresses:
                        for link in addresses[netifaces.AF_INET]:
                            ips.append((interface, link['addr']))
                except Exception:
                    pass
        except ImportError:
            logging.warning("netifaces module not found. Limited network information available.")
            
        # Fallback if no IPs found yet
        if len(ips) <= 1:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                ips.append(("Primary", local_ip))
            except Exception:
                pass
            finally:
                s.close()
    except Exception as e:
        logging.error(f"Error getting IP addresses: {e}")
    
    return ips

def get_public_ip() -> str:
    """Get the public IP address of this machine."""
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        return response.text
    except Exception as e:
        logging.warning(f"Could not determine public IP: {e}")
        return "Could not determine"

def monitor_connections():
    """Display active connections to the UDP server"""
    # Keep track of previously seen connections
    seen_connections = set()
    
    while True:
        try:
            # Track active seeders
            with tracker.seeders_lock:
                active_seeders = tracker.seeders.copy()
            
            if active_seeders:
                current_time = time.time()
                
                # Print seeder information
                print(f"\n{colorama.Fore.CYAN}==== Active Seeders ({len(active_seeders)}) ===={colorama.Style.RESET_ALL}")
                for ip, port, last_heartbeat in active_seeders:
                    time_since = current_time - last_heartbeat
                    if time_since < 60:
                        time_str = f"{time_since:.1f} seconds ago"
                    else:
                        time_str = f"{time_since/60:.1f} minutes ago"
                    
                    connection_key = f"{ip}:{port}"
                    if connection_key not in seen_connections:
                        # New connection
                        print(f"{colorama.Fore.GREEN}➕ NEW: {ip}:{port} - Last heartbeat: {time_str}{colorama.Style.RESET_ALL}")
                        seen_connections.add(connection_key)
                    else:
                        # Existing connection
                        print(f"{colorama.Fore.BLUE}✓ {ip}:{port} - Last heartbeat: {time_str}{colorama.Style.RESET_ALL}")
            else:
                print(f"\n{colorama.Fore.YELLOW}No active seeders connected.{colorama.Style.RESET_ALL}")
            
            # Also try to get actual socket connections if netstat is available
            try:
                import subprocess
                result = subprocess.run(['netstat', '-anu'], 
                                       capture_output=True, 
                                       text=True)
                connections = result.stdout.split('\n')
                udp_port = str(udp_server.server_address[1])
                udp_connections = [c for c in connections if f':{udp_port} ' in c]
                
                if udp_connections:
                    print(f"\n{colorama.Fore.CYAN}==== UDP Socket Connections ===={colorama.Style.RESET_ALL}")
                    for conn in udp_connections:
                        print(f"{colorama.Fore.WHITE}{conn.strip()}{colorama.Style.RESET_ALL}")
            except Exception:
                # Silently ignore errors (netstat might not be available)
                pass
                
        except Exception as e:
            logging.error(f"Error in monitor_connections: {e}")
            
        time.sleep(10)  # Check every 10 seconds

def enhance_udp_server_logging():
    """
    Patch the udp_server respond function to provide more verbose logging.
    This is a monkey patch that replaces the original function with our enhanced version.
    """
    original_respond = udp_server.respond
    
    def enhanced_respond():
        """Enhanced version of the respond function with better logging."""
        print(f"{colorama.Fore.GREEN}UDP Server started and ready to receive messages on {udp_server.server_address}{colorama.Style.RESET_ALL}")
        
        while True:
            try:
                # Wait for a message from a client
                message, client_address = udp_server.server_socket.recvfrom(2048)
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"\n{colorama.Fore.YELLOW}[{timestamp}] 📨 Received UDP message from {client_address}{colorama.Style.RESET_ALL}")
                logging.info(f"Received UDP message from {client_address}")

                # Decode the message
                try:
                    message_str = message.decode('utf-8')
                    print(f"{colorama.Fore.WHITE}   Message: {message_str}{colorama.Style.RESET_ALL}")
                except UnicodeDecodeError as e:
                    logging.error(f"Failed to decode message: {e}")
                    continue  # Skip this message and continue listening

                # Split the message into type and content
                try:
                    message_type, content = message_str.split(":", 1)
                except ValueError:
                    logging.error(f"Malformed message: {message_str}. Expected format: 'type:content'")
                    continue  # Skip this message and continue listening

                # Call the appropriate handler
                if message_type in udp_server.handlers:
                    try:
                        response = udp_server.handlers[message_type](content)
                        udp_server.server_socket.sendto(response.encode('utf-8'), client_address)
                        print(f"{colorama.Fore.CYAN}   Response: {response}{colorama.Style.RESET_ALL}")
                        logging.info(f"Sent response to {client_address}: {response}")
                    except Exception as e:
                        logging.error(f"Handler for '{message_type}' failed: {e}")
                else:
                    logging.warning(f"No handler found for message type: {message_type}")

            except Exception as e:
                logging.error(f"Unexpected error in respond thread: {e}")
                break  # Exit the loop on critical errors
    
    # Replace the original function with our enhanced version
    udp_server.respond = enhanced_respond

def enhance_tracker_logging():
    """
    Enhance the tracker module with more verbose logging.
    """
    original_register_seeder = tracker.register_seeder
    original_keep_alive = tracker.keep_alive
    original_seek_file = tracker.seek_file
    original_get_all_available_files = tracker.get_all_available_files
    
    def enhanced_register_seeder(seeder):
        """Enhanced version of register_seeder with better logging."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"\n{colorama.Fore.GREEN}[{timestamp}] Registration request from seeder: {seeder}{colorama.Style.RESET_ALL}")
        result = original_register_seeder(seeder)
        print(f"{colorama.Fore.WHITE}   Result: {result}{colorama.Style.RESET_ALL}")
        return result
    
    def enhanced_keep_alive(seeder):
        """Enhanced version of keep_alive with better logging."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"{colorama.Fore.BLUE}[{timestamp}] Heartbeat from seeder: {seeder}{colorama.Style.RESET_ALL}")
        result = original_keep_alive(seeder)
        return result
    
    def enhanced_seek_file(leecher, filename):
        """Enhanced version of seek_file with better logging."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"\n{colorama.Fore.MAGENTA}[{timestamp}] Leecher {leecher if leecher else 'unknown'} seeking file: {filename}{colorama.Style.RESET_ALL}")
        result = original_seek_file(leecher, filename)
        print(f"{colorama.Fore.WHITE}   Found {len(result)} seeders for {filename}{colorama.Style.RESET_ALL}")
        return result
    
    def enhanced_get_all_available_files():
        """Enhanced version of get_all_available_files with better logging."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"\n{colorama.Fore.CYAN}[{timestamp}] Request for all available files{colorama.Style.RESET_ALL}")
        result = original_get_all_available_files()
        print(f"{colorama.Fore.WHITE}   Found {len(result)} files: {result}{colorama.Style.RESET_ALL}")
        return result
    
    # Replace the original functions with our enhanced versions
    tracker.register_seeder = enhanced_register_seeder
    tracker.keep_alive = enhanced_keep_alive
    tracker.seek_file = enhanced_seek_file
    tracker.get_all_available_files = enhanced_get_all_available_files

def print_banner():
    """Print a nice banner for the tracker server."""
    banner = f"""
{colorama.Fore.CYAN}╔════════════════════════════════════════════════════════╗
║                                                        ║
║  {colorama.Fore.GREEN}P2P File Sharing - Tracker Server{colorama.Fore.CYAN}                   ║
║                                                        ║
║  {colorama.Fore.YELLOW}An implementation of a BitTorrent-like tracker server{colorama.Fore.CYAN}  ║
║  {colorama.Fore.YELLOW}for peer-to-peer file distribution{colorama.Fore.CYAN}                    ║
║                                                        ║
╚════════════════════════════════════════════════════════╝{colorama.Style.RESET_ALL}
"""
    print(banner)

def main():
    print_banner()
    
    # Setup argument parsing
    parser = argparse.ArgumentParser(description="P2P File Sharing Tracker Server")
    parser.add_argument('--ip', default='0.0.0.0', help='IP address to bind to (0.0.0.0 for all interfaces)')
    parser.add_argument('--port', type=int, default=12345, help='Port to listen on')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--monitor', action='store_true', help='Monitor active connections periodically')
    args = parser.parse_args()
    
    # Configure logging
    setup_logging(level=getattr(logging, args.log_level))
    
    # Add running flag to tracker
    tracker.running = True
    udp_server.running = True
    
    # Enhance the logging in the UDP server and tracker
    enhance_udp_server_logging()
    enhance_tracker_logging()
    
    # Set tracker server address
    udp_server.server_address = (args.ip, args.port)
    
    print(f"{colorama.Fore.GREEN}Starting tracker server on {args.ip}:{args.port}{colorama.Style.RESET_ALL}")
    
    # Register handlers
    tracker_handlers.register_handlers()
    
    try:
        # Start UDP server for tracker communication
        udp_server.start()
        
        # Display connection information
        print(f"\n{colorama.Fore.CYAN}=== TRACKER CONNECTION INFORMATION ==={colorama.Style.RESET_ALL}")
        print(f"{colorama.Fore.WHITE}Port: {args.port}{colorama.Style.RESET_ALL}")
        
        print(f"\n{colorama.Fore.CYAN}Local Network Addresses:{colorama.Style.RESET_ALL}")
        local_ips = get_ip_addresses()
        for interface, ip in local_ips:
            print(f"{colorama.Fore.WHITE}  - {interface}: {ip}{colorama.Style.RESET_ALL}")
        
        print(f"\n{colorama.Fore.CYAN}Public IP (for internet connections):{colorama.Style.RESET_ALL}")
        public_ip = get_public_ip()
        print(f"{colorama.Fore.WHITE}  - {public_ip}{colorama.Style.RESET_ALL}")
        
        print(f"\n{colorama.Fore.YELLOW}Connection instructions:{colorama.Style.RESET_ALL}")
        print(f"{colorama.Fore.WHITE}1. For connections within the same machine:")
        print(f"   IP: 127.0.0.1, Port: {args.port}")
        
        print("\n2. For connections within your local network:")
        print(f"   Use one of the local IPs above (not 0.0.0.0), Port: {args.port}")
        
        print("\n3. For connections over the internet:")
        print(f"   IP: {public_ip}, Port: {args.port}")
        print(f"   Note: You may need to configure port forwarding on your router{colorama.Style.RESET_ALL}")
        
        print(f"\n{colorama.Fore.GREEN}Tracker is running. Press Ctrl+C to stop...{colorama.Style.RESET_ALL}")

        # Start connection monitoring if requested
        if args.monitor:
            monitor_thread = threading.Thread(target=monitor_connections, daemon=True)
            monitor_thread.start()
            print(f"{colorama.Fore.BLUE}Connection monitoring enabled. Seeder status will update every 10 seconds.{colorama.Style.RESET_ALL}")
        
        # Keep the main thread alive
        while tracker.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n{colorama.Fore.YELLOW}Shutting down tracker server...{colorama.Style.RESET_ALL}")
        tracker.running = False
        udp_server.running = False
    except Exception as e:
        print(f"\n{colorama.Fore.RED}Error: {e}{colorama.Style.RESET_ALL}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
