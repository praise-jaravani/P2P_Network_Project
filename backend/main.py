import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import threading
import time
import logging
from typing import List, Dict, Optional
import json

# Import core modules with your working paths
from core.p2p_client import P2PClient
from core import tracker, udp_server, tracker_handlers

app = FastAPI(title="P2P File Sharing API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Global variables
clients = []
running = True
active_connections: List[WebSocket] = []
tracker_thread = None
udp_thread = None

# Configuration - could be moved to environment variables
TRACKER_IP = os.getenv("TRACKER_IP", "0.0.0.0")  # Changed to 0.0.0.0 for cross-machine networking
TRACKER_PORT = int(os.getenv("TRACKER_PORT", "12345"))
TRACKER_ADDRESS = (TRACKER_IP, TRACKER_PORT)
LOCAL_IP = os.getenv("LOCAL_IP", "0.0.0.0")  # Changed to 0.0.0.0 for cross-machine networking
LOCAL_PORT = int(os.getenv("LOCAL_PORT", "9000"))
FILES_DIR = os.getenv("FILES_DIR", "./files")

# Initialize the P2P components
leecher = None

@app.on_event("startup")
async def startup_event():
    """Initialize P2P components on startup"""
    global leecher
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize leecher client but don't connect it to any tracker yet
    leecher = P2PClient(
        mode="leecher",
        ip=LOCAL_IP,
        port=LOCAL_PORT,
        file_directory=FILES_DIR,
        tracker_address=None,  # No tracker connection initially
        become_seeder_after_download=True
    )
    
    # Add the client to the list but don't start it
    clients.append(leecher)
    
    # Start status update thread for WebSocket
    threading.Thread(target=status_updater, daemon=True).start()
    
    logging.info(f"P2P components initialized but not connected. Leecher ready at {LOCAL_IP}:{LOCAL_PORT}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    global running
    running = False
    
    # Stop all clients
    for client in clients:
        client.stop()
    
    logging.info("P2P components shut down")

# WebSocket connection manager
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Keep connection alive with ping-pong messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            # Otherwise just keep the connection open
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

# Status updater thread for WebSockets
def status_updater():
    """Send status updates to WebSocket clients"""
    global running
    
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def send_updates():
        """Async function to send updates to all active connections"""
        if not active_connections or not leecher:
            return
            
        try:
            # Get minimal status without triggering file refresh
            status = {
                "downloads": leecher.get_download_status(),
                "tracker": {
                    "address": f"{TRACKER_IP}:{TRACKER_PORT}"
                }
            }
            
            # Add tracker info if available
            if TRACKER_IP in ["0.0.0.0", "127.0.0.1"]:
                with tracker.seeders_lock:
                    status["tracker"]["active_seeders"] = len(tracker.seeders)
            
            # Use gather to send to all connections concurrently
            send_tasks = []
            for connection in active_connections[:]:
                send_tasks.append(connection.send_json(status))
            
            if send_tasks:
                await asyncio.gather(*send_tasks, return_exceptions=True)
                
        except Exception as e:
            logging.error(f"Error in status updater: {e}")
    
    while running:
        # Run the async function in this thread's event loop
        if active_connections and leecher:
            loop.run_until_complete(send_updates())
        
        time.sleep(5)  # Increase the delay to reduce load
    
    # Clean up the event loop when the thread exits
    loop.close()

# API Routes
@app.get("/api/files")
async def get_files():
    """Get list of available files"""
    if not leecher:
        raise HTTPException(status_code=503, detail="P2P client not initialized")
    
    files = leecher.get_available_files()
    return {"files": files}

@app.post("/api/download")
async def start_download(data: dict):
    """Start downloading a file"""
    if not leecher:
        raise HTTPException(status_code=503, detail="P2P client not initialized")
    
    filename = data.get("filename")
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    success = leecher.request_file(filename)
    return {"success": success}

@app.get("/api/status")
async def get_status():
    """Get system status"""
    if not leecher:
        raise HTTPException(status_code=503, detail="P2P client not initialized")
    
    return get_system_status()

@app.get("/api/downloaded")
async def get_downloaded():
    """Get list of downloaded files"""
    if not leecher:
        raise HTTPException(status_code=503, detail="P2P client not initialized")
    
    return {"files": leecher.files}

@app.post("/api/configure")
async def configure_client(data: dict):
    """Reconfigure the P2P client with new tracker settings"""
    global leecher, tracker_thread, udp_thread
    
    tracker_ip = data.get("trackerIp")
    tracker_port = int(data.get("trackerPort", "12345"))
    start_local_tracker = data.get("startLocalTracker", False)
    
    if not tracker_ip:
        raise HTTPException(status_code=400, detail="Tracker IP is required")
    
    # Create new tracker address
    new_tracker_address = (tracker_ip, tracker_port)
    
    # Stop the current client if it's running
    if leecher and leecher.running:
        leecher.stop()
    
    # Stop local tracker if it's running
    if tracker_thread or udp_thread:
        logging.info("Stopping existing tracker threads")
        # Signal tracker shutdown
        tracker.running = False
        udp_server.running = False
        
        # Wait for threads to finish
        if tracker_thread:
            tracker_thread.join(timeout=1)
        if udp_thread:
            udp_thread.join(timeout=1)
        
        # Reset thread references
        tracker_thread = None
        udp_thread = None
    
    # Start a local tracker if requested
    if start_local_tracker:
        logging.info(f"Starting local tracker on port {tracker_port}")
        
        # Configure and start the UDP server
        udp_server.configure_server(ip=tracker_ip, port=tracker_port)
        tracker_handlers.register_handlers()
        udp_thread = threading.Thread(target=udp_server.start, daemon=True)
        udp_thread.start()
        
        # Start tracker in another thread
        tracker_thread = threading.Thread(target=tracker.start_tracker, daemon=True)
        tracker_thread.start()
        
        # Give the tracker a moment to start up
        time.sleep(0.5)
    
    # Initialize new leecher with updated tracker
    leecher = P2PClient(
        mode="leecher",
        ip=LOCAL_IP,
        port=LOCAL_PORT,
        file_directory=FILES_DIR,
        tracker_address=new_tracker_address,
        become_seeder_after_download=True
    )
    
    # Start the leecher
    leecher.start()
    
    # Update the client in the clients list
    if clients:
        clients[0] = leecher
    else:
        clients.append(leecher)
    
    # Verify connection by attempting to get file list
    try:
        files = leecher.get_available_files()
        connection_verified = True
    except Exception as e:
        connection_verified = False
        logging.error(f"Tracker connection verification failed: {e}")
    
    return {
        "success": True,
        "tracker_address": f"{tracker_ip}:{tracker_port}",
        "local_tracker": start_local_tracker,
        "connection_verified": connection_verified
    }

def get_system_status():
    """Get the system status for API and WebSocket responses"""
    if not leecher:
        return {"error": "P2P client not initialized"}
    
    # Only get download status, don't refresh file list
    status = {
        "downloads": leecher.get_download_status(),
        "tracker": {
            "address": f"{TRACKER_IP}:{TRACKER_PORT}"
        }
    }
    
    if TRACKER_IP in ["0.0.0.0", "127.0.0.1"]:
        # If we're running the tracker, include active seeders count
        with tracker.seeders_lock:
            status["tracker"]["active_seeders"] = len(tracker.seeders)
    
    return status

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)