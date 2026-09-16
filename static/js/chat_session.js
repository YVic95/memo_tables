const CHAT_SESSION_STORAGE_KEY = 'activeChatSessionId';

async function getOrCreateChatSession() {
    let sessionId = localStorage.getItem(CHAT_SESSION_STORAGE_KEY);
    if (sessionId) {
        return sessionId;
    }

    const result = await fetch('/api/chat-sessions', { method: 'POST' });
    if (!result.ok) {
        throw new Error('Failed to create chat session');
    }

    const data = await result.json();
    sessionId = data.id;
    localStorage.setItem(CHAT_SESSION_STORAGE_KEY, sessionId);
    return sessionId;
}

async function setWorkflowStep(step) {
    const sessionId = await getOrCreateChatSession();
    return fetch(`/api/chat-sessions/${sessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workflow_step: step }),
    }).catch(err => console.warn('[chat-session] failed to update workflow step:', err));
}

async function setChatSessionTitle(languagePairId, ruleTitle) {
    const sessionId = await getOrCreateChatSession();
    return fetch(`/api/chat-sessions/${sessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language_pair_id: languagePairId, rule_title: ruleTitle }),
    }).catch(err => console.warn('[chat-session] failed to set chat session title:', err));
}

async function fetchActiveChatSession() {
    const result = await fetch('/api/chat-sessions/active');
    if (!result.ok) {
        return null;
    }
    const data = await result.json();
    return data || null;
}

async function fetchChatMessages(sessionId) {
    const result = await fetch(`/api/chat-sessions/${sessionId}/messages`);
    if (!result.ok) {
        throw new Error('Failed to fetch chat messages');
    }
    return result.json();
}

async function closeChatSession() {
    const sessionId = localStorage.getItem(CHAT_SESSION_STORAGE_KEY);
    if (!sessionId) {
        resetChatUI();
        return;
    }

    // Let any queued message persists finish against this session before we close it.
    await _persistQueue.catch(() => {});

    const result = await fetch(`/api/chat-sessions/${sessionId}/close`, {
        method: 'POST',
    });
    if (!result.ok) {
        throw new Error('Failed to close chat session');
    }

    localStorage.removeItem(CHAT_SESSION_STORAGE_KEY);
    resetChatUI();
}

function resetChatUI() {
    const chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
    }

    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-message');
    if (input) {
        input.value = '';
        input.disabled = true;
    }
    if (sendBtn) {
        sendBtn.disabled = true;
    }

    ['generate-table-btn', 'edit-table-btn', 'reapply-edits-btn', 'check-tables-before-save', 'close-chat-session-btn']
        .forEach(id => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.classList.add('hidden-button');
                btn.disabled = false;
            }
        });

    const proposeButton = document.getElementById('propose-missing-rules');
    if (proposeButton) {
        proposeButton.className = 'save-button';
        proposeButton.disabled = true;
    }

    document.getElementById('generate-table-btn')?.removeAttribute('data-rule-id');

    localStorage.removeItem('selectedLanguagePair');
    const addLanguagePairButton = document.getElementById('add-language-pair');
    const languagePairDropdown = document.getElementById('language-pair-dropdown');
    const languagePairSelect = document.getElementById('language-pair-select');
    if (addLanguagePairButton) {
        addLanguagePairButton.disabled = false;
        addLanguagePairButton.innerHTML = '<i class="fa-solid fa-plus"></i> Select Language Pair';
    }
    if (languagePairDropdown) {
        languagePairDropdown.classList.add('hidden');
    }
    if (languagePairSelect) {
        languagePairSelect.value = '';
    }

    nextTableId = 0;
    tableOrder = [];
    tableEditMode = false;
    selectedTable = null;
    hasEditHistory = false;
    insertTarget = null;
    closeTablePreview();
}
