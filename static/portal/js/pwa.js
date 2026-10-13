// ==============================================================================
// FlexyRide Corporate - Progressive Web App Client Controller
// Handles Service Worker Registration, Install Banner, and Network State
// ==============================================================================

(function() {
    'use strict';

    let deferredPrompt = null;

    // 1. Service Worker Registration
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function() {
            navigator.serviceWorker.register('/sw.js', { scope: '/' })
                .then(function(registration) {
                    // Update check periodically
                    registration.onupdatefound = function() {
                        const installingWorker = registration.installing;
                        if (installingWorker) {
                            installingWorker.onstatechange = function() {
                                if (installingWorker.state === 'installed') {
                                    if (navigator.serviceWorker.controller) {
                                        console.log('[PWA] New update available; will activate upon next reload.');
                                    } else {
                                        console.log('[PWA] Content is cached for offline use.');
                                    }
                                }
                            };
                        }
                    };
                })
                .catch(function(err) {
                    console.warn('[PWA] Service Worker registration failed:', err);
                });
        });
    }

    // 2. Install Banner UI Component
    function createInstallBanner() {
        if (document.getElementById('pwa-install-banner')) return;

        const banner = document.createElement('div');
        banner.id = 'pwa-install-banner';
        banner.className = 'fixed bottom-5 right-5 z-50 max-w-sm w-[calc(100%-2.5rem)] sm:w-96 p-4 rounded-2xl bg-[#0A0F1D]/95 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/60 transform translate-y-8 opacity-0 transition-all duration-300 ease-out flex flex-col gap-3';
        
        banner.innerHTML = `
            <div class="flex items-start justify-between gap-3">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#8CC63F]/20 to-slate-800 border border-[#8CC63F]/30 flex items-center justify-center shrink-0">
                        <img src="/static/portal/img/logo_icon.png" alt="FlexyRide" class="w-6 h-6 object-contain">
                    </div>
                    <div>
                        <h4 class="text-sm font-bold text-white tracking-tight">Install FlexyRide App</h4>
                        <p class="text-xs text-slate-400 leading-snug">Fast dispatch access, booking alerts & offline capability.</p>
                    </div>
                </div>
                <button type="button" id="pwa-dismiss-btn" aria-label="Dismiss banner" class="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/5 transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <div class="flex items-center gap-2 pt-1">
                <button type="button" id="pwa-install-btn" class="flex-1 py-2 px-3 rounded-xl bg-[#8CC63F] hover:bg-[#A3D959] text-slate-950 font-bold text-xs tracking-wide transition-all shadow-md shadow-[#8CC63F]/20 active:scale-95 inline-flex items-center justify-center gap-1.5">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                    <span>Install Application</span>
                </button>
                <button type="button" id="pwa-later-btn" class="py-2 px-3 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 font-semibold text-xs border border-white/5 transition-colors">
                    Later
                </button>
            </div>
        `;

        document.body.appendChild(banner);

        // Animate entrance
        requestAnimationFrame(() => {
            banner.classList.remove('translate-y-8', 'opacity-0');
            banner.classList.add('translate-y-0', 'opacity-100');
        });

        // Event Handlers
        const installBtn = document.getElementById('pwa-install-btn');
        const dismissBtn = document.getElementById('pwa-dismiss-btn');
        const laterBtn = document.getElementById('pwa-later-btn');

        if (installBtn) {
            installBtn.addEventListener('click', async function() {
                if (!deferredPrompt) return;
                deferredPrompt.prompt();
                const choiceResult = await deferredPrompt.userChoice;
                if (choiceResult.outcome === 'accepted') {
                    console.log('[PWA] User accepted the install prompt');
                }
                deferredPrompt = null;
                dismissBanner(banner);
            });
        }

        if (dismissBtn) {
            dismissBtn.addEventListener('click', function() {
                sessionStorage.setItem('flexyride_pwa_dismissed', 'true');
                dismissBanner(banner);
            });
        }

        if (laterBtn) {
            laterBtn.addEventListener('click', function() {
                sessionStorage.setItem('flexyride_pwa_dismissed', 'true');
                dismissBanner(banner);
            });
        }
    }

    function dismissBanner(banner) {
        if (!banner) return;
        banner.classList.remove('translate-y-0', 'opacity-100');
        banner.classList.add('translate-y-8', 'opacity-0');
        setTimeout(() => banner.remove(), 300);
    }

    // 3. Listen for Install Prompt
    window.addEventListener('beforeinstallprompt', function(e) {
        e.preventDefault();
        deferredPrompt = e;

        // Show banner after brief pause so page loads smoothly
        if (!sessionStorage.getItem('flexyride_pwa_dismissed')) {
            setTimeout(createInstallBanner, 2000);
        }
    });

    // 4. App Installed Confirmation
    window.addEventListener('appinstalled', function() {
        console.log('[PWA] FlexyRide Corporate was installed successfully.');
        const banner = document.getElementById('pwa-install-banner');
        if (banner) dismissBanner(banner);
    });

    // 5. Offline & Online Toast Notifications
    function showNetworkToast(message, isOnline) {
        const existing = document.getElementById('pwa-network-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.id = 'pwa-network-toast';
        toast.className = `fixed top-5 right-5 z-50 px-4 py-2.5 rounded-xl border shadow-xl flex items-center gap-2.5 text-xs font-semibold backdrop-blur-md transition-all duration-300 ${
            isOnline 
                ? 'bg-emerald-950/90 text-emerald-300 border-emerald-500/30 shadow-emerald-950/40' 
                : 'bg-amber-950/90 text-amber-300 border-amber-500/30 shadow-amber-950/40'
        }`;
        
        toast.innerHTML = `
            <span class="w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'}"></span>
            <span>${message}</span>
        `;

        document.body.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('opacity-0', '-translate-y-2');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    window.addEventListener('offline', function() {
        showNetworkToast('Offline mode active. Cached data is available.', false);
    });

    window.addEventListener('online', function() {
        showNetworkToast('Connection restored. Operational data synced.', true);
    });
})();
