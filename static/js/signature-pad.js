/**
 * Harmoni ERP - Signature Pad Component
 *
 * Canvas-based signature capture with mouse/touch support.
 * Features: draw, clear, undo, export as PNG base64.
 *
 * Usage:
 *   const pad = new SignaturePad('#canvas-id', { options });
 *   pad.toDataURL();  // => 'data:image/png;base64,...'
 *   pad.clear();
 *   pad.undo();
 *   pad.isEmpty();
 */

class SignaturePad {
    constructor(canvasSelector, options = {}) {
        this.canvas = typeof canvasSelector === 'string'
            ? document.querySelector(canvasSelector)
            : canvasSelector;

        if (!this.canvas) {
            console.error('SignaturePad: Canvas element not found:', canvasSelector);
            return;
        }

        this.ctx = this.canvas.getContext('2d');

        // Options with defaults
        this.options = Object.assign({
            penColor: '#1a1a2e',
            penWidth: 2.5,
            minWidth: 1.5,
            maxWidth: 4,
            velocityFilterWeight: 0.7,
            backgroundColor: 'rgba(255, 255, 255, 0)',
            dotSize: 3,
            throttle: 16,
            onBegin: null,
            onEnd: null,
        }, options);

        // State
        this._drawing = false;
        this._points = [];
        this._strokes = [];  // Array of strokes for undo
        this._currentStroke = [];
        this._lastVelocity = 0;
        this._lastWidth = this.options.penWidth;
        this._isEmpty = true;
        this._lastTimestamp = 0;

        // Set up canvas size
        this._resizeCanvas();

        // Bind events
        this._bindEvents();
    }

    // ── Public API ──────────────────────────────────────────────

    /**
     * Clear the signature pad.
     */
    clear() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this._strokes = [];
        this._currentStroke = [];
        this._isEmpty = true;
        this._resetPen();
    }

    /**
     * Undo the last stroke.
     */
    undo() {
        if (this._strokes.length === 0) return;
        this._strokes.pop();
        this._redraw();
    }

    /**
     * Check if the pad is empty (no strokes drawn).
     */
    isEmpty() {
        return this._isEmpty;
    }

    /**
     * Export the signature as a PNG data URL.
     * @returns {string} data:image/png;base64,...
     */
    toDataURL(type = 'image/png', quality = 1.0) {
        if (this._isEmpty) return '';

        // Create a temp canvas with white background for export
        const tmpCanvas = document.createElement('canvas');
        tmpCanvas.width = this.canvas.width;
        tmpCanvas.height = this.canvas.height;
        const tmpCtx = tmpCanvas.getContext('2d');

        // White background
        tmpCtx.fillStyle = '#ffffff';
        tmpCtx.fillRect(0, 0, tmpCanvas.width, tmpCanvas.height);

        // Draw the signature on top
        tmpCtx.drawImage(this.canvas, 0, 0);

        return tmpCanvas.toDataURL(type, quality);
    }

    /**
     * Load a signature from a data URL.
     */
    fromDataURL(dataUrl) {
        const img = new window.Image();
        img.onload = () => {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.drawImage(img, 0, 0, this.canvas.width, this.canvas.height);
            this._isEmpty = false;
        };
        img.src = dataUrl;
    }

    /**
     * Destroy event listeners.
     */
    destroy() {
        this._unbindEvents();
    }

    // ── Private: Drawing ────────────────────────────────────────

    _resetPen() {
        this._lastVelocity = 0;
        this._lastWidth = this.options.penWidth;
    }

    _beginStroke(point) {
        this._drawing = true;
        this._currentStroke = [point];
        this._points = [point];
        this._lastTimestamp = Date.now();
        this._resetPen();

        if (this.options.onBegin) this.options.onBegin();
    }

    _updateStroke(point) {
        if (!this._drawing) return;

        const now = Date.now();
        const elapsed = now - this._lastTimestamp;
        this._lastTimestamp = now;

        this._currentStroke.push(point);
        this._points.push(point);

        if (this._points.length >= 3) {
            const p0 = this._points[this._points.length - 3];
            const p1 = this._points[this._points.length - 2];
            const p2 = this._points[this._points.length - 1];

            // Calculate velocity for pressure simulation
            const dx = p2.x - p0.x;
            const dy = p2.y - p0.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const velocity = elapsed > 0 ? dist / elapsed : 0;

            // Smooth velocity
            this._lastVelocity =
                this.options.velocityFilterWeight * velocity +
                (1 - this.options.velocityFilterWeight) * this._lastVelocity;

            // Calculate width based on velocity (slower = thicker)
            const newWidth = this._strokeWidth(this._lastVelocity);

            // Draw quadratic curve through midpoints for smoothness
            const mid1 = { x: (p0.x + p1.x) / 2, y: (p0.y + p1.y) / 2 };
            const mid2 = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };

            this._drawCurve(mid1, p1, mid2, this._lastWidth, newWidth);
            this._lastWidth = newWidth;
        } else if (this._points.length === 2) {
            // Just two points: draw a line
            const p0 = this._points[0];
            const p1 = this._points[1];
            this._drawLine(p0, p1, this.options.penWidth);
        }

        this._isEmpty = false;
    }

    _endStroke() {
        if (!this._drawing) return;
        this._drawing = false;

        // If only one point, draw a dot
        if (this._currentStroke.length === 1) {
            const p = this._currentStroke[0];
            this._drawDot(p);
            this._isEmpty = false;
        }

        // Save stroke for undo
        if (this._currentStroke.length > 0) {
            this._strokes.push([...this._currentStroke]);
        }
        this._currentStroke = [];
        this._points = [];

        if (this.options.onEnd) this.options.onEnd();
    }

    _strokeWidth(velocity) {
        const { minWidth, maxWidth } = this.options;
        // Inverse relationship: faster movement = thinner line
        return Math.max(maxWidth / (velocity + 1), minWidth);
    }

    _drawDot(point) {
        this.ctx.beginPath();
        this.ctx.arc(point.x, point.y, this.options.dotSize, 0, 2 * Math.PI);
        this.ctx.fillStyle = this.options.penColor;
        this.ctx.fill();
    }

    _drawLine(p0, p1, width) {
        this.ctx.beginPath();
        this.ctx.moveTo(p0.x, p0.y);
        this.ctx.lineTo(p1.x, p1.y);
        this.ctx.strokeStyle = this.options.penColor;
        this.ctx.lineWidth = width;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';
        this.ctx.stroke();
    }

    _drawCurve(start, control, end, startWidth, endWidth) {
        this.ctx.beginPath();
        this.ctx.moveTo(start.x, start.y);
        this.ctx.quadraticCurveTo(control.x, control.y, end.x, end.y);
        this.ctx.strokeStyle = this.options.penColor;
        this.ctx.lineWidth = (startWidth + endWidth) / 2;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';
        this.ctx.stroke();
    }

    _redraw() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this._isEmpty = this._strokes.length === 0;

        for (const stroke of this._strokes) {
            if (stroke.length === 1) {
                this._drawDot(stroke[0]);
                continue;
            }
            this._resetPen();
            for (let i = 1; i < stroke.length; i++) {
                if (i >= 2) {
                    const p0 = stroke[i - 2];
                    const p1 = stroke[i - 1];
                    const p2 = stroke[i];
                    const mid1 = { x: (p0.x + p1.x) / 2, y: (p0.y + p1.y) / 2 };
                    const mid2 = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
                    this._drawCurve(mid1, p1, mid2, this.options.penWidth, this.options.penWidth);
                } else {
                    this._drawLine(stroke[0], stroke[1], this.options.penWidth);
                }
            }
        }
    }

    // ── Private: Canvas resize ──────────────────────────────────

    _resizeCanvas() {
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        const rect = this.canvas.getBoundingClientRect();

        this.canvas.width = rect.width * ratio;
        this.canvas.height = rect.height * ratio;
        this.ctx.scale(ratio, ratio);

        // CSS size stays the same
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';
    }

    // ── Private: Event handling ─────────────────────────────────

    _getPoint(event) {
        const rect = this.canvas.getBoundingClientRect();

        if (event.touches && event.touches.length > 0) {
            return {
                x: event.touches[0].clientX - rect.left,
                y: event.touches[0].clientY - rect.top,
            };
        }

        return {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
        };
    }

    _bindEvents() {
        // Store bound handlers for cleanup
        this._onMouseDown = (e) => {
            e.preventDefault();
            this._beginStroke(this._getPoint(e));
        };
        this._onMouseMove = (e) => {
            e.preventDefault();
            this._updateStroke(this._getPoint(e));
        };
        this._onMouseUp = (e) => {
            e.preventDefault();
            this._endStroke();
        };
        this._onMouseLeave = () => {
            this._endStroke();
        };

        this._onTouchStart = (e) => {
            e.preventDefault();
            this._beginStroke(this._getPoint(e));
        };
        this._onTouchMove = (e) => {
            e.preventDefault();
            this._updateStroke(this._getPoint(e));
        };
        this._onTouchEnd = (e) => {
            e.preventDefault();
            this._endStroke();
        };

        this._onResize = () => {
            // Save current image
            const data = this._strokes.length > 0 ? this.toDataURL() : null;
            this._resizeCanvas();
            if (data) this.fromDataURL(data);
        };

        // Mouse events
        this.canvas.addEventListener('mousedown', this._onMouseDown);
        this.canvas.addEventListener('mousemove', this._onMouseMove);
        this.canvas.addEventListener('mouseup', this._onMouseUp);
        this.canvas.addEventListener('mouseleave', this._onMouseLeave);

        // Touch events
        this.canvas.addEventListener('touchstart', this._onTouchStart, { passive: false });
        this.canvas.addEventListener('touchmove', this._onTouchMove, { passive: false });
        this.canvas.addEventListener('touchend', this._onTouchEnd, { passive: false });

        // Resize
        window.addEventListener('resize', this._onResize);
    }

    _unbindEvents() {
        this.canvas.removeEventListener('mousedown', this._onMouseDown);
        this.canvas.removeEventListener('mousemove', this._onMouseMove);
        this.canvas.removeEventListener('mouseup', this._onMouseUp);
        this.canvas.removeEventListener('mouseleave', this._onMouseLeave);
        this.canvas.removeEventListener('touchstart', this._onTouchStart);
        this.canvas.removeEventListener('touchmove', this._onTouchMove);
        this.canvas.removeEventListener('touchend', this._onTouchEnd);
        window.removeEventListener('resize', this._onResize);
    }
}


// ── Helper: Initialize signature pad with standard controls ─────

function initSignaturePad(canvasId, options = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error('initSignaturePad: Canvas not found:', canvasId);
        return null;
    }

    const pad = new SignaturePad(canvas, options);

    // Auto-bind buttons if they exist
    const clearBtn = document.getElementById(canvasId + '-clear');
    const undoBtn = document.getElementById(canvasId + '-undo');
    const saveBtn = document.getElementById(canvasId + '-save');
    const hiddenInput = document.getElementById(canvasId + '-data');

    if (clearBtn) {
        clearBtn.addEventListener('click', (e) => {
            e.preventDefault();
            pad.clear();
            if (hiddenInput) hiddenInput.value = '';
            // Update UI
            _updatePadStatus(canvasId, true);
        });
    }

    if (undoBtn) {
        undoBtn.addEventListener('click', (e) => {
            e.preventDefault();
            pad.undo();
            if (hiddenInput && pad.isEmpty()) hiddenInput.value = '';
            _updatePadStatus(canvasId, pad.isEmpty());
        });
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (pad.isEmpty()) {
                _showPadError(canvasId, 'Debe dibujar su firma primero.');
                return;
            }
            const data = pad.toDataURL();
            if (hiddenInput) hiddenInput.value = data;
            _updatePadStatus(canvasId, false);
            _showPadSuccess(canvasId, 'Firma capturada correctamente.');
        });
    }

    // Track drawing state for UI updates
    const origOnEnd = options.onEnd;
    pad.options.onEnd = function () {
        if (hiddenInput) hiddenInput.value = pad.toDataURL();
        _updatePadStatus(canvasId, pad.isEmpty());
        if (origOnEnd) origOnEnd();
    };

    return pad;
}

function _updatePadStatus(canvasId, empty) {
    const status = document.getElementById(canvasId + '-status');
    if (status) {
        if (empty) {
            status.innerHTML = '<span class="text-muted"><i class="fas fa-info-circle me-1"></i>Dibuje su firma en el recuadro</span>';
        } else {
            status.innerHTML = '<span class="text-success"><i class="fas fa-check-circle me-1"></i>Firma capturada</span>';
        }
    }
}

function _showPadError(canvasId, msg) {
    const status = document.getElementById(canvasId + '-status');
    if (status) {
        status.innerHTML = `<span class="text-danger"><i class="fas fa-exclamation-circle me-1"></i>${msg}</span>`;
    }
}

function _showPadSuccess(canvasId, msg) {
    const status = document.getElementById(canvasId + '-status');
    if (status) {
        status.innerHTML = `<span class="text-success"><i class="fas fa-check-circle me-1"></i>${msg}</span>`;
    }
}
