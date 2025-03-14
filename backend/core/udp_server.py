import socket
from datetime import datetime
import threading
import ast
import logging
import os
import time

from core import tracker

# Server setup (default values)
DEFAULT_IP = "0.0.0.0"  # Listen on all interfaces by default
DEFAULT_PORT = 12345

# Get IP and port from environment variables if available
server_ip = os.environ.get("TRACKER_IP", DEFAULT_IP)
server_port = int(os.environ.get("TRACKER_PORT", DEFAULT_PORT))
server_address = (server_ip, server_port)

# Create UDP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Add reuse socket option before binding
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Handlers dictionary
handlers = {}

def configure_server(ip=None, port=None):
    """
    Configure the server with specified IP and port.
    
    Args:
        ip: IP address to bind to (default: from environment or 0.0.0.0)
        port: Port to bind to (default: from environment or 12345)
    """
    global server_address
    
    if ip is not None:
        server_address = (ip, server_address[1])
    
    if port is not None:
        server_address = (server_address[0], port)
    
    logging.info(f"UDP Server configured to bind to {server_address[0]}:{server_address[1]}")

def bind_server():
    """Bind the server socket to the configured address"""
    try:
        server_socket.bind(server_address)
        logging.info(f"UDP Server bound to {server_address[0]}:{server_address[1]}")
        return True
    except OSError as e:
        if e.errno == 98:  # Address already in use
            logging.warning("Warning: UDP Server address already in use, continuing anyway")
            return True
        else:
            logging.error(f"Error binding UDP socket: {e}")
            return False

def start():
    """Start the UDP server listening for requests."""
    # Configure logging if not already configured
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Bind the server socket
    if not bind_server():
        return False
    
    # Start listener thread
    listener_thread = threading.Thread(target=respond, daemon=True)
    listener_thread.start()

    logging.info("UDP Server is running and listening for requests...")
    return True

def register_handler(message_type, handler):
    """Register a handler function for a specific message type."""
    handlers[message_type] = handler
    logging.debug(f"Registered handler for message type: {message_type}")

def respond():
    """Listen for incoming messages and call the appropriate handler."""
    while True:
        try:
            # Wait for a message from a client
            message, client_address = server_socket.recvfrom(2048)
            logging.debug(f"Received message from {client_address}: {message.decode()}")

            # Decode the message
            try:
                message = message.decode('utf-8')
            except UnicodeDecodeError as e:
                logging.error(f"Failed to decode message: {e}")
                continue  # Skip this message and continue listening

            # Split the message into type and content
            try:
                message_type, content = message.split(":", 1)
            except ValueError:
                logging.error(f"Malformed message: {message}. Expected format: 'type:content'")
                continue  # Skip this message and continue listening

            # Call the appropriate handler
            if message_type in handlers:
                try:
                    response = handlers[message_type](content)
                    server_socket.sendto(response.encode('utf-8'), client_address)
                    logging.debug(f"Sent response to {client_address}: {response}")
                except Exception as e:
                    logging.error(f"Handler for '{message_type}' failed: {e}")
            else:
                logging.warning(f"No handler found for message type: {message_type}")

        except Exception as e:
            logging.error(f"Unexpected error in respond thread: {e}")
            break  # Exit the loop on critical errors

def make_tuple(seeder_str):
    """Convert a string like "('127.0.0.1', 54321)" to a tuple ('127.0.0.1', 54321)"""
    return ast.literal_eval(seeder_str)

def register_seeder_handler(seeder):
    """
    Liaises with tracker to register this seeder

    Parameters:
        seeder (tuple): (IP Address, Port Number)

    Returns:
        str: Registration status message
    """
    logging.debug(f"UDP Server received seeder like: {seeder}")
    try:
        seeder = make_tuple(seeder)
        logging.debug(f"Parsed seeder tuple: {seeder}")
        return tracker.register_seeder(seeder)
    except Exception as e:
        logging.error(f"Error registering seeder: {e}")
        return f"Error: {str(e)}"

def keep_alive_handler(seeder):
    """
    Sends a heart beat to the tracker for keeping this seeder alive.

    Parameters:
        seeder (tuple): (IP Address, Port Number)
        
    Returns:
        str: Status message
    """
    logging.debug(f"UDP Server received heartbeat from: {seeder}")
    try:
        seeder = make_tuple(seeder)
        logging.debug(f"Parsed seeder tuple: {seeder}")
        return tracker.keep_alive(seeder)
    except Exception as e:
        logging.error(f"Error processing heartbeat: {e}")
        return f"Error: {str(e)}"

def have_file_question_handler(content):
    """
    Handler for "HaveFile?" message type. Used by the tracker to ask seeders
    if they have a specific file.
    
    Args:
        content: String containing the filename to check
        
    Returns:
        Response string with the list of seeders that have the file
    """
    filename = content.strip()
    logging.info(f"Checking seeders for file: {filename}")
    
    # Use the tracker's seek_file method to find seeders with the file
    seeders_with_file = tracker.seek_file(None, filename)
    
    # Return the list of seeders that have the file
    return f"RespondFile:{seeders_with_file}"

def request_file_handler(content):
    """
    Handler for "RequestFile" message type. Returns list of seeders
    that have the requested file.
    
    Args:
        content: String containing the filename to find
        
    Returns:
        Response string with list of seeders with the file
    """
    filename = content.strip()
    logging.info(f"Received request for file: {filename}")
    
    # Use the tracker's seek_file method to find seeders
    seeders_with_file = tracker.seek_file(None, filename)
    
    # Return the list of seeders
    return f"RespondFile:{seeders_with_file}"

def list_files_handler(content):
    """
    Handler for "ListFiles" message type. Returns a list of all files
    available from all seeders.
    
    Args:
        content: Empty string (not used)
        
    Returns:
        Response string with list of all available files
    """
    logging.info("Received request for list of all available files")
    
    # Get all available files
    all_files = tracker.get_all_available_files()
    
    # Return the list of files
    return f"FilesList:{all_files}"

# Example handler functions
def greet_handler(name):
    return f"Hello, {name}!"

def time_handler(_):
    return f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

# Initialize handlers dictionary with default handlers
handlers = {
    "Register": register_seeder_handler,
    "HeartBeat": keep_alive_handler,
    "GREET": greet_handler,
    "TIME": time_handler,
    "HaveFile?": have_file_question_handler,
    "RequestFile": request_file_handler,
    "ListFiles": list_files_handler,
}

if __name__ == "__main__":
    """Test the UDP server directly"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.info("Starting UDP server...")
    start()
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("UDP server shutting down...")