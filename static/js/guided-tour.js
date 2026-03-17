/**
 * Harmoni ERP - Guided Tour Component
 *
 * Highlights elements step by step with overlay.
 * Steps defined as array: [{target: '#sidebar', title: 'Menu', text: '...'}]
 * Next/Skip/Got it buttons.
 * Stores completion in localStorage.
 * Auto-trigger on first login.
 *
 * Usage:
 *   HarmoniTour.start();            // start with default steps
 *   HarmoniTour.start(customSteps); // start with custom steps
 *   HarmoniTour.reset();            // reset to show again
 */
const HarmoniTour = {
    steps: [
        {
            target: '#harmoniSidebar',
            title: 'Menu de Navegacion',
            text: 'Accede a todos los modulos del sistema: Personal, Asistencia, Nominas, Documentos, Vacaciones y mas.',
            position: 'right',
        },
        {
            target: '#globalSearchWrapper',
            title: 'Busqueda Global',
            text: 'Busca empleados, documentos o papeletas rapidamente. Usa Ctrl+K para abrir la busqueda desde cualquier pantalla.',
            position: 'bottom',
        },
        {
            target: '#notifWidget',
            title: 'Notificaciones',
            text: 'Recibe alertas de aprobaciones pendientes, vencimientos de contratos y comunicados importantes en tiempo real.',
            position: 'bottom',
        },
        {
            target: '.harmoni-ai-toggle, #harmoni-ai-toggle',
            title: 'Asistente de IA',
            text: 'Pregunta cualquier cosa sobre tu data de RRHH, leyes laborales peruanas, o pide generar reportes y analisis. Soporta OCR de imagenes y edicion de PDFs.',
            position: 'left',
        },
    ],
    current: 0,
    overlay: null,
    tooltip: null,
    _active: false,
    _previousStyles: [],
    _resizeHandler: null,
    _keyHandler: null,

    /**
     * Check if the tour should be shown (first visit).
     */
    shouldShow() {
        try {
            return !localStorage.getItem('harmoni_tour_done');
        } catch (e) {
            return false;
        }
    },

    /**
     * Start the tour. Optionally pass custom steps.
     */
    start(customSteps) {
        if (customSteps && customSteps.length > 0) {
            this.steps = customSteps;
        }
        if (this.steps.length === 0) return;

        this.current = 0;
        this._active = true;
        this._previousStyles = [];
        this._createOverlay();
        this._showStep();
        this._bindEvents();
    },

    /**
     * Move to the next step, or finish if on last step.
     */
    next() {
        this._cleanPreviousHighlight();
        this.current++;
        if (this.current >= this.steps.length) {
            this.complete();
            return;
        }
        this._showStep();
    },

    /**
     * Move to the previous step.
     */
    prev() {
        if (this.current <= 0) return;
        this._cleanPreviousHighlight();
        this.current--;
        this._showStep();
    },

    /**
     * Skip the tour entirely.
     */
    skip() {
        this.complete();
    },

    /**
     * Complete the tour and persist to localStorage.
     */
    complete() {
        try {
            localStorage.setItem('harmoni_tour_done', '1');
        } catch (e) {
            // ignore
        }
        this._cleanup();
    },

    /**
     * Reset tour state so it shows again.
     */
    reset() {
        try {
            localStorage.removeItem('harmoni_tour_done');
        } catch (e) {
            // ignore
        }
    },

    // ── Private methods ────────────────────────────────────────────

    _createOverlay() {
        // Remove any existing tour elements
        this._cleanup();

        // Overlay
        this.overlay = document.createElement('div');
        this.overlay.id = 'harmoni-tour-overlay';
        this.overlay.style.cssText = 'position:fixed;inset:0;z-index:10000;pointer-events:auto;';
        this.overlay.innerHTML = `
            <svg style="position:fixed;top:0;left:0;width:100%;height:100%;z-index:10000;">
                <defs>
                    <mask id="harmoni-tour-mask">
                        <rect x="0" y="0" width="100%" height="100%" fill="white"/>
                        <rect id="harmoni-tour-hole" x="0" y="0" width="0" height="0" rx="12" fill="black"/>
                    </mask>
                </defs>
                <rect x="0" y="0" width="100%" height="100%"
                      fill="rgba(0,0,0,0.55)" mask="url(#harmoni-tour-mask)"/>
            </svg>
        `;
        document.body.appendChild(this.overlay);

        // Tooltip container
        this.tooltip = document.createElement('div');
        this.tooltip.id = 'harmoni-tour-tooltip';
        this.tooltip.style.cssText = 'position:fixed;z-index:10002;background:#fff;border-radius:12px;padding:20px 24px;box-shadow:0 20px 60px rgba(0,0,0,.25),0 0 0 2px #0f766e;max-width:380px;min-width:280px;transition:opacity .2s,transform .2s;';
        document.body.appendChild(this.tooltip);
    },

    _showStep() {
        const step = this.steps[this.current];
        if (!step) { this.next(); return; }

        // Find target element (supports comma-separated selectors)
        const selectors = step.target.split(',').map(s => s.trim());
        let el = null;
        for (const sel of selectors) {
            el = document.querySelector(sel);
            if (el) break;
        }

        if (!el) {
            // Skip to next if target not found
            this.current++;
            if (this.current < this.steps.length) {
                this._showStep();
            } else {
                this.complete();
            }
            return;
        }

        // Scroll into view
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });

        // Save and apply highlight styles
        this._previousStyles.push({
            el: el,
            zIndex: el.style.zIndex,
            position: el.style.position,
            boxShadow: el.style.boxShadow,
            borderRadius: el.style.borderRadius,
        });

        el.style.position = el.style.position || 'relative';
        el.style.zIndex = '10001';
        el.style.boxShadow = '0 0 0 4px #0d9488, 0 0 20px rgba(13,148,136,.3)';
        el.style.borderRadius = '10px';

        // Update SVG hole
        const rect = el.getBoundingClientRect();
        const pad = 8;
        const hole = document.getElementById('harmoni-tour-hole');
        if (hole) {
            hole.setAttribute('x', rect.left - pad);
            hole.setAttribute('y', rect.top - pad);
            hole.setAttribute('width', rect.width + pad * 2);
            hole.setAttribute('height', rect.height + pad * 2);
        }

        // Build tooltip content
        const isFirst = this.current === 0;
        const isLast = this.current === this.steps.length - 1;
        const stepNum = this.current + 1;
        const totalSteps = this.steps.length;

        // Progress dots
        const dots = this.steps.map((_, i) =>
            `<div style="width:${i === this.current ? '16px' : '6px'};height:6px;border-radius:3px;background:${i === this.current ? '#0f766e' : '#e2e8f0'};transition:all .2s;"></div>`
        ).join('');

        this.tooltip.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="font-size:.7rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.5px;">
                    Paso ${stepNum} de ${totalSteps}
                </span>
                <div style="display:flex;gap:3px;">${dots}</div>
            </div>
            <h6 style="margin:0 0 6px;font-weight:700;font-size:.95rem;color:#0f172a;">${step.title}</h6>
            <p style="margin:0 0 16px;font-size:.85rem;color:#64748b;line-height:1.5;">${step.text}</p>
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <button onclick="HarmoniTour.skip()" style="background:none;border:none;color:#94a3b8;font-size:.8rem;cursor:pointer;padding:0;text-decoration:underline;">
                    Omitir tour
                </button>
                <div style="display:flex;gap:6px;">
                    ${!isFirst ? '<button onclick="HarmoniTour.prev()" style="padding:6px 12px;background:#f1f5f9;border:none;color:#475569;border-radius:8px;font-size:.82rem;cursor:pointer;font-weight:500;">Anterior</button>' : ''}
                    <button onclick="HarmoniTour.next()" style="padding:6px 16px;background:#0f766e;border:none;color:#fff;border-radius:8px;font-size:.82rem;cursor:pointer;font-weight:600;">
                        ${isLast ? '<i class="fas fa-check" style="font-size:.7rem;margin-right:4px;"></i>Entendido' : 'Siguiente'}
                    </button>
                </div>
            </div>
        `;

        // Position tooltip relative to target
        this._positionTooltip(rect, step.position || 'bottom');
    },

    _positionTooltip(targetRect, position) {
        const tip = this.tooltip;
        const pad = 16;
        let top, left;

        switch (position) {
            case 'right':
                top = targetRect.top;
                left = targetRect.right + pad;
                if (left + 400 > window.innerWidth) {
                    left = targetRect.left - 400 - pad;
                }
                break;
            case 'left':
                top = targetRect.top;
                left = targetRect.left - 400 - pad;
                if (left < 12) {
                    left = targetRect.right + pad;
                }
                break;
            case 'top':
                top = targetRect.top - 200 - pad;
                left = targetRect.left + targetRect.width / 2 - 190;
                break;
            case 'bottom':
            default:
                top = targetRect.bottom + pad;
                left = targetRect.left + targetRect.width / 2 - 190;
                if (top + 200 > window.innerHeight) {
                    top = targetRect.top - 200 - pad;
                }
                break;
        }

        // Clamp to viewport
        left = Math.max(12, Math.min(left, window.innerWidth - 400));
        top = Math.max(12, Math.min(top, window.innerHeight - 220));

        tip.style.top = top + 'px';
        tip.style.left = left + 'px';
    },

    _cleanPreviousHighlight() {
        while (this._previousStyles.length > 0) {
            const saved = this._previousStyles.pop();
            if (saved && saved.el) {
                saved.el.style.zIndex = saved.zIndex || '';
                saved.el.style.boxShadow = saved.boxShadow || '';
                saved.el.style.borderRadius = saved.borderRadius || '';
            }
        }
    },

    _bindEvents() {
        this._keyHandler = (e) => {
            if (!this._active) return;
            if (e.key === 'Escape') this.skip();
            else if (e.key === 'ArrowRight' || e.key === 'Enter') this.next();
            else if (e.key === 'ArrowLeft') this.prev();
        };
        document.addEventListener('keydown', this._keyHandler);

        this._resizeHandler = () => {
            if (this._active && this.current < this.steps.length) {
                this._showStep();
            }
        };
        window.addEventListener('resize', this._resizeHandler);
    },

    _cleanup() {
        this._active = false;
        this._cleanPreviousHighlight();

        if (this.overlay && this.overlay.parentNode) {
            this.overlay.parentNode.removeChild(this.overlay);
        }
        if (this.tooltip && this.tooltip.parentNode) {
            this.tooltip.parentNode.removeChild(this.tooltip);
        }
        this.overlay = null;
        this.tooltip = null;

        if (this._keyHandler) {
            document.removeEventListener('keydown', this._keyHandler);
            this._keyHandler = null;
        }
        if (this._resizeHandler) {
            window.removeEventListener('resize', this._resizeHandler);
            this._resizeHandler = null;
        }
    },
};

// Auto-trigger on first login (after page load)
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('harmoniSidebar') && HarmoniTour.shouldShow()) {
        setTimeout(() => HarmoniTour.start(), 2000);
    }
});
