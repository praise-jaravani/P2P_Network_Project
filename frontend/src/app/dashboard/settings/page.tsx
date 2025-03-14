'use client';

import React, { useEffect } from 'react';
import Header from '../../components/layout/header';
import SettingsForm from '../../components/settings/settings-form';
import { useAppContext } from '../../context/app-context';

export default function SettingsPage() {
  const { setActiveTab } = useAppContext();
  
  // Set active tab
  useEffect(() => {
    setActiveTab('settings');
  }, [setActiveTab]);

  return (
    <div className="py-6">
      <Header 
        title="Settings" 
        subtitle="Configure your P2P client"
      />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-6">
        <SettingsForm />
      </div>
    </div>
  );
}