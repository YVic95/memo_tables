document.addEventListener('htmx:load', function(event) {
    const container = event.target;
    
    // Initialize chat tab functionality
    initializeChatTab(container);
});

function initializeChatTab(container) {
    const addLanguagePairButton = container.querySelector('#add-language-pair');
    const proposeMissingRulesButton = container.querySelector('#propose-missing-rules');
    const languagePairDropdown = container.querySelector('#language-pair-dropdown');
    const languagePairSelect = container.querySelector('#language-pair-select');
    
    if (!addLanguagePairButton || !proposeMissingRulesButton || !languagePairDropdown || !languagePairSelect) {
        return;
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
            disableProposeMissingRulesButton();
        }
    });
    
    // Handle propose missing rules button
    proposeMissingRulesButton.addEventListener('click', async () => {
        if (!languagePairSelect.value) return;

        proposeMissingRulesButton.disabled = true;
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

function disableProposeMissingRulesButton() {
    const proposeButton = document.getElementById('propose-missing-rules');
    if (proposeButton) {
        proposeButton.disabled = true;
    }
}

// calls the create-rule-agent
async function callAgent(payload) {
    const selectedPair = document.getElementById('language-pair-select')?.value;

    const result = await fetch('/api/create-rule-agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, language_pair_id: selectedPair }),
    });

    if (!result.ok) {
        const error = await result.json();
        throw new Error(error.detail || 'Agent request failed');
    }

    return result.json();
}

// messages of the current chat session
function appendRuleMessage(role, rules) {
    const container = document.createElement('div');
    container.className = `message message-${role}`;

    const sender = document.createElement('div');
    sender.className = 'message-sender';
    sender.textContent = role === 'assistant' ? 'Assistant: ' : 'You: ';

    const list = document.createElement('ul');
    list.className = 'proposed-rules-list';

    rules.forEach(rule => {
        const item = document.createElement('li');
        item.className = 'proposed-rule';

        const title = document.createElement('strong');
        title.textContent = rule.title;

        const explanation = document.createElement('p');
        explanation.textContent = rule.explanation;

        item.appendChild(title);
        item.appendChild(explanation);

        // Make li clickable/selectable
        item.addEventListener('click', async () => {
            if (list.querySelector('.proposed-rule-selected')) {
                return; // A rule has already been selected
            }

            item.classList.add('proposed-rule-selected');

            // Fade out and remove all unselected cards in this list
            list.querySelectorAll('.proposed-rule').forEach(otherItem => {
                if (otherItem === item) return;

                otherItem.classList.add('proposed-rule-dismissed');

                // Remove from DOM after the animation finishes
                otherItem.addEventListener('transitionend', () => {
                    otherItem.remove();
                }, { once: true });
            });
            
            try {
                const reply = await callAgent({
                    type: 'initial_rule',
                    title: rule.title,
                    explanation: rule.explanation,
                });

                console.log('Initial rule created:', reply);

                // Display reply.full_content in the chat
                // appendContentMessage(reply.full_content);
            } catch (err) {
                console.error('Failed to initialize rule:', err);
            }
        });
        list.appendChild(item);
    });

    container.appendChild(sender);
    container.appendChild(list);

    // Hint for the user, shown only when there are rules to click on
    if (role === 'assistant' && rules.length > 0) {
        const hint = document.createElement('p');
        hint.className = 'proposed-rules-hint';
        hint.textContent = 'Click on the rule card you\'d like to learn more about to see details.';
        container.appendChild(hint);
    }

    document.getElementById('chat-messages').appendChild(container);
}