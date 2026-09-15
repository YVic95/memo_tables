// Rebuilds an open chat session from persisted messages on page load.
// Restored messages are re-rendered through the normal append paths, so their
// interactive elements (Save Rule buttons, click-to-edit, copy/insert) are bound.
// Persistence is suppressed during restore to avoid re-persisting existing messages.

async function restoreActiveChatIfAny() {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;

    const activeSession = await fetchActiveChatSession();

    if (!activeSession) {
        localStorage.removeItem(CHAT_SESSION_STORAGE_KEY);
        return;
    }

    if (chatMessages.children.length > 0) {
        return;
    }

    const messages = await fetchChatMessages(activeSession.id);
    if (!messages || messages.length === 0) {
        return;
    }

    // The user may have started chatting (or the section may have been swapped
    // away) while the fetch was in flight — don't clobber that state.
    if (document.getElementById('chat-messages') !== chatMessages || chatMessages.children.length > 0) {
        return;
    }

    localStorage.setItem(CHAT_SESSION_STORAGE_KEY, activeSession.id);

    let workflowStep = activeSession.workflow_step;
    if (workflowStep === 'editing_tables') {
        showToast('Edit session expired. The table you were editing could not be restored.', 3000, 'fa-solid fa-triangle-exclamation');
        workflowStep = 'table_generated';
        setWorkflowStep('table_generated');
    }

    const restored = analyzeRestoreMessages(messages);
    const ruleSaved = workflowStep !== null;

    chatMessages.innerHTML = '';

    setPersistenceSuppressed(true);
    try {
        messages.forEach(msg => {
            renderRestoredMessage(msg, restored, ruleSaved);
        });
    } finally {
        setPersistenceSuppressed(false);
    }

    if (restored.hasProposedRules) {
        hideProposeMissingRulesButton();
    }

    const restoredTableIds = Array.from(chatMessages.querySelectorAll('.grammar-table-container'))
        .map(el => el._tableData?.tableId)
        .filter(id => id !== undefined && id !== null);
    if (restoredTableIds.length > 0) {
        nextTableId = Math.max(...restoredTableIds);
    }

    applyWorkflowButtonState(workflowStep, restored.latestRuleId);
}

function analyzeRestoreMessages(messages) {
    const result = {
        hasProposedRules: false,
        latestRuleId: null,
        consumedLists: new Set(),
        selectedTitleByList: new Map(),
    };

    const fullRulePositions = [];
    messages.forEach(msg => {
        if (msg.message_type === 'full_rule') {
            fullRulePositions.push(msg.position);
            if (msg.content && msg.content.grammar_rule_id) {
                result.latestRuleId = msg.content.grammar_rule_id;
            }
        }
    });

    let pendingListPosition = null;
    let pendingTitles = null;
    let selectionRecorded = false;

    messages.forEach(msg => {
        const content = msg.content || {};

        if (msg.message_type === 'proposed_rules') {
            result.hasProposedRules = true;
            pendingListPosition = msg.position;
            pendingTitles = (content.rules || []).map(rule => rule.title);
            selectionRecorded = false;
            if (fullRulePositions.some(pos => pos > msg.position)) {
                result.consumedLists.add(msg.position);
            }
        } else if (msg.message_type === 'text' && msg.role === 'user' && pendingListPosition !== null && !selectionRecorded) {
            const text = (content.text || '').trim();
            const selectedTitle = pendingTitles.find(title => text.startsWith(title + ':') || text === title);
            if (selectedTitle) {
                result.selectedTitleByList.set(pendingListPosition, selectedTitle);
            }
            selectionRecorded = true;
            pendingListPosition = null;
            pendingTitles = null;
        } else if (msg.message_type === 'full_rule') {
            pendingListPosition = null;
            pendingTitles = null;
        }
    });

    return result;
}

function renderRestoredMessage(msg, restored, ruleSaved) {
    const content = msg.content || {};
    switch (msg.message_type) {
        case 'proposed_rules':
            appendRuleMessage(msg.role, content.rules || [], {
                selectable: !restored.consumedLists.has(msg.position),
                selectedTitle: restored.selectedTitleByList.get(msg.position) || null,
            });
            break;
        case 'text':
            if (msg.role === 'user') {
                appendUserMessage(content.text || '');
            } else {
                appendAssistantMessage(content.text || '');
            }
            break;
        case 'full_rule':
            appendFullRule({
                grammar_rule_id: content.grammar_rule_id,
                full_content: content.full_content,
            }, null, ruleSaved);
            break;
        case 'table':
            renderRestoredTable(content);
            break;
        case 'save_confirmation':
            renderSaveResponseInChat({
                message: content.message,
                skeleton_table: content.skeleton_table,
            });
            break;
        default:
            break;
    }
}

function renderRestoredTable(content) {
    if (content.table) {
        const el = renderTableData(content.table);
        appendToChat(el);
        return;
    }

    if (content.grouped_fragmentation && Array.isArray(content.tables)) {
        const separator = document.createElement('hr');
        separator.className = 'grammar-table-separator';
        appendToChat(separator);

        const subHeading = document.createElement('p');
        subHeading.className = 'grammar-table-subheading';
        subHeading.textContent = 'Fragmented Tables';
        appendToChat(subHeading);

        content.tables.forEach(table => {
            table.isFragmented = true;
            const el = renderTableData(table);
            appendToChat(el);
        });
    }
}

function applyWorkflowButtonState(workflowStep, ruleId) {
    const generateBtn = document.getElementById('generate-table-btn');
    const editBtn = document.getElementById('edit-table-btn');
    const checkBtn = document.getElementById('check-tables-before-save');

    if (generateBtn) {
        generateBtn.classList.add('hidden-button');
        generateBtn.dataset.ruleId = ruleId || '';
    }
    if (editBtn) {
        editBtn.classList.add('hidden-button');
    }
    if (checkBtn) {
        checkBtn.classList.add('hidden-button');
    }

    if (workflowStep === 'rule_saved' && ruleId && generateBtn) {
        generateBtn.classList.remove('hidden-button');
    }

    if (workflowStep === 'table_generated' || workflowStep === 'editing_tables') {
        if (editBtn) {
            editBtn.classList.remove('hidden-button');
        }
        if (checkBtn) {
            checkBtn.classList.remove('hidden-button');
        }
    }
}