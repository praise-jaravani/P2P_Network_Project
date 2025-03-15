import os
import time
import socket
import threading
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set, Union
import ast
import hashlib

# Import the file chunker for file operations
from core.file_chunker import FileChunker

class P2PClient:
    """
    A Peer-to-Peer client that can act as either a seeder or a leecher.
    
    Seeders:
    - Host files and serve chunks to leechers
    - Register with the tracker and send heartbeats
    - Respond to "HaveFile" queries

    Leechers:
    - Request file information from the tracker
    - Download chunks from multiple seeders in parallel
    - Reassemble chunks into complete files
    - Can transition to seeder mode after download
    """
    
    def __init__(self, mode: str, ip: str, port: int, 
                file_directory: str, tracker_address: tuple,
                become_seeder_after_download: bool = True,
                chunk_size: int = 512 * 1024,
                log_level: str = "INFO"):
        """
        Initialize a P2P client.
        
        Args:
            mode: Either 'seeder' or 'leecher'
            ip: IP address of this client
            port: Port number for this client's TCP server
            file_directory: Directory where files are stored or downloaded
            tracker_address: (IP, port) of the tracker server
            become_seeder_after_download: Whether leecher should become seeder after download
            chunk_size: Size of file chunks in bytes (default: 512 KB)
            log_level: Logging level (default: INFO)
        """
        # Configure logging
        self.logger = logging.getLogger(f"P2PClient-{mode}-{port}")
        numeric_level = getattr(logging, log_level.upper(), None)
        if not numeric_level:
            numeric_level = logging.INFO
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(numeric_level)
        
        # Basic client info
        self.mode = mode.lower()
        self.ip = ip
        self.port = port
        self.address = (ip, port)
        self.file_directory = Path(file_directory)
        self.tracker_address = tracker_address
        self.become_seeder_after_download = become_seeder_after_download
        
        # Create directory if it doesn't exist
        self.file_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize file chunker
        self.chunker = FileChunker(chunk_size=chunk_size)
        
        # Shared resources
        self.files = []  # List of available files
        self.running = False
        self.threads = []
        self.has_seeder_capability = False
        
        # Initialize based on mode
        if self.mode == 'seeder':
            self._init_seeder()
        elif self.mode == 'leecher':
            self._init_leecher()
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'seeder' or 'leecher'")
        
        self.logger.info(f"P2P client initialized: {mode} at {ip}:{port}")
    
    # ===== Initialization methods =====
    
    def _init_seeder(self):
        """Initialize seeder-specific resources"""
        # Scan for available files
        self.files = self._scan_files()
        self.logger.info(f"Seeder initialized with {len(self.files)} files")
        
        # TCP server for serving file chunks
        self.tcp_socket = None
        self.tcp_thread = None
        
        # Thread for sending heartbeats to tracker
        self.heartbeat_thread = None
        self.heartbeat_interval = 5  # seconds
    
    def _init_leecher(self):
        """Initialize leecher-specific resources"""
        # Download tracking
        self.download_queue = []  # Files queued for download
        self.current_downloads = {}  # {filename: {chunk_idx: status}}
        self.downloaded_files = []  # Successfully downloaded files
        
        # Storage for partial downloads
        self.temp_directory = self.file_directory / "temp"
        self.temp_directory.mkdir(exist_ok=True)
        
        self.logger.info("Leecher initialized")
    
    def _scan_files(self) -> List[str]:
        """
        Scan the file directory for available files.
        
        Returns:
            List of filenames available to share
        """
        files = []
        for file_path in self.file_directory.glob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                files.append(file_path.name)
        return files
    
    # ===== Main client methods =====
    
    def start(self):
        """Start the P2P client based on its mode"""
        if self.running:
            self.logger.info("Client already running")
            return
        
        self.running = True
        
        # Register with tracker
        success = self.register_with_tracker()
        if not success:
            self.logger.error("Failed to register with tracker")
            self.running = False
            return
        
        if self.mode == 'seeder' or self.has_seeder_capability:
            # Start UDP listener for direct messages (like ListFiles requests)
            self.start_udp_listener()
            
            # Start TCP server for serving chunks
            self.tcp_thread = threading.Thread(target=self._start_tcp_server)
            self.tcp_thread.daemon = True
            self.tcp_thread.start()
            self.threads.append(self.tcp_thread)
            
            # Start heartbeat thread
            self.heartbeat_thread = threading.Thread(target=self._send_heartbeats)
            self.heartbeat_thread.daemon = True
            self.heartbeat_thread.start()
            self.threads.append(self.heartbeat_thread)
            
            self.logger.info(f"Seeder started at {self.ip}:{self.port}")
        else:
            self.logger.info(f"Leecher started at {self.ip}:{self.port}")
    
    def stop(self):
        """Stop the P2P client and all its threads"""
        if not self.running:
            return
        
        self.running = False
        
        # Close TCP server if we're a seeder
        if (self.mode == 'seeder' or self.has_seeder_capability) and self.tcp_socket:
            try:
                self.tcp_socket.close()
            except Exception as e:
                self.logger.error(f"Error closing TCP socket: {e}")
        
        # Wait for threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=1)
        
        self.logger.info(f"P2P Client stopped ({self.mode})")
    
    # ===== Tracker communication =====
    
    def register_with_tracker(self) -> bool:
        """Register this client with the tracker."""
        try:
            # Create UDP socket for tracker communication
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.settimeout(5)  # 5 second timeout
            
            # Get an appropriate IP address to advertise
            advertised_ip = self.get_advertised_ip()
            advertised_address = (advertised_ip, self.port)
            
            # Prepare registration message
            message = f"Register:{advertised_address}"
            
            # Send registration request
            self.logger.info(f"Registering with tracker at {self.tracker_address}")
            udp_socket.sendto(message.encode('utf-8'), self.tracker_address)
            
            # Wait for response
            try:
                response, _ = udp_socket.recvfrom(2048)
                response = response.decode('utf-8')
                self.logger.info(f"Registration response: {response}")
                
                # Check for success
                if "Registered" in response or "Updated" in response:
                    return True
                else:
                    self.logger.error(f"Registration failed: {response}")
                    return False
            except socket.timeout:
                self.logger.error("Registration timed out")
                return False
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            return False
        finally:
            try:
                udp_socket.close()
            except:
                pass
            
    def get_advertised_ip(self) -> str:
        """
        Get the appropriate IP address to advertise to the tracker.
        
        Returns:
            A valid IP address that other peers can use to connect to this client
        """
        # If the self.ip is not 0.0.0.0, use it
        if self.ip != "0.0.0.0":
            return self.ip
        
        # For local testing, if the tracker is on localhost, use localhost
        if self.tracker_address and (
            self.tracker_address[0] == "127.0.0.1" or 
            self.tracker_address[0] == "localhost"
        ):
            return "127.0.0.1"
        
        # Try to get the local network IP
        try:
            # Create a temporary socket to determine which interface would be used
            # to connect to the tracker
            temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # This doesn't actually establish a connection, but it helps determine
            # which interface would be used
            tracker_ip = self.tracker_address[0] if self.tracker_address else "8.8.8.8"
            temp_socket.connect((tracker_ip, 80))
            
            # Get the IP of the interface that would be used
            local_ip = temp_socket.getsockname()[0]
            temp_socket.close()
            
            self.logger.info(f"Determined local IP address: {local_ip}")
            return local_ip
        except Exception as e:
            self.logger.warning(f"Failed to determine local IP: {e}, falling back to 127.0.0.1")
            return "127.0.0.1"
    
    def _send_heartbeats(self):
        """Periodically send heartbeats to the tracker while running"""
        while self.running:
            try:
                # Create UDP socket for tracker communication
                udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                udp_socket.settimeout(5)  # 5 second timeout
                
                # Get the appropriate IP to advertise
                advertised_ip = self.get_advertised_ip()
                advertised_address = (advertised_ip, self.port)
                
                # Prepare heartbeat message
                message = f"HeartBeat:{advertised_address}"
                
                # Send heartbeat
                udp_socket.sendto(message.encode('utf-8'), self.tracker_address)
                
                # No need to wait for response, but we'll log any we receive
                try:
                    response, _ = udp_socket.recvfrom(2048)
                    response = response.decode('utf-8')
                    self.logger.debug(f"Heartbeat response: {response}")
                except socket.timeout:
                    # Expected timeout, no response needed
                    pass
                except Exception as e:
                    self.logger.error(f"Heartbeat response error: {e}")
                
                # Close socket
                udp_socket.close()
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
            
            # Sleep for heartbeat interval
            time.sleep(self.heartbeat_interval)
    
    def _request_file_seeders(self, filename: str) -> List[Tuple[str, int]]:
        """
        Request list of seeders for a file from the tracker.
        
        Args:
            filename: Name of the file to request
            
        Returns:
            List of seeder addresses (ip, port) or empty list if none found
        """
        try:
            # Create UDP socket for tracker communication
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.settimeout(5)  # 5 second timeout
            
            # Prepare request message
            message = f"RequestFile:{filename}"
            
            # Send request
            self.logger.info(f"Requesting seeders for {filename} from tracker")
            udp_socket.sendto(message.encode('utf-8'), self.tracker_address)
            
            # Wait for response
            try:
                response, _ = udp_socket.recvfrom(2048)
                response = response.decode('utf-8')
                self.logger.info(f"Received seeder list: {response}")
                
                # Parse response (expecting "RespondFile:list_of_seeders")
                if response.startswith("RespondFile:"):
                    seeder_list_str = response[len("RespondFile:"):]
                    seeder_list = ast.literal_eval(seeder_list_str)
                    return seeder_list
                else:
                    self.logger.error(f"Unexpected response format: {response}")
                    return []
            except socket.timeout:
                self.logger.error("Request for seeders timed out")
                return []
        except Exception as e:
            self.logger.error(f"Error requesting seeders: {e}")
            return []
        finally:
            try:
                udp_socket.close()
            except:
                pass
    
    # ===== Seeder methods =====
    
    def _start_tcp_server(self):
        """Start TCP server to handle chunk requests from leechers"""
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.tcp_socket.bind((self.ip, self.port))
            self.tcp_socket.listen(5)  # Allow up to 5 queued connections
            
            self.logger.info(f"TCP Server started at {self.ip}:{self.port}")
            
            while self.running:
                try:
                    # Set a timeout to allow checking the running flag periodically
                    self.tcp_socket.settimeout(1.0)
                    
                    try:
                        # Accept incoming connection
                        client_socket, client_address = self.tcp_socket.accept()
                        self.logger.info(f"Connection from {client_address}")
                        
                        # Handle client request in a new thread
                        client_thread = threading.Thread(
                            target=self._handle_client_request,
                            args=(client_socket, client_address)
                        )
                        client_thread.daemon = True
                        client_thread.start()
                        self.threads.append(client_thread)
                    except socket.timeout:
                        # This is expected - just allows checking running flag
                        continue
                except Exception as e:
                    if self.running:  # Only log errors if we're still running
                        self.logger.error(f"TCP server error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to start TCP server: {e}")
    
    def _handle_client_request(self, client_socket, client_address):
        """
        Handle an incoming request from a leecher.
        
        Args:
            client_socket: Socket connected to the client
            client_address: (IP, port) of the client
        """
        try:
            # Receive request
            request = client_socket.recv(2048).decode('utf-8')
            self.logger.debug(f"Received request from {client_address}: {request}")
            
            # Parse request
            try:
                request_type, request_data = request.split(":", 1)
            except ValueError:
                self.logger.error(f"Malformed request: {request}")
                client_socket.close()
                return
            
            # Handle different request types
            if request_type == "Download":
                # Parse the download request data (expecting filename and chunk_index)
                try:
                    download_data = ast.literal_eval(request_data)
                    filename = download_data[0]
                    chunk_index = download_data[1]
                    
                    # Check if file exists
                    file_path = self.file_directory / filename
                    if not file_path.exists():
                        response = "Error:FileNotFound"
                        client_socket.send(response.encode('utf-8'))
                        return
                    
                    # Get file info to check if chunk index is valid
                    file_info = self.chunker.get_file_info(str(file_path))
                    if chunk_index >= file_info["total_chunks"]:
                        response = "Error:InvalidChunkIndex"
                        client_socket.send(response.encode('utf-8'))
                        return
                    
                    # Read the requested chunk
                    chunk_data = self.chunker.get_chunk(str(file_path), chunk_index)
                    
                    # Calculate hash for the chunk
                    chunk_hash = hashlib.sha256(chunk_data).hexdigest()
                    
                    # Send the hash first (as a fixed-length field for easy parsing)
                    client_socket.send(chunk_hash.encode('utf-8'))
                    
                    # Wait for confirmation that hash was received
                    client_socket.recv(4)  # Should receive "HASH" as confirmation
                    
                    # Send the chunk size as a 4-byte integer
                    chunk_size = len(chunk_data)
                    client_socket.send(chunk_size.to_bytes(4, byteorder='big'))
                    
                    # Then send the chunk data
                    client_socket.sendall(chunk_data)
                    
                    self.logger.info(f"Sent chunk {chunk_index} of {filename} to {client_address} ({chunk_size} bytes, hash: {chunk_hash[:8]}...)")
                except Exception as e:
                    self.logger.error(f"Error serving chunk: {e}")
                    response = f"Error:{str(e)}"
                    try:
                        client_socket.send(response.encode('utf-8'))
                    except:
                        pass
            elif request_type == "HaveFile":
                # Parse the file request
                filename = request_data.strip()
                
                # Check if we have the file
                file_path = self.file_directory / filename
                if file_path.exists():
                    # Get the number of chunks
                    file_info = self.chunker.get_file_info(str(file_path))
                    num_chunks = file_info["total_chunks"]
                    response = f"HaveFile:{num_chunks}"
                else:
                    response = "HaveFile:0"  # 0 indicates we don't have the file
                
                # Send response
                client_socket.send(response.encode('utf-8'))
                self.logger.debug(f"Responded to HaveFile request for {filename}: {response}")
            
            elif request_type == "ListFiles":
                # Return list of available files
                files = self._scan_files()
                response = f"FilesList:{files}"
                client_socket.send(response.encode('utf-8'))
                self.logger.debug(f"Responded to ListFiles request with {len(files)} files")
            
            else:
                # Unknown request type
                response = f"Error:UnknownRequestType:{request_type}"
                client_socket.send(response.encode('utf-8'))
                self.logger.warning(f"Unknown request type from {client_address}: {request_type}")
        except Exception as e:
            self.logger.error(f"Error handling client request: {e}")
        finally:
            # Close the connection
            try:
                client_socket.close()
            except:
                pass
    
    def handle_have_file_question(self, filename: str) -> int:
        """
        Check if we have a specific file and return the number of chunks.
        
        Args:
            filename: Name of the file to check
            
        Returns:
            Number of chunks we have (0 if we don't have the file)
        """
        file_path = self.file_directory / filename
        if file_path.exists():
            file_info = self.chunker.get_file_info(str(file_path))
            return file_info["total_chunks"]
        return 0
    
    # ===== Leecher methods =====
    
    def request_file(self, filename: str) -> bool:
        """
        Request to download a file.
        
        Args:
            filename: Name of the file to download
            
        Returns:
            True if download was initiated successfully, False otherwise
        """
        if self.mode != 'leecher' and not self.has_seeder_capability:
            self.logger.error("Can only request files in leecher mode")
            return False
            
        # Check if file is already downloaded or in progress
        if filename in self.downloaded_files:
            self.logger.info(f"File {filename} is already downloaded")
            return True
        
        if filename in self.current_downloads:
            self.logger.info(f"File {filename} is already being downloaded")
            return True
        
        # Request seeders for this file from the tracker
        seeders = self._request_file_seeders(filename)
        if not seeders:
            self.logger.error(f"No seeders found for {filename}")
            return False
        
        # Get file information from a seeder
        file_info = self._get_file_info_from_seeder(seeders[0], filename)
        if not file_info:
            self.logger.error(f"Failed to get file information for {filename}")
            return False
        
        # Initialize download tracking
        total_chunks = file_info["total_chunks"]
        self.current_downloads[filename] = {
            "file_info": file_info,
            "seeders": seeders,
            "chunk_status": {i: "pending" for i in range(total_chunks)},
            "completed_chunks": 0,
            "total_chunks": total_chunks
        }
        
        # Create an empty file to write chunks to
        output_path = self.file_directory / filename
        self.chunker.create_empty_file(str(output_path), file_info["file_size"])
        
        # Start download threads
        self.logger.info(f"Starting download of {filename} with {len(seeders)} seeders")
        self._start_download_threads(filename)
        return True
    
    def _get_file_info_from_seeder(self, seeder_address: tuple, filename: str) -> Optional[Dict]:
        """
        Get file information from a seeder.
        
        Args:
            seeder_address: (IP, port) of the seeder
            filename: Name of the file
            
        Returns:
            Dictionary with file information or None if failed
        """
        try:
            # Connect to seeder via TCP
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)  # 5 second timeout
            client_socket.connect(seeder_address)
            
            # Send HaveFile request
            message = f"HaveFile:{filename}"
            client_socket.send(message.encode('utf-8'))
            
            # Get response
            response = client_socket.recv(2048).decode('utf-8')
            
            # Check that we have a valid response
            if response.startswith("HaveFile:"):
                num_chunks = int(response.split(":", 1)[1])
                if num_chunks > 0:
                    # We need to get the chunk size and file size
                    # For simplicity, we'll use the default chunk size
                    # In a real implementation, this would be negotiated
                    return {
                        "filename": filename,
                        "total_chunks": num_chunks,
                        "chunk_size": self.chunker.chunk_size,
                        "file_size": num_chunks * self.chunker.chunk_size  # Approximation
                    }
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting file info from seeder {seeder_address}: {e}")
            return None
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def _start_download_threads(self, filename: str):
        """
        Start threads to download chunks in parallel.
        
        Args:
            filename: Name of the file to download
        """
        download_info = self.current_downloads[filename]
        total_chunks = download_info["total_chunks"]
        seeders = download_info["seeders"]
        
        # Determine chunks per seeder
        num_seeders = len(seeders)
        chunks_per_seeder = total_chunks // num_seeders
        remainder = total_chunks % num_seeders
        
        # Distribute chunks among seeders
        chunk_assignments = []
        start_chunk = 0
        
        for i in range(num_seeders):
            chunks_for_this_seeder = chunks_per_seeder
            if i < remainder:
                chunks_for_this_seeder += 1
                
            end_chunk = start_chunk + chunks_for_this_seeder
            chunk_range = list(range(start_chunk, end_chunk))
            chunk_assignments.append((seeders[i], chunk_range))
            start_chunk = end_chunk
        
        # Start a thread for each seeder with its assigned chunks
        for seeder, chunks in chunk_assignments:
            thread = threading.Thread(
                target=self._download_chunks_from_seeder,
                args=(filename, seeder, chunks)
            )
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
    
    def _download_chunks_from_seeder(self, filename: str, seeder_address: tuple, chunk_indices: List[int]):
        """
        Download a set of chunks from a specific seeder.
        
        Args:
            filename: Name of the file
            seeder_address: (IP, port) of the seeder
            chunk_indices: List of chunk indices to download
        """
        output_path = self.file_directory / filename
        
        for chunk_index in chunk_indices:
            if not self.running or filename not in self.current_downloads:
                return
                
            if self.current_downloads[filename]["chunk_status"].get(chunk_index) == "completed":
                continue
            
            # Mark chunk as in progress
            self.current_downloads[filename]["chunk_status"][chunk_index] = "downloading"
            
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                try:
                    # Connect to seeder
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.settimeout(10)  # 10 second timeout
                    client_socket.connect(seeder_address)
                    
                    # Request chunk
                    request = f"Download:{(filename, chunk_index)}"
                    client_socket.send(request.encode('utf-8'))
                    
                    # First receive the hash (64 characters for SHA-256)
                    hash_data = client_socket.recv(64)
                    if not hash_data or len(hash_data) != 64:
                        raise Exception("Failed to receive chunk hash")
                    
                    expected_hash = hash_data.decode('utf-8')
                    
                    # Acknowledge receipt of hash
                    client_socket.send(b"HASH")
                    
                    # Receive the chunk size (4 bytes)
                    size_bytes = client_socket.recv(4)
                    if not size_bytes or len(size_bytes) != 4:
                        raise Exception("Failed to receive chunk size")
                    
                    chunk_size = int.from_bytes(size_bytes, byteorder='big')
                    
                    # Receive the chunk data
                    chunk_data = b""
                    bytes_received = 0
                    
                    while bytes_received < chunk_size:
                        remaining = chunk_size - bytes_received
                        buffer_size = min(4096, remaining)  # 4KB buffer
                        data = client_socket.recv(buffer_size)
                        
                        if not data:
                            raise Exception("Connection closed before receiving complete chunk")
                        
                        chunk_data += data
                        bytes_received += len(data)
                    
                    # Verify the chunk integrity
                    actual_hash = hashlib.sha256(chunk_data).hexdigest()
                    if actual_hash != expected_hash:
                        self.logger.error(f"Chunk {chunk_index} failed integrity verification")
                        self.logger.debug(f"Expected: {expected_hash}, Actual: {actual_hash}")
                        raise Exception("Chunk integrity verification failed")
                    
                    # Write the chunk to the file only if verification passes
                    self.chunker.write_chunk(str(output_path), chunk_data, chunk_index)
                    
                    # Mark chunk as completed
                    self.current_downloads[filename]["chunk_status"][chunk_index] = "completed"
                    self.current_downloads[filename]["completed_chunks"] += 1
                    
                    # Print progress
                    completed = self.current_downloads[filename]["completed_chunks"]
                    total = self.current_downloads[filename]["total_chunks"]
                    progress = (completed / total) * 100
                    self.logger.info(f"Downloaded and verified chunk {chunk_index} of {filename} from {seeder_address} ({completed}/{total}, {progress:.1f}%)")
                    
                    # Check if download is complete
                    if completed == total:
                        self._handle_download_completion(filename)
                    
                    # Success, break the retry loop
                    break
                except Exception as e:
                    self.logger.error(f"Error downloading chunk {chunk_index} from {seeder_address}: {e}")
                    retry_count += 1
                    time.sleep(1)  # Wait before retrying
                finally:
                    try:
                        client_socket.close()
                    except:
                        pass
            
            # If all retries failed, mark chunk as pending again
            if retry_count == max_retries:
                if filename in self.current_downloads:  # Check if download was cancelled
                    self.current_downloads[filename]["chunk_status"][chunk_index] = "pending"
                    # Try to reassign this chunk to another seeder
                    self._reassign_chunk(filename, chunk_index)
    
    def _reassign_chunk(self, filename: str, chunk_index: int):
        """
        Reassign a failed chunk to another seeder.
        
        Args:
            filename: Name of the file
            chunk_index: Index of the chunk to reassign
        """
        # Check if download was cancelled
        if filename not in self.current_downloads:
            return
            
        # Get a list of available seeders
        seeders = self.current_downloads[filename]["seeders"]
        if not seeders:
            self.logger.error(f"No seeders available to reassign chunk {chunk_index}")
            return
        
        # Select a random seeder
        import random
        seeder = random.choice(seeders)
        
        # Start a new thread to download this chunk
        thread = threading.Thread(
            target=self._download_chunks_from_seeder,
            args=(filename, seeder, [chunk_index])
        )
        thread.daemon = True
        thread.start()
        self.threads.append(thread)
    
    def _handle_download_completion(self, filename: str):
        """
        Handle completion of a file download.
        
        Args:
            filename: Name of the completed file
        """
        self.logger.info(f"Download of {filename} completed!")
        
        # Add to downloaded files
        self.downloaded_files.append(filename)
        
        # Remove from current downloads
        del self.current_downloads[filename]
        
        # Add to available files
        if filename not in self.files:
            self.files.append(filename)
        
        # Transition to seeder if configured
        if self.become_seeder_after_download and not self.has_seeder_capability:
            self.transition_to_seeder()
    
    def transition_to_seeder(self):
        """Transition from leecher to seeder mode or add seeding capability"""
        if self.mode == 'seeder' or self.has_seeder_capability:
            self.logger.info("Already has seeder capability")
            return
        
        self.logger.info("Adding seeder capability while maintaining leecher functionality...")
        
        # Keep original mode's capability but add seeder features
        self.has_seeder_capability = True
        
        # Add the heartbeat_interval attribute
        self.heartbeat_interval = 5  # seconds
        
        # Start TCP server
        self.tcp_thread = threading.Thread(target=self._start_tcp_server)
        self.tcp_thread.daemon = True
        self.tcp_thread.start()
        self.threads.append(self.tcp_thread)
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._send_heartbeats)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        self.threads.append(self.heartbeat_thread)
        
        # Re-register with tracker as a seeder
        self.register_with_tracker()
        
        self.logger.info("Added seeder capability while maintaining leecher mode")
    
    # ===== Utility methods =====
    
    def get_download_status(self, filename: str = None) -> Dict:
        """
        Get status of current downloads.
        
        Args:
            filename: Specific file to get status for, or None for all
            
        Returns:
            Dictionary with download status information
        """
        if filename:
            if filename in self.current_downloads:
                info = self.current_downloads[filename]
                completed = info["completed_chunks"]
                total = info["total_chunks"]
                return {
                    "filename": filename,
                    "status": "downloading",
                    "progress": f"{completed}/{total} chunks ({(completed/total)*100:.1f}%)",
                    "seeders": len(info["seeders"])
                }
            elif filename in self.downloaded_files:
                return {
                    "filename": filename,
                    "status": "completed",
                    "progress": "100%"
                }
            else:
                return {
                    "filename": filename,
                    "status": "not found"
                }
        else:
            # Return status for all downloads
            result = {
                "current_downloads": [],
                "completed_downloads": self.downloaded_files
            }
            
            for filename, info in self.current_downloads.items():
                completed = info["completed_chunks"]
                total = info["total_chunks"]
                result["current_downloads"].append({
                    "filename": filename,
                    "progress": f"{completed}/{total} chunks ({(completed/total)*100:.1f}%)",
                    "seeders": len(info["seeders"])
                })
            
            return result
        
    def rescan_files(self):
        """Rescan the file directory for available files."""
        if self.mode == 'seeder' or self.has_seeder_capability:
            self.files = self._scan_files()
            return self.files
        return []
    
    def get_available_files(self):
        """
        Get a list of all available files from the tracker.
        
        Returns:
            List of filenames available from all seeders
        """
        # Add caching to prevent too many requests
        now = time.time()
        
        # Initialize cache attributes if they don't exist
        if not hasattr(self, '_file_cache_time'):
            self._file_cache_time = 0
            self._file_cache_result = []
        
        # Return cached result if not too old (use 5-second cache)
        if now - self._file_cache_time < 5:
            self.logger.debug(f"Using cached file list (age: {now - self._file_cache_time:.2f}s)")
            return self._file_cache_result
        
        # If we get here, the cache is expired, so make a real request
        self.logger.info(f"Requesting available files from tracker")
        
        # Create UDP socket for tracker communication
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.settimeout(5)  # 5 second timeout
        
        try:
            # Prepare request message
            message = "ListFiles:"
            
            # Send request
            udp_socket.sendto(message.encode('utf-8'), self.tracker_address)
            
            # Wait for response
            try:
                response, _ = udp_socket.recvfrom(4096)  # Use larger buffer for file lists
                response = response.decode('utf-8')
                
                # Parse response (expecting "FilesList:list_of_files")
                if response.startswith("FilesList:"):
                    files_list_str = response[len("FilesList:"):]
                    files_list = ast.literal_eval(files_list_str)
                    
                    # Update cache before returning
                    self._file_cache_time = now
                    self._file_cache_result = files_list
                    return files_list
                else:
                    self.logger.error(f"Unexpected response format: {response}")
                    return self._file_cache_result  # Return cached result on error
            except socket.timeout:
                self.logger.error("Request for file list timed out")
                return self._file_cache_result  # Return cached result on timeout
        except Exception as e:
            self.logger.error(f"Error requesting file list: {e}")
            return self._file_cache_result  # Return cached result on any error
        finally:
            udp_socket.close()
            
    # In the P2PClient class, add this method:
    def start_udp_listener(self):
        """Start a UDP server to listen for direct UDP messages from the tracker"""
        udp_thread = threading.Thread(target=self._udp_listener_thread)
        udp_thread.daemon = True
        udp_thread.start()
        self.threads.append(udp_thread)
        self.logger.info(f"Started UDP listener on {self.ip}:{self.port}")

    def _udp_listener_thread(self):
        """Thread to listen for UDP messages (especially ListFiles requests)"""
        try:
            # Create UDP socket for direct communication
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.bind((self.ip, self.port))
            
            while self.running:
                try:
                    # Set a timeout to allow checking the running flag
                    udp_socket.settimeout(1.0)
                    
                    try:
                        # Wait for a message
                        data, addr = udp_socket.recvfrom(4096)
                        message = data.decode('utf-8')
                        self.logger.info(f"Received UDP message from {addr}: {message}")
                        
                        # Handle different message types
                        if message.startswith("ListFiles:"):
                            files = self._scan_files()
                            response = f"FilesList:{files}"
                            self.logger.info(f"Responding to ListFiles request with {len(files)} files")
                            udp_socket.sendto(response.encode('utf-8'), addr)
                        
                    except socket.timeout:
                        # This is expected, just allows checking running flag
                        continue
                except Exception as e:
                    if self.running:  # Only log errors if we're still running
                        self.logger.error(f"UDP listener error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to start UDP listener: {e}")
        finally:
            try:
                udp_socket.close()
            except:
                pass


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="P2P File Sharing Client")
    parser.add_argument('--mode', choices=['seeder', 'leecher'], 
                        default='seeder',
                        help='Client mode (seeder or leecher)')
    parser.add_argument('--ip', default='0.0.0.0',
                        help='IP address to bind to')
    parser.add_argument('--port', type=int, default=8000,
                        help='Port to bind to')
    parser.add_argument('--tracker-ip', default='127.0.0.1',
                        help='Tracker server IP address')
    parser.add_argument('--tracker-port', type=int, default=12345,
                        help='Tracker server port')
    parser.add_argument('--files-dir', default='./files',
                        help='Directory for files')
    
    args = parser.parse_args()
    
    # Create the P2P client
    client = P2PClient(
        mode=args.mode,
        ip=args.ip,
        port=args.port,
        file_directory=args.files_dir,
        tracker_address=(args.tracker_ip, args.tracker_port)
    )
    
    try:
        # Start the client
        client.start()
        
        if args.mode == 'seeder':
            # Display available files
            files = client.rescan_files()
            if files:
                print(f"\nSharing {len(files)} files:")
                for file in files:
                    print(f"  - {file}")
            else:
                print("\nNo files found in the specified directory.")
        else:  # leecher mode
            # Get available files from tracker
            available_files = client.get_available_files()
            if available_files:
                print(f"\nAvailable files for download ({len(available_files)}):")
                for i, filename in enumerate(sorted(available_files), 1):
                    print(f"{i}. {filename}")
                
                # Ask user to select a file to download
                file_num = input("\nEnter file number to download (or press Enter to skip): ")
                if file_num and file_num.isdigit():
                    idx = int(file_num) - 1
                    if 0 <= idx < len(available_files):
                        filename = sorted(available_files)[idx]
                        print(f"Downloading {filename}...")
                        client.request_file(filename)
            else:
                print("No files available for download.")
        
        # Keep running until user exits
        print("\nClient is running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping client...")
    finally:
        client.stop()