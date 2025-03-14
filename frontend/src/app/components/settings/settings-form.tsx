'use client';

import React, { useState } from 'react';
import { useAppContext } from '../../context/app-context';
import { ConnectionSettings } from '../../types';

export default function SettingsForm() {
  const { connectionSettings, setConnectionSettings, isLoading } = useAppContext();
  const [formData, setFormData] = useState<ConnectionSettings>(connectionSettings);
  
  // Handle form input changes
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value,
    });
  };
  
  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setConnectionSettings(formData);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="p-6">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-6">Connection Settings</h2>
        
        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            {/* Tracker Settings */}
            <div>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-4">Tracker Configuration</h3>
              <div className="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-6">
                <div className="sm:col-span-3">
                  <label htmlFor="trackerIp" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Tracker IP
                  </label>
                  <div className="mt-1">
                    <input
                      type="text"
                      name="trackerIp"
                      id="trackerIp"
                      value={formData.trackerIp}
                      onChange={handleChange}
                      className="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md"
                      placeholder="127.0.0.1"
                    />
                  </div>
                </div>

                <div className="sm:col-span-3">
                  <label htmlFor="trackerPort" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Tracker Port
                  </label>
                  <div className="mt-1">
                    <input
                      type="text"
                      name="trackerPort"
                      id="trackerPort"
                      value={formData.trackerPort}
                      onChange={handleChange}
                      className="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md"
                      placeholder="12345"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Download Settings */}
            <div>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-4">Download Settings</h3>
              <div className="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-6">
                <div className="sm:col-span-6">
                  <label htmlFor="downloadDir" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Download Directory
                  </label>
                  <div className="mt-1">
                    <input
                      type="text"
                      name="downloadDir"
                      id="downloadDir"
                      value={formData.downloadDir}
                      onChange={handleChange}
                      className="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md"
                      placeholder="./downloads"
                    />
                  </div>
                  <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    This setting can only be changed through the backend configuration.
                  </p>
                </div>
              </div>
            </div>

            {/* Seeding Settings */}
            <div>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-4">Seeding Settings</h3>
              <div className="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-6">
                <div className="sm:col-span-6">
                  <div className="flex items-start">
                    <div className="flex items-center h-5">
                      <input
                        id="autoSeed"
                        name="autoSeed"
                        type="checkbox"
                        checked={formData.autoSeed}
                        onChange={handleChange}
                        className="focus:ring-blue-500 h-4 w-4 text-blue-600 border-gray-300 rounded"
                      />
                    </div>
                    <div className="ml-3 text-sm">
                      <label htmlFor="autoSeed" className="font-medium text-gray-700 dark:text-gray-300">
                        Automatically seed after download
                      </label>
                      <p className="text-gray-500 dark:text-gray-400">
                        When enabled, your client will automatically share files after they are downloaded.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-6 mt-6 border-t border-gray-200 dark:border-gray-700">
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setFormData(connectionSettings)}
                disabled={isLoading}
                className="py-2 px-4 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-650 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 mr-3"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Saving...
                  </>
                ) : 'Save Settings'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}