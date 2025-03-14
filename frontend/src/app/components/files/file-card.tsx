'use client';

import React from 'react';
import { useAppContext } from '../../context/app-context';
import { File } from '../../types';

interface FileCardProps {
  file: File;
}

export default function FileCard({ file }: FileCardProps) {
  const { startDownload, isLoading } = useAppContext();
  const [isDownloading, setIsDownloading] = React.useState(false);
  
  // Handle download button click
  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      await startDownload(file.filename);
      // Success is handled by the WebSocket updates
    } catch (error) {
      console.error('Failed to start download:', error);
    } finally {
      setIsDownloading(false);
    }
  };
  
  // Determine file type icon based on extension
  const getFileTypeIcon = (filename: string) => {
    const extension = filename.split('.').pop()?.toLowerCase();
    
    switch (extension) {
      case 'pdf':
        return (
          <svg className="w-8 h-8 text-red-500" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M7 18H17V16H7V18Z" fill="currentColor" />
            <path d="M17 14H7V12H17V14Z" fill="currentColor" />
            <path d="M7 10H11V8H7V10Z" fill="currentColor" />
            <path fillRule="evenodd" clipRule="evenodd" d="M6 2C4.34315 2 3 3.34315 3 5V19C3 20.6569 4.34315 22 6 22H18C19.6569 22 21 20.6569 21 19V9C21 5.13401 17.866 2 14 2H6ZM6 4H13V9H19V19C19 19.5523 18.5523 20 18 20H6C5.44772 20 5 19.5523 5 19V5C5 4.44772 5.44772 4 6 4ZM15 4.10002C16.6113 4.4271 17.9413 5.52906 18.584 7H15V4.10002Z" fill="currentColor" />
          </svg>
        );
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
        return (
          <svg className="w-8 h-8 text-purple-500" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path fillRule="evenodd" clipRule="evenodd" d="M7 7C5.34315 7 4 8.34315 4 10C4 11.6569 5.34315 13 7 13C8.65685 13 10 11.6569 10 10C10 8.34315 8.65685 7 7 7ZM6 10C6 9.44772 6.44772 9 7 9C7.55228 9 8 9.44772 8 10C8 10.5523 7.55228 11 7 11C6.44772 11 6 10.5523 6 10Z" fill="currentColor" />
            <path fillRule="evenodd" clipRule="evenodd" d="M3 3C1.34315 3 0 4.34315 0 6V18C0 19.6569 1.34315 21 3 21H21C22.6569 21 24 19.6569 24 18V6C24 4.34315 22.6569 3 21 3H3ZM21 5H3C2.44772 5 2 5.44772 2 6V18C2 18.5523 2.44772 19 3 19H7.31374L14.1924 12.1214C15.364 10.9498 17.2635 10.9498 18.435 12.1214L22 15.6863V6C22 5.44772 21.5523 5 21 5ZM21 19H10.1422L15.6066 13.5356C15.9971 13.145 16.6303 13.145 17.0208 13.5356L22 18.5147V18C22 18.5523 21.5523 19 21 19Z" fill="currentColor" />
          </svg>
        );
      case 'mp3':
      case 'wav':
      case 'ogg':
        return (
          <svg className="w-8 h-8 text-green-500" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M9 17C9 17.5523 8.55228 18 8 18C7.44772 18 7 17.5523 7 17C7 16.4477 7.44772 16 8 16C8.55228 16 9 16.4477 9 17Z" fill="currentColor" />
            <path d="M13 17C13 17.5523 12.5523 18 12 18C11.4477 18 11 17.5523 11 17C11 16.4477 11.4477 16 12 16C12.5523 16 13 16.4477 13 17Z" fill="currentColor" />
            <path d="M17 17C17 17.5523 16.5523 18 16 18C15.4477 18 15 17.5523 15 17C15 16.4477 15.4477 16 16 16C16.5523 16 17 16.4477 17 17Z" fill="currentColor" />
            <path fillRule="evenodd" clipRule="evenodd" d="M5 3C2.79086 3 1 4.79086 1 7V17C1 19.2091 2.79086 21 5 21H19C21.2091 21 23 19.2091 23 17V7C23 4.79086 21.2091 3 19 3H5ZM19 5H5C3.89543 5 3 5.89543 3 7V17C3 18.1046 3.89543 19 5 19H19C20.1046 19 21 18.1046 21 17V7C21 5.89543 20.1046 5 19 5Z" fill="currentColor" />
            <path d="M7 9.5C7 9.22386 7.22386 9 7.5 9H16.5C16.7761 9 17 9.22386 17 9.5V9.5C17 9.77614 16.7761 10 16.5 10H7.5C7.22386 10 7 9.77614 7 9.5V9.5Z" fill="currentColor" />
            <path d="M7 12.5C7 12.2239 7.22386 12 7.5 12H16.5C16.7761 12 17 12.2239 17 12.5V12.5C17 12.7761 16.7761 13 16.5 13H7.5C7.22386 13 7 12.7761 7 12.5V12.5Z" fill="currentColor" />
          </svg>
        );
      case 'mp4':
      case 'avi':
      case 'mov':
      case 'mkv':
        return (
          <svg className="w-8 h-8 text-blue-500" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path fillRule="evenodd" clipRule="evenodd" d="M5 3C2.79086 3 1 4.79086 1 7V17C1 19.2091 2.79086 21 5 21H19C21.2091 21 23 19.2091 23 17V7C23 4.79086 21.2091 3 19 3H5ZM19 5H5C3.89543 5 3 5.89543 3 7V17C3 18.1046 3.89543 19 5 19H19C20.1046 19 21 18.1046 21 17V7C21 5.89543 20.1046 5 19 5Z" fill="currentColor" />
            <path d="M15 12L10 8.5V15.5L15 12Z" fill="currentColor" />
          </svg>
        );
      case 'zip':
      case 'rar':
      case 'tar':
      case 'gz':
        return (
          <svg className="w-8 h-8 text-yellow-500" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M10 2H14V4H10V2Z" fill="currentColor" />
            <path d="M14 4H10V6H14V4Z" fill="currentColor" />
            <path d="M10 6H14V8H10V6Z" fill="currentColor" />
            <path d="M14 8H10V10H14V8Z" fill="currentColor" />
            <path d="M10 10H14V12H10V10Z" fill="currentColor" />
            <path d="M10 12H14V14H12V13H10V12Z" fill="currentColor" />
            <path fillRule="evenodd" clipRule="evenodd" d="M2 4C2 2.34315 3.34315 1 5 1H19C20.6569 1 22 2.34315 22 4V20C22 21.6569 20.6569 23 19 23H5C3.34315 23 2 21.6569 2 20V4ZM5 3H9V13H7V14H9V15H7V16H9V17H7V18H9V20C9 20.5523 8.55228 21 8 21H5C4.44772 21 4 20.5523 4 20V4C4 3.44772 4.44772 3 5 3ZM15 3H19C19.5523 3 20 3.44772 20 4V20C20 20.5523 19.5523 21 19 21H10V17H12V16H10V15H12V14H10V13H15V3Z" fill="currentColor" />
          </svg>
        );
      default:
        return (
          <svg className="w-8 h-8 text-gray-500" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path fillRule="evenodd" clipRule="evenodd" d="M3 5C3 3.34315 4.34315 2 6 2H14C14.2652 2 14.5196 2.10536 14.7071 2.29289L19.7071 7.29289C19.8946 7.48043 20 7.73478 20 8V19C20 20.6569 18.6569 22 17 22H6C4.34315 22 3 20.6569 3 19V5ZM6 4H13V8C13 8.55228 13.4477 9 14 9H18V19C18 19.5523 17.5523 20 17 20H6C5.44772 20 5 19.5523 5 19V5C5 4.44772 5.44772 4 6 4ZM15 4.41421L17.5858 7H15V4.41421Z" fill="currentColor" />
          </svg>
        );
    }
  };
  
  // Format file size
  const formatFileSize = (sizeInBytes?: number) => {
    if (!sizeInBytes) return 'Unknown size';
    
    if (sizeInBytes < 1024) {
      return `${sizeInBytes} B`;
    } else if (sizeInBytes < 1024 * 1024) {
      return `${(sizeInBytes / 1024).toFixed(1)} KB`;
    } else if (sizeInBytes < 1024 * 1024 * 1024) {
      return `${(sizeInBytes / (1024 * 1024)).toFixed(1)} MB`;
    } else {
      return `${(sizeInBytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="p-4">
        <div className="flex items-start space-x-3">
          {getFileTypeIcon(file.filename)}
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate">
              {file.filename}
            </h3>
            <div className="flex items-center mt-1 text-xs text-gray-500 dark:text-gray-400">
              <span>{formatFileSize(file.size)}</span>
              {file.seeders && (
                <>
                  <span className="mx-2">•</span>
                  <span>
                    {file.seeders} {file.seeders === 1 ? 'Seeder' : 'Seeders'}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
      
      <div className="bg-gray-50 dark:bg-gray-750 px-4 py-3 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={handleDownload}
          disabled={isDownloading || isLoading}
          className="w-full inline-flex justify-center items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isDownloading ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Downloading...
            </>
          ) : (
            <>
              <svg className="-ml-0.5 mr-2 h-4 w-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 4V16M12 16L8 12M12 16L16 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M3 19H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              Download
            </>
          )}
        </button>
      </div>
    </div>
  );
}