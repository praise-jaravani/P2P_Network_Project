'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { SystemStatus, File, ConnectionSettings } from '../types';
import { getSystemStatus, getAvailableFiles, downloadFile, configureTracker } from '../lib/api';
import { getWebSocketClient } from '../lib/websocket';
import { debounce } from 'lodash';

// Default connection settings
const DEFAULT_SETTINGS: ConnectionSettings = {
  trackerIp: '127.0.0.1',
  trackerPort: '12345',
  downloadDir: './downloads',
  autoSeed: true,
  useLocalTracker: true,
};

// Define context type
interface AppContextType {
  // State
  isConnected: boolean;
  systemStatus: SystemStatus | null;
  availableFiles: File[];
  connectionSettings: ConnectionSettings;
  isLoading: boolean;
  activeTab: string;
  
  // Actions
  setConnectionSettings: (settings: ConnectionSettings) => void;
  connectToTracker: () => Promise<boolean>;
  refreshFiles: () => Promise<void>;
  startDownload: (filename: string) => Promise<boolean>;
  setActiveTab: (tab: string) => void;
}

// Create context with default values
const AppContext = createContext<AppContextType>({
  isConnected: false,
  systemStatus: null,
  availableFiles: [],
  connectionSettings: DEFAULT_SETTINGS,
  isLoading: false,
  activeTab: 'files',
  
  setConnectionSettings: () => {},
  connectToTracker: async () => false,
  refreshFiles: async () => {},
  startDownload: async () => false,
  setActiveTab: () => {},
});

// Custom hook to use the app context
export const useAppContext = () => useContext(AppContext);

// Provider component
export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Load initial state from localStorage if available
  const [isConnected, setIsConnected] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('isConnected');
      return saved === 'true';
    }
    return false;
  });
  
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('systemStatus');
      return saved ? JSON.parse(saved) : null;
    }
    return null;
  });
  
  const [availableFiles, setAvailableFiles] = useState<File[]>([]);
  const [connectionSettings, setConnectionSettings] = useState<ConnectionSettings>(DEFAULT_SETTINGS);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('files');
  const [lastFileRefresh, setLastFileRefresh] = useState(0);

  // Save connection state to localStorage when it changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('isConnected', isConnected.toString());
    }
  }, [isConnected]);

  useEffect(() => {
    if (typeof window !== 'undefined' && systemStatus) {
      localStorage.setItem('systemStatus', JSON.stringify(systemStatus));
    }
  }, [systemStatus]);

  // Define fetch functions with useCallback to prevent recreation on every render
  const fetchSystemStatus = useCallback(async () => {
    try {
      console.log("Fetching system status...");
      const status = await getSystemStatus();
      console.log("System status received:", status);
      
      // Check if tracker info indicates we're connected
      const isActive = status.tracker && status.tracker.address !== 'Not connected';
      console.log("Connection active:", isActive);
      
      setSystemStatus(status);
      setIsConnected(isActive);
    } catch (error) {
      console.error('Error fetching system status:', error);
    }
  }, []);

  const fetchAvailableFiles = useCallback(async () => {
    // Add a timestamp check to avoid fetching too frequently
    const now = Date.now();
    if (now - lastFileRefresh < 5000) { // No more than once every 5 seconds
      console.log("Skipping file refresh - too soon");
      return;
    }
    
    try {
      console.log("Fetching available files...");
      setIsLoading(true);
      const files = await getAvailableFiles();
      console.log("Files received:", files);
      setAvailableFiles(files);
      setLastFileRefresh(now);
    } catch (error) {
      console.error("Error fetching files:", error);
    } finally {
      setIsLoading(false);
    }
  }, [lastFileRefresh]);

  // Initialize WebSocket connection when connected
  useEffect(() => {
    if (isConnected) {
      console.log("Initializing WebSocket connection due to connected state");
      const webSocketClient = getWebSocketClient();
      
      // Connect to WebSocket
      webSocketClient.connect();
      
      // Subscribe to updates
      const unsubscribe = webSocketClient.subscribe((data) => {
        console.log("Received WebSocket update:", data);
        setSystemStatus(data);
      });
      
      // Fetch initial system status
      fetchSystemStatus();
      
      // Cleanup on unmount
      return () => {
        unsubscribe();
        webSocketClient.disconnect();
      };
    }
  }, [isConnected, fetchSystemStatus]);

  // Separate effect for initial file fetch to avoid loops
  useEffect(() => {
    if (isConnected) {
      fetchAvailableFiles();
    }
  }, [isConnected, fetchAvailableFiles]);

  // Connect to tracker with useCallback
  const connectToTracker = useCallback(async (): Promise<boolean> => {
    console.log("Connecting to tracker with settings:", connectionSettings);
    setIsLoading(true);
    
    try {
      // First configure the backend with the new tracker settings
      const configSuccess = await configureTracker(
        connectionSettings.trackerIp,
        connectionSettings.trackerPort,
        connectionSettings.useLocalTracker || false
      );
      
      if (!configSuccess) {
        console.error("Failed to configure tracker on backend");
        return false;
      }
      
      // Check system status to verify the connection
      console.log("Fetching system status...");
      const status = await getSystemStatus();
      console.log("System status received:", status);
      
      // Check if tracker info indicates we're connected
      const isActive = status.tracker && status.tracker.address !== 'Not connected';
      console.log("Connection active:", isActive);
      
      setIsConnected(isActive);
      setSystemStatus(status);
      
      return isActive;
    } catch (error) {
      console.error('Failed to connect to tracker:', error);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [connectionSettings]);

  // Create debounced version of fetchAvailableFiles
  const debouncedFetchFiles = useCallback(
    debounce(async () => {
      await fetchAvailableFiles();
    }, 500),
    [fetchAvailableFiles]
  );
  
  // Refresh file list with useCallback (only need one version)
  const refreshFiles = useCallback(async () => {
    if (isConnected) {
      setIsLoading(true);
      await debouncedFetchFiles();
      setIsLoading(false);
    }
  }, [isConnected, debouncedFetchFiles]);

  // Start downloading a file with useCallback
  const startDownload = useCallback(async (filename: string): Promise<boolean> => {
    return await downloadFile(filename);
  }, []);

  // Context value
  const contextValue: AppContextType = {
    isConnected,
    systemStatus,
    availableFiles,
    connectionSettings,
    isLoading,
    activeTab,
    
    setConnectionSettings,
    connectToTracker,
    refreshFiles,
    startDownload,
    setActiveTab,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};