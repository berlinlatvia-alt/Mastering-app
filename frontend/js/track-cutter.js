/**
 * Manual Track Cutting Editor
 * Allows users to manually set cut points in the audio before pipeline runs
 */

export class TrackCutterUI {
  constructor(api) {
    this.api = api;
    this.audioBuffer = null;
    this.audioContext = null;
    this.waveformCanvas = null;
    this.waveformCtx = null;
    this.cutPoints = [];
    this.isPlaying = false;
    this.currentTime = 0;
    this.sourceNode = null;
    this.startTime = 0;
    this.draggingPoint = null;
    this.isDragging = false;
  }

  init() {
    this.waveformCanvas = document.getElementById('waveform-canvas');
    this.waveformCtx = this.waveformCanvas?.getContext('2d');
    
    if (this.waveformCanvas) {
      this.setupCanvasEvents();
      this.resizeCanvas();
      window.addEventListener('resize', () => this.resizeCanvas());
    }
  }

  resizeCanvas() {
    if (!this.waveformCanvas) return;
    const rect = this.waveformCanvas.parentElement.getBoundingClientRect();
    this.waveformCanvas.width = rect.width * window.devicePixelRatio;
    this.waveformCanvas.height = rect.height * window.devicePixelRatio;
    this.waveformCanvas.style.width = `${rect.width}px`;
    this.waveformCanvas.style.height = `${rect.height}px`;
    
    if (this.waveformCtx) {
      this.waveformCtx.scale(window.devicePixelRatio, window.devicePixelRatio);
    }
    
    if (this.audioBuffer) {
      this.drawWaveform();
    }
  }

  setupCanvasEvents() {
    const canvas = this.waveformCanvas;
    if (!canvas) return;

    const getMouseX = (e) => {
      const rect = canvas.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      return (clientX - rect.left) / rect.width;
    };

    const addCutPoint = (e) => {
      e.preventDefault();
      const x = getMouseX(e);
      const time = x * this.audioBuffer.duration;
      
      // Check if clicking near existing point
      const nearPoint = this.cutPoints.findIndex(p => Math.abs(p - time) < 0.5);
      
      if (nearPoint >= 0) {
        // Remove existing point
        this.cutPoints.splice(nearPoint, 1);
      } else {
        // Add new point
        this.cutPoints.push(time);
        this.cutPoints.sort((a, b) => a - b);
      }
      
      this.drawWaveform();
      this.updateCutList();
    };

    const startDrag = (e) => {
      e.preventDefault();
      const x = getMouseX(e);
      const time = x * this.audioBuffer.duration;
      
      // Check if near existing point
      const nearPoint = this.cutPoints.findIndex(p => Math.abs(p - time) < 1);
      
      if (nearPoint >= 0) {
        this.draggingPoint = nearPoint;
        this.isDragging = true;
        canvas.style.cursor = 'grabbing';
      }
    };

    const drag = (e) => {
      if (!this.isDragging || this.draggingPoint === null) return;
      e.preventDefault();
      
      const x = getMouseX(e);
      let time = x * this.audioBuffer.duration;
      
      // Clamp to bounds
      time = Math.max(0, Math.min(this.audioBuffer.duration, time));
      
      // Prevent overlap with adjacent points
      const prev = this.draggingPoint > 0 ? this.cutPoints[this.draggingPoint - 1] : 0;
      const next = this.draggingPoint < this.cutPoints.length - 1 ? this.cutPoints[this.draggingPoint + 1] : this.audioBuffer.duration;
      time = Math.max(prev + 0.5, Math.min(next - 0.5, time));
      
      this.cutPoints[this.draggingPoint] = time;
      this.drawWaveform();
      this.updateCutList();
    };

    const endDrag = () => {
      this.isDragging = false;
      this.draggingPoint = null;
      if (this.waveformCanvas) {
        this.waveformCanvas.style.cursor = 'crosshair';
      }
    };

    // Mouse events
    canvas.addEventListener('click', addCutPoint);
    canvas.addEventListener('mousedown', startDrag);
    canvas.addEventListener('mousemove', drag);
    canvas.addEventListener('mouseup', endDrag);
    canvas.addEventListener('mouseleave', endDrag);

    // Touch events
    canvas.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        const touch = e.touches[0];
        const x = (touch.clientX - canvas.getBoundingClientRect().left) / canvas.getBoundingClientRect().width;
        const time = x * this.audioBuffer.duration;
        const nearPoint = this.cutPoints.findIndex(p => Math.abs(p - time) < 1);
        
        if (nearPoint >= 0) {
          startDrag(e);
        } else {
          addCutPoint(e);
        }
      }
    });
    canvas.addEventListener('touchmove', drag);
    canvas.addEventListener('touchend', endDrag);
  }

  async loadAudio(file) {
    try {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const arrayBuffer = await file.arrayBuffer();
      this.audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
      this.cutPoints = [];
      this.currentTime = 0;
      this.drawWaveform();
      this.updateCutList();
      return true;
    } catch (error) {
      console.error('Failed to load audio:', error);
      return false;
    }
  }

  drawWaveform() {
    if (!this.audioBuffer || !this.waveformCtx) return;

    const width = this.waveformCanvas.width / window.devicePixelRatio;
    const height = this.waveformCanvas.height / window.devicePixelRatio;
    const ctx = this.waveformCtx;

    // Clear
    ctx.fillStyle = '#1a1d26';
    ctx.fillRect(0, 0, width, height);

    // Draw waveform
    const data = this.audioBuffer.getChannelData(0);
    const step = Math.ceil(data.length / width);
    const amp = height / 2;

    ctx.beginPath();
    ctx.strokeStyle = '#3a8cfd';
    ctx.lineWidth = 1;

    for (let i = 0; i < width; i++) {
      let min = 1.0;
      let max = -1.0;
      
      for (let j = 0; j < step; j++) {
        const datum = data[(i * step) + j];
        if (datum < min) min = datum;
        if (datum > max) max = datum;
      }
      
      ctx.moveTo(i, (1 + min) * amp);
      ctx.lineTo(i, (1 + max) * amp);
    }
    
    ctx.stroke();

    // Draw playhead
    if (this.isPlaying || this.currentTime > 0) {
      const playheadX = (this.currentTime / this.audioBuffer.duration) * width;
      ctx.beginPath();
      ctx.strokeStyle = '#e8a030';
      ctx.lineWidth = 2;
      ctx.moveTo(playheadX, 0);
      ctx.lineTo(playheadX, height);
      ctx.stroke();
    }

    // Draw cut points
    this.cutPoints.forEach((point, idx) => {
      const x = (point / this.audioBuffer.duration) * width;
      
      // Line
      ctx.beginPath();
      ctx.strokeStyle = '#ff4757';
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 3]);
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
      ctx.setLineDash([]);

      // Handle
      ctx.beginPath();
      ctx.fillStyle = '#ff4757';
      ctx.arc(x, 15, 6, 0, Math.PI * 2);
      ctx.fill();

      // Time label
      ctx.fillStyle = '#ff4757';
      ctx.font = '10px IBM Plex Mono';
      ctx.textAlign = 'center';
      ctx.fillText(this.formatTime(point), x, height - 5);
    });

    // Draw segment labels
    this.drawSegmentLabels(width, height);
  }

  drawSegmentLabels(width, height) {
    const points = [0, ...this.cutPoints, this.audioBuffer.duration];
    const ctx = this.waveformCtx;

    for (let i = 0; i < points.length - 1; i++) {
      const startX = (points[i] / this.audioBuffer.duration) * width;
      const endX = (points[i + 1] / this.audioBuffer.duration) * width;
      const centerX = (startX + endX) / 2;
      const duration = points[i + 1] - points[i];

      ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
      ctx.font = '11px IBM Plex Mono';
      ctx.textAlign = 'center';
      ctx.fillText(`Track ${i + 1} · ${this.formatTime(duration)}`, centerX, 35);
    }
  }

  updateCutList() {
    const listEl = document.getElementById('cut-points-list');
    if (!listEl) return;

    const points = [0, ...this.cutPoints, this.audioBuffer.duration];
    let html = '<div style="font-size:11px;color:var(--text3);margin-bottom:8px">Click on waveform to add/remove cut points. Drag to adjust.</div>';
    html += '<div class="cut-list">';

    for (let i = 0; i < points.length - 1; i++) {
      const start = points[i];
      const end = points[i + 1];
      const duration = end - start;
      html += `
        <div class="cut-item">
          <span class="cut-num">Track ${i + 1}</span>
          <span class="cut-time">${this.formatTime(start)} → ${this.formatTime(end)}</span>
          <span class="cut-dur">${this.formatTime(duration)}</span>
        </div>
      `;
    }

    html += '</div>';
    html += `<div style="margin-top:10px;font-size:11px;color:var(--text3)">Total tracks: ${points.length - 1}</div>`;

    listEl.innerHTML = html;
  }

  formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 100);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
  }

  play() {
    if (!this.audioBuffer || this.isPlaying) return;

    this.sourceNode = this.audioContext.createBufferSource();
    this.sourceNode.buffer = this.audioBuffer;
    this.sourceNode.connect(this.audioContext.destination);
    this.sourceNode.start(0, this.currentTime);
    this.startTime = this.audioContext.currentTime - this.currentTime;
    this.isPlaying = true;

    this.sourceNode.onended = () => {
      if (this.isPlaying) {
        this.stop();
      }
    };

    this.updatePlayButton();
    this.animatePlayhead();
  }

  stop() {
    if (this.sourceNode) {
      try {
        this.sourceNode.stop();
      } catch (e) {}
      this.sourceNode = null;
    }
    this.isPlaying = false;
    this.updatePlayButton();
  }

  togglePlay() {
    if (this.isPlaying) {
      this.stop();
    } else {
      this.play();
    }
  }

  updatePlayButton() {
    const btn = document.getElementById('waveform-play-btn');
    if (btn) {
      btn.textContent = this.isPlaying ? '⏸ Pause' : '▶ Play';
    }
  }

  animatePlayhead() {
    if (!this.isPlaying) return;

    this.currentTime = this.audioContext.currentTime - this.startTime;
    
    if (this.currentTime >= this.audioBuffer.duration) {
      this.currentTime = 0;
      this.stop();
    }

    this.drawWaveform();
    requestAnimationFrame(() => this.animatePlayhead());
  }

  skipTo(time) {
    this.currentTime = time;
    if (this.isPlaying) {
      this.stop();
      this.play();
    } else {
      this.drawWaveform();
    }
  }

  getCutPoints() {
    return this.cutPoints;
  }

  clearCutPoints() {
    this.cutPoints = [];
    this.drawWaveform();
    this.updateCutList();
  }

  autoDetectSilence(gate = -50, minSilence = 0.8) {
    if (!this.audioBuffer) return;

    const data = this.audioBuffer.getChannelData(0);
    const sr = this.audioBuffer.sampleRate;
    const duration = this.audioBuffer.duration;
    
    // Compute RMS envelope
    const windowMs = 10;
    const windowSize = Math.floor(sr * windowMs / 1000);
    const rms = [];
    
    for (let i = 0; i < data.length; i += windowSize) {
      let sum = 0;
      for (let j = 0; j < windowSize && i + j < data.length; j++) {
        sum += data[i + j] ** 2;
      }
      rms.push(Math.sqrt(sum / windowSize));
    }

    // Find silent regions
    const gateLinear = Math.pow(10, gate / 20);
    const minSilenceSamples = Math.floor(sr * minSilence);
    
    const cutPoints = [];
    let inSilence = false;
    let silenceStart = 0;

    for (let i = 0; i < rms.length; i++) {
      if (rms[i] < gateLinear && !inSilence) {
        inSilence = true;
        silenceStart = i;
      } else if (rms[i] >= gateLinear && inSilence) {
        inSilence = false;
        const silenceDuration = (i - silenceStart) * windowMs;
        if (silenceDuration >= minSilence * 1000) {
          const cutPoint = ((silenceStart + i) / 2) * windowMs / 1000;
          if (cutPoint > 1 && cutPoint < duration - 1) {
            cutPoints.push(cutPoint);
          }
        }
      }
    }

    this.cutPoints = cutPoints.slice(0, 10);
    this.drawWaveform();
    this.updateCutList();
  }

  show() {
    const panel = document.getElementById('cutter-panel');
    const container = document.getElementById('cutter-container');
    if (panel) panel.style.display = 'block';
    if (container) container.style.display = 'block';
    this.resizeCanvas();
  }

  hide() {
    const panel = document.getElementById('cutter-panel');
    const container = document.getElementById('cutter-container');
    if (panel) panel.style.display = 'none';
    if (container) container.style.display = 'none';
  }

  toggle() {
    const panel = document.getElementById('cutter-panel');
    const isVisible = panel && panel.style.display !== 'none';
    if (isVisible) {
      this.hide();
    } else {
      this.show();
    }
    return !isVisible;
  }

  async saveAndContinue() {
    // Save cut points to session
    const cutPoints = this.getCutPoints();
    
    // Send to backend
    try {
      await this.api.saveCutPoints(cutPoints);
    } catch (error) {
      console.error('Failed to save cut points:', error);
    }

    // Hide the panel
    this.hide();
    
    // Trigger pipeline run with cut points
    if (window.app && window.app.runPipelineAfterCutting) {
      window.app.runPipelineAfterCutting(cutPoints);
    }
  }
}
