document.addEventListener('htmx:load', function(event) {
    const container = event.target;

    // Initialize chat tab functionality
    initializeChatTab(container);
});

function initializeChatTab(container) {
    const addLanguagePairButton = container.querySelector('#add-language-pair');
    const proposeMissingRulesButton = container.querySelector('#propose-missing-rules');
    const generateTableBtn = container.querySelector('#generate-table-btn');
    const languagePairDropdown = container.querySelector('#language-pair-dropdown');
    const languagePairSelect = container.querySelector('#language-pair-select');

    if (!addLanguagePairButton || !proposeMissingRulesButton || !languagePairDropdown || !languagePairSelect) {
        return;
    }

    if (generateTableBtn) {
        generateTableBtn.addEventListener('click', async () => {
            const ruleId = generateTableBtn.dataset.ruleId;
            if (!ruleId) return;
            const languagePairId = languagePairSelect?.value;
            if (!languagePairId) return;

            generateTableBtn.className = 'hidden-button';
            
            const loader = document.getElementById('loader');
            loader.classList.add('htmx-request');

            try {
                const data = await generateTable(ruleId, languagePairId);
                const editTableBtn = document.getElementById('edit-table-btn');
                const checkTablesBeforeSaveBtn = document.getElementById('check-tables-before-save');
                if (editTableBtn && checkTablesBeforeSaveBtn) {
                    editTableBtn.classList.remove('hidden-button');
                    checkTablesBeforeSaveBtn.classList.remove('hidden-button');
                }
                displayGeneratedTables(data);
            } catch (err) {
                console.error('Failed to generate tables:', err);
            } finally {
                loader.classList.remove('htmx-request');
            }
        });
    }

    // Load saved language pair from localStorage
    const savedLanguagePair = localStorage.getItem('selectedLanguagePair');
    if (savedLanguagePair) {
        languagePairDropdown.classList.remove('hidden');
        addLanguagePairButton.innerHTML = '<i class="fa-solid fa-lock"></i> Select Language Pair';
        addLanguagePairButton.disabled = true;
        loadLanguagePairs().then(() => {
            languagePairSelect.value = savedLanguagePair;
            enableProposeMissingRulesButton();
        });
    }

    // Toggle language pair dropdown
    addLanguagePairButton.addEventListener('click', function() {
        if (languagePairDropdown.classList.contains('hidden')) {
            // Show dropdown and change button icon to restricted
            languagePairDropdown.classList.remove('hidden');
            addLanguagePairButton.innerHTML = '<i class="fa-solid fa-lock"></i> Select Language Pair';
            addLanguagePairButton.disabled = true;

            // Load language pairs
            loadLanguagePairs();
        } else {
            // Hide dropdown and restore button
            languagePairDropdown.classList.add('hidden');
            addLanguagePairButton.innerHTML = '<i class="fa-solid fa-plus"></i> Select Language Pair';
            addLanguagePairButton.disabled = false;
        }
    });

    // Handle language pair selection
    languagePairSelect.addEventListener('change', function() {
        const selectedValue = this.value;
        if (selectedValue) {
            // Save to localStorage
            localStorage.setItem('selectedLanguagePair', selectedValue);
            enableProposeMissingRulesButton();
        } else {
            // disableProposeMissingRulesButton();
            hideProposeMissingRulesButton();
        }
    });

    // Handle propose missing rules button
    proposeMissingRulesButton.addEventListener('click', async () => {
        if (!languagePairSelect.value) return;

        // proposeMissingRulesButton.disabled = true;
        proposeMissingRulesButton.className = 'hidden-button';
        try {
            const reply = await callAgent({
                type: 'propose_missing_rules'
            });
            appendRuleMessage('assistant', reply.rules);
        } catch (err) {
            console.error('Failed to propose missing rules:', err);
            appendRuleMessage('assistant', 'Something went wrong. Please try again.');
        }
    });
}
