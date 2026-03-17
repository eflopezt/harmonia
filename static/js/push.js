/**
 * Harmoni ERP — Push Notifications Client
 * Solicita permiso, suscribe al usuario y envía la suscripción al backend.
 */

(function() {
  'use strict';

  const PUSH_SUBSCRIBE_URL = '/api/push/subscribe/';
  const PUSH_UNSUBSCRIBE_URL = '/api/push/unsubscribe/';

  // VAPID public key — set this from your Django settings
  // Generate with: python -c "from py_vapid import Vapid; v=Vapid(); v.generate_keys(); print(v.public_key)"
  let VAPID_PUBLIC_KEY = null;

  const HarmoniPush = {
    /**
     * Initialize push notifications.
     * Call this after the page loads and the user is authenticated.
     */
    async init(options = {}) {
      if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.log('[Push] Push notifications not supported');
        return false;
      }

      if (options.vapidPublicKey) {
        VAPID_PUBLIC_KEY = options.vapidPublicKey;
      }

      // Check current permission state
      const permission = Notification.permission;
      if (permission === 'denied') {
        console.log('[Push] Notifications blocked by user');
        return false;
      }

      return true;
    },

    /**
     * Request notification permission from the user.
     * Returns 'granted', 'denied', or 'default'.
     */
    async requestPermission() {
      if (!('Notification' in window)) return 'denied';

      const permission = await Notification.requestPermission();
      console.log('[Push] Permission:', permission);

      if (permission === 'granted') {
        await this.subscribe();
      }

      return permission;
    },

    /**
     * Subscribe to push notifications and send subscription to backend.
     */
    async subscribe() {
      try {
        const registration = await navigator.serviceWorker.ready;

        // Check existing subscription
        let subscription = await registration.pushManager.getSubscription();

        if (!subscription && VAPID_PUBLIC_KEY) {
          // Create new subscription
          const applicationServerKey = this._urlBase64ToUint8Array(VAPID_PUBLIC_KEY);
          subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: applicationServerKey,
          });
          console.log('[Push] New subscription created');
        }

        if (subscription) {
          // Send subscription to backend
          await this._sendSubscriptionToServer(subscription);
          return subscription;
        }
      } catch (error) {
        console.error('[Push] Subscription failed:', error);
      }
      return null;
    },

    /**
     * Unsubscribe from push notifications.
     */
    async unsubscribe() {
      try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();

        if (subscription) {
          await subscription.unsubscribe();
          await this._removeSubscriptionFromServer(subscription);
          console.log('[Push] Unsubscribed successfully');
          return true;
        }
      } catch (error) {
        console.error('[Push] Unsubscribe failed:', error);
      }
      return false;
    },

    /**
     * Check if user is currently subscribed.
     */
    async isSubscribed() {
      try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();
        return !!subscription;
      } catch (error) {
        return false;
      }
    },

    /**
     * Show a local notification (for testing or in-app use).
     */
    async showLocalNotification(title, body, options = {}) {
      if (Notification.permission !== 'granted') {
        console.warn('[Push] No permission for notifications');
        return;
      }

      const registration = await navigator.serviceWorker.ready;
      registration.showNotification(title, {
        body: body,
        icon: '/static/images/icon-192.png',
        badge: '/static/images/favicon.svg',
        tag: options.tag || 'harmoni-local',
        data: { url: options.url || '/' },
        vibrate: [200, 100, 200],
        ...options,
      });
    },

    // ── Private helpers ──────────────────────────────────────────

    /**
     * Send push subscription to the Django backend.
     */
    async _sendSubscriptionToServer(subscription) {
      const csrfToken = this._getCsrfToken();
      try {
        const response = await fetch(PUSH_SUBSCRIBE_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({
            subscription: subscription.toJSON(),
            user_agent: navigator.userAgent,
          }),
        });

        if (response.ok) {
          console.log('[Push] Subscription sent to server');
        } else {
          console.warn('[Push] Server rejected subscription:', response.status);
        }
      } catch (error) {
        // Backend endpoint might not exist yet — that is OK
        console.log('[Push] Could not send subscription to server (endpoint may not exist yet)');
      }
    },

    /**
     * Remove push subscription from the Django backend.
     */
    async _removeSubscriptionFromServer(subscription) {
      const csrfToken = this._getCsrfToken();
      try {
        await fetch(PUSH_UNSUBSCRIBE_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({
            endpoint: subscription.endpoint,
          }),
        });
      } catch (error) {
        console.log('[Push] Could not remove subscription from server');
      }
    },

    /**
     * Convert VAPID key from base64 URL to Uint8Array.
     */
    _urlBase64ToUint8Array(base64String) {
      const padding = '='.repeat((4 - base64String.length % 4) % 4);
      const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');
      const rawData = atob(base64);
      const outputArray = new Uint8Array(rawData.length);
      for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
      }
      return outputArray;
    },

    /**
     * Get CSRF token from cookie or DOM.
     */
    _getCsrfToken() {
      // Try meta tag first
      const meta = document.querySelector('meta[name="csrf-token"]');
      if (meta) return meta.getAttribute('content');

      // Try hidden input
      const input = document.querySelector('[name=csrfmiddlewaretoken]');
      if (input) return input.value;

      // Try cookie
      const cookies = document.cookie.split(';');
      for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') return value;
      }
      return '';
    },
  };

  // Expose globally
  window.HarmoniPush = HarmoniPush;
})();
