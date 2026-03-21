/**
 * 5.1 AutoMaster - Main Application
 * Entry point, initializes all modules
 */

// Import modules
import { PipelineUI } from './pipeline.js';
import { TuningUI } from './tuning.js';
import { ExportUI } from './export.js';
import { API } from './api.js';

class App {
  constructor() {
    this.api = new API('http://127.0.0.1:8000/api');
    this.pipelineUI = new PipelineUI(this.api);
    this.tuningUI = new TuningUI(this.api);
    this.exportUI = new ExportUI(this.api);
    
    this.sessionId = null;
    this.filename = null;
    this.isRunning = false;
  }

  async init() {
    console.log('5.1 AutoMaster initializing...');
    
    // Initialize UI components
    this.pipelineUI.init();
    this.tuningUI.init();
    this.exportUI.init();
    
    // Setup event listeners
    this.setupEventListeners();
    
    // Start hardware monitoring
    this.startHardwareMonitor();
    
    console.log('5.1 AutoMaster ready');
  }

  setupEventListeners() {
    // File upload
    const fileInput = document.getElementById('fi');
    const dropZone = document.getElementById('dz');
    
    if (fileInput) {
      fileInput.addEventListener('change', (e) => this.handleFileUpload(e));
    }
    
    if (dropZone) {
      dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--amber-dim)';
        dropZone.style.background = 'var(--amber-glow)';
      });
      
      dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '';
        dropZone.style.background = '';
      });
      
      dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = '';
        dropZone.style.background = '';
        const files = e.dataTransfer.files;
        if (files.length > 0) {
          this.processFile(files[0]);
        }
      });
    }
    
    // Run button
    const runBtn = document.getElementById('run-btn');
    if (runBtn) {
      runBtn.addEventListener('click', () => this.runPipeline());
    }
    
    // Export button
    const exportBtn = document.getElementById('export-btn');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => this.showExport());
    }
    
    // Tuning button
    const tuneBtn = document.getElementById('tune-btn');
    if (tuneBtn) {
      tuneBtn.addEventListener('click', () => this.tuningUI.toggle());
    }
  }

  async handleFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
      await this.processFile(file);
    }
  }

  async processFile(file) {
    try {
      this.log('info', `Uploading: ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB)`);
      
      const result = await this.api.uploadFile(file);
      
      this.sessionId = result.session_id;
      this.filename = result.filename;
      
      // Update UI
      const fnameEl = document.getElementById('fn');
      const dzEl = document.getElementById('dz');
      const runBtn = document.getElementById('run-btn');
      
      if (fnameEl) fnameEl.textContent = result.filename;
      if (dzEl) dzEl.classList.add('has-file');
      if (runBtn) runBtn.disabled = false;
      
      this.log('ok', `✓ File uploaded: ${result.filename}`);
      
    } catch (error) {
      this.log('err', `Upload failed: ${error.message}`);
    }
  }

  async runPipeline() {
    if (this.isRunning) return;
    
    this.isRunning = true;
    const runBtn = document.getElementById('run-btn');
    if (runBtn) {
      runBtn.disabled = true;
      runBtn.textContent = '⏳ PROCESSING...';
    }
    
    try {
      // Get configuration
      const config = {
        target_lufs: parseFloat(this.getConfigValue('cfg-lufs', '-23.0')),
        stem_model: this.getConfigValue('cfg-model', 'htdemucs_6s'),
        silence_gate: parseInt(this.getConfigValue('cfg-gate', '-50')),
        output_format: this.getConfigValue('cfg-fmt', 'wav_48k_24bit'),
        studio_preset: this.tuningUI.currentPreset,
      };
      
      // Configure pipeline
      await this.api.configure(config);
      
      // Start pipeline
      await this.api.runPipeline();
      
      // Poll for progress
      await this.pollProgress();
      
    } catch (error) {
      this.log('err', `Pipeline failed: ${error.message}`);
      this.isRunning = false;
      if (runBtn) {
        runBtn.disabled = false;
        runBtn.textContent = '▶ RUN FULL PIPELINE';
      }
    }
  }

  async pollProgress() {
    const pollInterval = setInterval(async () => {
      try {
        const status = await this.api.getStatus();
        
        this.pipelineUI.updateStages(status.stages);
        this.pipelineUI.updateCurrentStage(status.current_stage);
        
        if (!status.is_running) {
          clearInterval(pollInterval);
          this.onPipelineComplete(status);
        }
      } catch (error) {
        console.error('Poll error:', error);
      }
    }, 500);
  }

  onPipelineComplete(status) {
    this.isRunning = false;
    
    const runBtn = document.getElementById('run-btn');
    const exportBtn = document.getElementById('export-btn');
    
    if (runBtn) {
      runBtn.disabled = false;
      runBtn.textContent = '↺ RUN AGAIN';
    }
    
    if (exportBtn) {
      exportBtn.classList.add('show');
    }
    
    this.log('ok', '🎉 PIPELINE COMPLETE — click ⬇ EXPORT FILES');
    this.pipelineUI.showDone();
  }

  showExport() {
    this.exportUI.show();
  }

  getConfigValue(id, defaultValue) {
    const el = document.getElementById(id);
    return el ? el.value : defaultValue;
  }

  log(type, message) {
    const el = document.getElementById('clog');
    if (!el) return;
    
    const now = new Date();
    const ts = now.toTimeString().split(' ')[0];
    
    const line = document.createElement('div');
    line.className = `ll ${type}`;
    line.innerHTML = `<span class="lt">${ts} </span>${message}`;
    
    el.appendChild(line);
    el.scrollTop = el.scrollHeight;
  }

  startHardwareMonitor() {
    setInterval(async () => {
      try {
        const hw = await this.api.getHardware();
        this.updateHardwareDisplay(hw);
      } catch (error) {
        // Ignore errors
      }
    }, 2000);
  }

  updateHardwareDisplay(hw) {
    const rb = document.getElementById('rb');
    const vb = document.getElementById('vb');
    const rv = document.getElementById('rv');
    const vv = document.getElementById('vv');
    
    if (rb) rb.style.width = `${hw.ram_percent}%`;
    if (vb) vb.style.width = `${hw.vram_percent}%`;
    if (rv) rv.textContent = `${hw.ram_used_gb} GB`;
    if (vv) vv.textContent = hw.vram_used_gb > 0 ? `${hw.vram_used_gb} GB` : '—';
  }
}

// Initialize app on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
  window.app.init();
});
