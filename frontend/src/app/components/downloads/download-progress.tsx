'use client';

import React from 'react';
import { DownloadProgress as DownloadProgressType } from '../../types';

interface DownloadProgressProps {
  download: DownloadProgressType;
}

export default function DownloadProgress({ download }: DownloadProgressProps) {
  // Extract number values from the progress string (e.g., "45/100 chunks (45.0%)")
  const progressMatch = download.progress.match(/(\d+)\/(\d+).*\((\d+\.?\d*)%\)/);
  const progressPercent = progressMatch ? parseFloat(progressMatch[3]) : 0;
  const completed = progressMatch ? parseInt(progressMatch[1], 10) : 0;
  const total = progressMatch ? parseInt(progressMatch[2], 10) : 1;
  
  // Determine status color
  const getStatusColor = () => {
    switch (download.status) {
      case 'completed':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      case 'downloading':
        return 'bg-blue-500';
      default:
        return 'bg-gray-300 dark:bg-gray-600';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm p-4 mb-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate" title={download.filename}>
          {download.filename}
        </h3>
        <div className="flex items-center">
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400 mr-2">
            {download.seeders} {download.seeders === 1 ? 'seeder' : 'seeders'}
          </span>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
            download.status === 'downloading' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
            download.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
            download.status === 'error' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' :
            'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
          }`}>
            {download.status || 'pending'}
          </span>
        </div>
      </div>
      
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mb-2">
        <div 
          className={`h-2.5 rounded-full ${getStatusColor()}`}
          style={{ width: `${progressPercent}%` }}
        ></div>
      </div>
      
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>{progressPercent.toFixed(1)}% complete</span>
        <span>{completed} of {total} chunks</span>
      </div>
      
      {/* Additional actions could be added here */}
      {download.status === 'downloading' && (
        <div className="mt-3 flex justify-end">
          <button
            className="text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white flex items-center"
          >
            <svg className="w-4 h-4 mr-1" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M6 18L18 6M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}