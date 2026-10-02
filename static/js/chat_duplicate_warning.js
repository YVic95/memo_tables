// Duplicate-rule pre-flight. Before a suggested rule is created, the agent is asked
// whether a similar rule already exists; when it does, an inline warning card offers
// "Create anyway" or "Cancel". The card is persisted as a chat message so the existing
// chat restore path brings it back, in place, after a page refresh.

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
    return checkResult.existing_rule || null;
}

function buildDuplicateWarningContent(proposedRule, existingRule) {
    return {
        proposed_rule: {
            title: proposedRule.title,
            explanation: proposedRule.explanation,
            canonical_rule_id: proposedRule.canonical_rule_id,
        },
        existing_rule: {
            id: existingRule.id,
            name: existingRule.name,
            description: existingRule.description ?? null,
        },
    };
}

function appendDuplicateWarning(proposedRule, existingRule, options) {
    const { isResolved = false, onProceed = null, onCancel = null } = options || {};

    if (!proposedRule || !existingRule) {
        console.warn('[duplicate-warning] skipping a warning without a proposed or existing rule');
        return;
    }

    const content = buildDuplicateWarningContent(proposedRule, existingRule);
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

    const card = document.createElement('div');
    card.className = 'duplicate-warning';
    if (isResolved) {
        card.classList.add('duplicate-warning-resolved');
    }

    const header = document.createElement('div');
    header.className = 'duplicate-warning-header';
    header.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i><span>Possible duplicate</span>';

    const message = document.createElement('p');
    message.className = 'duplicate-warning-text';
    const existingRuleName = document.createElement('strong');
    existingRuleName.textContent = content.existing_rule.name;
    message.append('You already have a rule called ', existingRuleName, '.');

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
    module.exports = { findDuplicateRule, buildDuplicateWarningContent, appendDuplicateWarning };
}
