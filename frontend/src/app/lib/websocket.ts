import { SystemStatus } from "../types";

type WebSocketCallback = (data: SystemStatus) => void;

export class WebSocketClient {
  private socket: WebSocket | null = null;
  private callbacks: WebSocketCallback[] = [];
  private connecting: boolean = false;
  private pingInterval: NodeJS.Timeout | null = null;
  private baseUrl: string;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectTimeout: NodeJS.Timeout | null = null;

  constructor() {
    // Only run this in the browser
    if (typeof window !== 'undefined') {
      // Use a fixed backend URL instead of window.location to avoid mismatches
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      
      // Use localhost:8000 explicitly rather than relying on window.location.host
      // This ensures we connect to the backend API server, not the frontend
      this.baseUrl = `${protocol}//localhost:8000/ws`;
      console.log("WebSocket will connect to:", this.baseUrl);
    } else {
      // Placeholder during server-side rendering
      this.baseUrl = '';
    }
  }

  connect(): void {
    // Don't attempt to connect during server-side rendering
    if (typeof window === 'undefined') return;
    
    if (this.socket?.readyState === WebSocket.OPEN) {
      console.log("WebSocket already connected");
      return;
    }
    
    if (this.connecting) {
      console.log("WebSocket connection already in progress");
      return;
    }
    
    this.connecting = true;
    
    try {
      console.log("Connecting to WebSocket at:", this.baseUrl);
      this.socket = new WebSocket(this.baseUrl);
      
      this.socket.onopen = () => {
        console.log("WebSocket connection established");
        this.connecting = false;
        this.reconnectAttempts = 0;
        
        // Set up ping interval to keep connection alive
        if (this.pingInterval) clearInterval(this.pingInterval);
        this.pingInterval = setInterval(() => this.ping(), 30000);
      };
      
      this.socket.onclose = (event) => {
        console.log(`WebSocket connection closed: ${event.code} - ${event.reason}`);
        this.connecting = false;
        if (this.pingInterval) {
          clearInterval(this.pingInterval);
          this.pingInterval = null;
        }
        
        // Try to reconnect
        this.attemptReconnect();
      };
      
      this.socket.onerror = (error) => {
        console.error("WebSocket error:", error);
        this.connecting = false;
        // Don't close here, let the onclose handler handle it
      };
      
      this.socket.onmessage = (event) => {
        try {
          if (event.data === "pong") {
            console.log("Received pong from server");
            return; // Ignore pong responses
          }
          
          console.log("Received WebSocket message:", event.data);
          
          const data = JSON.parse(event.data) as SystemStatus;
          this.notifyCallbacks(data);
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
        }
      };
    } catch (error) {
      console.error("Failed to create WebSocket:", error);
      this.connecting = false;
      this.attemptReconnect();
    }
  }
  
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
  
  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
  
  subscribe(callback: WebSocketCallback): () => void {
    this.callbacks.push(callback);
    return () => {
      this.callbacks = this.callbacks.filter(cb => cb !== callback);
    };
  }
  
  private ping(): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      console.log("Sending ping to server");
      this.socket.send("ping");
    }
  }
  
  private notifyCallbacks(data: SystemStatus): void {
    this.callbacks.forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error("Error in WebSocket callback:", error);
      }
    });
  }
}

// Singleton instance
let websocketInstance: WebSocketClient | null = null;

export function getWebSocketClient(): WebSocketClient {
  if (!websocketInstance) {
    websocketInstance = new WebSocketClient();
  }
  return websocketInstance;
}