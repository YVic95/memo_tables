let tableEditMode = false;
let selectedTable = null;
let tableEditElements = null;

document.addEventListener('htmx:load', function(event) {
    initializeTableEdit(event.target);
});

function initializeTableEdit(container) {
    const editTableBtn = container.querySelector('#edit-table-btn');
    const form = container.querySelector('#create-rule-chatbot');
    const input = container.querySelector('#chat-input');
    const sendBtn = container.querySelector('#send-message');

    if (!editTableBtn || !form || !input || !sendBtn) {
        return;
    }

    // Reset per-page state
    tableEditMode = false;
    selectedTable = null;
    tableEditElements = { editTableBtn, form, input, sendBtn };

    editTableBtn.addEventListener('click', enterTableEditMode);
    form.addEventListener('submit', onEditSubmit);
}

function enterTableEditMode() {
    if (tableEditMode) return;
    if (!tableEditElements) return;

    tableEditMode = true;
    console.log('[edit-tables] edit mode entered');

    appendAssistantMessage('Click the table you want to edit.');

    document.querySelectorAll('.grammar-table-container').forEach(container => {
        container.classList.remove('grammar-table-selected');
        container.classList.add('table-clickable');
    });
}

function onTableSelected(container) {
    if (!tableEditMode) return;

    const selection = window.getSelection();
    if (selection && !selection.isCollapsed && selection.toString().trim()) {
        return; // user is selecting/copying text, don't select the table
    }

    selectedTable = container._tableData;
    console.log('[edit-tables] selected table:', selectedTable);

    document.querySelectorAll('.grammar-table-container').forEach(other => {
        other.classList.remove('grammar-table-selected');
        if (other !== container) {
            other.classList.add('table-clickable');
        }
    });

    container.classList.add('grammar-table-selected');
    container.classList.remove('table-clickable');
    container.classList.remove('grammar-table-collapsed');
    const icon = container.querySelector('.grammar-table-title .table-collapse-toggle');
    if (icon) {
        icon.className = 'fa-solid fa-chevron-down table-collapse-toggle';
    }

    const { editTableBtn, input, sendBtn } = tableEditElements;

    editTableBtn.classList.add('hidden-button');
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();

    appendAssistantMessage(`You can now write your instructions for editing "${selectedTable.title}" below and press the send button.`);
}

async function onEditSubmit(event) {
    event.preventDefault();

    if (!tableEditElements || !selectedTable) return;

    const { input, sendBtn } = tableEditElements;
    const instructions = input.value.trim();
    if (!instructions) return;

    appendUserMessage(instructions);

    tableEditMode = false;

    input.disabled = true;
    sendBtn.disabled = true;

    const loader = document.getElementById('loader');
    loader.classList.add('htmx-request');

    try {
        const data = await editTable(instructions, selectedTable);
        console.log('[edit-tables] edited table response:', data);

        input.value = '';

        const editedEl = renderTableData(data.edited_table);
        appendToChat(editedEl);

        appendAssistantMessage('Table updated. Click the table you just updated to continue editing, or click another table.');

        // Re-enter edit mode so the user can continue on the result or pick another table
        enterTableEditMode();
    } catch (err) {
        console.error('Failed to edit table:', err);
        appendAssistantMessage('Something went wrong while editing the table. Please try again.');
        input.disabled = false;
        sendBtn.disabled = false;
    } finally {
        loader.classList.remove('htmx-request');
    }
}

async function editTable(instructions, table) {
    const selectedPair = document.getElementById('language-pair-select')?.value;

    const result = await fetch('/api/edit-tables', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language_pair_id: selectedPair, instructions, table }),
    });

    console.log('[edit-tables] request payload:', {
        language_pair_id: selectedPair,
        instructions,
        table,
    });

    if (!result.ok) {
        const err = await result.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to edit table');
    }

    return result.json();
}

function appendAssistantMessage(text) {
    const container = createRuleMessageContainer('assistant');
    const message = document.createElement('p');
    message.className = 'table-edit-hint';
    message.textContent = text;
    container.appendChild(message);
    appendToChat(container);
}

function appendUserMessage(text) {
    const container = createRuleMessageContainer('user');
    const message = document.createElement('p');
    message.className = 'table-edit-hint';
    message.textContent = text;
    container.appendChild(message);
    appendToChat(container);
}

function deleteTableFromChat(container) {
    container.remove();
    if (selectedTable === container._tableData) {
        selectedTable = null;
        tableEditElements.input.disabled = true;
        tableEditElements.sendBtn.disabled = true;
    }
}