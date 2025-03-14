// File related types
export interface File {
    filename: string;
    size?: number;
    seeders?: number;
  }
  
  // Download status types
  export interface DownloadProgress {
    filename: string;
    progress: string;
    seeders: number;
    status?: 'pending' | 'downloading' | 'completed' | 'error';
  }
  
  export interface DownloadStatus {
    current_downloads: DownloadProgress[];
    completed_downloads: string[];
  }
  
  // Tracker status
  export interface TrackerInfo {
    address: string;
    active_seeders?: number;
  }
  
  // System status from the API
  export interface SystemStatus {
    downloads: DownloadStatus;
    tracker: TrackerInfo;
    error?: string;
  }
  
  // Connection settings
  export interface ConnectionSettings {
    trackerIp: string;
    trackerPort: string;
    downloadDir?: string;
    autoSeed: boolean;
    useLocalTracker?: boolean;
  }