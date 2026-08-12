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
