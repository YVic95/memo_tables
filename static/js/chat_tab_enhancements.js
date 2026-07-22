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

function markdownToHtml(text) {
    if (!text) return '';

    let normalized = text
        .replace(/(?<!\n)(?=## )/g, '\n')
        .replace(/(?<!\n)(?=### )/g, '\n')
        .replace(/(?<!\n)(?=# )/g, '\n')
        .trim();

    const rawLines = normalized.split('\n');

    // Drop lines that are pure heading-hash dividers (tolerating stray
    // invisible/odd whitespace characters some LLM output contains).
    const lines = rawLines.filter(raw => {
        const cleaned = raw.replace(/[\s\u00A0\u200B\uFEFF]+/g, '');
        return !/^#{1,6}$/.test(cleaned);
    });

    function inline(s) {
        return s
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>');
    }

    // --- Pass 1: tokenize non-blank lines into typed blocks ---
    const tokens = [];
    let sawFirstHeading = false; // first heading-like line = title (h2), rest = h3
    for (const raw of lines) {
        const line = raw.trim();
        if (!line) continue; // blank lines are just separators, not tokens
        let m;
        if ((m = line.match(/^#{1,3}\s+(.+)/))) {
            if (!sawFirstHeading) {
                tokens.push({ type: 'h2', text: m[1] });
                sawFirstHeading = true;
            } else {
                tokens.push({ type: 'h3', text: m[1] });
            }
        }
        else if ((m = line.match(/^\d+\.\s+(.+)/))) tokens.push({ type: 'ol', text: m[1] });
        else if ((m = line.match(/^[-*]\s+(.+)/))) tokens.push({ type: 'ul', text: m[1] }); // - or *
        else tokens.push({ type: 'p', text: line });
    }

    // --- Pass 2: render, nesting consecutive `ul` tokens under the
    // preceding `ol` item instead of treating them as siblings ---
    const out = [];
    let i = 0;
    while (i < tokens.length) {
        const t = tokens[i];

        if (t.type === 'h2') { out.push('<h2>' + inline(t.text) + '</h2>'); i++; continue; }
        if (t.type === 'h3') { out.push('<h3>' + inline(t.text) + '</h3>'); i++; continue; }
        if (t.type === 'p')  { out.push('<p>' + inline(t.text) + '</p>'); i++; continue; }

        if (t.type === 'ol') {
            out.push('<ol>');
            while (i < tokens.length && tokens[i].type === 'ol') {
                const item = tokens[i];
                i++;
                let nested = '';
                if (i < tokens.length && tokens[i].type === 'ul') {
                    nested = '<ul>';
                    while (i < tokens.length && tokens[i].type === 'ul') {
                        nested += '<li>' + inline(tokens[i].text) + '</li>';
                        i++;
                    }
                    nested += '</ul>';
                }
                out.push('<li>' + inline(item.text) + nested + '</li>');
            }
            out.push('</ol>');
            continue;
        }

        if (t.type === 'ul') {
            out.push('<ul>');
            while (i < tokens.length && tokens[i].type === 'ul') {
                out.push('<li>' + inline(tokens[i].text) + '</li>');
                i++;
            }
            out.push('</ul>');
            continue;
        }

        i++; // safety fallback, shouldn't be reached
    }

    return out.join('\n');
}

function appendFullRule(reply, originalRule) {
    const fullRule = document.createElement('div');
    fullRule.className = 'full-rule-content';

    const title = document.createElement('strong');
    title.textContent = reply.title ?? originalRule.title;

    const body = document.createElement('div');
    body.className = 'full-rule-body';
    body.innerHTML = markdownToHtml(reply.full_content ?? '');

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