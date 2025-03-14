'use client';

import React, { useEffect } from 'react';
import Header from '../../components/layout/header';
import DownloadList from '../../components/downloads/download-list';
import { useAppContext } from '../../context/app-context';

export default function DownloadsPage() {
  const { setActiveTab } = useAppContext();
  
  // Set active tab
  useEffect(() => {
    setActiveTab('downloads');
  }, [setActiveTab]);

  return (
    <div className="py-6">
      <Header 
        title="Downloads" 
        subtitle="Manage your active and completed downloads"
      />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-6">
        <DownloadList />
      </div>
    </div>
  );
}