// messages of the current chat session
function appendRuleMessage(role, rules, options) {
    const container = createRuleMessageContainer(role);
    const list = createRulesList(rules, options);

    container.appendChild(list);

    if (role === 'assistant' && rules.length > 0) {
        container.appendChild(createRulesHint());
    }

    appendToChat(container);

    if (Array.isArray(rules)) {
        persistProposedRulesMessage(rules);
    } else if (typeof rules === 'string' && rules.length > 0) {
        persistTextMessage(role, rules);
    }
}

function createRuleMessageContainer(role) {
    const container = document.createElement('div');
    container.className = `message message-${role}`;

    const sender = document.createElement('div');
    sender.className = 'message-sender';
    sender.textContent = role === 'assistant' ? 'Assistant' : 'You';

    container.appendChild(sender);

    return container;
}

function createRulesList(rules, options) {
    const list = document.createElement('ul');
    list.className = 'proposed-rules-list';

    const visibleRules = (options && options.selectedTitle)
        ? rules.filter(rule => rule.title === options.selectedTitle)
        : rules;

    visibleRules.forEach(rule => {
        list.appendChild(createRuleItem(rule, list, options));
    });

    return list;
}

function createRuleItem(rule, list, options) {
    const item = document.createElement('li');
    item.className = 'proposed-rule';

    const title = document.createElement('strong');
    title.textContent = rule.title;

    const explanation = document.createElement('p');
    explanation.textContent = rule.explanation;

    item.append(title, explanation);

    if (options && options.selectable === false) {
        if (rule.title === options.selectedTitle) {
            item.classList.add('proposed-rule-selected');
        } else {
            item.classList.add('proposed-rule-dismissed');
        }
        return item;
    }

    item.addEventListener('click', () => onRuleSelected(item, list, rule));

    return item;
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
