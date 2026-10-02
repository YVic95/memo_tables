// Duplicate-rule pre-flight. Before a suggested rule is created, the agent is asked
// whether a similar rule already exists; when it does, an inline warning card offers
// "Create anyway" or "Cancel". The card is persisted as a chat message so the existing
// chat restore path brings it back, in place, after a page refresh.
//
// check names up to three matching rules, best-fitting first, rather than
// only the single best. Cards persisted before that stored one rule under
// `existing_rule`, so both shapes are read — see readExistingRules.

function readExistingRules(content) {
    if (Array.isArray(content.existing_rules)) {
        return content.existing_rules;
    }
    if (content.existing_rule) {
        return [content.existing_rule];
    }
    return [];
}

async function findDuplicateRule(proposedRule) {
    let checkResult;
    try {
        checkResult = await callAgent({
            type: 'check_similar',
            title: proposedRule.title,
            explanation: proposedRule.explanation,
        });
    } catch (err) {
        // A failed check must never stop the admin from creating the rule.
        console.warn('[duplicate-warning] check failed, creating the rule anyway:', err);
        return null;
    }

    if (!checkResult || !checkResult.similar) {
        return null;
    }
    const matches = readExistingRules(checkResult);
    return matches.length ? matches : null;
}

function buildDuplicateWarningContent(proposedRule, existingRules) {
    return {
        proposed_rule: {
            title: proposedRule.title,
            explanation: proposedRule.explanation,
            canonical_rule_id: proposedRule.canonical_rule_id,
        },
        existing_rules: existingRules,
    };
}

function appendDuplicateWarning(proposedRule, existingRules, options) {
    const { isResolved = false, onProceed = null, onCancel = null } = options || {};

    if (!proposedRule || !existingRules || existingRules.length === 0) {
        console.warn('[duplicate-warning] skipping a warning without a proposed rule or any matching rule');
        return;
    }

    const content = buildDuplicateWarningContent(proposedRule, existingRules);
    const container = createRuleMessageContainer('assistant');

    const dismissCard = () => container.remove();
    const card = createDuplicateWarningCard(content, {
        isResolved,
        onProceed: onProceed || (() => {
            dismissCard();
            startRuleCreation(content.proposed_rule);
        }),
        onCancel: () => {
            dismissCard();
            if (onCancel) onCancel();
        },
    });

    container.appendChild(card);
    appendToChat(container);
    persistDuplicateWarningMessage(content);
}

function createDuplicateWarningCard(content, handlers) {
    const { isResolved, onProceed, onCancel } = handlers;
    // Read through the normaliser rather than off the key, so a card built from
    // either persisted shape renders.
    const existingRules = readExistingRules(content);

    const card = document.createElement('div');
    card.className = 'duplicate-warning';
    if (isResolved) {
        card.classList.add('duplicate-warning-resolved');
    }

    const header = document.createElement('div');
    header.className = 'duplicate-warning-header';
    header.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i><span>Possible duplicate</span>';

    // A div rather than the p this used to be, because several matches render as a
    // list inside it and a p may not contain one.
    const message = document.createElement('div');
    message.className = 'duplicate-warning-text';

    if (existingRules.length === 1) {
        const existingRuleName = document.createElement('strong');
        existingRuleName.textContent = existingRules[0].name;
        message.append('You already have a rule called ', existingRuleName, '.');
    } else {
        message.append(
            `You already have ${existingRules.length} rules that may cover the same ground:`
        );
        const list = document.createElement('ul');
        list.className = 'duplicate-warning-list';
        // Already ordered best-fit first by the check, so the order is kept as is.
        for (const rule of existingRules) {
            const item = document.createElement('li');
            item.textContent = rule.name;
            list.appendChild(item);
        }
        message.appendChild(list);
    }

    card.append(header, message);

    if (isResolved) {
        return card;
    }

    const actions = document.createElement('div');
    actions.className = 'duplicate-warning-actions';

    const createAnywayButton = document.createElement('button');
    createAnywayButton.className = 'save-button';
    createAnywayButton.innerHTML = '<i class="fa-solid fa-arrow-right"></i> Create anyway';
    createAnywayButton.addEventListener('click', onProceed);

    const cancelButton = document.createElement('button');
    cancelButton.className = 'duplicate-warning-cancel';
    cancelButton.innerHTML = '<i class="fa-solid fa-xmark"></i> Cancel';
    cancelButton.addEventListener('click', onCancel);

    actions.append(createAnywayButton, cancelButton);
    card.appendChild(actions);

    return card;
}

if (typeof module === 'object' && module.exports) {
    module.exports = {
        findDuplicateRule,
        buildDuplicateWarningContent,
        appendDuplicateWarning,
        readExistingRules,
    };
}
