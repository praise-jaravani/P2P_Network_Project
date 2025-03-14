'use client';

import React, { useEffect } from 'react';
import Header from '../../components/layout/header';
import FileList from '../../components/files/file-list';
import { useAppContext } from '../../context/app-context';

export default function FilesPage() {
  const { refreshFiles, setActiveTab, isConnected, availableFiles } = useAppContext();
  
  // Set active tab
  useEffect(() => {
    setActiveTab('files');
    
    // Only fetch files when connected and if we don't have any yet
    if (isConnected && availableFiles.length === 0) {
      refreshFiles();
    }
  }, [refreshFiles, setActiveTab, isConnected, availableFiles.length]);

  return (
    <div className="py-6">
      <Header 
        title="Available Files" 
        subtitle="Browse and download files from the network"
      />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-6">
        <FileList />
      </div>
    </div>
  );
}