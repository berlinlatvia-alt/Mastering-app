/**
 * Studio Tuning UI Controller
 * Manages the tuning drawer, presets, and parameters
 */

export class TuningUI {
  constructor(api) {
    this.api = api;
    this.currentPreset = 'pop';
    this.isOpen = false;
    this.config = {
      tape: 35,
      harm: 20,
      buscomp: 45,
      trans: 55,
      para: 25,
      low: 3,
      mid: -2,
      air: 4,
      sub: 60,
      width: 100,
      rear: 40,
      verb: 30,
      lfe: 80,
      console: 'SSL 4000 G',
    };
  }

  init() {
    this.setupEventListeners();
    this.loadPresets();
  }

  setupEventListeners() {
    // Slider inputs
    const sliders = document.querySelectorAll('.tslider');
    sliders.forEach((slider) => {
      slider.addEventListener('input', (e) => this.handleSliderChange(e));
    });

    // Toggle pills
    const pills = document.querySelectorAll('.tpill');
    pills.forEach((pill) => {
      pill.addEventListener('click', (e) => this.handlePillClick(e));
    });

    // Console select
    const consoleSelect = document.getElementById('t-console');
    if (consoleSelect) {
      consoleSelect.addEventListener('change', (e) => {
        this.config.console = e.target.value;
        this.sendConfig();
      });
    }
  }

  async loadPresets() {
    try {
      const response = await this.api.getPresets();
      this.presets = response.presets || {};
    } catch (error) {
      // Use defaults
      this.presets = {
        pop: { tape: 35, harm: 20, buscomp: 45, trans: 55, para: 25, low: 3, mid: -2, air: 4, sub: 60, width: 100, rear: 40, verb: 30, lfe: 80 },
        rock: { tape: 60, harm: 45, buscomp: 65, trans: 75, para: 40, low: 6, mid: 2, air: 2, sub: 75, width: 110, rear: 35, verb: 20, lfe: 80 },
        electronic: { tape: 10, harm: 5, buscomp: 55, trans: 80, para: 50, low: 8, mid: -4, air: 8, sub: 85, width: 130, rear: 55, verb: 25, lfe: 90 },
        jazz: { tape: 45, harm: 30, buscomp: 25, trans: 30, para: 10, low: 1, mid: 1, air: 3, sub: 40, width: 90, rear: 50, verb: 55, lfe: 70 },
        hiphop: { tape: 25, harm: 35, buscomp: 70, trans: 85, para: 60, low: 9, mid: -3, air: 5, sub: 90, width: 105, rear: 30, verb: 15, lfe: 100 },
        cinematic: { tape: 50, harm: 25, buscomp: 35, trans: 45, para: 20, low: 4, mid: -1, air: 6, sub: 65, width: 120, rear: 70, verb: 65, lfe: 80 },
      };
    }
  }

  toggle() {
    const drawer = document.getElementById('tdrawer');
    const overlay = document.getElementById('tov');
    const btn = document.getElementById('tune-btn');

    if (!drawer) return;

    this.isOpen = !this.isOpen;

    if (this.isOpen) {
      drawer.classList.add('open');
      if (overlay) overlay.classList.add('open');
      if (btn) btn.classList.add('active');
    } else {
      drawer.classList.remove('open');
      if (overlay) overlay.classList.remove('open');
      if (btn) btn.classList.remove('active');
    }
  }

  close() {
    if (!this.isOpen) return;
    this.toggle();
  }

  async applyPreset(presetName, element) {
    // Update UI
    document.querySelectorAll('.pchip').forEach((c) => c.classList.remove('active'));
    if (element) element.classList.add('active');

    this.currentPreset = presetName;
    const preset = this.presets[presetName];

    if (!preset) return;

    // Update sliders
    Object.entries(preset).forEach(([key, value]) => {
      const slider = document.getElementById(`t-${key}`);
      if (slider) {
        slider.value = value;
        this.config[key] = value;
        this.updateValueDisplay(key, value);
      }
    });

    // Send to backend
    try {
      await this.api.applyPreset(presetName);
      console.log(`Preset applied: ${presetName}`);
    } catch (error) {
      console.error('Failed to apply preset:', error);
    }
  }

  handleSliderChange(event) {
    const slider = event.target;
    const key = slider.id.replace('t-', '');
    const value = parseInt(slider.value);

    this.config[key] = value;
    this.updateValueDisplay(key, value);

    // Debounced send
    clearTimeout(this.sendTimeout);
    this.sendTimeout = setTimeout(() => this.sendConfig(), 300);
  }

  handlePillClick(event) {
    const pill = event.currentTarget;
    pill.classList.toggle('on');

    // Update linked chain node
    const chainId = pill.dataset.chain;
    if (chainId) {
      const chainNode = document.getElementById(chainId);
      if (chainNode) {
        chainNode.classList.toggle('on', pill.classList.contains('on'));
      }
    }
  }

  updateValueDisplay(key, value) {
    const display = document.getElementById(`tv-${key}`);
    if (!display) return;

    const numericKeys = ['tape', 'harm', 'buscomp', 'trans', 'para', 'width', 'rear', 'verb', 'sub'];
    const dbKeys = ['low', 'mid', 'air'];

    if (numericKeys.includes(key)) {
      display.textContent = `${value}%`;
    } else if (dbKeys.includes(key)) {
      display.textContent = `${value >= 0 ? '+' : ''}${value} dB`;
    } else if (key === 'lfe') {
      display.textContent = `${value} Hz`;
    } else {
      display.textContent = value;
    }
  }

  async sendConfig() {
    try {
      await this.api.configureStudio(this.config);
    } catch (error) {
      console.error('Failed to send studio config:', error);
    }
  }
}
