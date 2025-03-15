import socket
import time
import threading
from datetime import datetime
import logging

# List of seeders
seeders = []
seeders_lock = threading.Lock()  # For atomic changes of seeders


def register_seeder(seeder):
    """
    Registers the seeder in the list as a tuple of its address and time received.

    Parameters:
    seeder (tuple): (IP Address, Port Number)

    Returns:
    str: Registration status message
    """
    try:
        current_time = time.time()
        
        # Check if this seeder already exists, and if so, just update the timestamp
        with seeders_lock:
            for i, (ip, port, _) in enumerate(seeders):
                if (ip, port) == seeder:
                    # Update timestamp for existing seeder
                    seeders[i] = (ip, port, current_time)
                    logging.info(f"Updated seeder {seeder} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")
                    return f"Updated: {seeder} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # If not found, add the new seeder
            logging.info(f"About to add seeder {seeder}")
            seeders.append((*seeder, current_time))
            logging.info(f"Registered seeder {seeder} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")
            return f"Registered: {seeder} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    except Exception as e:
        logging.error(f"Failed to register seeder: {e}")
        return f"Failed to Register seeder: {seeder}"


def keep_alive(seeder):
    """
    Updates the last heartbeat time for a given (IP, port) pair.
    
    Parameters:
    seeder (tuple): (IP Address, Port Number)
    
    Returns:
    str: Status message
    """
    logging.debug(f"Received heartbeat from {seeder}")
    current_time = time.time()
    with seeders_lock:
        for i, (ip, port, last_heartbeat) in enumerate(seeders):
            if (ip, port) == seeder:
                seeders[i] = (ip, port, current_time)
                return f"KeptAlive: {seeder}"
        # If not found, add it to the list
        seeders.append((*seeder, current_time))
    return f"Registered: {seeder}"


def remove_inactive_seeders():
    """Continuously removes servers with no heartbeat for more than 10 seconds."""
    global seeders

    while True:
        try:
            # If no seeders, wait a bit and check again
            if len(seeders) == 0:
                time.sleep(1)
                continue
                
            current_time = time.time()
            
            # Keep only the active seeders (with last_heartbeat within 10 seconds)
            with seeders_lock:  # Synchronize access
                # First deduplicate seeders by taking the most recent timestamp for each (IP, port) pair
                unique_seeders = {}
                for ip, port, last_heartbeat in seeders:
                    key = (ip, port)
                    if key not in unique_seeders or last_heartbeat > unique_seeders[key]:
                        unique_seeders[key] = last_heartbeat
                
                # Then filter by time and convert back to list format
                old_count = len(seeders)
                seeders[:] = [(ip, port, last_heartbeat) for (ip, port), last_heartbeat in unique_seeders.items()
                             if current_time - last_heartbeat <= 10]
                new_count = len(seeders)
                
                if old_count != new_count:
                    logging.info(f"Removed {old_count - new_count} inactive seeders. Active seeders: {len(seeders)}")
                    logging.debug(f"Updated seeders list: {seeders}")
        except Exception as e:
            logging.error(f"Error in remove_inactive_seeders: {e}")
            
        time.sleep(10)  # Check every 10 seconds


def seek_file(leecher, filename):
    """
    Returns a shortlist of seeders that have any non-zero chunks of the desired file.

    Parameters:
        leecher (tuple): (IP Address, Port Number) of the leecher requesting the file.
        filename (str): The name of the file being requested.

    Returns:
        list: A list of seeders (tuples of IP and port) that have non-zero chunks of the file.
    """
    shortlist = []

    # Get the list of active seeders
    with seeders_lock:
        active_seeders = [(ip, port) for ip, port, _ in seeders]
    
    # Query each seeder to check if they have the file
    for seeder_address in active_seeders:
        try:
            # Create TCP socket for communication
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
                    # Seeder has the file, add to shortlist
                    shortlist.append(seeder_address)
                    logging.info(f"Seeder {seeder_address} has {chunks} chunks of {filename}")
        except Exception as e:
            logging.error(f"Error querying seeder {seeder_address} for {filename}: {e}")

    logging.info(f"Found {len(shortlist)} seeders for {filename}")
    return shortlist


def get_all_available_files():
    """
    Get a list of all unique files available from all seeders using UDP.
    
    Returns:
        list: A list of all unique filenames available
    """
    all_files = set()
    
    # Get the list of active seeders
    with seeders_lock:
        active_seeders = [(ip, port) for ip, port, _ in seeders]
    
    # Create a UDP socket for querying seeders
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(10)  # Increased to 10 seconds
    logging.info(f"Requesting file list from {len(active_seeders)} active seeders")
    
    try:
        # Query each seeder for their available files
        for seeder_address in active_seeders:
            try:
                # Send the ListFiles request via UDP
                logging.info(f"Sending ListFiles request to {seeder_address}")
                request = "ListFiles:"
                udp_socket.sendto(request.encode('utf-8'), seeder_address)
                
                # Wait for response
                try:
                    response, _ = udp_socket.recvfrom(4096)
                    response = response.decode('utf-8')
                    
                    # Parse the response
                    if response.startswith("FilesList:"):
                        files_str = response.split(":", 1)[1]
                        try:
                            import ast
                            files = ast.literal_eval(files_str)
                            all_files.update(files)
                            logging.debug(f"Seeder {seeder_address} has files: {files}")
                        except Exception as e:
                            logging.error(f"Error parsing file list from {seeder_address}: {e}")
                except socket.timeout:
                    logging.warning(f"Timeout waiting for file list from {seeder_address}")
            except Exception as e:
                logging.error(f"Error querying seeder {seeder_address} for files: {e}")
    finally:
        udp_socket.close()
    
    return list(all_files)

def start_tracker():
    """Start the UDP tracker and keep it running, managing seeders and requests."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logging.info("Starting tracker...")
    
    # Start the remove_inactive_seeders function in a separate thread
    threading.Thread(target=remove_inactive_seeders, daemon=True).start()

    logging.info("Tracker started and running...")

    # Example: The tracker continues running indefinitely, handling peer requests
    while True:
        try:
            time.sleep(1)  # This keeps the main thread alive
        except KeyboardInterrupt:
            logging.info("Tracker shutting down...")
            break


if __name__ == "__main__":
    # Start the tracker (which will also run remove_inactive_seeders concurrently)
    start_tracker()