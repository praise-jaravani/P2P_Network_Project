'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAppContext } from '../../context/app-context';

const navItems = [
  { name: 'Files', path: '/dashboard/files', icon: 'folder' },
  { name: 'Downloads', path: '/dashboard/downloads', icon: 'download' },
  { name: 'Seeding', path: '/dashboard/seeding', icon: 'upload' },
  { name: 'Settings', path: '/dashboard/settings', icon: 'settings' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { systemStatus } = useAppContext();
  const [isMounted, setIsMounted] = useState(false);
  
  // Set isMounted to true after component mounts to prevent hydration mismatch
  useEffect(() => {
    setIsMounted(true);
  }, []);
  
  // Helper function to determine if a nav item is active
  const isActive = (path: string) => pathname === path;
  
  // Format active seeders count
  const activeSeeders = systemStatus?.tracker?.active_seeders || 0;
  
  // Count current downloads
  const activeDownloads = systemStatus?.downloads?.current_downloads?.length || 0;
  
  // Total completed downloads
  const completedDownloads = systemStatus?.downloads?.completed_downloads?.length || 0;

  return (
    <div className="w-64 bg-white dark:bg-gray-900 h-full flex flex-col shadow-lg">
      {/* Logo Header */}
      <div className="h-16 flex items-center justify-center border-b border-gray-200 dark:border-gray-800">
        <Link href="/dashboard" className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="3" fill="currentColor"/>
              <path d="M12 3C7.02944 3 3 7.02944 3 12C3 16.9706 7.02944 21 12 21C16.9706 21 21 16.9706 21 12" 
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              <path d="M3.5 8.5L7 5M20.5 15.5L17 19M7 19L3.5 15.5M17 5L20.5 8.5" 
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            P2P Share
          </span>
        </Link>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 py-6 px-4">
        <ul className="space-y-2">
          {navItems.map((item) => (
            <li key={item.name}>
              <Link
                href={item.path}
                className={`flex items-center px-4 py-3 rounded-lg transition-colors ${
                  isActive(item.path)
                    ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                    : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
                }`}
              >
                <span className="mr-3">
                  {item.icon === 'folder' && (
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M3 8.2V17C3 19.2091 4.79086 21 7 21H17C19.2091 21 21 19.2091 21 17V8.2M3 8.2V7C3 4.79086 4.79086 3 7 3H9.46482C10.4474 3 11.3622 3.47545 11.9512 4.2678L12.5 5H17C19.2091 5 21 6.79086 21 9V8.2M3 8.2H21" 
                        stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                  )}
                  {item.icon === 'download' && (
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 3V16M12 16L16 12M12 16L8 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M3 15V17C3 18.1046 3.89543 19 5 19H19C20.1046 19 21 18.1046 21 17V15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                  )}
                  {item.icon === 'upload' && (
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 16V3M12 3L16 7M12 3L8 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M3 15V17C3 18.1046 3.89543 19 5 19H19C20.1046 19 21 18.1046 21 17V15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                  )}
                  {item.icon === 'settings' && (
                    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M19.4 15C19.1277 15.8031 19.2584 16.6718 19.75 17.35C20.1294 17.8686 20.064 18.5646 19.6 19C19.136 19.4354 18.4399 19.5008 17.9213 19.1213C17.2426 18.6298 16.3733 18.4995 15.5699 18.7722C14.7672 19.0447 14.1687 19.6775 14 20.5C13.8764 21.0499 13.4015 21.476 12.8334 21.4994C12.2657 21.5227 11.7602 21.1361 11.6 20.6C11.4313 19.7775 10.8328 19.1447 10.0301 18.8722C9.22676 18.5995 8.35742 18.7298 7.67875 19.2212C7.16016 19.6008 6.46402 19.5354 6 19.1C5.53605 18.6646 5.47066 17.9686 5.85 17.45C6.34172 16.7718 6.47262 15.9032 6.20039 15.1C5.92816 14.2967 5.29486 13.6968 4.47222 13.5333C3.92396 13.3625 3.53745 12.8557 3.56079 12.2876C3.58413 11.7192 4.01037 11.2444 4.56 11.1333C5.38264 10.9646 6.01568 10.3661 6.28791 9.56284C6.56014 8.7596 6.42924 7.89026 5.93752 7.21161C5.55818 6.693 5.62357 5.99686 6.08752 5.56284C6.55148 5.12883 7.24762 5.06344 7.76624 5.44276C8.44488 5.93448 9.31422 6.06557 10.1174 5.79335C10.9207 5.52115 11.5192 4.88803 11.6878 4.0654C11.8488 3.52938 12.3543 3.14251 12.9215 3.16586C13.4893 3.18921 13.9642 3.61556 14.0878 4.16551C14.2564 4.98816 14.8549 5.62127 15.6582 5.89349C16.4614 6.16572 17.3312 6.03462 18.0098 5.54251C18.5285 5.16317 19.2246 5.22857 19.6582 5.66257C20.0921 6.09658 20.1575 6.79272 19.7782 7.31134C19.2865 7.98998 19.1558 8.85932 19.428 9.66255C19.7003 10.4658 20.3336 11.0653 21.1562 11.2339C21.7042 11.345 22.1304 11.8198 22.1538 12.3879C22.1771 12.9561 21.7906 13.463 21.2546 13.6333C20.432 13.8019 19.799 14.4001 19.4 15.2033V15Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  )}
                </span>
                {item.name}
                
                {/* Badges for Downloads and Seeding */}
                {item.name === 'Downloads' && activeDownloads > 0 && (
                  <span className="ml-auto bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-300 px-2 py-0.5 rounded-full text-xs">
                    {activeDownloads}
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      
      {/* Status Section */}
      <div className="mt-auto border-t border-gray-200 dark:border-gray-800 p-4">
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">Network Status</h3>
          
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-300">Active Seeders:</span>
              <span className="text-sm font-medium text-gray-900 dark:text-white">{activeSeeders}</span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-300">Downloads:</span>
              <span className="text-sm font-medium text-gray-900 dark:text-white">{activeDownloads}/{completedDownloads}</span>
            </div>
            
            {/* Tracker status with client-side only rendering */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-300">Tracker:</span>
              {isMounted ? (
                <span className="flex items-center">
                  <span className={`h-2 w-2 rounded-full mr-2 ${systemStatus ? 'bg-green-500' : 'bg-red-500'}`}></span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {systemStatus ? 'Connected' : 'Disconnected'}
                  </span>
                </span>
              ) : (
                <span className="text-sm font-medium text-gray-400">Loading...</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}