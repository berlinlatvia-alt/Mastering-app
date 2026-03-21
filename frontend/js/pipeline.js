/**
 * Pipeline UI Controller
 * Manages stage display, progress, and visualization
 */

export class PipelineUI {
  constructor(api) {
    this.api = api;
    this.currentStageIndex = 0;
    this.stages = this.initializeStages();
  }

  initializeStages() {
    return [
      {
        num: '01',
        title: 'Input Preparation & Analysis',
        sub: 'Resample · normalize · spectral scan',
        badges: [
          { l: 'CPU', c: 'bc' },
          { l: '~0.5 GB RAM', c: 'br' },
          { l: 'AUTO', c: 'ba' },
        ],
        ram: 6,
        vram: 0,
        steps: [
          'Load WAV via libsndfile',
          'Detect sample rate and bit depth',
          'Resample to 48 kHz / 32-bit float',
          'True-peak scan (all samples)',
          'Measure integrated loudness (LUFS)',
          'Compute stereo width coefficient',
          'Spectral balance check',
          'Generate analysis report',
        ],
      },
      {
        num: '02',
        title: 'Track Cutting (Auto Silence Detection)',
        sub: 'RMS envelope · zero-crossing align · split',
        badges: [
          { l: 'CPU', c: 'bc' },
          { l: '~1 GB RAM', c: 'br' },
          { l: 'AUTO', c: 'ba' },
        ],
        ram: 10,
        vram: 0,
        wf: true,
        steps: [
          'Compute RMS envelope (10 ms windows)',
          'Apply silence gate at threshold',
          'Detect silence regions > 800 ms',
          'Generate candidate cut points',
          'Align cuts to zero-crossing',
          'Merge short segments (< 2 s)',
          'Preview cut markers on waveform',
          'Export discrete track segments',
        ],
      },
      {
        num: '03',
        title: 'Stem Separation (Demucs v4)',
        sub: 'htdemucs_6s · 6 stems · GPU accelerated',
        badges: [
          { l: '6–8 GB VRAM', c: 'bv' },
          { l: '~6 GB RAM', c: 'br' },
          { l: 'AUTO', c: 'ba' },
        ],
        ram: 75,
        vram: 90,
        steps: [
          'Load htdemucs_6s model weights',
          'Chunk → 7s overlapping segments',
          'GPU pass — vocals',
          'GPU pass — drums',
          'GPU pass — bass',
          'GPU pass — guitar',
          'GPU pass — piano',
          'GPU pass — other',
          'Overlap-add reconstruction',
          'Validate stem SDR scores',
        ],
      },
      {
        num: '04',
        title: '5.1 Channel Assignment & Spatial Upmix',
        sub: 'Stem routing · pan law · LFE crossover',
        badges: [
          { l: 'CPU', c: 'bc' },
          { l: '~4 GB RAM', c: 'br' },
          { l: 'AUTO', c: 'ba' },
        ],
        ram: 45,
        vram: 0,
        ch: true,
        steps: [
          'Mono-sum vocals → Center',
          'Bass → LFE via 80 Hz Butterworth LP',
          'Bass residual → Front L/R',
          'Drums transients → Front L/R wide',
          'Drum ambience → Ls/Rs',
          'Guitar/piano → Front L/R',
          'Other → Ls/Rs reverb field',
          'ITU-R BS.775 levels',
          'Phase coherence check',
          'Render 6-channel interleaved',
        ],
      },
      {
        num: '05',
        title: 'Pro Studio EQ, Dynamics & Color',
        sub: 'Console emulation · tape · bus comp · exciter',
        badges: [
          { l: 'CPU', c: 'bc' },
          { l: '~5 GB RAM', c: 'br' },
          { l: 'AUTO', c: 'ba' },
          { l: 'STUDIO', c: 'bs' },
        ],
        ram: 55,
        vram: 0,
        steps: [
          'HPF all channels @ 20 Hz',
          'Console emulation (harmonic model)',
          'Tape saturation per stem',
          'Bus glue compression',
          'Transient shaper (punch/attack)',
          'Parallel compression blend',
          'Per-channel EQ tonal shape',
          'Air shelf boost (10 kHz+)',
          'De-esser on center channel',
          'Rear shelf −4 dB @ 12 kHz',
        ],
      },
      {
        num: '06',
        title: 'Loudness Normalization (EBU R128)',
        sub: 'Integrated LUFS · true-peak · LRA',
        badges: [
          { l: 'CPU', c: 'bc' },
          { l: '~2 GB RAM', c: 'br' },
          { l: 'AUTO', c: 'ba' },
        ],
        ram: 20,
        vram: 0,
        steps: [
          'Measure integrated loudness per channel',
          'Measure LRA (loudness range)',
          'Measure true-peak per channel',
          'Compute multi-channel sum loudness',
          'Apply make-up gain to target',
          'Re-verify true-peak < −1 dBTP',
          'EBU R128 compliance report',
          'Write LUFS metadata tags',
        ],
      },
      {
        num: '07',
        title: 'Encode & Export',
        sub: '6-ch WAV · AC-3 · DTS · metadata embed',
        badges: [
          { l: 'CPU', c: 'bc' },
          { l: '~3 GB RAM', c: 'br' },
          { l: 'AUTO', c: 'ba' },
        ],
        ram: 28,
        vram: 0,
        steps: [
          'Write 6-channel interleaved WAV',
          'Encode Dolby AC-3 640 kbps',
          'Encode DTS 5.1 1509 kbps',
          'Embed dialnorm metadata',
          'Write EBU R128 tags',
          'Generate QC report PDF',
          'Verify channel order (ffprobe)',
          'Pipeline complete',
        ],
      },
    ];
  }

  init() {
    this.buildSidebar();
  }

  buildSidebar() {
    const sl = document.getElementById('sl');
    if (!sl) return;

    sl.innerHTML = '';
    this.stages.forEach((stage, i) => {
      const el = document.createElement('div');
      el.className = 'si';
      el.id = `si${i}`;
      el.innerHTML = `
        <div class="sn" id="sn${i}">${stage.num}</div>
        <div class="sname">${stage.title}</div>
        <div class="sstatus pending" id="ss${i}">—</div>
      `;
      sl.appendChild(el);
    });
  }

  updateStages(stages) {
    if (!stages) return;

    stages.forEach((stage, i) => {
      const item = document.getElementById(`si${i}`);
      const status = document.getElementById(`ss${i}`);

      if (!item || !status) return;

      item.className = `si ${stage.status}`;
      status.className = `sstatus ${stage.status}`;
      status.textContent = {
        pending: '—',
        running: 'RUN',
        done: 'OK',
        error: 'ERR',
      }[stage.status] || '—';

      // Update stage card if active
      if (stage.status === 'running') {
        this.renderStageCard(i, stage);
      }
    });
  }

  updateCurrentStage(index) {
    this.currentStageIndex = index;
  }

  renderStageCard(stageIndex, stageData) {
    const sd = document.getElementById('sd');
    if (!sd) return;

    const stage = this.stages[stageIndex];
    if (!stage) return;

    const progress = stageData.progress || 0;
    const steps = stage.steps;
    const completedSteps = Math.floor((progress / 100) * steps.length);

    const badges = stage.badges.map((b) => `<span class="badge ${b.c}">${b.l}</span>`).join('');

    const stepItems = steps
      .map((step, i) => {
        const cls = i < completedSteps ? 'done' : i === completedSteps ? 'running' : 'pending';
        const ch = i < completedSteps ? '✓' : i === completedSteps ? '▸' : '○';
        return `<li class="stepitem"><span class="stepck ${cls}">${ch}</span><span class="steptxt ${cls}">${step}</span></li>`;
      })
      .join('');

    let extra = '';

    // Waveform visualization for stage 02
    if (stage.wf) {
      const cutMarks = [32.5, 65.0, 102.3, 138.7, 177.1].map((t, i) => {
        const detected = completedSteps >= 4 + i;
        return `<span class="cm ${detected ? 'det' : ''}">${detected ? '✓' : '○'} Cut ${i + 1} @ ${this.formatTime(t)}</span>`;
      }).join('');

      extra = `
        <div class="wfsec">
          <div class="wflabel">Waveform + Cut Detection</div>
          <canvas class="wfc" id="wfc"></canvas>
          <div class="cutmarks">${cutMarks}</div>
        </div>
      `;
    }

    // Channel matrix for stage 04
    if (stage.ch) {
      const channels = [
        { n: 'L', src: 'Guitar + Piano', l: 78 },
        { n: 'C', src: 'Vocals (mono)', l: 62 },
        { n: 'R', src: 'Guitar + Piano', l: 78 },
        { n: 'Ls', src: 'Drums amb + Other', l: 44 },
        { n: 'LFE', src: 'Bass <80 Hz', l: 55 },
        { n: 'Rs', src: 'Drums amb + Other', l: 44 },
      ];

      const active = completedSteps >= 3;
      extra = `
        <div class="chmat">
          ${channels
            .map(
              (c) => `
            <div class="chcell ${active ? 'act' : ''} ${c.n === 'LFE' ? 'lfe' : ''}">
              <div class="chname">${c.n}</div>
              <div class="chsrc">${c.src}</div>
              <div class="chlv"><div class="chlvf" style="width:${active ? c.l : 0}%"></div></div>
            </div>
          `
            )
            .join('')}
        </div>
      `;
    }

    const pctClass = progress >= 100 ? 'done' : 'scan';
    const pctText = progress >= 100 ? 'Complete' : `${Math.round(progress)}%`;

    sd.innerHTML = `
      <div class="scard">
        <div class="sch">
          <div class="scnum">${stage.num}</div>
          <div>
            <div class="sctitle">${stage.title}</div>
            <div class="scsub">${stage.sub}</div>
          </div>
        </div>
        <div class="scbadges">${badges}</div>
        <div class="progc">
          <div class="progl">
            <span>${pctText}</span>
            <span>RAM ${(stage.ram / 100 * 16).toFixed(0)} GB · VRAM ${stage.vram > 0 ? (stage.vram / 100 * 8).toFixed(1) + ' GB' : '—'}</span>
          </div>
          <div class="progt">
            <div class="progf ${pctClass}" style="width:${progress}%"></div>
          </div>
        </div>
        ${extra}
        <ul class="steplist">${stepItems}</ul>
      </div>
    `;

    // Draw waveform if present
    if (stage.wf) {
      this.drawWaveform('wfc', progress / 100);
    }
  }

  drawWaveform(canvasId, progress) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const dpr = window.devicePixelRatio || 1;
    const width = canvas.offsetWidth || 560;
    const height = 68;

    canvas.width = width * dpr;
    canvas.height = height * dpr;

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    // Draw waveform
    ctx.beginPath();
    for (let i = 0; i < 300; i++) {
      const t = i / 300;
      const amp =
        (0.3 + 0.6 * Math.sin(t * Math.PI) * (0.7 + 0.3 * Math.sin(t * 23))) *
        (0.6 + 0.4 * (Math.sin(i * 127.1 + 311.7) * 0.5 + 0.5));
      ctx.moveTo(t * width, height / 2 - amp * height / 2 * 0.85);
      ctx.lineTo(t * width, height / 2 + amp * height / 2 * 0.85);
    }
    ctx.strokeStyle = '#2dd4a030';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Overlay for progress
    if (progress < 1) {
      ctx.fillStyle = 'rgba(13, 14, 16, 0.55)';
      ctx.fillRect(progress * width, 0, width * (1 - progress), height);
    }

    // Draw cut markers
    const cutPoints = [0.145, 0.29, 0.475, 0.635, 0.8];
    cutPoints.forEach((p, i) => {
      if (progress >= p) {
        ctx.beginPath();
        ctx.moveTo(p * width, 0);
        ctx.lineTo(p * width, height);
        ctx.strokeStyle = '#e8a030';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([3, 3]);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = '#e8a030';
        ctx.font = '9px IBM Plex Mono, monospace';
        ctx.fillText(`T${i + 1}`, p * width + 3, 11);
      }
    });
  }

  showDone() {
    const sd = document.getElementById('sd');
    if (!sd) return;

    sd.innerHTML = `
      <div class="done-banner">
        <div class="done-icon">✓</div>
        <div class="done-title">Pipeline Complete</div>
        <div class="done-sub">All stages finished · Click <strong style="color:var(--teal)">⬇ EXPORT FILES</strong> to choose destination formats</div>
      </div>
    `;
  }

  formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = (seconds % 60).toFixed(1);
    return `${m.toString().padStart(2, '0')}:${s.padStart(5, '0')}`;
  }
}
