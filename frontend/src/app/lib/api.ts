import { File, SystemStatus } from "../types/";

// API base URL - this should match your backend URL
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000/api';
console.log("API connecting to:", API_BASE);

// Get available files
export async function getAvailableFiles(): Promise<File[]> {
  try {
    console.log("Fetching available files from API");
    const response = await fetch(`${API_BASE}/files`);
    
    if (!response.ok) {
      throw new Error(`Error fetching files: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log("Files response:", data);
    
    // Check if we have an array of strings and convert to File objects
    if (data.files && Array.isArray(data.files)) {
      if (data.files.length > 0 && typeof data.files[0] === 'string') {
        // Convert string array to File objects with proper type annotation
        const fileObjects = data.files.map((filename: string) => ({ 
          filename,
          // Optional: You could add default values for other properties
          // size: 0,
          // seeders: 0
        }));
        console.log("Converted file objects:", fileObjects);
        return fileObjects;
      }
      return data.files; // Already in correct format
    }
    return [];
  } catch (error) {
    console.error('Failed to fetch available files:', error);
    return [];
  }
}

// Get system status
export async function getSystemStatus(): Promise<SystemStatus> {
  try {
    console.log("Fetching system status from API");
    const response = await fetch(`${API_BASE}/status`);
    
    if (!response.ok) {
      throw new Error(`Error fetching status: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log("Status response:", data);
    return data;
  } catch (error) {
    console.error('Failed to fetch system status:', error);
    return {
      downloads: {
        current_downloads: [],
        completed_downloads: []
      },
      tracker: {
        address: 'Not connected'
      },
      error: 'Failed to connect to backend'
    };
  }
}

// Start downloading a file
export async function downloadFile(filename: string): Promise<boolean> {
  try {
    console.log("Requesting download for file:", filename);
    const response = await fetch(`${API_BASE}/download`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ filename }),
    });
    
    if (!response.ok) {
      throw new Error(`Error starting download: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log("Download response:", data);
    return data.success || false;
  } catch (error) {
    console.error(`Failed to start download for ${filename}:`, error);
    return false;
  }
}

// Get downloaded files
export async function getDownloadedFiles(): Promise<string[]> {
  try {
    console.log("Fetching downloaded files");
    const response = await fetch(`${API_BASE}/downloaded`);
    
    if (!response.ok) {
      throw new Error(`Error fetching downloaded files: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log("Downloaded files response:", data);
    return data.files || [];
  } catch (error) {
    console.error('Failed to fetch downloaded files:', error);
    return [];
  }
}

// Configure tracker
export async function configureTracker(trackerIp: string, trackerPort: string, startLocalTracker: boolean): Promise<boolean> {
  try {
    console.log("Configuring tracker:", { trackerIp, trackerPort, startLocalTracker });
    const response = await fetch(`${API_BASE}/configure`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ trackerIp, trackerPort, startLocalTracker }),
    });
    
    if (!response.ok) {
      throw new Error(`Error configuring tracker: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log("Configuration response:", data);
    return data.success || false;
  } catch (error) {
    console.error(`Failed to configure tracker:`, error);
    return false;
  }
}