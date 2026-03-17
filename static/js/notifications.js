/**
 * Harmoni ERP - Notifications Module
 *
 * - Poll /comunicaciones/notificaciones/json/ every 60s
 * - Update badge number in navbar bell icon (#notifBadge)
 * - Show toast popup for new notifications (bottom-right, auto-dismiss 5s)
 * - Click toast -> navigate to notification target
 *
 * Integrates with the existing notification widget in base.html.
 */
const HarmoniNotifs = {
    pollInterval: 60000,
    toastDuration: 5000,
    lastCount: 0,
    lastIds: new Set(),
    timer: null,
    toastContainer: null,

    /**
     * Initialize: create toast container, first fetch, start polling.
     */
    init() {
        // Create toast container
        this.toastContainer = document.getElementById('harmoniNotifToasts');
        if (!this.toastContainer) {
            this.toastContainer = document.createElement('div');
            this.toastContainer.id = 'harmoniNotifToasts';
            Object.assign(this.toastContainer.style, {
                position: 'fixed',
                bottom: '20px',
                right: '20px',
                zIndex: '9999',
                display: 'flex',
                flexDirection: 'column-reverse',
                gap: '8px',
                maxWidth: '380px',
                pointerEvents: 'none',
            });
            document.body.appendChild(this.toastContainer);
        }

        // Load previous IDs
        try {
            const stored = localStorage.getItem('harmoni_notif_ids');
            if (stored) this.lastIds = new Set(JSON.parse(stored));
        } catch (e) { /* ignore */ }

        // Initial fetch (silent — no toasts)
        this.fetchNotifications(true);

        // Start polling
        this.timer = setInterval(() => this.fetchNotifications(false), this.pollInterval);

        // Refresh when tab becomes visible
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) this.fetchNotifications(false);
        });
    },

    /**
     * Fetch notifications from the server.
     */
    async fetchNotifications(isInitial) {
        try {
            const r = await fetch('/comunicaciones/notificaciones/json/', {
                headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin',
            });
            if (!r.ok) return;
            const data = await r.json();
            const items = data.items || [];
            const count = data.count || 0;

            // Update badge
            this.updateBadge(count);

            // Detect new unread notifications and show toasts
            if (!isInitial && items.length > 0) {
                const newItems = items.filter(n => !n.leida && !this.lastIds.has(n.id));
                newItems.slice(0, 3).forEach(n => this.showToast(n));
            }

            // Save current IDs
            this.lastIds = new Set(items.map(n => n.id));
            this.lastCount = count;
            try {
                localStorage.setItem('harmoni_notif_ids', JSON.stringify([...this.lastIds]));
            } catch (e) { /* ignore */ }
        } catch (e) {
            // Try fallback count endpoint
            this.fetchCount();
        }
    },

    /**
     * Fallback: fetch just the count.
     */
    async fetchCount() {
        try {
            const r = await fetch('/comunicaciones/notificaciones/count/', {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (!r.ok) return;
            const data = await r.json();
            const count = data.unread || data.count || 0;
            this.updateBadge(count);

            if (count > this.lastCount && this.lastCount > 0) {
                this.showToast({
                    asunto: 'Nueva notificacion',
                    icono: 'fa-bell',
                    color: '#0f766e',
                    tiempo: 'Ahora',
                    url: '/comunicaciones/notificaciones/',
                });
            }
            this.lastCount = count;
        } catch (e) { /* offline or error — silent */ }
    },

    /**
     * Update the badge number in the navbar bell icon.
     */
    updateBadge(count) {
        // Primary badge (#notifBadge from base.html)
        const badge = document.getElementById('notifBadge');
        if (badge) {
            badge.textContent = count > 99 ? '99+' : (count > 9 ? '9+' : count);
            badge.style.display = count > 0 ? 'block' : 'none';
        }
        // Legacy badge (#notif-badge)
        const legacyBadge = document.getElementById('notif-badge');
        if (legacyBadge) {
            legacyBadge.textContent = count > 99 ? '99+' : count;
            legacyBadge.style.display = count > 0 ? 'flex' : 'none';
        }
    },

    /**
     * Show a toast notification in the bottom-right corner.
     */
    showToast(notification) {
        if (!this.toastContainer) return;

        const toast = document.createElement('div');
        toast.className = 'harmoni-notif-toast';
        const iconColor = notification.color || '#0f766e';
        const iconClass = notification.icono || 'fa-bell';

        Object.assign(toast.style, {
            pointerEvents: 'auto',
            background: '#fff',
            borderRadius: '12px',
            boxShadow: '0 8px 30px rgba(0,0,0,.15), 0 0 0 1px rgba(0,0,0,.05)',
            padding: '14px 16px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px',
            cursor: 'pointer',
            opacity: '0',
            transform: 'translateX(40px)',
            transition: 'opacity .3s, transform .3s',
            maxWidth: '380px',
            minWidth: '280px',
        });

        toast.innerHTML = `
            <div style="width:34px;height:34px;border-radius:50%;background:${iconColor}15;color:${iconColor};
                        display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:.8rem;">
                <i class="fas ${this._escapeHtml(iconClass)}"></i>
            </div>
            <div style="flex:1;min-width:0;">
                <div style="font-size:.83rem;font-weight:600;color:#0f172a;line-height:1.3;margin-bottom:2px;">
                    ${this._escapeHtml(notification.asunto || 'Nueva notificacion')}
                </div>
                <div style="font-size:.72rem;color:#94a3b8;">
                    ${this._escapeHtml(notification.tiempo || 'Ahora')}
                </div>
            </div>
            <button style="background:none;border:none;color:#cbd5e1;cursor:pointer;font-size:.9rem;
                          padding:0;line-height:1;flex-shrink:0;" title="Cerrar">
                <i class="fas fa-times"></i>
            </button>
        `;

        // Click handler
        toast.addEventListener('click', (e) => {
            if (e.target.closest('button')) {
                this._removeToast(toast);
                return;
            }
            const url = notification.url;
            if (url && url !== '#') {
                this.markRead(notification.id, url);
            }
            this._removeToast(toast);
        });

        this.toastContainer.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0)';
        });

        // Auto-dismiss after 5 seconds
        setTimeout(() => this._removeToast(toast), this.toastDuration);
    },

    /**
     * Remove a toast with animation.
     */
    _removeToast(toast) {
        if (!toast || !toast.parentNode) return;
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        setTimeout(() => {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 300);
    },

    /**
     * Mark a notification as read and optionally redirect.
     */
    async markRead(id, redirectUrl) {
        const csrf = this._getCsrfToken();
        try {
            await fetch(`/comunicaciones/notificaciones/${id}/leer/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrf },
                credentials: 'same-origin',
            });
        } catch (e) { /* ignore */ }
        if (redirectUrl && redirectUrl !== '#') {
            window.location.href = redirectUrl;
        }
        this.fetchNotifications(true);
    },

    /**
     * Mark all notifications as read.
     */
    async markAllRead() {
        const csrf = this._getCsrfToken();
        try {
            await fetch('/comunicaciones/notificaciones/leer-todas/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin',
            });
        } catch (e) { /* ignore */ }
        this.fetchNotifications(true);
    },

    /**
     * Force refresh notifications.
     */
    refresh() {
        this.fetchNotifications(false);
    },

    /**
     * Stop polling.
     */
    stop() {
        if (this.timer) clearInterval(this.timer);
        this.timer = null;
    },

    // ── Helpers ─────────────────────────────────────────────────

    _getCsrfToken() {
        const match = document.cookie.split(';').map(c => c.trim())
            .find(c => c.startsWith('csrftoken='));
        if (match) return match.split('=')[1];
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        return input ? input.value : '';
    },

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    },
};

// Auto-init when DOM is ready
document.addEventListener('DOMContentLoaded', () => HarmoniNotifs.init());
