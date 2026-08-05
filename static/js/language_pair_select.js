async function loadLanguagePairs() {
    return fetch('/api/language-pairs')
        .then(response => response.json())
        .then(data => {
            const languagePairSelect = document.getElementById('language-pair-select');
            if (!languagePairSelect) return;

            // Clear existing options except the first one
            while (languagePairSelect.options.length > 1) {
                languagePairSelect.remove(1);
            }

            // Select Language Pairs to dropdown
            data.language_pairs.forEach(pair => {
                const option = document.createElement('option');
                option.value = pair.pair_id;
                option.textContent = `${pair.native_name} → ${pair.target_name}`;
                languagePairSelect.appendChild(option);
            });

            // Restore saved selection
            const savedLanguagePair = localStorage.getItem('selectedLanguagePair');
            if (savedLanguagePair) {
                languagePairSelect.value = savedLanguagePair;
            }
        })
        .catch(error => {
            console.error('Error loading language pairs:', error);
        });
}

function enableProposeMissingRulesButton() {
    const proposeButton = document.getElementById('propose-missing-rules');
    if (proposeButton) {
        proposeButton.disabled = false;
    }
}

function hideProposeMissingRulesButton() {
    const proposeButton = document.getElementById('propose-missing-rules');
    if (proposeButton) {
        proposeButton.className = 'hidden-button';
    }
}

function disableProposeMissingRulesButton() {
    const proposeButton = document.getElementById('propose-missing-rules');
    if (proposeButton) {
        proposeButton.disabled = true;
    }
}
