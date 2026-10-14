/**
 * FlexyRide Corporate - Cookie & Privacy Preference Manager
 * Manages user cookie choices with localStorage persistence, cookie sync, and granular categories.
 */
(function() {
    'use strict';

    const STORAGE_KEY = 'flexyride_cookie_consent';
    const COOKIE_NAME = 'flexyride_cookie_consent';

    const DEFAULT_PREFERENCES = {
        necessary: true,
        functional: true,
        analytics: false,
        marketing: false,
        version: '1.0',
        timestamp: null
    };

    function getSavedConsent() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (raw) return JSON.parse(raw);
        } catch (e) {
            console.warn('[CookieConsent] Failed to parse local storage consent', e);
        }
        return null;
    }

    function saveConsent(consent) {
        consent.necessary = true; // Always mandatory
        consent.timestamp = new Date().toISOString();
        consent.version = '1.0';

        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(consent));
        } catch (e) {
            console.warn('[CookieConsent] Failed to write localStorage', e);
        }

        // Set 1-year browser cookie for server awareness
        const cookieVal = encodeURIComponent(JSON.stringify(consent));
        document.cookie = `${COOKIE_NAME}=${cookieVal}; path=/; max-age=31536000; SameSite=Lax`;

        // Dispatch window event for analytics / tag managers
        window.dispatchEvent(new CustomEvent('cookie_consent_updated', { detail: consent }));

        hideBanner();
        hideModal();
        updateTriggerBadge(true);
    }

    function showBanner() {
        const banner = document.getElementById('cookie-consent-banner');
        if (!banner) return;
        banner.classList.remove('hidden', 'translate-y-full', 'opacity-0');
        banner.classList.add('translate-y-0', 'opacity-100');
    }

    function hideBanner() {
        const banner = document.getElementById('cookie-consent-banner');
        if (!banner) return;
        banner.classList.add('translate-y-full', 'opacity-0');
        setTimeout(() => {
            banner.classList.add('hidden');
        }, 400);
    }

    function showModal() {
        const modal = document.getElementById('cookie-preference-modal');
        if (!modal) return;
        
        // Sync toggles with current consent
        const current = getSavedConsent() || DEFAULT_PREFERENCES;
        const funcToggle = document.getElementById('cookie-toggle-functional');
        const anaToggle = document.getElementById('cookie-toggle-analytics');
        const mktToggle = document.getElementById('cookie-toggle-marketing');

        if (funcToggle) funcToggle.checked = !!current.functional;
        if (anaToggle) anaToggle.checked = !!current.analytics;
        if (mktToggle) mktToggle.checked = !!current.marketing;

        modal.classList.remove('hidden');
        modal.classList.add('flex');
    }

    function hideModal() {
        const modal = document.getElementById('cookie-preference-modal');
        if (!modal) return;
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }

    function updateTriggerBadge(visible) {
        const badge = document.getElementById('cookie-reopen-btn');
        if (!badge) return;
        if (visible) {
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }

    // Public API on window
    window.openCookiePreferences = function() {
        hideBanner();
        showModal();
    };

    window.getCookieConsent = function() {
        return getSavedConsent();
    };

    // Initialize on DOM load
    document.addEventListener('DOMContentLoaded', function() {
        const saved = getSavedConsent();

        // Bind banner actions
        const acceptAllBtn = document.getElementById('cookie-accept-all');
        const necessaryOnlyBtn = document.getElementById('cookie-necessary-only');
        const customizeBtn = document.getElementById('cookie-customize');
        const modalAcceptAllBtn = document.getElementById('cookie-modal-accept-all');
        const modalSaveBtn = document.getElementById('cookie-modal-save');
        const modalCloseBtn = document.getElementById('cookie-modal-close');
        const reopenBtn = document.getElementById('cookie-reopen-btn');

        if (acceptAllBtn) {
            acceptAllBtn.addEventListener('click', function() {
                saveConsent({
                    necessary: true,
                    functional: true,
                    analytics: true,
                    marketing: true
                });
            });
        }

        if (necessaryOnlyBtn) {
            necessaryOnlyBtn.addEventListener('click', function() {
                saveConsent({
                    necessary: true,
                    functional: false,
                    analytics: false,
                    marketing: false
                });
            });
        }

        if (customizeBtn) {
            customizeBtn.addEventListener('click', function() {
                showModal();
            });
        }

        if (modalAcceptAllBtn) {
            modalAcceptAllBtn.addEventListener('click', function() {
                saveConsent({
                    necessary: true,
                    functional: true,
                    analytics: true,
                    marketing: true
                });
            });
        }

        if (modalSaveBtn) {
            modalSaveBtn.addEventListener('click', function() {
                const funcToggle = document.getElementById('cookie-toggle-functional');
                const anaToggle = document.getElementById('cookie-toggle-analytics');
                const mktToggle = document.getElementById('cookie-toggle-marketing');

                saveConsent({
                    necessary: true,
                    functional: funcToggle ? funcToggle.checked : true,
                    analytics: anaToggle ? anaToggle.checked : false,
                    marketing: mktToggle ? mktToggle.checked : false
                });
            });
        }

        if (modalCloseBtn) {
            modalCloseBtn.addEventListener('click', function() {
                hideModal();
            });
        }

        if (reopenBtn) {
            reopenBtn.addEventListener('click', function() {
                showModal();
            });
        }

        // Check if banner should sprout
        if (!saved) {
            // Polite sprout delay
            setTimeout(showBanner, 700);
            updateTriggerBadge(false);
        } else {
            updateTriggerBadge(true);
        }

        // Initialize icons if lucide is present
        if (window.lucide) {
            window.lucide.createIcons();
        }
    });
})();
