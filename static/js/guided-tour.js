/**
 * Harmoni — Guided tour for first-time users
 */
const HarmoniTour = {
    steps: [
        { target: '.sidebar', title: 'Menu lateral', text: 'Aqui encuentras todos los modulos: Personal, Asistencia, Nominas, y mas.', position: 'right' },
        { target: '.topbar-h1', title: 'Pagina actual', text: 'El titulo te indica en que seccion estas.', position: 'bottom' },
        { target: '#harmoni-ai-toggle, .ai-toggle', title: 'IA Asistente', text: 'Pregunta cualquier cosa sobre RRHH, leyes laborales o tu data. Haz clic para abrir el chat.', position: 'left' },
        { target: '#notif-bell, .notif-bell', title: 'Notificaciones', text: 'Aqui veras alertas, aprobaciones pendientes y comunicados.', position: 'bottom' },
    ],
    current: 0,
    overlay: null,

    shouldShow() {
        return !localStorage.getItem('harmoni_tour_done');
    },

    start() {
        if (!this.shouldShow()) return;
        this.current = 0;
        this.createOverlay();
        this.showStep();
    },

    createOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.id = 'tour-overlay';
        this.overlay.style.cssText = 'position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.5);transition:opacity .3s';
        document.body.appendChild(this.overlay);
    },

    showStep() {
        const step = this.steps[this.current];
        const el = document.querySelector(step.target);
        if (!el) { this.next(); return; }

        // Remove old tooltip
        document.getElementById('tour-tooltip')?.remove();

        // Highlight element
        el.style.position = el.style.position || 'relative';
        el.style.zIndex = '10001';
        el.style.boxShadow = '0 0 0 4px #06b6d4, 0 0 20px rgba(6,182,212,.3)';
        el.style.borderRadius = '8px';

        // Create tooltip
        const rect = el.getBoundingClientRect();
        const tip = document.createElement('div');
        tip.id = 'tour-tooltip';
        tip.style.cssText = `position:fixed;z-index:10002;background:#fff;border-radius:12px;padding:20px;box-shadow:0 12px 40px rgba(0,0,0,.2);max-width:300px;font-family:Inter,sans-serif`;
        tip.innerHTML = `
            <div style="font-size:.7rem;color:#0f766e;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Paso ${this.current + 1} de ${this.steps.length}</div>
            <div style="font-size:1rem;font-weight:700;color:#0f172a;margin-bottom:6px">${step.title}</div>
            <div style="font-size:.85rem;color:#64748b;margin-bottom:16px;line-height:1.5">${step.text}</div>
            <div style="display:flex;gap:8px;justify-content:flex-end">
                <button onclick="HarmoniTour.skip()" style="padding:6px 14px;border:1px solid #e2e8f0;background:#fff;border-radius:6px;font-size:.8rem;cursor:pointer;color:#64748b">Saltar</button>
                <button onclick="HarmoniTour.next()" style="padding:6px 14px;background:#0f766e;color:#fff;border:none;border-radius:6px;font-size:.8rem;cursor:pointer;font-weight:600">${this.current < this.steps.length - 1 ? 'Siguiente' : 'Entendido'}</button>
            </div>`;

        // Position
        if (step.position === 'bottom') { tip.style.top = (rect.bottom + 12) + 'px'; tip.style.left = rect.left + 'px'; }
        else if (step.position === 'right') { tip.style.top = rect.top + 'px'; tip.style.left = (rect.right + 12) + 'px'; }
        else { tip.style.top = rect.top + 'px'; tip.style.right = (window.innerWidth - rect.left + 12) + 'px'; }

        document.body.appendChild(tip);
    },

    next() {
        // Clean previous
        const prev = this.steps[this.current];
        const prevEl = document.querySelector(prev?.target);
        if (prevEl) { prevEl.style.zIndex = ''; prevEl.style.boxShadow = ''; }

        this.current++;
        if (this.current >= this.steps.length) { this.end(); return; }
        this.showStep();
    },

    skip() { this.end(); },

    end() {
        localStorage.setItem('harmoni_tour_done', '1');
        document.getElementById('tour-overlay')?.remove();
        document.getElementById('tour-tooltip')?.remove();
        this.steps.forEach(s => {
            const el = document.querySelector(s.target);
            if (el) { el.style.zIndex = ''; el.style.boxShadow = ''; }
        });
    }
};
document.addEventListener('DOMContentLoaded', () => setTimeout(() => HarmoniTour.start(), 2000));
