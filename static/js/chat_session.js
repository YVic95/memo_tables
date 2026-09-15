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
