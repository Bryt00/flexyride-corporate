/**
 * Corporate Transport Request Booking Wizard
 * Manages 6-step form navigation, step validation, review summary generation,
 * and Google Places Autocomplete integration.
 */

let currentStep = 1;
const totalSteps = 6;

function getWizardConfig() {
    const form = document.getElementById('wizard-form');
    const initStep = form ? parseInt(form.dataset.initialStep || '1', 10) : 1;
    const serverMapsKey = (form?.dataset?.googleMapsApiKey || '').trim();
    const storedMapsKey = (sessionStorage.getItem('GOOGLE_MAPS_API_KEY') || '').trim();
    return {
        initialStep: isNaN(initStep) ? 1 : initStep,
        googleApiKey: serverMapsKey || storedMapsKey
    };
}

function updateWizardUI() {
    // Update progress bar
    const progressPercentage = ((currentStep - 1) / (totalSteps - 1)) * 100;
    const progressBar = document.getElementById('wizard-progress-bar');
    if (progressBar) {
        progressBar.style.width = `${progressPercentage}%`;
    }

    for (let i = 1; i <= totalSteps; i++) {
        const content = document.getElementById(`step-content-${i}`);
        const indicator = document.getElementById(`step-nav-${i}`);
        if (!content || !indicator) continue;

        const icon = indicator.querySelector('.icon-container');
        const label = indicator.querySelector('span');

        if (i === currentStep) {
            content.classList.remove('hidden');
            indicator.className = "step-indicator flex flex-col items-center gap-3 cursor-pointer group text-[#8CC63F]";
            if (icon) icon.className = "icon-container w-11 h-11 rounded-2xl bg-[#8CC63F] text-[#0A0F1D] flex items-center justify-center font-black shadow-lg shadow-[#8CC63F]/30 transform scale-110 transition-all duration-300";
            if (label) label.className = "hidden sm:inline text-[#8CC63F] font-black transition-colors duration-300 drop-shadow-md";
        } else if (i < currentStep) {
            content.classList.add('hidden');
            indicator.className = "step-indicator flex flex-col items-center gap-3 cursor-pointer group text-emerald-400";
            if (icon) icon.className = "icon-container w-10 h-10 rounded-2xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold transition-all duration-300 group-hover:bg-emerald-500/30";
            if (label) label.className = "hidden sm:inline text-emerald-400 font-bold transition-colors duration-300";
        } else {
            content.classList.add('hidden');
            indicator.className = "step-indicator flex flex-col items-center gap-3 cursor-pointer group text-slate-500";
            if (icon) icon.className = "icon-container w-10 h-10 rounded-2xl surface-well text-slate-500 flex items-center justify-center font-bold transition-all duration-300 group-hover:bg-white/10 group-hover:text-slate-300";
            if (label) label.className = "hidden sm:inline text-slate-500 font-medium transition-colors duration-300 group-hover:text-slate-300";
        }
    }

    // Button visibility
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const submitBtn = document.getElementById('submit-btn');

    if (prevBtn) {
        if (currentStep === 1) {
            prevBtn.classList.add('hidden');
        } else {
            prevBtn.classList.remove('hidden');
        }
    }

    if (nextBtn && submitBtn) {
        if (currentStep === totalSteps) {
            nextBtn.classList.add('hidden');
            submitBtn.classList.remove('hidden');
            populateReviewSummary();
        } else {
            nextBtn.classList.remove('hidden');
            submitBtn.classList.add('hidden');
        }
    }
}

function populateReviewSummary() {
    const journeyTypeSelect = document.querySelector('[name="journey_type"]');
    const journeyTypeText = journeyTypeSelect ? (journeyTypeSelect.options[journeyTypeSelect.selectedIndex]?.text || 'One-Way Journey') : 'One-Way Journey';
    const journeyTypeVal = journeyTypeSelect ? journeyTypeSelect.value : '';

    const pickup = document.querySelector('[name="pickup_address"]')?.value || 'Not specified';
    const dest = document.querySelector('[name="destination_address"]')?.value || 'Not specified';
    const dept = document.querySelector('[name="departure_datetime"]')?.value || 'Not specified';
    const returnDate = document.querySelector('[name="return_datetime"]')?.value || '';
    const airportName = document.querySelector('[name="airport_name"]')?.value || '';
    const flightNum = document.querySelector('[name="flight_number"]')?.value || '';
    const flightTime = document.querySelector('[name="flight_datetime"]')?.value || '';

    const name = document.querySelector('[name="full_name"]')?.value || 'Not specified';
    const phone = document.querySelector('[name="phone_number"]')?.value || 'Not provided';
    const email = document.querySelector('[name="email"]')?.value || 'Not provided';
    const count = document.querySelector('[name="passenger_count"]')?.value || '1';

    const catSelect = document.querySelector('[name="requested_vehicle_category"]');
    const catText = catSelect ? (catSelect.options[catSelect.selectedIndex]?.text || 'Standard Sedan') : 'Standard Sedan';

    const accessibility = document.querySelector('[name="accessibility_required"]')?.checked || false;
    const executive = document.querySelector('[name="executive_vehicle_required"]')?.checked || false;
    const notes = document.querySelector('[name="additional_stops_notes"]')?.value || '';

    // 1. Journey & Route
    const jtEl = document.getElementById('review-journey-type');
    if (jtEl) jtEl.textContent = journeyTypeText;

    const pEl = document.getElementById('review-pickup');
    if (pEl) pEl.textContent = pickup;

    const dEl = document.getElementById('review-dest');
    if (dEl) dEl.textContent = dest;

    const dpEl = document.getElementById('review-departure');
    if (dpEl) dpEl.textContent = dept.replace('T', ' at ');

    // Return Date (if Return journey)
    const retContainer = document.getElementById('review-return-container');
    const retEl = document.getElementById('review-return');
    if (retContainer && retEl) {
        if (journeyTypeVal === 'RETURN' || returnDate) {
            retContainer.classList.remove('hidden');
            retEl.textContent = returnDate ? returnDate.replace('T', ' at ') : 'Not specified';
        } else {
            retContainer.classList.add('hidden');
        }
    }

    // Airport / Flight Container
    const flightContainer = document.getElementById('review-flight-container');
    const airportEl = document.getElementById('review-airport');
    const flightNumEl = document.getElementById('review-flight-num');
    const flightTimeEl = document.getElementById('review-flight-time');
    const flightTimeRow = document.getElementById('review-flight-time-row');

    if (flightContainer) {
        const isAirport = journeyTypeVal === 'AIRPORT_TRANSFER' || journeyTypeVal === 'AIRPORT_MEET_GREET' || flightNum || airportName;
        if (isAirport) {
            flightContainer.classList.remove('hidden');
            if (airportEl) airportEl.textContent = airportName || 'International Airport';
            if (flightNumEl) flightNumEl.textContent = flightNum || 'Not specified';
            if (flightTimeEl && flightTimeRow) {
                if (flightTime) {
                    flightTimeRow.classList.remove('hidden');
                    flightTimeEl.textContent = flightTime.replace('T', ' at ');
                } else {
                    flightTimeRow.classList.add('hidden');
                }
            }
        } else {
            flightContainer.classList.add('hidden');
        }
    }

    // 2. Passenger Details
    const passEl = document.getElementById('review-passenger');
    if (passEl) passEl.textContent = name;

    const phEl = document.getElementById('review-phone');
    if (phEl) phEl.textContent = phone;

    const emEl = document.getElementById('review-email');
    if (emEl) emEl.textContent = email;

    const cntEl = document.getElementById('review-count');
    if (cntEl) cntEl.textContent = `${count} Passenger${parseInt(count) > 1 ? 's' : ''}`;

    // 3. Vehicle Specification
    const catEl = document.getElementById('review-category');
    if (catEl) catEl.textContent = catText;

    // 4. Requirements & Notes
    const accessBadge = document.getElementById('review-badge-accessibility');
    if (accessBadge) {
        if (accessibility) {
            accessBadge.className = 'px-2.5 py-1 rounded-lg text-[11px] font-bold bg-blue-500/20 text-blue-400 flex items-center gap-1 border border-blue-500/30';
            accessBadge.innerHTML = `<i data-lucide="accessibility" class="w-3.5 h-3.5"></i> Wheelchair / Ramp Requested`;
        } else {
            accessBadge.className = 'px-2.5 py-1 rounded-lg text-[11px] font-bold bg-white/5 text-slate-400 flex items-center gap-1';
            accessBadge.innerHTML = `<i data-lucide="accessibility" class="w-3.5 h-3.5"></i> Standard Vehicle`;
        }
    }

    const execBadge = document.getElementById('review-badge-executive');
    if (execBadge) {
        if (executive) {
            execBadge.className = 'px-2.5 py-1 rounded-lg text-[11px] font-bold bg-amber-500/20 text-amber-400 flex items-center gap-1 border border-amber-500/30';
            execBadge.innerHTML = `<i data-lucide="crown" class="w-3.5 h-3.5"></i> VIP / Executive Attire Requested`;
        } else {
            execBadge.className = 'px-2.5 py-1 rounded-lg text-[11px] font-bold bg-white/5 text-slate-400 flex items-center gap-1';
            execBadge.innerHTML = `<i data-lucide="crown" class="w-3.5 h-3.5"></i> Standard Chauffeur`;
        }
    }

    const notesEl = document.getElementById('review-notes');
    if (notesEl) {
        notesEl.textContent = notes.trim() ? notes : 'None specified';
    }

    // Re-render Lucide icons inside Step 6
    if (window.lucide) {
        const step6 = document.getElementById('step-content-6');
        if (step6) lucide.createIcons({ root: step6 });
    }
}

function goToStep(step) {
    if (step < currentStep) {
        currentStep = step;
        updateWizardUI();
    } else if (step === currentStep + 1) {
        nextStep();
    } else if (step <= totalSteps) {
        // Validate all steps up to the target step
        let canAdvance = true;
        for (let s = 1; s < step; s++) {
            const pane = document.getElementById(`step-content-${s}`);
            if (!pane) continue;
            const inputs = pane.querySelectorAll('input, select, textarea');
            for (let input of inputs) {
                if (input.type === 'hidden') continue;
                if (!input.checkValidity()) {
                    canAdvance = false;
                    currentStep = s;
                    updateWizardUI();
                    input.focus();
                    return;
                }
            }
        }
        if (canAdvance) {
            currentStep = step;
            updateWizardUI();
        }
    }
}

function validateAllSteps() {
    for (let step = 1; step <= 5; step++) {
        const pane = document.getElementById(`step-content-${step}`);
        if (!pane) continue;
        const inputs = pane.querySelectorAll('input, select, textarea');
        for (let input of inputs) {
            if (input.type === 'hidden') continue;
            if (!input.checkValidity()) {
                currentStep = step;
                updateWizardUI();
                input.focus();
                input.classList.add('ring-2', 'ring-red-500', 'bg-red-500/10');

                const existingErr = input.parentElement.querySelector('.custom-error-text') || 
                                    input.parentElement.parentElement.querySelector('.custom-error-text');
                if (!existingErr) {
                    const errorMsg = document.createElement('p');
                    errorMsg.className = 'custom-error-text text-[11px] text-rose-400 font-bold mt-1.5 flex items-center gap-1';
                    errorMsg.innerHTML = `<i data-lucide="alert-circle" class="w-3 h-3"></i> ${input.validationMessage || "This field is required."}`;
                    if (input.parentElement.classList.contains('relative') || input.parentElement.classList.contains('autocomplete-wrapper')) {
                        input.parentElement.parentElement.appendChild(errorMsg);
                    } else {
                        input.parentElement.appendChild(errorMsg);
                    }
                    if (window.lucide) {
                        lucide.createIcons({ root: errorMsg });
                    }
                }
                return false;
            }
        }
    }
    return true;
}

function nextStep() {
    if (currentStep < totalSteps) {
        const currentPane = document.getElementById(`step-content-${currentStep}`);
        if (!currentPane) return;
        const inputs = currentPane.querySelectorAll('input, select, textarea');
        let isValid = true;
        
        // Clear previous custom error states
        currentPane.querySelectorAll('.custom-error-text').forEach(el => el.remove());
        inputs.forEach(input => input.classList.remove('ring-2', 'ring-red-500', 'bg-red-500/10'));
        
        for (let input of inputs) {
            // Ignore hidden fields for validation
            if (input.type === 'hidden') continue;
            
            if (!input.checkValidity()) {
                isValid = false;
                
                // Highlight the invalid input
                input.classList.add('ring-2', 'ring-red-500', 'bg-red-500/10');
                
                // Create and append custom error message
                const errorMsg = document.createElement('p');
                errorMsg.className = 'custom-error-text text-[11px] text-rose-400 font-bold mt-1.5 flex items-center gap-1';
                errorMsg.innerHTML = `<i data-lucide="alert-circle" class="w-3 h-3"></i> ${input.validationMessage || "This field is required."}`;
                
                // Handle wrapper cases (like the relative div for autocomplete)
                if (input.parentElement.classList.contains('relative') || input.parentElement.classList.contains('autocomplete-wrapper')) {
                    input.parentElement.parentElement.appendChild(errorMsg);
                } else {
                    input.parentElement.appendChild(errorMsg);
                }
                
                // Re-initialize icons for the newly added error message
                if (window.lucide) {
                    lucide.createIcons({ root: errorMsg });
                }
            }
        }
        
        if (!isValid) return;

        currentStep++;
        updateWizardUI();
    }
}

function prevStep() {
    if (currentStep > 1) {
        currentStep--;
        updateWizardUI();
    }
}

// --- Location Autocomplete with Google Places API ---
function setupGooglePlacesAutocomplete(inputId, latId, lngId) {
    const input = document.getElementById(inputId);
    const latInput = document.getElementById(latId);
    const lngInput = document.getElementById(lngId);
    if (!input) return;

    if (window.google && window.google.maps && window.google.maps.places) {
        const autocomplete = new google.maps.places.Autocomplete(input, {
            fields: ['formatted_address', 'geometry', 'name']
        });

        autocomplete.addListener('place_changed', function() {
            const place = autocomplete.getPlace();
            if (!place.geometry || !place.geometry.location) return;

            if (latInput) latInput.value = place.geometry.location.lat().toFixed(6);
            if (lngInput) lngInput.value = place.geometry.location.lng().toFixed(6);
        });
    }
}

window.initGooglePlaces = function() {
    setupGooglePlacesAutocomplete('id_pickup_address', 'id_pickup_latitude', 'id_pickup_longitude');
    setupGooglePlacesAutocomplete('id_destination_address', 'id_destination_latitude', 'id_destination_longitude');
};

// Global exports for inline HTML handler compatibility
window.goToStep = goToStep;
window.nextStep = nextStep;
window.prevStep = prevStep;
window.updateWizardUI = updateWizardUI;
window.populateReviewSummary = populateReviewSummary;
window.validateAllSteps = validateAllSteps;

document.addEventListener('DOMContentLoaded', () => {
    const config = getWizardConfig();
    currentStep = config.initialStep;
    updateWizardUI();

    const form = document.getElementById('wizard-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!validateAllSteps()) {
                e.preventDefault();
                return false;
            }

            const submitBtn = document.getElementById('submit-btn');
            if (submitBtn) {
                submitBtn.classList.add('opacity-75', 'pointer-events-none');
                submitBtn.innerHTML = `
                    <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-[#0A0F1D] inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Submitting Request...</span>
                `;
                // Non-blocking disable after submit event finishes to prevent browser aborting form POST
                setTimeout(() => {
                    submitBtn.disabled = true;
                }, 0);
            }
        });
    }

    if (config.googleApiKey) {
        if (window.google && window.google.maps && window.google.maps.places) {
            window.initGooglePlaces();
        } else {
            const script = document.createElement('script');
            script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(config.googleApiKey)}&libraries=places&callback=initGooglePlaces`;
            script.async = true;
            script.defer = true;
            document.head.appendChild(script);
        }
    }
});
