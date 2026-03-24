/**
 * Export UI Controller
 * Manages export file selection and download
 */

export class ExportUI {
  constructor(api) {
    this.api = api;
    this.selectedFiles = new Set();
    this.exportGroups = this.initializeExportGroups();
  }

  initializeExportGroups() {
    this.basicGroup = {
      id: 'basic_files',
      icon: '🎵',
      label: 'Your Processed Files',
      color: 'var(--teal)',
      colorDim: 'var(--teal-dim)',
      why: 'Here are the 3 essential mix formats requested.',
      files: [
        { n: 'spotify_master.wav', s: '~89 MB', f: 'WAV 24-bit', lossless: true, c: true, note: 'DistroKid / Spotify' },
        { n: 'youtube_ready.mp3', s: '~9 MB', f: 'MP3 320k', lossless: false, c: true, note: 'YouTube / Quick Sharing' },
        { n: 'surround_5.1_master.flac', s: '~118 MB', f: 'FLAC 5.1', lossless: true, c: true, note: 'Pro Surround Master' }
      ]
    };

    return [
      {
        id: 'archive',
        icon: '🗄',
        label: 'Archival / Mastering Handoff',
        color: 'var(--teal)',
        colorDim: 'var(--teal-dim)',
        why: 'Lossless masters for studio handoff, label delivery, or future re-encode. Keep these forever.',
        files: [
          { n: 'track_01_5.1.wav', s: '38.2 MB', f: 'WAV 24-bit', lossless: true, c: true },
          { n: 'track_02_5.1.wav', s: '41.7 MB', f: 'WAV 24-bit', lossless: true, c: true },
          { n: 'track_03_5.1.wav', s: '44.9 MB', f: 'WAV 24-bit', lossless: true, c: true },
          { n: 'track_04_5.1.wav', s: '35.1 MB', f: 'WAV 24-bit', lossless: true, c: true },
          { n: 'track_05_5.1.wav', s: '29.8 MB', f: 'WAV 24-bit', lossless: true, c: true },
          { n: 'album_5.1_master.flac', s: '118 MB', f: 'FLAC 6ch', lossless: true, c: true, note: 'Lossless · ~52% of WAV' },
          { n: 'qc_report.pdf', s: '0.2 MB', f: 'PDF', c: true },
        ],
      },
      {
        id: 'car',
        icon: '🚗',
        label: 'Car Audio (Head Unit Decoding)',
        color: 'var(--amber)',
        colorDim: 'var(--amber-dim)',
        why: 'Almost every car head unit from 2010+ decodes Dolby AC-3. DTS is for premium installs (B&O, Mark Levinson, Bose).',
        files: [
          { n: 'album_car_dolby.ac3', s: '18.1 MB', f: 'AC-3 640k', c: true, note: 'Universal — all head units' },
          { n: 'album_car_dts.dts', s: '42.3 MB', f: 'DTS 1509k', c: false, note: 'Premium systems only' },
          { n: 'album_car_truehd.thd', s: '156 MB', f: 'TrueHD', c: false, note: 'Blu-ray / high-end only' },
        ],
      },
      {
        id: 'headphones',
        icon: '🎧',
        label: 'Pro Headphones & Multi-Driver IEMs',
        color: 'var(--purple)',
        colorDim: 'var(--purple-dim)',
        why: 'Binaural renders process the 5.1 mix through HRTF filters — giving AirPods Pro or DUNU tribrid IEM a genuine spatial field.',
        files: [
          { n: 'album_binaural_hrtf.flac', s: '62 MB', f: 'FLAC Binaural', c: true, note: 'HRTF from 5.1 · best on wired IEMs' },
          { n: 'album_binaural_spatial.aac', s: '14 MB', f: 'AAC 256k', c: true, note: 'Apple Spatial Audio compatible' },
          { n: 'album_binaural_headtracking.wav', s: '89 MB', f: 'WAV Binaural', c: false, note: 'Max quality · wired reference' },
        ],
      },
      {
        id: 'fans',
        icon: '🎵',
        label: 'Fan Downloads (Bandcamp / Direct Store)',
        color: '#5b9cf6',
        colorDim: 'var(--blue-dim)',
        why: 'FLAC is what audiophile fans expect on Bandcamp. The stereo FLAC covers non-surround listeners. MP3 is the universal fallback.',
        files: [
          { n: 'album_5.1_fans.flac', s: '118 MB', f: 'FLAC 6ch', lossless: true, c: true, note: 'Surround lossless · Bandcamp premium' },
          { n: 'album_stereo_downmix.flac', s: '42 MB', f: 'FLAC Stereo', lossless: true, c: true, note: 'For non-surround listeners' },
          { n: 'album_stereo_320.mp3', s: '9.4 MB', f: 'MP3 320k', c: false, note: 'Max compatibility fallback' },
        ],
      },
      {
        id: 'streaming',
        icon: '📡',
        label: 'Streaming / Distribution',
        color: 'var(--red)',
        colorDim: 'var(--red-dim)',
        why: '⚠ No major DSP (Spotify, Apple Music, Tidal) distributes discrete 5.1. These are stereo deliverables — the downmix for platforms.',
        files: [
          { n: 'album_distro_stereo.wav', s: '89 MB', f: 'WAV Stereo', c: true, note: 'DistroKid / TuneCore master' },
          { n: 'album_distro_aac.m4a', s: '12 MB', f: 'AAC 256k', c: false, note: 'iTunes / Apple Music delivery' },
          { n: 'ATMOS_NOTE.txt', s: '<1 KB', f: 'README', c: true, note: 'Explains Atmos vs 5.1 for label' },
        ],
      },
    ];
  }

  init() {
    // Nothing specific needed
  }

  reset() {
    // Clear the export panel back to idle state
    const sd = document.getElementById('sd');
    const idle = document.getElementById('idle');
    if (sd) {
      sd.innerHTML = '';
      if (idle) idle.style.display = '';
    }
    this.selectedFiles = new Set();
  }

  show(exportedFiles = []) {
    const sd = document.getElementById('sd');
    if (!sd) return;

    // Check if we are in basic mode
    const isBasic = !document.getElementById('tab-pro')?.classList.contains('active');

    let fileIdx = 0;
    let contentHtml = '';
    
    if (isBasic) {
      // BASIC MODE: Create a dynamic group based on actual exported files
      // If exportedFiles is empty for some reason, fallback to basicGroup
      let filesToRender = this.basicGroup.files;
      
      if (exportedFiles && exportedFiles.length > 0) {
        filesToRender = exportedFiles.map((f, i) => {
          let isLossless = f.format.includes('FLAC') || f.format.includes('WAV');
          return {
            n: f.filename || `output_${i}`,
            s: f.size_mb ? `${f.size_mb} MB` : '~ MB',
            f: f.format || 'Audio',
            lossless: isLossless,
            c: true,
            note: f.label || ''
          };
        });
      }
      
      const dynamicGroup = {
        id: 'basic_files',
        icon: '🎵',
        label: 'Your Processed Files',
        color: 'var(--teal)',
        colorDim: 'var(--teal-dim)',
        why: 'Here are the essential mix formats requested.',
        files: filesToRender
      };
      
      // Save this dynamic group so checkbox selection extraction works
      this.basicGroup = dynamicGroup;
      
      contentHtml = this.renderGroup(this.basicGroup, 0, 0);
    } else {
      // PRO MODE: Show all 5 groups + quick filters
      contentHtml = `
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px">
          <button onclick="window.app.exportUI.quickSelect('all')" style="padding:4px 10px;background:var(--bg3);border:1px solid var(--border2);border-radius:4px;font-family:var(--mono);font-size:10px;color:var(--text2);cursor:pointer">All Recommended</button>
          <button onclick="window.app.exportUI.quickSelect('car')" style="padding:4px 10px;background:var(--bg3);border:1px solid var(--border2);border-radius:4px;font-family:var(--mono);font-size:10px;color:var(--text2);cursor:pointer">Car Only</button>
          <button onclick="window.app.exportUI.quickSelect('fans')" style="padding:4px 10px;background:var(--bg3);border:1px solid var(--border2);border-radius:4px;font-family:var(--mono);font-size:10px;color:var(--text2);cursor:pointer">Fan Store Only</button>
          <button onclick="window.app.exportUI.quickSelect('headphones')" style="padding:4px 10px;background:var(--bg3);border:1px solid var(--border2);border-radius:4px;font-family:var(--mono);font-size:10px;color:var(--text2);cursor:pointer">Headphones Only</button>
          <button onclick="window.app.exportUI.quickSelect('archive')" style="padding:4px 10px;background:var(--bg3);border:1px solid var(--border2);border-radius:4px;font-family:var(--mono);font-size:10px;color:var(--text2);cursor:pointer">Archive Only</button>
        </div>
        ${this.exportGroups.map((group, gi) => {
          const html = this.renderGroup(group, gi, fileIdx);
          fileIdx += group.files.length;
          return html;
        }).join('')}
      `;
    }

    sd.innerHTML = `
      <div class="done-banner">
        <div class="done-icon">✓</div>
        <div class="done-title">Pipeline Complete — Export Ready</div>
        <div class="done-sub">${isBasic ? 'Your files are ready to download.' : 'Files are grouped by playback destination. Check what you need, then export.'}</div>
      </div>
      
      ${contentHtml}
      
      <div class="scard">
        <button class="export-action" id="exp-act-btn" onclick="window.app.exportUI.doExport()">⬇ Export Selected Files</button>
        <div class="export-progress" id="exp-prog" style="display:none">
          <div class="export-progress-fill" id="exp-prog-fill"></div>
        </div>
        <div class="enote" style="margin-top:7px">Files will be downloaded natively via your browser.</div>
      </div>
    `;
  }

  renderGroup(group, groupIndex, startIdx) {
    const filesHtml = group.files
      .map((file, fi) => {
        const idx = startIdx + fi;
        const losslessBadge = file.lossless
          ? `<span style="font-size:8px;padding:1px 5px;border-radius:2px;background:rgba(45,212,160,.12);color:var(--teal);margin-right:3px">LOSSLESS</span>`
          : '';
        const noteTxt = file.note
          ? `<span style="font-size:9px;color:var(--text3);margin-left:4px">· ${file.note}</span>`
          : '';

        return `
          <div class="efrow" style="background:var(--bg3);border-left:2px solid ${file.c ? group.color : 'var(--border)'}">
            <input type="checkbox" id="ef${idx}" ${file.c ? 'checked' : ''} style="accent-color:${group.color};cursor:pointer">
            <label class="efname" for="ef${idx}" style="cursor:pointer">${file.n}</label>
            ${losslessBadge}
            <span class="efsize">${file.s}</span>
            <span class="effmt" style="background:${group.colorDim};color:${group.color}">${file.f}</span>
            ${noteTxt}
          </div>
        `;
      })
      .join('');

    return `
      <div class="scard" style="margin-bottom:10px">
        <div style="display:flex;align-items:center;gap:9px;margin-bottom:8px">
          <span style="font-size:16px">${group.icon}</span>
          <div>
            <div style="font-size:12px;font-weight:500;color:${group.color}">${group.label}</div>
            <div style="font-size:10px;color:var(--text3);margin-top:2px;line-height:1.5">${group.why}</div>
          </div>
        </div>
        <div class="efiles" style="margin:0">${filesHtml}</div>
      </div>
    `;
  }

  quickSelect(option) {
    // Reset all
    document.querySelectorAll('.efrow input[type=checkbox]').forEach((cb) => {
      cb.checked = false;
    });

    const groupIndex = {
      all: -1,
      archive: 0,
      car: 1,
      headphones: 2,
      fans: 3,
      streaming: 4,
    }[option];

    if (option === 'all') {
      // Select all except streaming
      [0, 1, 2, 3].forEach((idx) => this.selectGroup(idx));
    } else {
      this.selectGroup(groupIndex);
    }
  }

  selectGroup(groupIndex) {
    let fileIdx = 0;
    this.exportGroups.forEach((group, gi) => {
      group.files.forEach((_, fi) => {
        if (gi === groupIndex) {
          const el = document.getElementById(`ef${fileIdx}`);
          if (el) el.checked = true;
        }
        fileIdx++;
      });
    });
  }

  async doExport() {
    const btn = document.getElementById('exp-act-btn');
    const prog = document.getElementById('exp-prog');
    const fill = document.getElementById('exp-prog-fill');

    if (!btn || !prog || !fill) return;

    // Get selected files
    const selected = [];
    const isBasic = !document.getElementById('tab-pro')?.classList.contains('active');
    
    if (isBasic) {
      // In basic mode, check the basic group
      for (let i = 0; i < this.basicGroup.files.length; i++) {
        const el = document.getElementById(`ef${i}`);
        if (el && el.checked) {
          selected.push(this.basicGroup.files[i]);
        }
      }
    } else {
      // In pro mode, check all groups
      let fileIdx = 0;
      this.exportGroups.forEach((group) => {
        group.files.forEach((file) => {
          const el = document.getElementById(`ef${fileIdx}`);
          if (el && el.checked) {
            selected.push(file);
          }
          fileIdx++;
        });
      });
    }

    if (selected.length === 0) {
      alert('Please select at least one file to export');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Exporting...';
    prog.style.display = 'block';

    const baseUrl = window.app.api.baseURL || `${window.location.origin}/api`;
    const sessionId = window.app.sessionId;

    if (!sessionId) {
      alert('Session expired. Please run the pipeline again.');
      btn.disabled = false;
      btn.textContent = '⬇ Export Selected Files';
      prog.style.display = 'none';
      return;
    }

    // Trigger sequential downloads using the API client's blob method for better compatibility
    for (let i = 0; i < selected.length; i++) {
      const file = selected[i];
      const progress = ((i + 1) / selected.length) * 100;
      fill.style.width = `${progress}%`;

      console.log(`Downloading: ${file.n}`);

      // Use the API client's downloadFile method which handles blobs properly
      try {
        await window.app.api.downloadFile(sessionId, file.n);
      } catch (error) {
        console.error(`Download failed for ${file.n}:`, error);
        // Fallback: try direct anchor download without URL encoding
        const downloadUrl = `${baseUrl}/download/${sessionId}/${encodeURIComponent(file.n)}`;
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = file.n;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }

      // Stagger downloads heavily so the browser doesn't block multiple files
      await new Promise((resolve) => setTimeout(resolve, 2500));
    }

    btn.textContent = '✓ Export Complete';
    fill.style.width = '100%';

    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = '⬇ Export Selected Files';
      prog.style.display = 'none';
    }, 2000);
  }

  generateManifest(selectedFiles, totalMB) {
    const preset = this.currentPreset || 'pop';
    const lines = [
      '5.1 AutoMaster — Export Manifest',
      `Preset: ${preset.toUpperCase()}`,
      '------------------------------------------------',
      '',
    ];

    const isBasic = !document.getElementById('tab-pro')?.classList.contains('active');
    let fileIdx = 0;
    
    if (isBasic) {
      lines.push(`[${this.basicGroup.label.toUpperCase()}]`);
      this.basicGroup.files.forEach((file) => {
        const isChecked = selectedFiles.includes(file);
        lines.push(`  ${isChecked ? '✓' : '○'}  ${file.n}   ${file.s}   ${file.f}${isChecked ? '' : ' (skipped)'}`);
      });
      lines.push('');
    } else {
      this.exportGroups.forEach((group) => {
        lines.push(`[${group.label.toUpperCase()}]`);
        group.files.forEach((file) => {
          const isChecked = selectedFiles.includes(file);
          lines.push(`  ${isChecked ? '✓' : '○'}  ${file.n}   ${file.s}   ${file.f}${isChecked ? '' : ' (skipped)'}`);
          fileIdx++;
        });
        lines.push('');
      });
    }

    lines.push('------------------------------------------------');
    lines.push(`Total: ${selectedFiles.length} files / ${totalMB.toFixed(0)} MB`);
    lines.push('');
    lines.push('NOTE: Dolby Atmos (Apple Music/Tidal) needs a separate');
    lines.push('Atmos mix session. This 5.1 master is the source for that.');

    return lines.join('\n');
  }

  downloadManifest(content) {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'automaster_export_manifest.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }
}
