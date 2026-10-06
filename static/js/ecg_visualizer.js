/**
 * Clinical Hospital ECG Waveform Renderer
 * Visualizes dynamic cardiac telemetry across a clean medical grid.
 */

class ECGVisualizer {
    constructor(canvasId, rhythmType = 'SINUS', bpm = 75, isDecoy = false) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.rhythmType = rhythmType.toUpperCase();
        this.bpm = bpm || 75;
        this.isDecoy = isDecoy;

        this.width = this.canvas.width = this.canvas.offsetWidth || 800;
        this.height = this.canvas.height = this.canvas.offsetHeight || 140;
        this.midY = this.height / 2;

        this.x = 0;
        this.step = 2; // px per tick
        this.phase = 0; // 0 to 1 cycle
        this.history = [];

        // Clinical Hospital Color Palette (no neon glow)
        if (this.isDecoy) {
            this.traceColor = '#7c3aed'; // Decoy purple
            this.bgColor = '#faf5ff';
            this.gridMajor = 'rgba(216, 180, 254, 0.4)';
            this.gridMinor = 'rgba(233, 213, 255, 0.25)';
        } else if (this.rhythmType.includes('VT') || this.rhythmType.includes('STEMI')) {
            this.traceColor = '#dc2626'; // Acute medical alert crimson
            this.bgColor = '#fff5f5';
            this.gridMajor = 'rgba(254, 202, 202, 0.5)';
            this.gridMinor = 'rgba(254, 226, 226, 0.3)';
        } else {
            this.traceColor = '#0284c7'; // Clinical hospital blue
            this.bgColor = '#f8fafc';
            this.gridMajor = 'rgba(203, 213, 225, 0.5)';
            this.gridMinor = 'rgba(226, 232, 240, 0.3)';
        }

        this.init();
    }

    init() {
        this.ctx.fillStyle = this.bgColor;
        this.ctx.fillRect(0, 0, this.width, this.height);
        this.drawFullGrid();
        this.animate();
    }

    drawFullGrid() {
        // Minor grid 5px
        this.ctx.strokeStyle = this.gridMinor;
        this.ctx.lineWidth = 0.5;
        for (let x = 0; x < this.width; x += 10) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.height);
            this.ctx.stroke();
        }
        for (let y = 0; y < this.height; y += 10) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.width, y);
            this.ctx.stroke();
        }

        // Major grid 25px
        this.ctx.strokeStyle = this.gridMajor;
        this.ctx.lineWidth = 1;
        for (let x = 0; x < this.width; x += 25) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.height);
            this.ctx.stroke();
        }
        for (let y = 0; y < this.height; y += 25) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.width, y);
            this.ctx.stroke();
        }
    }

    getVoltage(t) {
        const p = t % 1.0;

        if (this.isDecoy) {
            if (p < 0.2) return Math.sin(p * Math.PI * 10) * 15;
            if (p < 0.5) return (p > 0.35 ? 25 : -25);
            return Math.sin(p * Math.PI * 4) * 10;
        }

        if (this.rhythmType.includes('VT')) {
            return -Math.sin(p * Math.PI * 2) * (this.height * 0.35);
        }

        if (this.rhythmType.includes('STEMI')) {
            if (p >= 0.1 && p < 0.2) return -10 * Math.sin((p - 0.1) * Math.PI * 10);
            if (p >= 0.32 && p < 0.35) return 8;
            if (p >= 0.35 && p < 0.39) return -55;
            if (p >= 0.39 && p < 0.43) return 12;
            if (p >= 0.43 && p < 0.70) return -26; // ST elevation
            if (p >= 0.70 && p < 0.85) return -20 * Math.sin((p - 0.7) * Math.PI * 6.6);
            return (Math.random() - 0.5) * 1.5;
        }

        // Standard Normal Sinus Rhythm (P-Q-R-S-T)
        if (p >= 0.12 && p < 0.22) return -8 * Math.sin((p - 0.12) * Math.PI * 10);
        if (p >= 0.34 && p < 0.36) return 6;
        if (p >= 0.36 && p < 0.40) return -50 * Math.sin((p - 0.36) * Math.PI * 25);
        if (p >= 0.40 && p < 0.44) return 12 * Math.sin((p - 0.40) * Math.PI * 25);
        if (p >= 0.58 && p < 0.75) return -14 * Math.sin((p - 0.58) * Math.PI * 5.88);
        return (Math.random() - 0.5) * 1.2;
    }

    animate() {
        const cycleSpeed = (this.bpm / 60) * 0.015;
        this.phase += cycleSpeed;
        const voltage = this.getVoltage(this.phase);
        const y = this.midY + voltage;

        // Erase ahead sweep band
        const eraseWidth = 14;
        this.ctx.fillStyle = this.bgColor;
        this.ctx.fillRect(this.x, 0, eraseWidth, this.height);

        // Re-draw subtle grid line behind erased band
        this.drawGridSegment(this.x, eraseWidth);

        // Draw crisp clinical line
        if (this.prevY !== undefined) {
            this.ctx.beginPath();
            this.ctx.moveTo(this.x - this.step, this.prevY);
            this.ctx.lineTo(this.x, y);
            this.ctx.strokeStyle = this.traceColor;
            this.ctx.lineWidth = 2.2;
            this.ctx.lineCap = 'round';
            this.ctx.stroke();
        }

        this.prevY = y;
        this.x += this.step;

        if (this.x >= this.width) {
            this.x = 0;
            this.prevY = undefined;
        }

        requestAnimationFrame(() => this.animate());
    }

    drawGridSegment(startX, width) {
        this.ctx.strokeStyle = this.gridMajor;
        this.ctx.lineWidth = 0.8;
        for (let gx = Math.floor(startX / 25) * 25; gx < startX + width; gx += 25) {
            if (gx >= startX && gx <= startX + width) {
                this.ctx.beginPath();
                this.ctx.moveTo(gx, 0);
                this.ctx.lineTo(gx, this.height);
                this.ctx.stroke();
            }
        }
        for (let gy = 0; gy < this.height; gy += 25) {
            this.ctx.beginPath();
            this.ctx.moveTo(startX, gy);
            this.ctx.lineTo(startX + width, gy);
            this.ctx.stroke();
        }
    }
}

window.ECGVisualizer = ECGVisualizer;
