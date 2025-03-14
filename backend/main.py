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
    
    # Start the tracker if running locally
    if TRACKER_IP in ["0.0.0.0", "127.0.0.1"]:
        # Configure and start the UDP server
        udp_server.configure_server(ip=TRACKER_IP, port=TRACKER_PORT)
        tracker_handlers.register_handlers()
        udp_thread = threading.Thread(target=udp_server.start, daemon=True)
        udp_thread.start()
        
        # Start tracker in another thread
        tracker_thread = threading.Thread(target=tracker.start_tracker, daemon=True)
        tracker_thread.start()
        
    # Initialize leecher client
    leecher = P2PClient(
        mode="leecher",
        ip=LOCAL_IP,
        port=LOCAL_PORT,
        file_directory=FILES_DIR,
        tracker_address=TRACKER_ADDRESS,
        become_seeder_after_download=True
    )
    
    # Start the leecher
    leecher.start()
    clients.append(leecher)
    
    # Start status update thread for WebSocket
    threading.Thread(target=status_updater, daemon=True).start()
    
    logging.info(f"P2P components initialized. Leecher running at {LOCAL_IP}:{LOCAL_PORT}")

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
    
    # Create a new event loop for this thread once
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        while running:
            if active_connections and leecher:
                try:
                    # Only get system status, don't refresh files
                    status = get_system_status()
                    
                    # Send updates to all active connections
                    for connection in active_connections[:]:  # Use a copy of the list
                        try:
                            loop.run_until_complete(connection.send_json(status))
                        except Exception as e:
                            logging.error(f"Error sending WebSocket update: {e}")
                            # Connection might be closed, but not properly removed
                            if connection in active_connections:
                                active_connections.remove(connection)
                except Exception as e:
                    logging.error(f"Error in status updater: {e}")
            
            time.sleep(2)  # Update every 2 seconds
    except Exception as e:
        logging.error(f"Fatal error in status updater thread: {e}")
    finally:
        # Close the loop when exiting
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

def get_system_status():
    """Get the system status for API and WebSocket responses"""
    if not leecher:
        return {"error": "P2P client not initialized"}
    
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