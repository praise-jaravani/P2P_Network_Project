'use client';

import { useEffect, useState } from 'react';
import ConnectionForm from './components/connection-form';
import LoadingScreen from './components/layout/loading-screen';
import { AppProvider } from './context/app-context';

export default function Home() {
  const [showLoading, setShowLoading] = useState(true);
  
  useEffect(() => {
    // Hide loading screen after timeout
    const timer = setTimeout(() => {
      setShowLoading(false);
    }, 1000);
    
    return () => clearTimeout(timer);
  }, []);

  return (
    <AppProvider>
      {showLoading && <LoadingScreen />}
      
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white dark:bg-gray-800 py-8 px-4 shadow sm:rounded-lg sm:px-10">
            <ConnectionForm />
          </div>
        </div>
      </div>
    </AppProvider>
  );
}