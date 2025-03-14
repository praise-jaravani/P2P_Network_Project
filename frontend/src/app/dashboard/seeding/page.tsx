'use client';

import React, { useEffect } from 'react';
import Header from '../../components/layout/header';
import SeedingList from '../../components/seeding/seeding-list';
import { useAppContext } from '../../context/app-context';

export default function SeedingPage() {
  const { setActiveTab } = useAppContext();
  
  // Set active tab
  useEffect(() => {
    setActiveTab('seeding');
  }, [setActiveTab]);

  return (
    <div className="py-6">
      <Header 
        title="Seeding" 
        subtitle="Files you are sharing with the network"
      />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-6">
        <SeedingList />
      </div>
    </div>
  );
}