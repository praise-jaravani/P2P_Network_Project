import socket
import threading
import ast
import logging
from typing import Dict, List, Tuple

# Import the tracker module for access to the seeders list
from core import tracker

def have_file_question_handler(content: str) -> str:
    """
    Handler for "HaveFile?" message type. Queries all active seeders to check
    if they have a specific file and returns the list of seeders with the file.
    
    Args:
        content: The filename to check for
        
    Returns:
        String response with the number of chunks (0 if not found)
    """
    filename = content.strip()
    logging.info(f"Checking if seeders have file: {filename}")
    
    # Get the list of active seeders
    with tracker.seeders_lock:
        active_seeders = [(ip, port) for ip, port, _ in tracker.seeders]
    
    seeders_with_file = []
    
    # Query each seeder to check if they have the file
    for seeder_address in active_seeders:
        try:
            # Connect to the seeder using TCP
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(2)  # Short timeout
            client_socket.connect(seeder_address)
            
            # Send the HaveFile request
            request = f"HaveFile:{filename}"
            client_socket.send(request.encode('utf-8'))
            
            # Get the response
            response = client_socket.recv(1024).decode('utf-8')
            client_socket.close()
            
            # Check if the seeder has the file
            if response.startswith("HaveFile:"):
                chunks = int(response.split(":", 1)[1])
                if chunks > 0:
                    # Seeder has the file, add to list
                    seeders_with_file.append((seeder_address, chunks))
        except Exception as e:
            logging.error(f"Error querying seeder {seeder_address}: {e}")
    
    # Return the count of seeders with the file
    return f"HaveFile:{len(seeders_with_file)}"

def request_file_handler(content: str) -> str:
    """
    Handler for "RequestFile" message type. Returns a list of seeders 
    that have the requested file.
    
    Args:
        content: The filename requested
        
    Returns:
        String response with list of seeders that have the file
    """
    filename = content.strip()
    logging.info(f"Received request for file: {filename}")
    
    # Use the tracker's seek_file method to find seeders with the file
    seeders_with_file = tracker.seek_file(None, filename)
    
    # Return the list of seeders
    return f"RespondFile:{seeders_with_file}"

def have_file_handler(content: str) -> str:
    """
    Handler for "HaveFile" message type. Used by seeders to report
    how many chunks of a file they have.
    
    Args:
        content: Tuple of (chunks, filename)
        
    Returns:
        Acknowledgment string
    """
    try:
        # Parse the content (expecting a tuple of chunks and filename)
        chunks, filename = ast.literal_eval(content)
        logging.info(f"Seeder reports having {chunks} chunks of {filename}")
        
        # In a real implementation, we would store this information
        # For now, just acknowledge the receipt
        return f"Received:HaveFile:{chunks}:{filename}"
    except Exception as e:
        logging.error(f"Error parsing HaveFile content: {e}")
        return f"Error:InvalidFormat"

def list_files_handler(content: str) -> str:
    """
    Handler for "ListFiles" message type. Returns a list of all available files.
    
    Args:
        content: Empty string (not used)
        
    Returns:
        String response with list of all files available from seeders
    """
    logging.info("Received request for list of available files")
    
    # Get all available files using the tracker's method
    all_files = tracker.get_all_available_files()
    
    # Return the list of files
    return f"FilesList:{all_files}"

# Register these handlers with the UDP server
def register_handlers():
    """Register all the handlers with the UDP server."""
    try:
        from core import udp_server
        udp_server.register_handler("HaveFile?", have_file_question_handler)
        udp_server.register_handler("RequestFile", request_file_handler)
        udp_server.register_handler("HaveFile", have_file_handler)
        udp_server.register_handler("ListFiles", list_files_handler)  # New handler
        logging.info("Registered tracker handlers with UDP server")
    except ImportError as e:
        logging.error(f"Failed to import udp_server module: {e}")
    except Exception as e:
        logging.error(f"Error registering handlers: {e}")