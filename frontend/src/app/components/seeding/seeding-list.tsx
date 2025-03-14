'use client';

import React from 'react';
import { useAppContext } from '../../context/app-context';

export default function SeedingList() {
  const { systemStatus, isLoading } = useAppContext();
  
  // Get completed downloads, which are also being seeded
  const seedingFiles = systemStatus?.downloads?.completed_downloads || [];
  
  // If loading
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <svg className="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>
    );
  }

  // If no files are being seeded
  if (seedingFiles.length === 0) {
    return (
      <div className="py-12 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 text-center">
        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">No files being seeded</h3>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          You aren't seeding any files yet. Download files to automatically start seeding them.
        </p>
        <div className="mt-6">
          <button
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            onClick={() => window.location.href = '/dashboard/files'}
          >
            Find files to download
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white">Seeding Files</h2>
            <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded dark:bg-blue-900 dark:text-blue-300">
              {seedingFiles.length} files
            </span>
          </div>
        </div>
        <ul className="divide-y divide-gray-200 dark:divide-gray-700">
          {seedingFiles.map((filename) => (
            <li key={filename} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-750">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="flex-shrink-0 bg-green-100 dark:bg-green-900 p-2 rounded-full">
                    <svg className="w-5 h-5 text-green-600 dark:text-green-300" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 16V3M12 3L16 7M12 3L8 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M3 15V17C3 18.1046 3.89543 19 5 19H19C20.1046 19 21 18.1046 21 17V15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{filename}</p>
                    <div className="flex items-center text-xs text-gray-500 dark:text-gray-400">
                      <span>Active • 100% available</span>
                    </div>
                  </div>
                </div>
                <div>
                  <button className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 5V19M5 12H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </button>
                </div>
              </div>
              
              {/* Upload statistics would go here */}
              <div className="mt-2 grid grid-cols-2 gap-4">
                <div className="bg-gray-50 dark:bg-gray-800 rounded p-2">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Upload Speed</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">-</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 rounded p-2">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Total Uploaded</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">-</p>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}