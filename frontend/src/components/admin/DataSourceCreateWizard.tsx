/**
 * DataSourceCreateWizard Component
 *
 * Multi-step wizard for creating new data source connections.
 * Supports: JDBC, REST API, CSV, JSON
 */

import { useState } from 'react';
import api from '../../services/api';

type DataSourceType = 'jdbc' | 'rest_api' | 'csv' | 'json';
type JDBCDriver = 'postgresql' | 'mysql' | 'oracle' | 'sqlserver';
type AuthType = 'none' | 'basic' | 'bearer_token' | 'api_key';

interface CreateWizardProps {
  onClose: () => void;
  onSuccess: () => void;
}

export function DataSourceCreateWizard({ onClose, onSuccess }: CreateWizardProps) {
  const [step, setStep] = useState(1);
  const [sourceType, setSourceType] = useState<DataSourceType>('rest_api');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  // JDBC fields
  const [jdbcDriver, setJdbcDriver] = useState<JDBCDriver>('postgresql');
  const [host, setHost] = useState('localhost');
  const [port, setPort] = useState('5432');
  const [database, setDatabase] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // REST API fields
  const [baseUrl, setBaseUrl] = useState('');
  const [dataEndpoint, setDataEndpoint] = useState('/');
  const [testEndpoint, setTestEndpoint] = useState('/health');
  const [authType, setAuthType] = useState<AuthType>('none');
  const [apiToken, setApiToken] = useState('');
  const [apiKeyName, setApiKeyName] = useState('X-API-Key');
  const [apiKeyValue, setApiKeyValue] = useState('');

  // CSV/JSON fields
  const [filePath, setFilePath] = useState('');

  // UI state
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [creating, setCreating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [existingSourceId, setExistingSourceId] = useState<string | null>(null);

  const handleTypeSelect = (type: DataSourceType) => {
    setSourceType(type);
    setStep(2);

    // Set default ports
    if (type === 'jdbc') {
      if (jdbcDriver === 'postgresql') setPort('5432');
      else if (jdbcDriver === 'mysql') setPort('3306');
      else if (jdbcDriver === 'oracle') setPort('1521');
      else if (jdbcDriver === 'sqlserver') setPort('1433');
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);

    try {
      // Build config
      const config: any = {};
      const auth_config: any = {};

      if (sourceType === 'jdbc') {
        config.driver = jdbcDriver;
        config.host = host;
        config.port = parseInt(port);
        config.database = database;
        auth_config.username = username;
        auth_config.password = password;
      } else if (sourceType === 'rest_api') {
        config.base_url = baseUrl;
        config.data_endpoint = dataEndpoint;
        config.test_endpoint = testEndpoint;
        if (authType === 'bearer_token') {
          auth_config.type = 'bearer_token';
          auth_config.token = apiToken;
        } else if (authType === 'api_key') {
          auth_config.type = 'api_key';
          auth_config.key_name = apiKeyName;
          auth_config.key_value = apiKeyValue;
        }
      } else if (sourceType === 'csv' || sourceType === 'json') {
        config.file_path = filePath;
      }

      // Create temporary source
      const response = await api.post('/data-sources/create', {
        name: name || 'Test Connection',
        source_type: sourceType,
        description,
        config,
        auth_config
      });

      setTestResult({
        success: true,
        message: response.data.test_result || 'Connection successful'
      });
    } catch (error: any) {
      if (error.response?.status === 409) {
        const detail = error.response.data?.detail;
        const existId = typeof detail === 'object' ? detail?.source_id : null;
        setExistingSourceId(existId);
        setTestResult({
          success: true,
          message: `Source already exists (${existId ?? 'existing'}). Will reuse it.`,
        });
      } else {
        setTestResult({
          success: false,
          message: error.response?.data?.detail || 'Connection failed',
        });
      }
    } finally {
      setTesting(false);
    }
  };

  const handleCreate = async () => {
    // If we already know it exists from the test phase, skip creation
    if (existingSourceId) {
      onSuccess();
      onClose();
      return;
    }

    setCreating(true);
    try {
      const config: any = {};
      const auth_config: any = {};

      if (sourceType === 'jdbc') {
        config.driver = jdbcDriver;
        config.host = host;
        config.port = parseInt(port);
        config.database = database;
        auth_config.username = username;
        auth_config.password = password;
      } else if (sourceType === 'rest_api') {
        config.base_url = baseUrl;
        config.data_endpoint = dataEndpoint;
        config.test_endpoint = testEndpoint;
        if (authType === 'bearer_token') {
          auth_config.type = 'bearer_token';
          auth_config.token = apiToken;
        } else if (authType === 'api_key') {
          auth_config.type = 'api_key';
          auth_config.key_name = apiKeyName;
          auth_config.key_value = apiKeyValue;
        }
      } else if (sourceType === 'csv' || sourceType === 'json') {
        config.file_path = filePath;
      }

      await api.post('/data-sources/create', {
        name,
        source_type: sourceType,
        description,
        config,
        auth_config,
      });

      onSuccess();
      onClose();
    } catch (error: any) {
      if (error.response?.status === 409) {
        // Source was created during test phase, treat as success
        onSuccess();
        onClose();
      } else {
        alert(error.response?.data?.detail || 'Failed to create data source');
      }
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={onClose} />

      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Create Data Source</h2>
              <p className="text-sm text-gray-500 mt-0.5">
                Step {step} of 3 - {step === 1 ? 'Select Type' : step === 2 ? 'Configure' : 'Test & Create'}
              </p>
            </div>
            <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Progress Bar */}
          <div className="px-6 py-3 bg-gray-50">
            <div className="flex items-center gap-2">
              {[1, 2, 3].map(s => (
                <div key={s} className={`flex-1 h-2 rounded-full ${s <= step ? 'bg-purple-600' : 'bg-gray-300'}`} />
              ))}
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {/* Step 1: Select Type */}
            {step === 1 && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">Select Data Source Type</h3>
                <div className="grid grid-cols-2 gap-4">
                  {/* JDBC */}
                  <button
                    onClick={() => handleTypeSelect('jdbc')}
                    className="p-6 border-2 border-gray-200 rounded-xl hover:border-purple-600 hover:bg-purple-50 transition-all text-left"
                  >
                    <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mb-3">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                      </svg>
                    </div>
                    <h4 className="font-semibold text-gray-900">Database (JDBC)</h4>
                    <p className="text-sm text-gray-600 mt-1">PostgreSQL, MySQL, Oracle, SQL Server</p>
                  </button>

                  {/* REST API */}
                  <button
                    onClick={() => handleTypeSelect('rest_api')}
                    className="p-6 border-2 border-gray-200 rounded-xl hover:border-purple-600 hover:bg-purple-50 transition-all text-left"
                  >
                    <div className="w-12 h-12 bg-green-100 text-green-600 rounded-lg flex items-center justify-center mb-3">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                      </svg>
                    </div>
                    <h4 className="font-semibold text-gray-900">REST API</h4>
                    <p className="text-sm text-gray-600 mt-1">HTTP/HTTPS API endpoints</p>
                  </button>

                  {/* CSV */}
                  <button
                    onClick={() => handleTypeSelect('csv')}
                    className="p-6 border-2 border-gray-200 rounded-xl hover:border-purple-600 hover:bg-purple-50 transition-all text-left"
                  >
                    <div className="w-12 h-12 bg-purple-100 text-purple-600 rounded-lg flex items-center justify-center mb-3">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <h4 className="font-semibold text-gray-900">CSV File</h4>
                    <p className="text-sm text-gray-600 mt-1">Comma-separated values</p>
                  </button>

                  {/* JSON */}
                  <button
                    onClick={() => handleTypeSelect('json')}
                    className="p-6 border-2 border-gray-200 rounded-xl hover:border-purple-600 hover:bg-purple-50 transition-all text-left"
                  >
                    <div className="w-12 h-12 bg-orange-100 text-orange-600 rounded-lg flex items-center justify-center mb-3">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                      </svg>
                    </div>
                    <h4 className="font-semibold text-gray-900">JSON File</h4>
                    <p className="text-sm text-gray-600 mt-1">JavaScript Object Notation</p>
                  </button>
                </div>
              </div>
            )}

            {/* Step 2: Configure */}
            {step === 2 && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-gray-900">Configure Connection</h3>

                {/* Basic Info */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Name *</label>
                    <input
                      type="text"
                      value={name}
                      onChange={e => setName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-purple-600"
                      placeholder="e.g., Production Database"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                    <input
                      type="text"
                      value={description}
                      onChange={e => setDescription(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-purple-600"
                      placeholder="Optional description"
                    />
                  </div>
                </div>

                {/* JDBC Configuration */}
                {sourceType === 'jdbc' && (
                  <div className="space-y-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <h4 className="font-semibold text-gray-900">Database Configuration</h4>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Database Type *</label>
                      <select
                        value={jdbcDriver}
                        onChange={e => {
                          setJdbcDriver(e.target.value as JDBCDriver);
                          // Set default port
                          if (e.target.value === 'postgresql') setPort('5432');
                          else if (e.target.value === 'mysql') setPort('3306');
                          else if (e.target.value === 'oracle') setPort('1521');
                          else if (e.target.value === 'sqlserver') setPort('1433');
                        }}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-purple-600"
                      >
                        <option value="postgresql">PostgreSQL</option>
                        <option value="mysql">MySQL</option>
                        <option value="oracle">Oracle</option>
                        <option value="sqlserver">SQL Server</option>
                      </select>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      <div className="col-span-2">
                        <label className="block text-sm font-medium text-gray-700 mb-2">Host *</label>
                        <input
                          type="text"
                          value={host}
                          onChange={e => setHost(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                          placeholder="localhost"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Port *</label>
                        <input
                          type="text"
                          value={port}
                          onChange={e => setPort(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Database Name *</label>
                      <input
                        type="text"
                        value={database}
                        onChange={e => setDatabase(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                        placeholder="mydb"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Username *</label>
                        <input
                          type="text"
                          value={username}
                          onChange={e => setUsername(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Password *</label>
                        <input
                          type="password"
                          value={password}
                          onChange={e => setPassword(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* REST API Configuration */}
                {sourceType === 'rest_api' && (
                  <div className="space-y-4 p-4 bg-green-50 rounded-lg border border-green-200">
                    <h4 className="font-semibold text-gray-900">API Configuration</h4>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Base URL *</label>
                      <input
                        type="text"
                        value={baseUrl}
                        onChange={e => setBaseUrl(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                        placeholder="https://api.example.com"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Data Endpoint</label>
                        <input
                          type="text"
                          value={dataEndpoint}
                          onChange={e => setDataEndpoint(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                          placeholder="/data"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Test Endpoint</label>
                        <input
                          type="text"
                          value={testEndpoint}
                          onChange={e => setTestEndpoint(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                          placeholder="/health"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Authentication</label>
                      <select
                        value={authType}
                        onChange={e => setAuthType(e.target.value as AuthType)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      >
                        <option value="none">None</option>
                        <option value="bearer_token">Bearer Token</option>
                        <option value="api_key">API Key</option>
                      </select>
                    </div>

                    {authType === 'bearer_token' && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Bearer Token</label>
                        <input
                          type="password"
                          value={apiToken}
                          onChange={e => setApiToken(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                          placeholder="your-bearer-token"
                        />
                      </div>
                    )}

                    {authType === 'api_key' && (
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Header Name</label>
                          <input
                            type="text"
                            value={apiKeyName}
                            onChange={e => setApiKeyName(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                            placeholder="X-API-Key"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">API Key</label>
                          <input
                            type="password"
                            value={apiKeyValue}
                            onChange={e => setApiKeyValue(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* CSV/JSON Configuration */}
                {(sourceType === 'csv' || sourceType === 'json') && (
                  <div className="space-y-4 p-4 bg-purple-50 rounded-lg border border-purple-200">
                    <h4 className="font-semibold text-gray-900">Upload File</h4>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Select {sourceType.toUpperCase()} file *</label>
                      <input
                        type="file"
                        accept={sourceType === 'csv' ? '.csv' : '.json'}
                        onChange={async (e) => {
                          const file = e.target.files?.[0];
                          if (!file) return;

                          setIsUploading(true);
                          const formData = new FormData();
                          formData.append('file', file);

                          try {
                            const response = await api.post('/data-sources/upload', formData, {
                              headers: { 'Content-Type': 'multipart/form-data' }
                            });
                            setFilePath(response.data.file_path);
                          } catch (error: any) {
                            alert(error.response?.data?.detail || 'Failed to upload file');
                          } finally {
                            setIsUploading(false);
                          }
                        }}
                        disabled={isUploading}
                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100"
                      />
                      {isUploading && <p className="text-sm text-purple-600 mt-2">Uploading...</p>}
                      {filePath && !isUploading && (
                        <p className="text-sm text-green-600 mt-2 font-mono break-all bg-green-100 p-2 rounded">
                          Uploaded: {filePath}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Step 3: Test */}
            {step === 3 && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-gray-900">Test Connection</h3>

                {/* Connection Summary */}
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <h4 className="font-semibold text-gray-900 mb-2">Connection Summary</h4>
                  <dl className="space-y-2 text-sm">
                    <div className="flex">
                      <dt className="w-32 font-medium text-gray-600">Name:</dt>
                      <dd className="text-gray-900">{name}</dd>
                    </div>
                    <div className="flex">
                      <dt className="w-32 font-medium text-gray-600">Type:</dt>
                      <dd className="text-gray-900">{sourceType.replace('_', ' ').toUpperCase()}</dd>
                    </div>
                    {sourceType === 'jdbc' && (
                      <>
                        <div className="flex">
                          <dt className="w-32 font-medium text-gray-600">Database:</dt>
                          <dd className="text-gray-900">{jdbcDriver}</dd>
                        </div>
                        <div className="flex">
                          <dt className="w-32 font-medium text-gray-600">Host:</dt>
                          <dd className="text-gray-900">{host}:{port}</dd>
                        </div>
                      </>
                    )}
                    {sourceType === 'rest_api' && (
                      <div className="flex">
                        <dt className="w-32 font-medium text-gray-600">URL:</dt>
                        <dd className="text-gray-900">{baseUrl}</dd>
                      </div>
                    )}
                  </dl>
                </div>

                {/* Test Button */}
                <button
                  onClick={handleTestConnection}
                  disabled={testing}
                  className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 flex items-center justify-center gap-2"
                >
                  {testing ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Testing Connection...
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      Test Connection
                    </>
                  )}
                </button>

                {/* Test Result */}
                {testResult && (
                  <div className={`p-4 rounded-lg border ${testResult.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                    <div className="flex items-start gap-3">
                      {testResult.success ? (
                        <svg className="w-6 h-6 text-green-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      ) : (
                        <svg className="w-6 h-6 text-red-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      )}
                      <div>
                        <h4 className={`font-semibold ${testResult.success ? 'text-green-900' : 'text-red-900'}`}>
                          {testResult.success ? 'Connection Successful' : 'Connection Failed'}
                        </h4>
                        <p className={`text-sm mt-1 ${testResult.success ? 'text-green-700' : 'text-red-700'}`}>
                          {testResult.message}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
            <button
              onClick={() => {
                if (step > 1) setStep(step - 1);
                else onClose();
              }}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-100"
            >
              {step === 1 ? 'Cancel' : 'Back'}
            </button>

            {step < 3 && (
              <button
                onClick={() => setStep(step + 1)}
                disabled={
                  (step === 2 && !name) ||
                  (step === 2 && sourceType === 'jdbc' && (!host || !database || !username)) ||
                  (step === 2 && sourceType === 'rest_api' && !baseUrl) ||
                  (step === 2 && (sourceType === 'csv' || sourceType === 'json') && !filePath)
                }
                className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400"
              >
                Continue
              </button>
            )}

            {step === 3 && (
              <button
                onClick={handleCreate}
                disabled={creating || !testResult?.success}
                className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 flex items-center gap-2"
              >
                {creating ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Data Source'
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
