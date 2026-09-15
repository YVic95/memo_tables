// Fire-and-forget persistence of every message rendered into the rules chat.
// A failed persist call never surfaces an error and never interrupts the chat flow.

let _persistQueue = Promise.resolve();
let _persistenceSuppressed = false;

function setPersistenceSuppressed(suppressed) {
    _persistenceSuppressed = suppressed;
}

function persistChatMessage(role, messageType, content) {
    if (_persistenceSuppressed) {
        return Promise.resolve();
    }

    _persistQueue = _persistQueue
        .then(() => getOrCreateChatSession())
        .then(sessionId => fetch('/api/chat-messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, role, message_type: messageType, content }),
        }))
        .catch(err => console.warn('[chat-persist] failed to persist message:', err));

    return _persistQueue;
}

function persistProposedRulesMessage(rules) {
    persistChatMessage('assistant', 'proposed_rules', { rules });
}

function persistUserRuleSelectedMessage(rule) {
    persistChatMessage('user', 'text', {
        text: `${rule.title}: ${rule.explanation}`,
    });
}

function persistFullRuleMessage(reply) {
    persistChatMessage('assistant', 'full_rule', {
        grammar_rule_id: reply.grammar_rule_id,
        full_content: reply.full_content ?? '',
        title: reply.title ?? '',
        explanation: reply.explanation ?? '',
    });
}

function persistTableMessage(tablePayload) {
    const fragmented = tablePayload.fragmented_tables || [];
    if (tablePayload.edited_table) {
        persistChatMessage('assistant', 'table', { table: tablePayload.edited_table });
        return;
    }

    persistChatMessage('assistant', 'table', { table: tablePayload.general_table });

    if (fragmented.length > 0) {
        persistChatMessage('assistant', 'table', {
            grouped_fragmentation: true,
            tables: fragmented,
        });
    }
}

function persistTextMessage(role, text) {
    persistChatMessage(role, 'text', { text });
}

function persistSaveConfirmationMessage(reply) {
    persistChatMessage('assistant', 'save_confirmation', {
        message: reply.message,
        skeleton_table: reply.skeleton_table,
    });
}