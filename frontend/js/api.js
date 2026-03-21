/**
 * API Client
 * Handles all HTTP requests to the backend
 */

export class API {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        const detail = error.detail;
        const message = Array.isArray(detail)
          ? detail.map(e => e.msg || JSON.stringify(e)).join(', ')
          : (detail || `HTTP ${response.status}`);
        throw new Error(message);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  // Status & Hardware
  async getStatus() {
    return this.request('/status');
  }

  async getHardware() {
    return this.request('/hardware');
  }

  async getPresets() {
    return this.request('/presets');
  }

  // File Upload
  async uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const url = `${this.baseURL}/upload`;
    
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      const detail = error.detail;
      const message = Array.isArray(detail)
        ? detail.map(e => e.msg || JSON.stringify(e)).join(', ')
        : (detail || `HTTP ${response.status}`);
      throw new Error(message);
    }

    return await response.json();
  }

  // Configuration
  async configure(config) {
    return this.request('/configure', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  async configureStudio(config) {
    return this.request('/studio-config', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  async applyPreset(presetName) {
    return this.request(`/studio-preset/${presetName}`, {
      method: 'POST',
    });
  }

  // Pipeline Control
  async runPipeline() {
    return this.request('/run', {
      method: 'POST',
    });
  }

  // Export
  async getExportFiles(sessionId) {
    return this.request(`/export/${sessionId}`);
  }

  async downloadFile(sessionId, filename) {
    const url = `${this.baseURL}/download/${sessionId}/${filename}`;
    
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error('Download failed');
    }

    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(downloadUrl);
  }
}
