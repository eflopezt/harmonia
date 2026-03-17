/**
 * Harmoni — Notification center (poll + badge + toast)
 */
const HarmoniNotifs = {
    pollInterval: 60000,
    lastCount: 0,
    timer: null,

    init() {
        this.updateBadge();
        this.timer = setInterval(() => this.updateBadge(), this.pollInterval);
    },

    async updateBadge() {
        try {
            const r = await fetch('/comunicaciones/notificaciones/count/', {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            if (!r.ok) return;
            const data = await r.json();
            const count = data.unread || 0;
            const badge = document.getElementById('notif-badge');
            if (badge) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = count > 0 ? 'flex' : 'none';
            }
            if (count > this.lastCount && this.lastCount > 0) {
                this.showToast('Nueva notificacion', 'Tienes notificaciones sin leer');
            }
            this.lastCount = count;
        } catch (e) { /* offline or error */ }
    },

    showToast(title, body) {
        const toast = document.createElement('div');
        toast.className = 'harmoni-toast';
        toast.innerHTML = `<strong>${title}</strong><br><small>${body}</small>`;
        toast.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;background:#0f766e;color:#fff;padding:14px 20px;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.15);font-size:.85rem;max-width:300px;animation:slideUp .3s ease;cursor:pointer';
        toast.onclick = () => { window.location.href = '/comunicaciones/notificaciones/'; toast.remove(); };
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    },

    async markRead(id) {
        await fetch(`/comunicaciones/notificaciones/${id}/leida/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '', 'X-Requested-With': 'XMLHttpRequest' }
        });
        this.updateBadge();
    },

    async markAllRead() {
        await fetch('/comunicaciones/notificaciones/marcar-todas/', {
            method: 'POST',
            headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '', 'X-Requested-With': 'XMLHttpRequest' }
        });
        this.updateBadge();
    }
};
document.addEventListener('DOMContentLoaded', () => HarmoniNotifs.init());
