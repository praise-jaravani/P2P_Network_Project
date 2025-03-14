'use client';

import { useState, useEffect } from 'react';
import { AppProvider, useAppContext } from '../context/app-context';
import Sidebar from '../components/layout/sidebar';
import LoadingScreen from '../components/layout/loading-screen';
import { useRouter } from 'next/navigation';

// Wrapper component to allow using hooks
function DashboardLayoutContent({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isConnected, systemStatus } = useAppContext();
  
  // If not connected, redirect to home page
  useEffect(() => {
    console.log("Dashboard Layout - Connection Check:", { 
      isConnected, 
      hasSystemStatus: !!systemStatus 
    });
    
    if (!isConnected && !systemStatus) {
      console.log("Not connected, redirecting to home");
      router.push('/');
    }
  }, [isConnected, systemStatus, router]);
  
  return (
    <div className="h-screen flex overflow-hidden bg-gray-100 dark:bg-gray-900">
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main content */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Main content scrollable container */}
        <main className="flex-1 relative overflow-y-auto focus:outline-none">
          {children}
        </main>
      </div>
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
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
      <DashboardLayoutContent>{children}</DashboardLayoutContent>
    </AppProvider>
  );
}