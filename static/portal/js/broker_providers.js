/**
 * Transport Provider Management & Modal Controllers
 * Handles provider onboarding, editing, Paystack bank lookup & account verification,
 * specialization category chips, and fleet/driver modal drilldowns.
 */

// Static fallback directories for instant UI rendering without network wait
const BANK_DIRECTORIES = {
    'BANK': [
        { name: "Absa Bank Ghana Ltd", code: "030100" },
        { name: "Access Bank", code: "280100" },
        { name: "ADB Bank Limited", code: "080100" },
        { name: "ARB Apex Bank", code: "070101" },
        { name: "Bank of Africa Ghana", code: "210100" },
        { name: "CAL Bank Limited", code: "140100" },
        { name: "Consolidated Bank Ghana Limited", code: "340100" },
        { name: "Ecobank Ghana Limited", code: "130100" },
        { name: "FBNBank Ghana Limited", code: "200100" },
        { name: "Fidelity Bank Ghana Limited", code: "240100" },
        { name: "First Atlantic Bank Limited", code: "170100" },
        { name: "First National Bank Ghana Limited", code: "330100" },
        { name: "GCB Bank Limited", code: "040100" },
        { name: "Guaranty Trust Bank (Ghana) Limited", code: "230100" },
        { name: "National Investment Bank Limited", code: "050100" },
        { name: "OmniBSCI Bank", code: "360100" },
        { name: "Prudential Bank Limited", code: "180100" },
        { name: "Republic Bank (GH) Limited", code: "110100" },
        { name: "Société Générale Ghana Limited", code: "090100" },
        { name: "Stanbic Bank Ghana Limited", code: "190100" },
        { name: "Standard Chartered Bank Ghana Limited", code: "020100" },
        { name: "United Bank for Africa Ghana Limited", code: "060100" },
        { name: "Universal Merchant Bank Ghana Limited", code: "100100" },
        { name: "Zenith Bank Ghana", code: "120100" }
    ],
    'MOBILE_MONEY': [
        { name: "MTN Mobile Money", code: "MTN" },
        { name: "Vodafone / Telecel Cash", code: "VOD" },
        { name: "AirtelTigo Money", code: "ATL" }
    ]
};

// Cache dynamic bank list fetched from Paystack API
const dynamicBanksCache = {
    'BANK': null,
    'MOBILE_MONEY': null
};

function populateBanks(prefix, channel, selectedCode) {
    const select = document.getElementById(prefix + 'SettlementBank');
    const nameInput = document.getElementById(prefix + 'SettlementBankName');
    if (!select) return;

    const currentVal = selectedCode || select.value || '';
    select.innerHTML = '<option value="">-- Select Bank / Network --</option>';

    const list = dynamicBanksCache[channel] || BANK_DIRECTORIES[channel] || [];
    list.forEach(b => {
        const opt = document.createElement('option');
        opt.value = b.code;
        opt.textContent = b.name;
        if (currentVal && (b.code === currentVal || b.name === currentVal)) {
            opt.selected = true;
        }
        select.appendChild(opt);
    });

    // Set bank name hidden input
    const selOpt = select.options[select.selectedIndex];
    if (nameInput) {
        nameInput.value = (selOpt && selOpt.value) ? selOpt.textContent : '';
    }

    // Fetch live from Paystack if not cached yet
    const apiType = channel === 'MOBILE_MONEY' ? 'mobile_money' : 'ghipss';
    if (!dynamicBanksCache[channel]) {
        fetch('/api/paystack/banks/?type=' + apiType)
            .then(r => r.json())
            .then(data => {
                if (data && data.success && Array.isArray(data.banks) && data.banks.length > 0) {
                    dynamicBanksCache[channel] = data.banks;
                    const recheckVal = select.value || selectedCode || '';
                    select.innerHTML = '<option value="">-- Select Bank / Network --</option>';
                    data.banks.forEach(b => {
                        const opt = document.createElement('option');
                        opt.value = b.code;
                        opt.textContent = b.name;
                        if (recheckVal && (b.code === recheckVal || b.name === recheckVal)) {
                            opt.selected = true;
                        }
                        select.appendChild(opt);
                    });
                    const newSel = select.options[select.selectedIndex];
                    if (nameInput) {
                        nameInput.value = (newSel && newSel.value) ? newSel.textContent : '';
                    }
                }
            })
            .catch(() => { /* uses static fallback cleanly */ });
    }
}

function onPayoutChannelChanged(prefix, channel) {
    populateBanks(prefix, channel, '');
    const feedback = document.getElementById(prefix + 'ResolveFeedback');
    const acctNameInput = document.getElementById(prefix + 'AccountName');
    if (feedback) {
        feedback.className = 'hidden';
        feedback.innerHTML = '';
    }
    if (acctNameInput) acctNameInput.value = '';
}

function onBankSelectionChanged(prefix) {
    const select = document.getElementById(prefix + 'SettlementBank');
    const nameInput = document.getElementById(prefix + 'SettlementBankName');
    if (select && nameInput) {
        const selOpt = select.options[select.selectedIndex];
        nameInput.value = (selOpt && selOpt.value) ? selOpt.textContent : '';
    }
}

function verifyPaystackAccount(prefix) {
    const bankSelect = document.getElementById(prefix + 'SettlementBank');
    const accountInput = document.getElementById(prefix + 'AccountNumber');
    const feedback = document.getElementById(prefix + 'ResolveFeedback');
    const acctNameInput = document.getElementById(prefix + 'AccountName');
    const btn = document.getElementById(prefix + 'VerifyBtn');

    const bankCode = bankSelect ? bankSelect.value.trim() : '';
    const acctNum = accountInput ? accountInput.value.trim().replace(/\s+/g, '') : '';

    if (!bankCode) {
        if (feedback) {
            feedback.className = 'text-xs p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 block flex items-center gap-2';
            feedback.innerHTML = '<i data-lucide="alert-circle" class="w-4 h-4 shrink-0"></i><span>Please select a settlement bank or MoMo network first.</span>';
            if (window.lucide) lucide.createIcons();
        }
        return;
    }

    if (!acctNum) {
        if (feedback) {
            feedback.className = 'text-xs p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 block flex items-center gap-2';
            feedback.innerHTML = '<i data-lucide="alert-circle" class="w-4 h-4 shrink-0"></i><span>Please enter an account or Mobile Money number.</span>';
            if (window.lucide) lucide.createIcons();
        }
        return;
    }

    const origBtnHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="inline-block animate-spin mr-1">⟳</span> Checking...';
    if (feedback) {
        feedback.className = 'text-xs p-3 rounded-xl border border-amber-400/30 bg-amber-400/10 text-amber-300 block flex items-center gap-2';
        feedback.innerHTML = '<span class="inline-block animate-spin mr-1">⟳</span> <span>Verifying account details with Paystack...</span>';
    }

    fetch('/api/paystack/resolve-account/?account_number=' + encodeURIComponent(acctNum) + '&bank_code=' + encodeURIComponent(bankCode))
        .then(r => r.json())
        .then(data => {
            btn.disabled = false;
            btn.innerHTML = origBtnHtml;
            if (data.success && data.account_name) {
                if (acctNameInput) acctNameInput.value = data.account_name;
                if (feedback) {
                    feedback.className = 'text-xs p-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200 block space-y-1';
                    feedback.innerHTML = `
                        <div class="flex items-center gap-2 font-bold text-emerald-700 dark:text-emerald-400">
                            <i data-lucide="check-circle-2" class="w-4 h-4 shrink-0"></i>
                            <span>Paystack Account Verified</span>
                        </div>
                        <div class="text-emerald-950 dark:text-emerald-100 font-mono text-xs pl-6">
                            Account Holder: <strong class="font-black text-slate-900 dark:text-emerald-200" style="color: #064e3b !important;">${data.account_name}</strong>
                        </div>
                    `;
                    if (window.lucide) lucide.createIcons();
                }
            } else {
                if (feedback) {
                    feedback.className = 'text-xs p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300 block flex items-center gap-2';
                    feedback.innerHTML = '<i data-lucide="alert-circle" class="w-4 h-4 shrink-0"></i><span>' + (data.message || 'Could not verify account holder with Paystack.') + '</span>';
                    if (window.lucide) lucide.createIcons();
                }
            }
        })
        .catch(() => {
            btn.disabled = false;
            btn.innerHTML = origBtnHtml;
            if (feedback) {
                feedback.className = 'text-xs p-3 rounded-xl border border-amber-400/30 bg-amber-400/10 text-amber-300 block flex items-center gap-2';
                feedback.innerHTML = '<i data-lucide="alert-triangle" class="w-4 h-4 shrink-0"></i><span>Could not reach Paystack verification service. You may still save details.</span>';
                if (window.lucide) lucide.createIcons();
            }
        });
}

// Category Multi-Selection Chips
function toggleCategoryChip(prefix, catName, btn) {
    const hiddenInput = document.getElementById(prefix + 'Specializations');
    const countEl = document.getElementById(prefix + 'SelectedCatCount');
    if (!hiddenInput) return;

    let selected = hiddenInput.value
        ? hiddenInput.value.split(',').map(s => s.trim()).filter(Boolean)
        : [];

    const normalizedTarget = (catName || '').trim().toLowerCase();
    const existingIdx = selected.findIndex(s => s.toLowerCase() === normalizedTarget);

    if (existingIdx > -1) {
        selected.splice(existingIdx, 1);
        btn.classList.remove('bg-amber-400', 'text-[#080D18]', 'border-amber-400', 'font-bold');
        btn.classList.add('bg-white/5', 'text-slate-300', 'border-white/10', 'font-semibold');
    } else {
        selected.push((catName || '').trim());
        btn.classList.remove('bg-white/5', 'text-slate-300', 'border-white/10', 'font-semibold');
        btn.classList.add('bg-amber-400', 'text-[#080D18]', 'border-amber-400', 'font-bold');
    }

    hiddenInput.value = selected.join(', ');
    if (countEl) {
        countEl.textContent = selected.length + ' selected';
    }
}

function setCategoryChips(prefix, specializationsStr) {
    const hiddenInput = document.getElementById(prefix + 'Specializations');
    const countEl = document.getElementById(prefix + 'SelectedCatCount');
    if (hiddenInput) {
        hiddenInput.value = specializationsStr || '';
    }

    const selected = (specializationsStr || '')
        .split(',')
        .map(s => s.trim().toLowerCase())
        .filter(Boolean);

    const buttons = document.querySelectorAll('.cat-chip-' + prefix);
    let matchCount = 0;
    buttons.forEach(btn => {
        const cat = (btn.textContent || '').trim().toLowerCase();
        if (selected.includes(cat)) {
            btn.classList.remove('bg-white/5', 'text-slate-300', 'border-white/10', 'font-semibold');
            btn.classList.add('bg-amber-400', 'text-[#080D18]', 'border-amber-400', 'font-bold');
            matchCount++;
        } else {
            btn.classList.remove('bg-amber-400', 'text-[#080D18]', 'border-amber-400', 'font-bold');
            btn.classList.add('bg-white/5', 'text-slate-300', 'border-white/10', 'font-semibold');
        }
    });

    if (countEl) {
        countEl.textContent = matchCount + ' selected';
    }
}

// =========================================================================
// Onboard Provider Wizard State & Navigation
// =========================================================================
let currentOnboardStep = 1;

function goToOnboardStep(step) {
    if (step < 1 || step > 3) return;

    // Validate current step if moving forward
    if (step > currentOnboardStep) {
        if (!validateOnboardStep(currentOnboardStep)) {
            return;
        }
    }

    currentOnboardStep = step;

    // Update Step Panes & Nav Badges
    for (let s = 1; s <= 3; s++) {
        const pane = document.getElementById('onboardStepPane-' + s);
        const nav = document.getElementById('onboardStepNav-' + s);
        const badge = document.getElementById('onboardStepBadge-' + s);
        const label = document.getElementById('onboardStepLabel-' + s);

        if (pane) {
            if (s === step) {
                pane.classList.remove('hidden');
                pane.style.display = 'block';
            } else {
                pane.classList.add('hidden');
                pane.style.display = 'none';
            }
        }

        if (nav && badge && label) {
            if (s === step) {
                // Active step
                nav.className = 'group flex items-center gap-2 p-2 rounded-xl transition-all border border-amber-400/40 bg-amber-400/10 text-left cursor-pointer';
                badge.className = 'w-6 h-6 rounded-lg bg-amber-400 text-[#080D18] flex items-center justify-center font-black text-xs shrink-0 shadow-sm shadow-amber-400/30';
                badge.innerHTML = s;
                label.className = 'block text-[11px] font-bold text-amber-400 truncate';
            } else if (s < step) {
                // Completed step
                nav.className = 'group flex items-center gap-2 p-2 rounded-xl transition-all border border-emerald-500/30 bg-emerald-500/10 text-left cursor-pointer';
                badge.className = 'w-6 h-6 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center font-bold text-xs shrink-0';
                badge.innerHTML = '✓';
                label.className = 'block text-[11px] font-bold text-emerald-400 truncate';
            } else {
                // Upcoming step
                nav.className = 'group flex items-center gap-2 p-2 rounded-xl transition-all border border-white/5 bg-white/5 text-left cursor-pointer opacity-70 hover:opacity-100';
                badge.className = 'w-6 h-6 rounded-lg bg-white/10 text-slate-400 flex items-center justify-center font-bold text-xs shrink-0';
                badge.innerHTML = s;
                label.className = 'block text-[11px] font-bold text-slate-300 truncate';
            }
        }
    }

    // Update Progress Bar
    const progress = document.getElementById('onboardWizardProgress');
    if (progress) {
        const pct = step === 1 ? 33.33 : (step === 2 ? 66.66 : 100);
        progress.style.width = pct + '%';
    }

    // Update Footer Action Buttons
    const prevBtn = document.getElementById('onboardPrevBtn');
    const nextBtn = document.getElementById('onboardNextBtn');
    const nextText = document.getElementById('onboardNextBtnText');
    const submitBtn = document.getElementById('onboardSubmitBtn');

    if (prevBtn) {
        if (step > 1) {
            prevBtn.classList.remove('hidden');
        } else {
            prevBtn.classList.add('hidden');
        }
    }

    if (nextBtn && submitBtn) {
        if (step === 3) {
            nextBtn.classList.add('hidden');
            submitBtn.classList.remove('hidden');
        } else {
            nextBtn.classList.remove('hidden');
            submitBtn.classList.add('hidden');
            if (nextText) {
                nextText.textContent = step === 1 ? 'Next: Fleet & Scope' : 'Next: Portal & Payout';
            }
        }
    }

    // Scroll inner body back to top on step transition
    const scrollContainer = document.getElementById('onboardModalBody');
    if (scrollContainer) {
        scrollContainer.scrollTop = 0;
    }

    try {
        if (window.lucide && typeof lucide.createIcons === 'function') {
            lucide.createIcons();
        }
    } catch (e) {
        console.warn('Lucide icon refresh error:', e);
    }
}

function nextOnboardStep() {
    if (!validateOnboardStep(currentOnboardStep)) return;
    if (currentOnboardStep < 3) {
        goToOnboardStep(currentOnboardStep + 1);
    }
}

function prevOnboardStep() {
    if (currentOnboardStep > 1) {
        goToOnboardStep(currentOnboardStep - 1);
    }
}

function validateOnboardStep(step) {
    if (step === 1) {
        const companyName = document.getElementById('onboardCompanyName');
        const contactPerson = document.getElementById('onboardContactPerson');
        const email = document.getElementById('onboardEmail');
        const phone = document.getElementById('onboardPhone');

        const fields = [
            { el: companyName, name: 'Company Legal Name' },
            { el: contactPerson, name: 'Contact Person' },
            { el: email, name: 'Dispatch Email' },
            { el: phone, name: 'Phone Number' }
        ];

        for (const f of fields) {
            if (!f.el) continue;
            const val = (f.el.value || '').trim();
            if (!val) {
                f.el.focus();
                if (typeof f.el.reportValidity === 'function') {
                    f.el.reportValidity();
                }
                return false;
            }
            if (f.el.type === 'email' && typeof f.el.checkValidity === 'function' && !f.el.checkValidity()) {
                f.el.focus();
                f.el.reportValidity();
                return false;
            }
        }
        return true;
    }
    return true;
}

// 1. Onboard Modal
function openOnboardModal() {
    goToOnboardStep(1);
    populateBanks('onboard', 'BANK', '');
    setCategoryChips('onboard', '');
    const feedback = document.getElementById('onboardResolveFeedback');
    if (feedback) {
        feedback.className = 'hidden';
        feedback.innerHTML = '';
    }
    const modal = document.getElementById('onboardModal');
    if (modal) modal.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
}

function closeOnboardModal() {
    const modal = document.getElementById('onboardModal');
    if (modal) modal.classList.add('hidden');
}

// 2. Edit Modal
function openEditModal(provId) {
    const scriptEl = document.getElementById('prov-data-' + provId);
    if (!scriptEl) return;
    const data = JSON.parse(scriptEl.textContent);

    document.getElementById('editProviderId').value = data.id;
    document.getElementById('editModalHeaderTitle').textContent = 'Edit: ' + data.company_name;
    document.getElementById('editCompanyName').value = data.company_name;
    document.getElementById('editRegistrationNumber').value = data.registration_number;
    document.getElementById('editContactPerson').value = data.contact_person;
    document.getElementById('editEmail').value = data.email;
    document.getElementById('editPhone').value = data.phone;
    document.getElementById('editAddress').value = data.address;
    document.getElementById('editServiceArea').value = data.service_area;
    setCategoryChips('edit', data.specializations);
    document.getElementById('editStatus').value = data.status;
    document.getElementById('editRating').value = parseFloat(data.overall_rating) || 5.0;

    // Payout and Subaccount Fields
    const channel = data.payout_channel || 'BANK';
    if (channel === 'MOBILE_MONEY') {
        const momoRadio = document.getElementById('editChannelMomo');
        if (momoRadio) momoRadio.checked = true;
    } else {
        const bankRadio = document.getElementById('editChannelBank');
        if (bankRadio) bankRadio.checked = true;
    }

    populateBanks('edit', channel, data.settlement_bank);
    document.getElementById('editAccountNumber').value = data.account_number || '';
    document.getElementById('editAccountName').value = data.account_name || '';
    document.getElementById('editPercentageCharge').value = parseFloat(data.percentage_charge) || 0.0;

    // Subaccount Badge & Alert Banner
    const badge = document.getElementById('editSubaccountBadge');
    const alertBox = document.getElementById('editSubaccountAlert');
    const feedback = document.getElementById('editResolveFeedback');

    if (feedback) {
        if (data.account_name) {
            feedback.className = 'text-xs p-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200 block space-y-1';
            feedback.innerHTML = `
                <div class="flex items-center gap-2 font-bold text-emerald-700 dark:text-emerald-400">
                    <i data-lucide="check-circle-2" class="w-4 h-4 shrink-0"></i>
                    <span>Paystack Account Verified</span>
                </div>
                <div class="text-emerald-950 dark:text-emerald-100 font-mono text-xs pl-6">
                    Account Holder: <strong class="font-black text-slate-900 dark:text-emerald-200" style="color: #064e3b !important;">${data.account_name}</strong>
                </div>
            `;
        } else {
            feedback.className = 'hidden';
            feedback.innerHTML = '';
        }
    }

    if (badge && alertBox) {
        if (data.paystack_subaccount_status && data.paystack_subaccount_status.includes('Error:')) {
            badge.className = 'text-[10px] font-mono font-bold px-2.5 py-1 rounded-md bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/25';
            badge.textContent = 'Sync Required';
            alertBox.className = 'text-xs p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-950 dark:text-amber-200 block space-y-2';
            alertBox.innerHTML = `
                <div class="flex items-center justify-between gap-2">
                    <div class="flex items-center gap-2 font-bold text-amber-800 dark:text-amber-300">
                        <i data-lucide="alert-triangle" class="w-4 h-4 shrink-0 text-amber-600"></i>
                        <span>Paystack Subaccount Needs Live Sync</span>
                    </div>
                    <button type="button" onclick="syncCurrentEditProviderSubaccount()" id="modalAlertSyncBtn" 
                            class="px-2.5 py-1 rounded-lg bg-amber-400 hover:bg-amber-300 text-[#080D18] text-[11px] font-black transition-all flex items-center gap-1 active:scale-95 shadow-sm cursor-pointer shrink-0">
                        <i data-lucide="refresh-cw" class="w-3 h-3"></i>
                        <span>Sync Live Now</span>
                    </button>
                </div>
                <div class="text-[11px] pl-6 text-slate-700 dark:text-slate-300">
                    Previous Code: <strong class="font-mono text-slate-900 dark:text-white">${data.paystack_subaccount_code || 'None'}</strong>
                    • Status: <span class="text-rose-600 dark:text-rose-400 font-bold">${data.paystack_subaccount_status}</span>
                </div>
                <div class="text-[10px] pl-6 text-amber-900 dark:text-amber-200 leading-relaxed">
                    This subaccount code was created in Test mode and was not found on your active Live Paystack account. Click <strong>Sync Live Now</strong> above or <strong>Save Changes</strong> below to automatically provision this provider on Live Paystack.
                </div>
            `;
        } else if (data.paystack_subaccount_code) {
            badge.className = 'text-[10px] font-mono font-bold px-2.5 py-1 rounded-md bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/25';
            badge.textContent = data.paystack_subaccount_code;
            alertBox.className = 'text-xs p-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 block space-y-1';
            alertBox.innerHTML = `
                <div class="flex items-center gap-2 font-bold text-emerald-700 dark:text-emerald-400">
                    <i data-lucide="shield-check" class="w-4 h-4 shrink-0"></i>
                    <span>Paystack Subaccount Connected</span>
                </div>
                <div class="text-slate-700 dark:text-slate-300 text-[11px] pl-6">
                    Subaccount Code: <strong class="font-mono text-slate-900 dark:text-white">${data.paystack_subaccount_code}</strong>
                    ${data.paystack_subaccount_status ? ' • Status: ' + data.paystack_subaccount_status : ''}
                </div>
            `;
        } else if (data.settlement_bank && data.account_number) {
            badge.className = 'text-[10px] font-bold px-2.5 py-1 rounded-md bg-amber-400/15 text-amber-600 dark:text-amber-400 border border-amber-400/25';
            badge.textContent = 'Pending Approval';
            alertBox.className = 'text-xs p-3 rounded-xl border border-amber-400/20 bg-amber-400/10 text-amber-800 dark:text-amber-300 block';
            alertBox.innerHTML = `
                <div class="flex items-center gap-2 font-semibold text-amber-800 dark:text-amber-300">
                    <i data-lucide="clock" class="w-4 h-4 shrink-0"></i>
                    <span>Banking details saved. Paystack subaccount will be created when status is Approved.</span>
                </div>
            `;
        } else {
            badge.className = 'text-[10px] font-bold px-2.5 py-1 rounded-md bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-white/5';
            badge.textContent = 'No Subaccount';
            alertBox.className = 'hidden';
            alertBox.innerHTML = '';
        }
    }

    const editModal = document.getElementById('editModal');
    if (editModal) editModal.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
}

function closeEditModal() {
    const modal = document.getElementById('editModal');
    if (modal) modal.classList.add('hidden');
}

async function syncCurrentEditProviderSubaccount() {
    const provId = document.getElementById('editProviderId')?.value;
    if (!provId) return;

    const syncBtns = [
        document.getElementById('editModalSyncBtn'),
        document.getElementById('modalAlertSyncBtn')
    ].filter(Boolean);

    syncBtns.forEach(btn => {
        btn.disabled = true;
        btn.innerHTML = '<span class="inline-block animate-spin mr-1">⟳</span> Syncing...';
    });

    const formData = new FormData();
    formData.append('action', 'sync_provider_subaccount');
    formData.append('provider_id', provId);
    formData.append('ajax', '1');

    const csrfEl = document.querySelector('#editModal input[name="csrfmiddlewaretoken"]') || document.querySelector('input[name="csrfmiddlewaretoken"]');
    const csrfToken = csrfEl ? csrfEl.value : '';

    try {
        const response = await fetch(window.location.href, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            }
        });
        const result = await response.json();

        if (result.success) {
            // Update in-page script tag cache for this provider
            const scriptEl = document.getElementById('prov-data-' + provId);
            if (scriptEl) {
                try {
                    const d = JSON.parse(scriptEl.textContent);
                    d.paystack_subaccount_code = result.subaccount_code;
                    d.paystack_subaccount_status = result.subaccount_status || 'Active on Paystack';
                    if (result.account_name) d.account_name = result.account_name;
                    if (result.settlement_bank_name) d.settlement_bank_name = result.settlement_bank_name;
                    scriptEl.textContent = JSON.stringify(d);
                } catch (_) {}
            }

            // Re-render subaccount status in modal
            const badge = document.getElementById('editSubaccountBadge');
            const alertBox = document.getElementById('editSubaccountAlert');

            if (badge) {
                badge.className = 'text-[10px] font-mono font-bold px-2.5 py-1 rounded-md bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/25';
                badge.textContent = result.subaccount_code;
            }
            if (alertBox) {
                alertBox.className = 'text-xs p-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 block space-y-1';
                alertBox.innerHTML = `
                    <div class="flex items-center gap-2 font-bold text-emerald-700 dark:text-emerald-400">
                        <i data-lucide="shield-check" class="w-4 h-4 shrink-0"></i>
                        <span>Live Paystack Subaccount Connected</span>
                    </div>
                    <div class="text-slate-700 dark:text-slate-300 text-[11px] pl-6">
                        Subaccount Code: <strong class="font-mono text-slate-900 dark:text-white">${result.subaccount_code}</strong>
                        • Status: <span class="text-emerald-600 dark:text-emerald-400 font-semibold">${result.subaccount_status || 'Active on Paystack'}</span>
                    </div>
                `;
            }
            if (window.lucide) lucide.createIcons();

            syncBtns.forEach(btn => {
                btn.disabled = false;
                btn.innerHTML = '<i data-lucide="check" class="w-3 h-3 text-emerald-600 dark:text-emerald-400"></i><span>Synced Live</span>';
            });
            setTimeout(() => {
                syncBtns.forEach(btn => {
                    btn.innerHTML = '<i data-lucide="refresh-cw" class="w-3 h-3"></i><span>Sync Live Now</span>';
                    if (window.lucide) lucide.createIcons();
                });
            }, 3000);
        } else {
            alert('Paystack Live Sync notice: ' + (result.message || 'Subaccount sync could not be completed.'));
            syncBtns.forEach(btn => {
                btn.disabled = false;
                btn.innerHTML = '<i data-lucide="refresh-cw" class="w-3 h-3"></i><span>Retry Sync</span>';
                if (window.lucide) lucide.createIcons();
            });
        }
    } catch (err) {
        alert('Could not complete live sync request. Please verify network connectivity.');
        syncBtns.forEach(btn => {
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="refresh-cw" class="w-3 h-3"></i><span>Retry Sync</span>';
            if (window.lucide) lucide.createIcons();
        });
    }
}

// 3. Fleet & Driver Drilldown Modal
function openFleetModal(provId) {
    const scriptEl = document.getElementById('prov-data-' + provId);
    if (!scriptEl) return;
    const data = JSON.parse(scriptEl.textContent);

    document.getElementById('fleetModalTitle').textContent = data.company_name;
    document.getElementById('fleetModalSubtitle').textContent = 'Permit: ' + (data.registration_number || 'DVLA-GH-COMM-048') + ' • ' + (data.service_area || 'National Network');

    // Render Vehicles
    const vList = document.getElementById('fleetVehicleList');
    document.getElementById('fleetVehicleCount').textContent = data.vehicles.length + ' registered units';
    if (data.vehicles.length === 0) {
        vList.innerHTML = '<div class="p-4 rounded-xl surface-well text-xs text-slate-400 text-center">No vehicles registered yet by this provider.</div>';
    } else {
        vList.innerHTML = data.vehicles.map(v => `
            <div class="p-3.5 rounded-xl surface-well border border-white/5 flex items-center justify-between text-xs">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center font-bold text-xs">
                        ${v.seating_capacity}p
                    </div>
                    <div>
                        <span class="font-bold text-white">${v.year ? v.year + ' ' : ''}${v.make} ${v.model}</span>
                        <span class="text-[10px] text-slate-400 block font-mono">Plate: <strong class="text-amber-400">${v.registration_number}</strong> • ${v.category}</span>
                    </div>
                </div>
                <span class="px-2 py-0.5 rounded-md text-[10px] font-bold ${v.compliance_status.includes('Compliant') ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20' : 'bg-amber-400/15 text-amber-400 border border-amber-400/20'}">
                    ${v.compliance_status}
                </span>
            </div>
        `).join('');
    }

    // Render Drivers
    const dList = document.getElementById('fleetDriverList');
    document.getElementById('fleetDriverCount').textContent = data.drivers.length + ' vetted drivers';
    if (data.drivers.length === 0) {
        dList.innerHTML = '<div class="p-4 rounded-xl surface-well text-xs text-slate-400 text-center">No drivers registered yet by this provider.</div>';
    } else {
        dList.innerHTML = data.drivers.map(d => `
            <div class="p-3.5 rounded-xl surface-well border border-white/5 flex items-center justify-between text-xs">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center font-bold text-xs">
                        <i data-lucide="user" class="w-4 h-4"></i>
                    </div>
                    <div>
                        <span class="font-bold text-white">${d.full_name}</span>
                        <span class="text-[10px] text-slate-400 block font-mono">License: ${d.license_number} • ${d.phone_number}</span>
                    </div>
                </div>
                <span class="px-2 py-0.5 rounded-md text-[10px] font-bold ${d.compliance_status.includes('Compliant') ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20' : 'bg-amber-400/15 text-amber-400 border border-amber-400/20'}">
                    ${d.compliance_status}
                </span>
            </div>
        `).join('');
    }

    const modal = document.getElementById('fleetModal');
    if (modal) modal.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
}

function closeFleetModal() {
    const modal = document.getElementById('fleetModal');
    if (modal) modal.classList.add('hidden');
}

// 4. Delete Modal
function openDeleteModal(provId, name, vehCount, quoteCount) {
    document.getElementById('deleteProviderId').value = provId;
    document.getElementById('deleteProviderName').textContent = name;
    const msg = (vehCount > 0 || quoteCount > 0)
        ? `This provider has ${vehCount} vehicle(s) and ${quoteCount} quotation(s). To preserve transactional audits, this operator will be set to SUSPENDED.`
        : `This provider has no active fleet or quotations and will be permanently removed from the system.`;
    document.getElementById('deleteWarningMessage').innerHTML = msg;

    const modal = document.getElementById('deleteModal');
    if (modal) modal.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
}

function closeDeleteModal() {
    const modal = document.getElementById('deleteModal');
    if (modal) modal.classList.add('hidden');
}

// Global exports for inline HTML handler compatibility
window.goToOnboardStep = goToOnboardStep;
window.nextOnboardStep = nextOnboardStep;
window.prevOnboardStep = prevOnboardStep;
window.validateOnboardStep = validateOnboardStep;
window.populateBanks = populateBanks;
window.onPayoutChannelChanged = onPayoutChannelChanged;
window.onBankSelectionChanged = onBankSelectionChanged;
window.verifyPaystackAccount = verifyPaystackAccount;
window.toggleCategoryChip = toggleCategoryChip;
window.setCategoryChips = setCategoryChips;
window.openOnboardModal = openOnboardModal;
window.closeOnboardModal = closeOnboardModal;
window.openEditModal = openEditModal;
window.closeEditModal = closeEditModal;
window.openFleetModal = openFleetModal;
window.closeFleetModal = closeFleetModal;
window.openDeleteModal = openDeleteModal;
window.closeDeleteModal = closeDeleteModal;
window.syncCurrentEditProviderSubaccount = syncCurrentEditProviderSubaccount;

document.addEventListener('DOMContentLoaded', function() {
    populateBanks('onboard', 'BANK', '');

    // Dismiss on backdrop click or ESC key
    window.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeOnboardModal();
            closeEditModal();
            closeFleetModal();
            closeDeleteModal();
        }
    });
});
