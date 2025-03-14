'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppContext } from '../context/app-context';

export default function ConnectionForm() {
  const router = useRouter();
  const { connectionSettings, setConnectionSettings, connectToTracker, isLoading, isConnected } = useAppContext();
  
  // Add tracker mode state
  const [trackerMode, setTrackerMode] = useState('local'); // 'local' or 'remote'
  
  const [formData, setFormData] = useState({
    trackerIp: connectionSettings.trackerIp,
    trackerPort: connectionSettings.trackerPort,
  });
  
  const [error, setError] = useState<string | null>(null);
  
  // Check if already connected, redirect to dashboard
  useEffect(() => {
    const checkConnection = async () => {
      if (isConnected) {
        console.log("Already connected, redirecting to dashboard...");
        router.push('/dashboard/files');
      }
    };
    
    checkConnection();
  }, [isConnected, router]);
  
  // Handle form input changes
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value,
    });
  };
  
  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    console.log("Form submitted with:", formData, "Tracker mode:", trackerMode);
    
    // Update connection settings
    setConnectionSettings({
      ...connectionSettings,
      trackerIp: formData.trackerIp,
      trackerPort: formData.trackerPort,
      useLocalTracker: trackerMode === 'local',
    });
    
    // Try to connect
    try {
      console.log("Attempting to connect to tracker...");
      const success = await connectToTracker();
      console.log("Connection result:", success);
      
      if (success) {
        console.log("Connection successful, redirecting to dashboard...");
        // Use setTimeout to ensure state updates have completed
        setTimeout(() => {
          router.push('/dashboard/files');
        }, 300);
      } else {
        setError('Failed to connect to tracker. Please check your settings and try again.');
      }
    } catch (error) {
      setError('An unexpected error occurred. Please try again.');
      console.error('Connection error:', error);
    }
  };

  return (
    <div className="max-w-md w-full space-y-8">
      <div className="text-center">
        <div className="flex justify-center">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center">
            <svg className="w-10 h-10 text-white" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="3" fill="currentColor"/>
              <path d="M12 3C7.02944 3 3 7.02944 3 12C3 16.9706 7.02944 21 12 21C16.9706 21 21 16.9706 21 12" 
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <path d="M3.5 8.5L7 5M20.5 15.5L17 19M7 19L3.5 15.5M17 5L20.5 8.5" 
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
        </div>
        <h1 className="mt-4 text-3xl font-extrabold text-gray-900 dark:text-white">P2P File Sharing</h1>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Connect to a tracker to start sharing files with the network
        </p>
      </div>
      
      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-300 px-4 py-3 rounded relative" role="alert">
          <span className="block sm:inline">{error}</span>
        </div>
      )}
      
      <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
        <div className="rounded-md shadow-sm -space-y-px">
          <div>
            <label htmlFor="trackerIp" className="sr-only">Tracker IP</label>
            <input
              id="trackerIp"
              name="trackerIp"
              type="text"
              required
              className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-700 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white dark:bg-gray-800 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
              placeholder="Tracker IP (e.g., 127.0.0.1)"
              value={formData.trackerIp}
              onChange={handleChange}
            />
          </div>
          <div>
            <label htmlFor="trackerPort" className="sr-only">Tracker Port</label>
            <input
              id="trackerPort"
              name="trackerPort"
              type="text"
              required
              pattern="[0-9]*"
              className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-700 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white dark:bg-gray-800 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
              placeholder="Tracker Port (e.g., 12345)"
              value={formData.trackerPort}
              onChange={handleChange}
            />
          </div>
        </div>

        {/* Tracker mode selection */}
        <div className="mt-4">
          <div className="flex items-center space-x-4">
            <div className="flex items-center">
              <input
                id="local-tracker"
                name="trackerMode"
                type="radio"
                checked={trackerMode === 'local'}
                onChange={() => setTrackerMode('local')}
                className="h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500"
              />
              <label htmlFor="local-tracker" className="ml-2 block text-sm text-gray-600 dark:text-gray-400">
                Start local tracker
              </label>
            </div>
            <div className="flex items-center">
              <input
                id="remote-tracker"
                name="trackerMode"
                type="radio"
                checked={trackerMode === 'remote'}
                onChange={() => setTrackerMode('remote')}
                className="h-4 w-4 text-blue-600 border-gray-300 focus:ring-blue-500"
              />
              <label htmlFor="remote-tracker" className="ml-2 block text-sm text-gray-600 dark:text-gray-400">
                Connect to remote tracker
              </label>
            </div>
          </div>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {trackerMode === 'local' ? 
              'Start a tracker on this machine' : 
              'Connect to an existing tracker on another machine'}
          </p>
        </div>

        <div>
          <button
            type="submit"
            disabled={isLoading}
            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Connecting...
              </>
            ) : 'Connect to Tracker'}
          </button>
        </div>
      </form>
    </div>
  );
}