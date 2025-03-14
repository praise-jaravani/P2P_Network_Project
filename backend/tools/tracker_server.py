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
from typing import List, Tuple

# Add the parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import tracker, udp_server, tracker_handlers

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
        # Fallback if netifaces is not available
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            ips.append(("Primary", local_ip))
            s.close()
        except Exception:
            pass
    
    return ips

def get_public_ip() -> str:
    """Get the public IP address of this machine."""
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        return response.text
    except Exception:
        return "Could not determine"

def monitor_connections():
    """Display active connections to the UDP server every 5 seconds."""
    while True:
        try:
            import subprocess
            result = subprocess.run(['netstat', '-anu'], 
                                   capture_output=True, 
                                   text=True)
            connections = result.stdout.split('\n')
            udp_connections = [c for c in connections if ':12345 ' in c]
            
            if udp_connections:
                print("\n=== Active UDP Connections ===")
                for conn in udp_connections:
                    print(conn.strip())
                print("===============================")
        except Exception as e:
            pass  # Silently fail if netstat is not available
            
        time.sleep(5)

def enhance_udp_server_logging():
    """
    Patch the udp_server respond function to provide more verbose logging.
    This is a monkey patch that replaces the original function with our enhanced version.
    """
    original_respond = udp_server.respond
    
    def enhanced_respond():
        """Enhanced version of the respond function with better logging."""
        while True:
            try:
                # Wait for a message from a client
                message, client_address = udp_server.server_socket.recvfrom(2048)
                print(f"\n⭐ Received UDP message from {client_address}")
                logging.info(f"⭐ Received UDP message from {client_address}")

                # Decode the message
                try:
                    message_str = message.decode('utf-8')
                    print(f"   Message: {message_str}")
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
                        print(f"   Response: {response}")
                        logging.info(f"⭐ Sent response to {client_address}: {response}")
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
    
    def enhanced_register_seeder(seeder):
        """Enhanced version of register_seeder with better logging."""
        print(f"\n🆕 Registration request from seeder: {seeder}")
        result = original_register_seeder(seeder)
        print(f"   Result: {result}")
        return result
    
    def enhanced_keep_alive(seeder):
        """Enhanced version of keep_alive with better logging."""
        print(f"\n💓 Heartbeat from seeder: {seeder}")
        result = original_keep_alive(seeder)
        print(f"   Result: {result}")
        return result
    
    def enhanced_seek_file(leecher, filename):
        """Enhanced version of seek_file with better logging."""
        print(f"\n🔍 Leecher {leecher} seeking file: {filename}")
        result = original_seek_file(leecher, filename)
        print(f"   Found {len(result)} seeders for {filename}")
        return result
    
    # Replace the original functions with our enhanced versions
    tracker.register_seeder = enhanced_register_seeder
    tracker.keep_alive = enhanced_keep_alive
    tracker.seek_file = enhanced_seek_file

def main():
    # Setup argument parsing
    parser = argparse.ArgumentParser(description="P2P File Sharing Tracker Server")
    parser.add_argument('--ip', default='0.0.0.0', help='IP address to bind to (0.0.0.0 for all interfaces)')
    parser.add_argument('--port', type=int, default=12345, help='Port to listen on')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    parser.add_argument('--monitor', action='store_true', help='Monitor active connections')
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Enhance the logging in the UDP server and tracker
    enhance_udp_server_logging()
    enhance_tracker_logging()
    
    # Set tracker server address
    udp_server.server_address = (args.ip, args.port)
    
    print(f"Starting tracker server on {args.ip}:{args.port}")
    
    # Register handlers
    tracker_handlers.register_handlers()
    
    try:
        # Start UDP server for tracker communication
        udp_server.start()
        
        # Display connection information
        print("\n=== TRACKER CONNECTION INFORMATION ===")
        print(f"Port: {args.port}")
        
        print("\nLocal Network Addresses:")
        local_ips = get_ip_addresses()
        for interface, ip in local_ips:
            print(f"  - {interface}: {ip}")
        
        print("\nPublic IP (for internet connections):")
        public_ip = get_public_ip()
        print(f"  - {public_ip}")
        
        print("\nConnection instructions:")
        print("1. For connections within the same machine:")
        print(f"   IP: 127.0.0.1, Port: {args.port}")
        
        print("2. For connections within your local network:")
        print(f"   Use one of the local IPs above (not 0.0.0.0), Port: {args.port}")
        
        print("3. For connections over the internet:")
        print(f"   IP: {public_ip}, Port: {args.port}")
        print("   Note: You may need to configure port forwarding on your router")
        
        print("\nTracker is running. Press Ctrl+C to stop...")

        # Start connection monitoring if requested
        if args.monitor:
            import threading
            monitor_thread = threading.Thread(target=monitor_connections, daemon=True)
            monitor_thread.start()
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down tracker server...")
    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())