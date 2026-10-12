/**
 * Passenger Live Journey Tracking & Google Maps Telemetry
 * Handles passenger real-time route visualization, driver marker positioning,
 * interactive 5-star trip rating, and dynamic API key prompts.
 */

const darkMapStyles = [
    { elementType: "geometry", stylers: [{ color: "#0A0F1D" }] },
    { elementType: "labels.text.stroke", stylers: [{ color: "#0A0F1D" }] },
    { elementType: "labels.text.fill", stylers: [{ color: "#74829c" }] },
    { featureType: "administrative.locality", elementType: "labels.text.fill", stylers: [{ color: "#cbd5e1" }] },
    { featureType: "poi", elementType: "labels.text.fill", stylers: [{ color: "#64748b" }] },
    { featureType: "poi.park", elementType: "geometry", stylers: [{ color: "#0f172a" }] },
    { featureType: "road", elementType: "geometry", stylers: [{ color: "#1e293b" }] },
    { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#2d3748" }] },
    { featureType: "transit", elementType: "geometry", stylers: [{ color: "#161f33" }] },
    { featureType: "water", elementType: "geometry", stylers: [{ color: "#050811" }] },
    { featureType: "water", elementType: "labels.text.fill", stylers: [{ color: "#475569" }] }
];

function getMapsApiKey() {
    const body = document.body;
    const serverKey = (body ? body.dataset.googleMapsApiKey || '' : '').trim();
    const storedKey = (sessionStorage.getItem('GOOGLE_MAPS_API_KEY') || '').trim();
    return serverKey || storedKey;
}

function renderApiKeyPrompt() {
    const mapContainer = document.getElementById('map');
    if (!mapContainer) return;

    mapContainer.innerHTML = `
        <div class="w-full h-full flex flex-col items-center justify-center p-6 text-center bg-[#070B14]/90 backdrop-blur-md relative z-20">
            <div class="max-w-md w-full p-6 rounded-2xl bg-[#0A0F1D] shadow-2xl space-y-4">
                <div class="w-12 h-12 mx-auto rounded-xl bg-[#8CC63F]/15 flex items-center justify-center text-[#8CC63F]">
                    <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"></polygon>
                        <line x1="9" y1="3" x2="9" y2="18"></line>
                        <line x1="15" y1="6" x2="15" y2="21"></line>
                    </svg>
                </div>
                <div>
                    <h3 class="text-sm font-black text-white">Google Maps API Key Required</h3>
                    <p class="text-xs text-slate-400 mt-1 leading-relaxed">
                        Enter your Google Maps API key to activate passenger live GPS telemetry.
                    </p>
                </div>
                <div class="space-y-2">
                    <input id="runtimePassengerMapKey" type="password" placeholder="AIzaSy..." class="w-full bg-[#10172A] rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-[#8CC63F]/40" />
                    <button onclick="saveAndLoadPassengerKey()" class="w-full py-2.5 bg-[#8CC63F] hover:bg-[#73A233] text-[#0A0F1D] font-black rounded-xl text-xs transition-all shadow-md active:scale-95">
                        Activate Live Google Map
                    </button>
                </div>
                <p class="text-[11px] text-slate-500">
                    Or configure <code class="text-slate-300 font-mono">GOOGLE_MAPS_API_KEY</code> in your Django settings.
                </p>
            </div>
        </div>
    `;
}

function saveAndLoadPassengerKey() {
    const input = document.getElementById('runtimePassengerMapKey');
    const key = (input ? input.value : '').trim();
    if (!key) {
        alert('Please paste a valid Google Maps API Key.');
        return;
    }
    sessionStorage.setItem('GOOGLE_MAPS_API_KEY', key);
    loadGoogleMapsScript(key);
}

window.initPassengerMap = function() {
    const mapContainer = document.getElementById('map');
    if (!mapContainer) return;
    mapContainer.innerHTML = '';

    // Airport to Destination Hotel
    const pickupCoords = { lat: 5.6052, lng: -0.1681 };
    const destCoords = { lat: 5.5539, lng: -0.1989 };
    const driverCoords = { lat: 5.5780, lng: -0.1800 };

    const map = new google.maps.Map(mapContainer, {
        center: driverCoords,
        zoom: 13,
        styles: darkMapStyles,
        disableDefaultUI: true,
        zoomControl: true
    });

    function createSvgMarker(url, size) {
        return {
            url: url,
            scaledSize: new google.maps.Size(size, size),
            anchor: new google.maps.Point(size / 2, size / 2)
        };
    }

    const pickupIconSvg = 'data:image/svg+xml;utf-8,' + encodeURIComponent(`
        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">
            <circle cx="14" cy="14" r="12" fill="#8CC63F" stroke="#ffffff" stroke-width="3"/>
            <circle cx="14" cy="14" r="4" fill="#ffffff"/>
        </svg>
    `);

    const destIconSvg = 'data:image/svg+xml;utf-8,' + encodeURIComponent(`
        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">
            <circle cx="14" cy="14" r="12" fill="#EF4444" stroke="#ffffff" stroke-width="3"/>
            <circle cx="14" cy="14" r="4" fill="#ffffff"/>
        </svg>
    `);

    const carIconSvg = 'data:image/svg+xml;utf-8,' + encodeURIComponent(`
        <svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 44 44">
            <circle cx="22" cy="22" r="20" fill="#0A0F1D" stroke="#8CC63F" stroke-width="3"/>
            <path d="M14 26l2-6h12l2 6" stroke="#8CC63F" stroke-width="2" fill="none" stroke-linecap="round"/>
            <rect x="13" y="24" width="18" height="6" rx="2" fill="#8CC63F"/>
            <circle cx="17" cy="30" r="2" fill="#0A0F1D"/>
            <circle cx="27" cy="30" r="2" fill="#0A0F1D"/>
        </svg>
    `);

    new google.maps.Marker({
        position: pickupCoords,
        map: map,
        title: 'Pickup (Airport)',
        icon: createSvgMarker(pickupIconSvg, 28)
    });

    new google.maps.Marker({
        position: destCoords,
        map: map,
        title: 'Destination (Hotel / Office)',
        icon: createSvgMarker(destIconSvg, 28)
    });

    const driverMarker = new google.maps.Marker({
        position: driverCoords,
        map: map,
        title: 'Driver Live Telemetry Location',
        icon: createSvgMarker(carIconSvg, 44),
        zIndex: 999
    });

    // Simulated Telemetry Ping Pulsing
    let step = 0;
    setInterval(() => {
        step += 0.0001;
        driverMarker.setPosition({
            lat: 5.5780 - (step * 0.4),
            lng: -0.1800 - (step * 0.3)
        });
    }, 2500);

    const routeCoordinates = [
        pickupCoords,
        { lat: 5.5950, lng: -0.1740 },
        { lat: 5.5870, lng: -0.1770 },
        driverCoords,
        { lat: 5.5680, lng: -0.1890 },
        destCoords
    ];

    const routePath = new google.maps.Polyline({
        path: routeCoordinates,
        geodesic: true,
        strokeColor: '#8CC63F',
        strokeOpacity: 0.9,
        strokeWeight: 4
    });
    routePath.setMap(map);

    const bounds = new google.maps.LatLngBounds();
    routeCoordinates.forEach(c => bounds.extend(c));
    map.fitBounds(bounds, 60);
};

function loadGoogleMapsScript(key) {
    if (window.google && window.google.maps) {
        window.initPassengerMap();
        return;
    }
    const existingScript = document.getElementById('google-maps-passenger-sdk');
    if (existingScript) existingScript.remove();

    const script = document.createElement('script');
    script.id = 'google-maps-passenger-sdk';
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}&libraries=geometry,places&callback=initPassengerMap`;
    script.async = true;
    script.defer = true;
    script.onerror = function() {
        alert('Failed to load Google Maps SDK. Please check your API key.');
        renderApiKeyPrompt();
    };
    document.head.appendChild(script);
}

// Global exports
window.saveAndLoadPassengerKey = saveAndLoadPassengerKey;
window.renderApiKeyPrompt = renderApiKeyPrompt;

document.addEventListener('DOMContentLoaded', () => {
    if (window.lucide) {
        lucide.createIcons();
    }
    const googleApiKey = getMapsApiKey();
    if (googleApiKey) {
        loadGoogleMapsScript(googleApiKey);
    } else {
        renderApiKeyPrompt();
    }
});
