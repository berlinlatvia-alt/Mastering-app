/**
 * 5.1 AutoMaster - Main Application
 * Entry point, initializes all modules
 */

// Import modules
import { PipelineUI } from './pipeline.js';
import { TuningUI } from './tuning.js';
import { ExportUI } from './export.js';
import { TrackCutterUI } from './track-cutter.js';
import { API } from './api.js';

class App {
  constructor() {
    this.api = new API(`${window.location.origin}/api`);
    this.pipelineUI = new PipelineUI(this.api);
    this.tuningUI = new TuningUI(this.api);
    this.exportUI = new ExportUI(this.api);
    this.trackCutter = new TrackCutterUI(this.api);

    this.sessionId = null;
    this.filename = null;
    this.isRunning = false;
    this.useManualCutting = false;
  }

  async init() {
    console.log('5.1 AutoMaster initializing...');

    // Initialize UI components
    this.pipelineUI.init();
    this.tuningUI.init();
    this.exportUI.init();
    this.trackCutter.init();

    // Setup event listeners
    this.setupEventListeners();

    // Start hardware monitoring
    this.startHardwareMonitor();

    // Note: Download directory panel shown after pipeline complete
    this.downloadDirConfigShown = false;

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

    // Guide button
    const guideBtn = document.getElementById('guide-btn');
    const helpModal = document.getElementById('help-modal');
    if (guideBtn && helpModal) {
      guideBtn.addEventListener('click', () => helpModal.classList.add('show'));
    }

    // Platform buttons
    const platformGrid = document.getElementById('platform-grid');
    if (platformGrid) {
      platformGrid.addEventListener('click', (e) => {
        const btn = e.target.closest('.plat-btn');
        if (!btn) return;
        platformGrid.querySelectorAll('.plat-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentPlatform = btn.dataset.platform;
        this.syncQuickConfig();
      });
    }

    // Genre chip buttons
    const genreGrid = document.getElementById('genre-chip-grid');
    if (genreGrid) {
      genreGrid.addEventListener('click', (e) => {
        const btn = e.target.closest('.genre-chip');
        if (!btn) return;
        genreGrid.querySelectorAll('.genre-chip').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentGenre = btn.dataset.genre;
        this.syncQuickConfig();
      });
    }

    // Global mode switcher (called from inline onclick on tab buttons)
    window.switchMode = (mode) => {
      const basicEl = document.getElementById('cfg-basic');
      const advEl = document.getElementById('cfg-advanced');
      const tabBasic = document.getElementById('tab-basic');
      const tabPro = document.getElementById('tab-pro');
      if (mode === 'basic') {
        if (basicEl) basicEl.style.display = 'block';
        if (advEl) advEl.style.display = 'none';
        if (tabBasic) tabBasic.classList.add('active');
        if (tabPro) tabPro.classList.remove('active');
      } else {
        if (basicEl) basicEl.style.display = 'none';
        if (advEl) advEl.style.display = 'block';
        if (tabBasic) tabBasic.classList.remove('active');
        if (tabPro) tabPro.classList.add('active');
      }
    };
  }

  syncQuickConfig() {
    const platform = this.currentPlatform || 'spotify';
    const genre = this.currentGenre || 'pop';

    const lufsEl = document.getElementById('cfg-lufs');
    const modelEl = document.getElementById('cfg-model');
    const fmtEl = document.getElementById('cfg-fmt');

    // Platform → format/lufs
    if (platform === 'lossless') {
      if (fmtEl) fmtEl.value = 'flac';
      if (lufsEl) lufsEl.value = '-14.0';
    } else if (platform === 'cinema') {
      if (lufsEl) lufsEl.value = '-23.0';
    } else {
      if (lufsEl) lufsEl.value = '-14.0';
    }

    // Always best model in basic mode
    if (modelEl) modelEl.value = 'htdemucs_6s';

    // Map to studio preset
    let presetName = genre;
    if (platform === 'spotify') {
      presetName = genre === 'hiphop' ? 'spotify_hiphop'
        : genre === 'rock' ? 'spotify_rock'
        : genre === 'pop' ? 'spotify_pop'
        : genre === 'rnb' ? 'spotify_rb'
        : genre === 'afrobeats' ? 'spotify_rb'  // closest Spotify match
        : `spotify_pop`; // fallback
    }
    this.tuningUI.applyPreset(presetName);
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
      const cutterBtn = document.getElementById('cutter-toggle-btn');

      if (fnameEl) fnameEl.textContent = result.filename;
      if (dzEl) dzEl.classList.add('has-file');
      if (runBtn) runBtn.disabled = false;
      if (cutterBtn) cutterBtn.style.display = 'block';  // Show track cutting button

      this.log('ok', `✓ File uploaded: ${result.filename}`);

      // Load audio into track cutter for visualization
      await this.trackCutter.loadAudio(file);

    } catch (error) {
      this.log('err', `Upload failed: ${error.message}`);
    }
  }

  resetForNewRun() {
    // Clear console log
    const clog = document.getElementById('clog');
    if (clog) clog.innerHTML = '';

    // Hide export button, archive button, and export panel
    const exportBtn = document.getElementById('export-btn');
    if (exportBtn) exportBtn.classList.remove('show');
    const archiveBtn = document.getElementById('archive-btn');
    if (archiveBtn) archiveBtn.classList.remove('show');

    // Hide track cutter panel
    const cutterBtn = document.getElementById('cutter-toggle-btn');
    if (cutterBtn) cutterBtn.style.display = 'none';
    if (this.trackCutter) this.trackCutter.hide();

    // Hide download directory config
    const downloadDirConfig = document.getElementById('download-dir-config');
    if (downloadDirConfig) downloadDirConfig.style.display = 'none';
    this.downloadDirConfigShown = false;

    // Reset stage list status indicators in the UI
    const idleEl = document.getElementById('idle');
    const sdEl = document.getElementById('sd');
    if (idleEl) idleEl.style.display = '';
    if (sdEl) {
      // Remove any export/complete views, keep the idle state visible
      const existingExport = sdEl.querySelector('.export-complete');
      if (existingExport) existingExport.remove();
    }

    // Let exportUI know to reset
    if (this.exportUI && typeof this.exportUI.reset === 'function') {
      this.exportUI.reset();
    }
  }

  resetToIdle() {
    this.sessionId = null;
    this.filename = null;
    this.isRunning = false;

    // Reset UI elements
    const fnameEl = document.getElementById('fn');
    const dzEl = document.getElementById('dz');
    const runBtn = document.getElementById('run-btn');
    const abortBtn = document.getElementById('abort-btn');
    const cutterBtn = document.getElementById('cutter-toggle-btn');
    const exportBtn = document.getElementById('export-btn');
    const archiveBtn = document.getElementById('archive-btn');
    const downloadDirConfig = document.getElementById('download-dir-config');
    const sdEl = document.getElementById('sd');

    if (fnameEl) fnameEl.textContent = '';
    if (dzEl) dzEl.classList.remove('has-file');
    if (runBtn) {
      runBtn.disabled = true;
      runBtn.textContent = '▶ RUN FULL PIPELINE';
    }
    if (abortBtn) {
      abortBtn.style.display = 'none';
      abortBtn.disabled = false;
      abortBtn.textContent = '⏹ ABORT PROCESSING';
    }
    if (cutterBtn) cutterBtn.style.display = 'none';
    if (exportBtn) exportBtn.classList.remove('show');
    if (archiveBtn) archiveBtn.classList.remove('show');
    if (downloadDirConfig) downloadDirConfig.style.display = 'none';
    this.downloadDirConfigShown = false;

    // Restore idle state in main panel
    if (sdEl) {
      sdEl.innerHTML = `
        <div class="idle-state" id="idle">
          <div class="idle-icon">⬡</div>
          <div class="idle-title">Load a WAV file to begin</div>
          <div class="idle-sub">
            Fully automatic — track cutting · stem separation<br>
            5.1 upmix · pro mastering · encode<br><br>
            Use <strong style="color:var(--purple)">⚙ Studio Tuning</strong> to dial in the sound.
          </div>
        </div>
      `;
    }

    // Reset components
    if (this.pipelineUI) this.pipelineUI.reset();
    if (this.trackCutter) this.trackCutter.reset();
    if (this.exportUI) this.exportUI.reset();

    this.log('info', 'Window refreshed. Ready for new song.');
  }

  async runPipeline() {
    if (this.isRunning) return;

    // Show where output files will be saved before starting
    try {
      const dirInfo = await this.api.getOutputDir();
      this.log('info', `📁 Output folder: ${dirInfo.path}`);
    } catch (_) {}

    // Auto-reset UI for fresh run
    this.resetForNewRun();

    // Get cut points from track cutter (if user used it)
    const cutPoints = this.trackCutter.getCutPoints();

    this.isRunning = true;
    const runBtn = document.getElementById('run-btn');
    const abortBtn = document.getElementById('abort-btn');
    
    if (runBtn) {
      runBtn.disabled = true;
      runBtn.textContent = '⏳ PROCESSING...';
    }
    
    if (abortBtn) {
      abortBtn.style.display = 'block';
    }

    try {
      // Get configuration
      const config = {
        target_lufs: parseFloat(this.getConfigValue('cfg-lufs', '-14.0')),
        stem_model: this.getConfigValue('cfg-model', 'htdemucs_6s'),
        silence_gate: parseInt(this.getConfigValue('cfg-gate', '-50')),
        output_format: this.getConfigValue('cfg-fmt', 'wav_48k_24bit'),
        studio_preset: this.tuningUI.currentPreset,
        mode: document.getElementById('tab-pro')?.classList.contains('active') ? 'pro' : 'basic',
        cut_points: cutPoints,
        skip_track_cutting: !document.getElementById('cfg-auto-silence')?.checked,
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
      const abortBtn = document.getElementById('abort-btn');
      if (abortBtn) abortBtn.style.display = 'none';
    }
  }

  async runPipelineAfterCutting(cutPoints = []) {
    // Called from track cutter "Apply & Run" button
    this.isRunning = true;
    const runBtn = document.getElementById('run-btn');
    const abortBtn = document.getElementById('abort-btn');
    
    if (runBtn) {
      runBtn.disabled = true;
      runBtn.textContent = '⏳ PROCESSING...';
    }

    if (abortBtn) {
      abortBtn.style.display = 'block';
    }

    try {
      // Get configuration
      const config = {
        target_lufs: parseFloat(this.getConfigValue('cfg-lufs', '-14.0')),
        stem_model: this.getConfigValue('cfg-model', 'htdemucs_6s'),
        silence_gate: parseInt(this.getConfigValue('cfg-gate', '-50')),
        output_format: this.getConfigValue('cfg-fmt', 'wav_48k_24bit'),
        studio_preset: this.tuningUI.currentPreset,
        mode: document.getElementById('tab-pro')?.classList.contains('active') ? 'pro' : 'basic',
        cut_points: cutPoints,
        skip_track_cutting: !document.getElementById('cfg-auto-silence')?.checked,
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
      const abortBtn = document.getElementById('abort-btn');
      if (abortBtn) abortBtn.style.display = 'none';
    }
  }

  async pollProgress() {
    const pollInterval = setInterval(async () => {
      try {
        const status = await this.api.getStatus();

        // Log stage progress and update sidebar + console
        if (status.stages) {
          status.stages.forEach((stage) => {
            if (stage.status === 'running' || stage.status === 'done') {
              // Push any new logs to console output
              const logs = stage.logs || [];
              const key = `_logCount_${stage.stage_num}`;
              const prev = this[key] || 0;
              logs.slice(prev).forEach((l) => this.log(l.t || 'info', l.m));
              this[key] = logs.length;
            }
          });
        }

        this.pipelineUI.updateStages(status.stages);
        this.pipelineUI.updateCurrentStage(status.current_stage);

        if (!status.is_running) {
          clearInterval(pollInterval);
          const failedStage = status.stages && status.stages.find(s => s.status === 'error');
          if (failedStage) {
            const isAborted = failedStage.status === 'aborted' || (failedStage.logs && failedStage.logs.some(l => l.m.includes('aborted')));
            this.log(isAborted ? 'warn' : 'err', `Pipeline ${isAborted ? 'aborted' : 'failed'} at stage ${failedStage.stage_num}: ${failedStage.name}`);
            this.isRunning = false;
            
            const runBtn = document.getElementById('run-btn');
            if (runBtn) { runBtn.disabled = false; runBtn.textContent = '▶ RUN FULL PIPELINE'; }
            
            const abortBtn = document.getElementById('abort-btn');
            if (abortBtn) abortBtn.style.display = 'none';
            
            // Auto-refresh after a short delay on abort
            if (isAborted) {
              setTimeout(() => this.resetToIdle(), 3000);
            }
          } else {
            this.onPipelineComplete(status);
          }
        }
      } catch (error) {
        console.error('Poll error:', error);
        this.log('err', `Poll error: ${error.message}`);
      }
    }, 500);
  }

  onPipelineComplete(status) {
    this.isRunning = false;

    const abortBtn = document.getElementById('abort-btn');
    if (abortBtn) abortBtn.style.display = 'none';

    // Save last results for the export UI
    if (status.exported_files) {
      this.lastExportedFiles = status.exported_files;
    }

    const runBtn = document.getElementById('run-btn');
    const exportBtn = document.getElementById('export-btn');

    if (runBtn) {
      runBtn.disabled = false;
      runBtn.textContent = '↺ RUN AGAIN';
    }

    if (exportBtn) {
      exportBtn.classList.add('show');
    }

    // Show the ZIP archive button
    const archiveBtn = document.getElementById('archive-btn');
    if (archiveBtn) archiveBtn.classList.add('show');

    // Show download directory configuration
    this.showDownloadDirConfig();

    this.log('ok', '🎉 PIPELINE COMPLETE — click ⬇ EXPORT FILES to download');

    // Tell the user exactly where the files were saved on disk
    this.api.getOutputDir().then(result => {
      this.log('info', `📁 Files saved to: ${result.path}`);
    }).catch(() => {});

    this.pipelineUI.showDone();
  }

  showDownloadDirConfig() {
    if (this.downloadDirConfigShown) return;
    
    const configEl = document.getElementById('download-dir-config');
    const pathEl = document.getElementById('download-dir-path');
    
    if (configEl) configEl.style.display = 'block';
    
    // Load current directory
    this.api.getOutputDir().then(result => {
      if (pathEl) pathEl.value = result.path;
      this.downloadDir = result.path;
    }).catch(err => console.error('Failed to load output dir:', err));
    
    this.downloadDirConfigShown = true;
  }

  showExport() {
    this.exportUI.show(this.lastExportedFiles || []);
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

  async loadDownloadDir() {
    try {
      const result = await this.api.getOutputDir();
      const configEl = document.getElementById('download-dir-config');
      const pathEl = document.getElementById('download-dir-path');
      
      if (configEl) configEl.style.display = 'block';
      if (pathEl) pathEl.value = result.path;
      
      this.downloadDir = result.path;
    } catch (error) {
      console.error('Failed to load download directory:', error);
    }
  }

  async browseDownloadDir() {
    // Simple approach: prompt for path
    const path = prompt('Enter the full path for download directory:\n(e.g., C:\\Users\\YourName\\Downloads\\Mastered)', this.downloadDir || '');
    
    if (path) {
      try {
        const result = await this.api.setOutputDir(path);
        
        const pathEl = document.getElementById('download-dir-path');
        if (pathEl) pathEl.value = result.path;
        
        this.downloadDir = result.path;
        this.log('ok', `✓ Download directory: ${result.path}`);
      } catch (error) {
        this.log('err', `Failed to set directory: ${error.message}`);
        alert(`Error: ${error.message}`);
      }
    }
  }

  async resetDownloadDir() {
    try {
      const result = await this.api.setOutputDir(this.api.baseURL.replace('/api', '') + '/output');
      
      const pathEl = document.getElementById('download-dir-path');
      if (pathEl) pathEl.value = result.path;
      
      this.downloadDir = result.path;
      this.log('ok', `✓ Download directory reset to default`);
    } catch (error) {
      this.log('err', `Failed to reset directory: ${error.message}`);
    }
  }

  async abortPipeline() {
    try {
      this.log('warn', '⏹ Aborting processing...');
      const response = await this.api.abortPipeline();
      this.log('info', response.message || 'Abort signal sent.');
      
      const abortBtn = document.getElementById('abort-btn');
      if (abortBtn) {
        abortBtn.disabled = true;
        abortBtn.textContent = '⏹ ABORTING...';
      }

      // The pollProgress will catch the 'aborted' status and call resetToIdle
    } catch (error) {
      this.log('err', `Abort failed: ${error.message}`);
    }
  }

  async downloadArchive() {
    if (!this.sessionId) return;
    
    try {
      this.log('ok', '🗜 Generating and downloading ZIP archive...');
      
      // Create custom filename: "Song Name_Master.zip"
      let baseName = this.filename ? this.filename.replace(/\.[^/.]+$/, "") : `AutoMaster_${this.sessionId.slice(0, 8)}`;
      let zipName = `${baseName}_Master.zip`;
      
      await this.api.downloadArchive(this.sessionId, zipName);
      
      this.log('ok', '✓ Archive downloaded successfully.');
      
      // Refresh window after successful download
      setTimeout(() => {
        this.log('info', 'Refreshing window for next song...');
        this.resetToIdle();
      }, 5000);
    } catch (e) {
      this.log('err', `Archive download failed: ${e.message}`);
    }
  }
}

// Initialize app on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
  window.app.init();
});
