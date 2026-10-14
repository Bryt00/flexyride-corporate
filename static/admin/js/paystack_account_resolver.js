/**
 * Paystack Live Bank & Account Resolver for Django Admin (ProviderCompany)
 * Supports both standard Django admin and Django Unfold layouts.
 */
(function() {
    'use strict';

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

    const dynamicBanks = { 'BANK': null, 'MOBILE_MONEY': null };

    document.addEventListener('DOMContentLoaded', function() {
        const payoutChannelEl = document.getElementById('id_payout_channel');
        const settlementBankEl = document.getElementById('id_settlement_bank');
        const settlementBankNameEl = document.getElementById('id_settlement_bank_name');
        const accountNumberEl = document.getElementById('id_account_number');
        const accountNameEl = document.getElementById('id_account_name');

        if (!accountNumberEl || !settlementBankEl) {
            return;
        }

        // Convert settlement_bank text input to select if not already
        let bankSelect = settlementBankEl;
        if (settlementBankEl.tagName.toLowerCase() !== 'select') {
            const select = document.createElement('select');
            select.id = settlementBankEl.id;
            select.name = settlementBankEl.name;
            select.className = settlementBankEl.className || 'vTextField';
            select.setAttribute('style', 'min-width: 260px; padding: 6px 12px; border-radius: 8px;');
            const initialVal = settlementBankEl.value;
            settlementBankEl.parentNode.replaceChild(select, settlementBankEl);
            bankSelect = select;
            bankSelect.dataset.initialValue = initialVal;
        }

        function populateBankList() {
            const channel = (payoutChannelEl && payoutChannelEl.value) || 'BANK';
            const currentVal = bankSelect.value || bankSelect.dataset.initialValue || '';
            const isLive = Boolean(dynamicBanks[channel]);
            const list = dynamicBanks[channel] || BANK_DIRECTORIES[channel] || [];

            bankSelect.innerHTML = '<option value="">-- Select Bank / Mobile Network ' + (isLive ? '(' + list.length + ' Live Banks)' : '') + ' --</option>';

            let matched = false;
            list.forEach(b => {
                const opt = document.createElement('option');
                opt.value = b.code;
                opt.textContent = b.name + ' (' + b.code + ')';
                if (currentVal && (b.code === currentVal || b.name === currentVal)) {
                    opt.selected = true;
                    matched = true;
                }
                bankSelect.appendChild(opt);
            });

            // If an existing record has a saved bank code not in the directory, retain it
            if (currentVal && !matched && currentVal !== '__custom__') {
                const customSavedOpt = document.createElement('option');
                customSavedOpt.value = currentVal;
                customSavedOpt.textContent = currentVal + ' (Custom / Saved Code)';
                customSavedOpt.selected = true;
                bankSelect.appendChild(customSavedOpt);
            }

            // Option to type a custom code manually
            const manualOpt = document.createElement('option');
            manualOpt.value = '__custom__';
            manualOpt.textContent = '✏️ Enter Other / Custom Bank Code...';
            bankSelect.appendChild(manualOpt);

            if (settlementBankNameEl && bankSelect.selectedIndex > 0 && bankSelect.value !== '__custom__') {
                const text = bankSelect.options[bankSelect.selectedIndex].textContent;
                settlementBankNameEl.value = text.replace(/\s\([^)]+\)$/, '');
            }

            // Fetch live bank directory dynamically from Paystack API
            const apiType = channel === 'MOBILE_MONEY' ? 'mobile_money' : 'ghipss';
            if (!dynamicBanks[channel]) {
                fetch('/api/paystack/banks/?type=' + apiType)
                    .then(r => r.json())
                    .then(data => {
                        if (data && data.success && Array.isArray(data.banks) && data.banks.length > 0) {
                            dynamicBanks[channel] = data.banks;
                            populateBankList();
                        }
                    })
                    .catch(() => {
                        // Offline or network error: continues seamlessly with static directory
                    });
            }
        }

        if (payoutChannelEl) {
            payoutChannelEl.addEventListener('change', populateBankList);
        }

        bankSelect.addEventListener('change', function() {
            if (bankSelect.value === '__custom__') {
                const customCode = prompt('Enter custom Paystack bank code or network ID:');
                if (customCode && customCode.trim()) {
                    const code = customCode.trim();
                    const newOpt = document.createElement('option');
                    newOpt.value = code;
                    newOpt.textContent = code + ' (Manual Code)';
                    newOpt.selected = true;
                    bankSelect.insertBefore(newOpt, bankSelect.lastChild);
                    if (settlementBankNameEl) {
                        settlementBankNameEl.value = code;
                    }
                } else {
                    bankSelect.selectedIndex = 0;
                }
            } else if (settlementBankNameEl && bankSelect.selectedIndex > 0) {
                const text = bankSelect.options[bankSelect.selectedIndex].textContent;
                settlementBankNameEl.value = text.replace(/\s\([^)]+\)$/, '');
            }
            clearStatus();
        });

        populateBankList();

        // Inject Verification UI beside Account Number
        const container = document.createElement('div');
        container.style.marginTop = '8px';
        container.style.display = 'flex';
        container.style.alignItems = 'center';
        container.style.gap = '10px';
        container.style.flexWrap = 'wrap';

        const verifyBtn = document.createElement('button');
        verifyBtn.type = 'button';
        verifyBtn.innerHTML = '⚡ Verify Account with Paystack';
        verifyBtn.style.padding = '6px 14px';
        verifyBtn.style.backgroundColor = '#10b981';
        verifyBtn.style.color = '#ffffff';
        verifyBtn.style.border = 'none';
        verifyBtn.style.borderRadius = '6px';
        verifyBtn.style.cursor = 'pointer';
        verifyBtn.style.fontWeight = '600';
        verifyBtn.style.fontSize = '12px';
        verifyBtn.style.transition = 'all 0.2s';

        const statusBadge = document.createElement('span');
        statusBadge.style.fontSize = '12px';
        statusBadge.style.fontWeight = '500';
        statusBadge.style.display = 'none';

        container.appendChild(verifyBtn);
        container.appendChild(statusBadge);

        if (accountNumberEl.parentNode) {
            accountNumberEl.parentNode.appendChild(container);
        }

        function clearStatus() {
            statusBadge.style.display = 'none';
            statusBadge.innerHTML = '';
        }

        verifyBtn.addEventListener('click', function() {
            const bankCode = bankSelect.value.trim();
            const acctNum = accountNumberEl.value.trim().replace(/\s+/g, '');

            if (!bankCode) {
                statusBadge.style.display = 'inline-block';
                statusBadge.style.color = '#ef4444';
                statusBadge.innerHTML = '⚠️ Please select a settlement bank first.';
                return;
            }

            if (!acctNum || acctNum.length < 5) {
                statusBadge.style.display = 'inline-block';
                statusBadge.style.color = '#ef4444';
                statusBadge.innerHTML = '⚠️ Please enter an account number.';
                return;
            }

            const origHtml = verifyBtn.innerHTML;
            verifyBtn.disabled = true;
            verifyBtn.innerHTML = '⏳ Querying Paystack...';
            statusBadge.style.display = 'inline-block';
            statusBadge.style.color = '#f59e0b';
            statusBadge.innerHTML = 'Resolving registered account details...';

            fetch('/api/paystack/resolve-account/?account_number=' + encodeURIComponent(acctNum) + '&bank_code=' + encodeURIComponent(bankCode))
                .then(r => r.json())
                .then(data => {
                    verifyBtn.disabled = false;
                    verifyBtn.innerHTML = origHtml;

                    if (data && data.success && data.account_name) {
                        if (accountNameEl) {
                            accountNameEl.value = data.account_name;
                        }
                        statusBadge.style.display = 'inline-block';
                        statusBadge.style.color = '#10b981';
                        statusBadge.innerHTML = '✓ <strong>Verified:</strong> ' + data.account_name;
                    } else {
                        statusBadge.style.display = 'inline-block';
                        statusBadge.style.color = '#ef4444';
                        statusBadge.innerHTML = '✕ ' + (data.message || 'Could not verify account with Paystack.');
                    }
                })
                .catch(err => {
                    verifyBtn.disabled = false;
                    verifyBtn.innerHTML = origHtml;
                    statusBadge.style.display = 'inline-block';
                    statusBadge.style.color = '#ef4444';
                    statusBadge.innerHTML = '✕ Network error querying Paystack verification API.';
                });
        });

        // Trigger verify button on Enter inside account number input
        accountNumberEl.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                verifyBtn.click();
            }
        });
    });
})();
