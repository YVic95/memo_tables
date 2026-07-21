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
    const loader = document.getElementById('loader');

    loader.classList.add('htmx-request');

    const selectedPair = document.getElementById('language-pair-select')?.value;

    try {
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
    } finally {
        loader.classList.remove('htmx-request');
    }

}

const NODE_LABELS = {
    categorize: 'Categorizing rule',
    persist_rule: 'Saving rule',
    translate_rule: 'Translating',
    persist_translation: 'Saving translation',
    generate_content: 'Generating content',
};

const NODE_ORDER = ['categorize', 'persist_rule', 'translate_rule', 'persist_translation', 'generate_content'];

async function callAgentStream(payload, onEvent) {
    const selectedPair = document.getElementById('language-pair-select')?.value;

    const response = await fetch('/api/create-rule-agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, language_pair_id: selectedPair }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Agent request failed');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = "";
    while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split("\n\n");
        buffer = events.pop();

        for (const event of events) {
            let eventType = null;
            let data = null;

            for (const line of event.split("\n")) {
                if (line.startsWith("event: ")) {
                    eventType = line.slice(7);
                } else if (line.startsWith("data: ")) {
                    data = JSON.parse(line.slice(6));
                }
            }

            if (eventType && data) {
                onEvent(eventType, data);
            }
        }
    }
}

function createProgressContainer() {
    const container = document.createElement('div');
    container.className = 'agent-progress';

    const title = document.createElement('div');
    title.className = 'agent-progress-title';
    title.textContent = 'Creating your rule...';

    const steps = document.createElement('div');
    steps.className = 'agent-progress-steps';

    NODE_ORDER.forEach(node => {
        const step = document.createElement('div');
        step.className = 'agent-progress-step';
        step.dataset.node = node;

        const icon = document.createElement('span');
        icon.className = 'step-icon';

        const label = document.createElement('span');
        label.className = 'step-label';
        label.textContent = NODE_LABELS[node];

        step.append(icon, label);
        steps.appendChild(step);
    });

    container.append(title, steps);
    return container;
}

function updateProgress(container, completedNodes, activeNode) {
    const steps = container.querySelectorAll('.agent-progress-step');
    steps.forEach(step => {
        const node = step.dataset.node;
        step.classList.remove('active', 'completed');

        if (completedNodes.has(node)) {
            step.classList.add('completed');
            step.querySelector('.step-icon').innerHTML = '<i class="fa-solid fa-check"></i>';
        } else if (node === activeNode) {
            step.classList.add('active');
            step.querySelector('.step-icon').innerHTML = '<i class="fa-solid fa-spinner fa-spin-pulse"></i>';
        } else {
            step.querySelector('.step-icon').innerHTML = '';
        }
    });
}

function markProgressComplete(container) {
    const title = container.querySelector('.agent-progress-title');
    if (title) {
        title.textContent = 'Rule created';
    }

    container.classList.add('agent-progress-done');

    const steps = container.querySelectorAll('.agent-progress-step');
    steps.forEach(step => {
        step.classList.remove('active');
        step.classList.add('completed');
        step.querySelector('.step-icon').innerHTML = '<i class="fa-solid fa-check"></i>';
    });
}

// messages of the current chat session
function appendRuleMessage(role, rules) {
    const container = createRuleMessageContainer(role);
    const list = createRulesList(rules);

    container.appendChild(list);

    if (role === 'assistant' && rules.length > 0) {
        container.appendChild(createRulesHint());
    }

    appendToChat(container);
}

function createRuleMessageContainer(role) {
    const container = document.createElement('div');
    container.className = `message message-${role}`;

    const sender = document.createElement('div');
    sender.className = 'message-sender';
    sender.textContent = role === 'assistant' ? 'Assistant: ' : 'You: ';

    container.appendChild(sender);

    return container;
}

function createRulesList(rules) {
    const list = document.createElement('ul');
    list.className = 'proposed-rules-list';

    rules.forEach(rule => {
        list.appendChild(createRuleItem(rule, list));
    });

    return list;
}

function createRuleItem(rule, list) {
    const item = document.createElement('li');
    item.className = 'proposed-rule';

    const title = document.createElement('strong');
    title.textContent = rule.title;

    const explanation = document.createElement('p');
    explanation.textContent = rule.explanation;

    item.append(title, explanation);

    item.addEventListener('click', () => onRuleSelected(item, list, rule));

    return item;
}

async function onRuleSelected(item, list, rule) {
    if (list.querySelector('.proposed-rule-selected')) {
        return;
    }

    item.classList.add('proposed-rule-selected');

    dismissOtherRules(list, item);

    const progressContainer = createProgressContainer();
    appendToChat(progressContainer);

    try {
        const completedNodes = new Set();
        let finalResult = null;
        let serverError = null;

        await callAgentStream({
            type: 'initial_rule',
            title: rule.title,
            explanation: rule.explanation,
        }, (eventType, data) => {
            if (eventType === 'node_start') {
                updateProgress(progressContainer, completedNodes, data.node);
            } else if (eventType === 'node_complete') {
                completedNodes.add(data.node);
                updateProgress(progressContainer, completedNodes, null);
            } else if (eventType === 'done') {
                finalResult = data;
            } else if (eventType === 'error') {
                console.warn("Error while processing")
                serverError = data;
            }
        });

        // Keep the progress bar in place, just mark it as finished
        markProgressComplete(progressContainer);

        if (finalResult) {
            appendFullRule(finalResult, rule);
        } else if (serverError) {
            console.error('Agent stream reported an error:', serverError);
            appendStreamError(serverError.message || 'Something went wrong while creating the rule.');
        } else {
            console.warn('Stream finished without a "done" event; nothing to append.');
            appendStreamError('The connection ended before the rule finished generating. Please try again.');
        }
    } catch (err) {
        console.error('Failed to initialize rule:', err);
        markProgressComplete(progressContainer);
        appendStreamError('Something went wrong while creating the rule.');
    }
}

function dismissOtherRules(list, selectedItem) {
    list.querySelectorAll('.proposed-rule').forEach(item => {
        if (item === selectedItem) return;

        item.classList.add('proposed-rule-dismissed');

        item.addEventListener(
            'transitionend',
            () => item.remove(),
            { once: true }
        );
    });
}

function appendFullRule(reply, originalRule) {
    const fullRule = document.createElement('div');
    fullRule.className = 'full-rule-content';

    const title = document.createElement('strong');
    title.textContent = reply.title ?? originalRule.title;

    const body = document.createElement('p');
    body.textContent = reply.full_content ?? '';

    fullRule.append(title, body);
    appendToChat(fullRule);
}

function appendStreamError(message) {
    const errorEl = document.createElement('div');
    errorEl.className = 'full-rule-error';
    errorEl.textContent = message;
    appendToChat(errorEl);
}

function createRulesHint() {
    const hint = document.createElement('p');
    hint.className = 'proposed-rules-hint';
    hint.textContent =
        "Click on the rule card you'd like to learn more about to see details.";

    return hint;
}

function appendToChat(elem) {
    const chat = document.getElementById('chat-messages');
    chat.appendChild(elem);
    elem.scrollIntoView({ behavior: 'smooth' });
}