import { SystemStatus } from "../types";

type WebSocketCallback = (data: SystemStatus) => void;

export class WebSocketClient {
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private callbacks: WebSocketCallback[] = [];
  private baseUrl: string;
  private connectionInProgress = false;

  constructor() {
    // Use the proper WebSocket URL based on the server configuration
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Use the same host as the current page by default, or specified host if available
    const host = process.env.NEXT_PUBLIC_WS_HOST || window.location.host;
    this.baseUrl = `${protocol}//${host}/ws`;
    console.log("WebSocket will connect to:", this.baseUrl);
  }

  // Connect to the WebSocket server
  connect(): void {
    if (this.connectionInProgress) {
      console.log("WebSocket connection already in progress");
      return;
    }
    
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      console.log("WebSocket already connected or connecting");
      return;
    }

    this.connectionInProgress = true;
    
    try {
      console.log("Attempting to connect to WebSocket at:", this.baseUrl);
      this.socket = new WebSocket(this.baseUrl);

      this.socket.onopen = () => {
        console.log('WebSocket connection established');
        this.reconnectAttempts = 0;
        this.connectionInProgress = false;
        // Send a keep-alive message
        this.socket?.send("ping");
      };

      this.socket.onmessage = (event) => {
        try {
          // Handle keep-alive response
          if (event.data === "pong") {
            return;
          }
          
          const data = JSON.parse(event.data) as SystemStatus;
          console.log("WebSocket received message:", data);
          this.notifyCallbacks(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.socket.onclose = (event) => {
        console.log('WebSocket connection closed', event.code, event.reason);
        this.connectionInProgress = false;
        this.attemptReconnect();
      };

      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.connectionInProgress = false;
        // Don't automatically close - let the onclose handler deal with it
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.connectionInProgress = false;
      this.attemptReconnect();
    }
  }

  // Disconnect from the WebSocket server
  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    
    this.connectionInProgress = false;
  }

  // Subscribe to status updates
  subscribe(callback: WebSocketCallback): () => void {
    this.callbacks.push(callback);

    // Return an unsubscribe function
    return () => {
      this.callbacks = this.callbacks.filter(cb => cb !== callback);
    };
  }

  // Send a ping to keep the connection alive
  sendPing(): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send("ping");
    }
  }

  // Attempt to reconnect with exponential backoff
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Maximum reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);

    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  // Notify all subscribers of a status update
  private notifyCallbacks(data: SystemStatus): void {
    this.callbacks.forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error('Error in WebSocket callback:', error);
      }
    });
  }
}

// Singleton instance
let websocketInstance: WebSocketClient | null = null;

// Get or create the WebSocket client instance
export function getWebSocketClient(): WebSocketClient {
  if (!websocketInstance) {
    websocketInstance = new WebSocketClient();
  }
  return websocketInstance;
}