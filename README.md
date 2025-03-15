# P2P File Sharing System

A simplified BitTorrent-like peer-to-peer file sharing system with a modern web interface. This project implements a decentralized content sharing system that enables users to download and upload file chunks efficiently from multiple peers.

## Tech Stack

### Backend
- **Python**: Core language for the backend implementation
- **FastAPI**: High-performance web framework for building APIs
- **WebSockets**: For real-time communication with the frontend
- **UDP/TCP Sockets**: Native Python sockets for P2P communication
- **Threading**: For concurrent operations

### Frontend
- **Next.js**: React framework for building the user interface
- **TypeScript**: For type-safe code
- **Tailwind CSS**: For styling components
- **React Context**: For state management
- **WebSockets**: For real-time updates from the backend

## Overview

This P2P file sharing system consists of three main components that work together:

1. **Tracker** - Coordinates peer discovery and file availability
2. **Seeder** - Provides file chunks for download
3. **Leecher** - Downloads chunks from multiple peers and assembles them

The system utilizes UDP for lightweight tracker communication and TCP for reliable file transfers, mimicking the BitTorrent protocol's approach.

## Features

- Tracker server for peer coordination
- Seeders that share files with the network
- Leechers that download files from multiple seeders
- File chunking and reassembly
- SHA-256 integrity verification
- Automatic transition from leecher to seeder
- Modern web interface for file browsing and downloading
- Real-time progress updates via WebSockets

## Project Structure

```
.
├── backend/
│   ├── core/
│   │   ├── file_chunker.py       # Handles file splitting and reassembly
│   │   ├── p2p_client.py         # Main client implementation
│   │   ├── tracker.py            # Tracker coordination logic
│   │   ├── tracker_handlers.py   # Handlers for tracker commands
│   │   └── udp_server.py         # UDP server implementation
│   ├── tools/
│   │   ├── leecher_client.py     # Standalone leecher client
│   │   ├── seeder_client.py      # Standalone seeder client
│   │   └── tracker_server.py     # Standalone tracker server
│   ├── requirements.txt          # Python dependencies
│   └── main.py                   # FastAPI backend server
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/       # React components
│   │   │   ├── context/          # React context providers
│   │   │   ├── dashboard/        # Dashboard pages
│   │   │   ├── lib/              # Utility functions and API clients
│   │   │   └── types/            # TypeScript type definitions
│   │   └── app/
│   ├── package.json
│   └── next.config.ts
└── README.md
```

## Prerequisites

- Python 3.8+
- Node.js 18+
- npm or yarn

## Setup Instructions

### Backend Setup

1. Create a virtual environment (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create directories for file storage:
   ```bash
   mkdir -p files seeder_files
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   # or
   yarn install
   ```

## Running the System

The components must be started in the correct sequence for the system to work properly.

### 1. Start the Tracker Server

The tracker coordinates peer discovery and file availability.

```bash
python3 tracker_server.py --ip 127.0.0.1 --port 12345
```

### 2. Start the Seeder Client

The seeder shares files with the network.

```bash
python3 seeder_client.py --ip 127.0.0.1 --port 8001 --tracker-ip 127.0.0.1 --tracker-port 12345 --files-dir ./seeder_files
```

### 3. Start the Backend API Server

The backend API server provides a bridge between the web interface and the P2P network.

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Start the Frontend

The frontend provides a user-friendly interface for interacting with the P2P network.

```bash
npm run dev
# or
yarn dev
```

### 5. Connect via the Frontend

1. Open your browser and go to `http://localhost:3000`
2. In the connection form, enter:
   - Tracker IP: 127.0.0.1
   - Tracker Port: 12345
   - Select "Connect to remote tracker" (since you're already running the tracker separately)
3. Click "Connect to Tracker"
4. You should be redirected to the dashboard where you can view and download files

## Technical Implementation Details

### Protocol Design

The system implements two distinct protocols for different aspects of the P2P communication:

#### 1. Tracker Protocol (UDP)

UDP is used for lightweight, stateless communication between peers and the tracker. This includes:

- **Registration**: Peers register with the tracker to announce their presence
- **Heartbeats**: Regular messages to maintain active status
- **File Discovery**: Requesting and providing lists of available files
- **Peer Discovery**: Finding peers that have specific files

Message Format: `MessageType:Content`

Examples:
- `Register:('127.0.0.1', 8001)`
- `HeartBeat:('127.0.0.1', 8001)`
- `ListFiles:`
- `RequestFile:filename.mp4`

#### 2. File Transfer Protocol (TCP)

TCP is used for reliable, connection-oriented file transfers between peers:

- **Chunk Requests**: Leechers request specific chunks from seeders
- **Chunk Transfers**: Reliable delivery of file data
- **Verification**: SHA-256 hashing for integrity checks

Message Format: `CommandType:Parameters`

Examples:
- `Download:(filename.mp4, 0)` (requesting chunk 0 of a file)
- `HaveFile:filename.mp4` (querying if a peer has a specific file)

### File Chunking

Files are split into equal-sized chunks (default: 512 KB) to enable:

1. **Parallel Downloads**: Multiple chunks can be downloaded simultaneously from different seeders
2. **Resilience**: Failed chunk transfers can be retried individually
3. **Distributed Storage**: Different peers can host different subsets of chunks

The `FileChunker` class handles:
- Splitting files into chunks
- Reassembling chunks into complete files
- Generating and verifying SHA-256 hashes for integrity

### System Architecture

#### Backend Components

1. **Tracker Server (`tracker_server.py`)**:
   - Maintains a registry of active seeders
   - Responds to peer discovery requests
   - Coordinates the network by providing information about available files and peers
   - Implements a UDP server to handle lightweight peer communication

2. **P2P Client (`p2p_client.py`)**:
   - Dual-mode operation as either seeder or leecher
   - TCP server component for handling chunk requests (seeder mode)
   - Multi-threaded download manager (leecher mode)
   - Automatic transition from leecher to seeder after download

3. **FastAPI Server (`main.py`)**:
   - Provides a RESTful API for the frontend
   - Creates and manages a P2P client instance
   - Implements WebSocket connections for real-time updates
   - Handles configuration changes and download requests

#### Frontend Components

1. **React Context (`app-context.tsx`)**:
   - Manages global state for the application
   - Handles authentication and connection status
   - Provides methods for interacting with the backend API

2. **API Client (`api.ts`)**:
   - Implements communication with the backend API
   - Handles file listing, download requests, and configuration

3. **WebSocket Client (`websocket.ts`)**:
   - Maintains a persistent connection to the backend
   - Provides real-time updates for download progress and peer activity
   - Implements reconnection logic for network resilience

4. **Dashboard UI Components**:
   - File browser with search functionality
   - Download management interface
   - Settings configuration
   - Status monitoring

### Communication Flow

1. **Initial Connection**:
   - User enters tracker details in the frontend
   - Frontend sends configuration to the backend via REST API
   - Backend creates or updates its P2P client to connect to the specified tracker
   - Backend establishes a WebSocket connection for real-time updates

2. **File Discovery**:
   - Backend sends a `ListFiles` request to the tracker via UDP
   - Tracker forwards the request to all active seeders
   - Seeders respond with their available files
   - Tracker aggregates responses and sends them back to the requesting peer
   - Backend forwards the list to the frontend

3. **File Download**:
   - User selects a file to download in the UI
   - Frontend sends a download request to the backend
   - Backend queries the tracker for peers having the file
   - Tracker returns a list of seeders for the file
   - Backend creates multiple TCP connections to seeders and requests different chunks
   - As chunks arrive, they are verified and assembled
   - Progress is reported to the frontend via WebSocket updates

4. **Transition to Seeder**:
   - After a file is completely downloaded, the leecher can become a seeder
   - The client registers with the tracker as a seeder for the downloaded file
   - Other peers can now download chunks from this peer

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- This project was developed as part of the CSC3002 Networks course at the University of Cape Town
- Inspired by the BitTorrent protocol and modern web application architectures
