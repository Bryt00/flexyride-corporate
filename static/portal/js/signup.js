/**
 * Multi-step Corporate Account Registration Wizard
 * Handles step navigation, HTML5 validation, summary updates, and password visibility.
 */
let currentStep = 1;
const totalSteps = 3;

function updateStepUI(step) {
    for (let i = 1; i <= totalSteps; i++) {
        const contentEl = document.getElementById(`step-content-${i}`);
        const badgeEl = document.getElementById(`step-badge-${i}`);
        const textEl = document.getElementById(`step-text-${i}`);

        if (!contentEl || !badgeEl || !textEl) continue;

        if (i === step) {
            contentEl.classList.remove('hidden');
            badgeEl.className = "w-10 h-10 rounded-full bg-[#8CC63F] text-[#0A0F1D] flex items-center justify-center text-xs font-black shadow-md shadow-[#8CC63F]/25 ring-4 ring-[#8CC63F]/25 transition-all duration-300";
            badgeEl.innerText = i;
            textEl.className = "text-xs font-black text-slate-900 mt-2 text-center tracking-tight";
        } else if (i < step) {
            contentEl.classList.add('hidden');
            badgeEl.className = "w-10 h-10 rounded-full bg-emerald-500 text-white flex items-center justify-center text-xs font-bold transition-all duration-300 shadow-sm";
            badgeEl.innerHTML = '<svg class="w-4 h-4 stroke-[3]" viewBox="0 0 24 24" fill="none" stroke="currentColor"><polyline points="20 6 9 17 4 12"></polyline></svg>';
            textEl.className = "text-xs font-bold text-slate-700 mt-2 text-center tracking-tight";
        } else {
            contentEl.classList.add('hidden');
            badgeEl.className = "w-10 h-10 rounded-full bg-slate-100 text-slate-400 border border-slate-200 flex items-center justify-center text-xs font-bold transition-all duration-300";
            badgeEl.innerText = i;
            textEl.className = "text-xs font-medium text-slate-400 mt-2 text-center tracking-tight";
        }
    }

    // Calculate progress percentage
    const progressPct = ((step - 1) / (totalSteps - 1)) * 100;
    const progressBar = document.getElementById('step-progress-bar');
    if (progressBar) {
        progressBar.style.width = `${progressPct}%`;
    }

    currentStep = step;
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

function validateStep(step) {
    const stepEl = document.getElementById(`step-content-${step}`);
    if (!stepEl) return true;

    const inputs = stepEl.querySelectorAll('input, select, textarea');
    let isValid = true;
    let firstInvalid = null;

    inputs.forEach(input => {
        // Check HTML5 validity
        if (!input.checkValidity()) {
            isValid = false;
            input.reportValidity();
            if (!firstInvalid) firstInvalid = input;
            input.classList.add('border-red-500', 'ring-2', 'ring-red-200');
        } else {
            input.classList.remove('border-red-500', 'ring-2', 'ring-red-200');
        }
    });

    if (firstInvalid) {
        firstInvalid.focus();
    }
    return isValid;
}

function updateReviewSummary() {
    const companyNameInput = document.querySelector('input[name="company_name"]');
    const companyEmailInput = document.querySelector('input[name="company_email"]');
    const firstNameInput = document.querySelector('input[name="first_name"]');
    const lastNameInput = document.querySelector('input[name="last_name"]');
    const adminPhoneInput = document.querySelector('input[name="admin_phone"]');

    const companyNameSpan = document.getElementById('summary-company-name');
    const companyEmailSpan = document.getElementById('summary-company-email');
    const adminNameSpan = document.getElementById('summary-admin-name');
    const adminPhoneSpan = document.getElementById('summary-admin-phone');

    if (companyNameSpan && companyNameInput) companyNameSpan.textContent = companyNameInput.value || '-';
    if (companyEmailSpan && companyEmailInput) companyEmailSpan.textContent = companyEmailInput.value || '-';
    if (adminNameSpan) {
        const fn = (firstNameInput && firstNameInput.value) || '';
        const ln = (lastNameInput && lastNameInput.value) || '';
        adminNameSpan.textContent = `${fn} ${ln}`.trim() || '-';
    }
    if (adminPhoneSpan && adminPhoneInput) adminPhoneSpan.textContent = adminPhoneInput.value || '-';
}

function nextStep() {
    if (validateStep(currentStep)) {
        if (currentStep < totalSteps) {
            if (currentStep === 2) {
                updateReviewSummary();
            }
            updateStepUI(currentStep + 1);
            scrollToCardTop();
        }
    }
}

function prevStep() {
    if (currentStep > 1) {
        updateStepUI(currentStep - 1);
        scrollToCardTop();
    }
}

function goToStep(targetStep) {
    // Can always go backwards
    if (targetStep < currentStep) {
        updateStepUI(targetStep);
        scrollToCardTop();
    } else if (targetStep > currentStep) {
        // Must validate current step before jumping forward
        if (validateStep(currentStep)) {
            if (targetStep === 3) updateReviewSummary();
            updateStepUI(targetStep);
            scrollToCardTop();
        }
    }
}

function scrollToCardTop() {
    const card = document.getElementById('signup-card');
    if (card) {
        window.scrollTo({
            top: card.getBoundingClientRect().top + window.pageYOffset - 40,
            behavior: 'smooth'
        });
    }
}

function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';
    btn.innerHTML = isPassword 
        ? '<i data-lucide="eye-off" class="w-4 h-4 text-slate-700"></i>' 
        : '<i data-lucide="eye" class="w-4 h-4 text-slate-400"></i>';
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

// Bind to window object for inline event handlers
window.updateStepUI = updateStepUI;
window.validateStep = validateStep;
window.updateReviewSummary = updateReviewSummary;
window.nextStep = nextStep;
window.prevStep = prevStep;
window.goToStep = goToStep;
window.scrollToCardTop = scrollToCardTop;
window.togglePasswordVisibility = togglePasswordVisibility;

document.addEventListener('DOMContentLoaded', function() {
    // Determine initial step based on any existing form validation errors
    const card = document.getElementById('signup-card');
    const initialStep = parseInt(card?.dataset?.initialStep || '1', 10);
    if (initialStep === 3) {
        updateReviewSummary();
    }
    updateStepUI(initialStep);
});
