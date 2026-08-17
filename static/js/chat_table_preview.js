document.addEventListener('htmx:load', function(event) {
    initializeTablePreview(event.target);
});

function initializeTablePreview(container) {
    const checkBtn = container.querySelector('#check-tables-before-save');
    if (!checkBtn) return;
    checkBtn.addEventListener('click', showTablePreview);
}

let tableOrder = [];

function getLatestTables() {
    const latestTables = new Map();
    document.querySelectorAll('#chat-messages .grammar-table-container').forEach(el => {
        if (el._tableData) {
            const key = el._tableData.tableId || el._tableData.title;
            latestTables.set(key, el._tableData);
        }
    });

    const tables = Array.from(latestTables.values());

    if (tableOrder.length > 0) {
        tables.sort((a, b) => {
            const indexA = a.tableId !== undefined ? tableOrder.indexOf(a.tableId) : -1;
            const indexB = b.tableId !== undefined ? tableOrder.indexOf(b.tableId) : -1;
            const rankA = indexA === -1 ? tableOrder.length : indexA;
            const rankB = indexB === -1 ? tableOrder.length : indexB;
            return rankA - rankB;
        });
    }

    return tables;
}

function showTablePreview() {
    const tables = getLatestTables();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.id = 'table-preview-modal-overlay';

    const modal = document.createElement('div');
    modal.className = 'modal modal-wide';
    modal.id = 'table-preview-modal';

    const content = document.createElement('div');
    content.className = 'modal-content';

    const header = document.createElement('div');
    header.className = 'modal-header';

    const heading = document.createElement('h3');
    heading.textContent = 'Tables before saving';

    const closeBtn = document.createElement('button');
    closeBtn.className = 'close-button';
    closeBtn.setAttribute('aria-label', 'Close');
    closeBtn.innerHTML = '&times;';

    header.append(heading, closeBtn);

    const previewContent = document.createElement('div');
    previewContent.id = 'table-preview-content';

    if (tables.length === 0) {
        const empty = document.createElement('p');
        empty.textContent = 'No tables generated yet.';
        previewContent.appendChild(empty);
    } else {
        if (tables.length > 1) {
            const hint = document.createElement('p');
            hint.className = 'table-preview-hint';
            hint.textContent = 'Drag tables to change their order.';
            previewContent.appendChild(hint);
        }

        tables.forEach(table => {
            previewContent.appendChild(renderTableData(table, true));
        });

        initTableDrag(previewContent);
    }

    content.append(header, previewContent);

    if (tables.length > 0) {
        const footer = document.createElement('div');
        footer.className = 'modal-buttons';

        const saveBtn = document.createElement('button');
        saveBtn.className = 'save-button';
        saveBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Tables';
        saveBtn.addEventListener('click', onSaveTablesClick);
        footer.appendChild(saveBtn);

        content.appendChild(footer);
    }

    modal.appendChild(content);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    overlay.classList.add('show');

    closeBtn.addEventListener('click', closeTablePreview);
    overlay.addEventListener('click', function(event) {
        if (event.target === overlay) {
            closeTablePreview();
        }
    });
}

function closeTablePreview() {
    const overlay = document.getElementById('table-preview-modal-overlay');
    if (overlay) {
        const previewContent = overlay.querySelector('#table-preview-content');
        if (previewContent) {
            tableOrder = Array.from(previewContent.querySelectorAll('.grammar-table-container'))
                .map(el => el._tableData?.tableId)
                .filter(id => id !== undefined);
        }
        overlay.classList.remove('show');
        overlay.remove();
    }
}

async function onSaveTablesClick(event) {
    const saveBtn = event.currentTarget;
    const overlay = document.getElementById('table-preview-modal-overlay');
    const previewContent = overlay.querySelector('#table-preview-content');
    if (!previewContent) return;

    const tables = Array.from(previewContent.querySelectorAll('.grammar-table-container'))
        .map(el => el._tableData)
        .filter(data => data !== undefined);

    const grammarRuleId = document.getElementById('generate-table-btn')?.dataset.ruleId;
    const languagePairId = document.getElementById('language-pair-select')?.value;

    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin-pulse"></i> Saving...';

    try {
        const result = await fetch('/api/save-tables', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                language_pair_id: languagePairId,
                session_id: await getOrCreateChatSession(),
                grammar_rule_id: grammarRuleId,
                tables: tables,
            }),
        });

        if (!result.ok) {
            const err = await result.json().catch(() => ({}));
            throw new Error(err.detail || 'Failed to save tables');
        }

        saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> Saved';
    } catch (err) {
        console.error('Failed to save tables:', err);
        saveBtn.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Error';
        saveBtn.disabled = false;
    }
}

function initTableDrag(content) {
    const containers = content.querySelectorAll('.grammar-table-container');
    if (containers.length < 2) return;

    let dragEl = null;

    containers.forEach(el => {
        const title = el.querySelector('.grammar-table-title');
        const textNode = title.childNodes[0];

        const span = document.createElement('span');
        span.className = 'table-preview-title';
        span.textContent = textNode.textContent;

        const grip = document.createElement('i');
        grip.className = 'fa-solid fa-grip-vertical table-preview-grip';
        grip.draggable = true;
        grip.title = 'Drag to reorder';

        span.prepend(grip);
        title.replaceChild(span, textNode);

        el.addEventListener('dragstart', function(e) {
            dragEl = e.target.closest('.grammar-table-container');
            if (!dragEl) return;
            e.dataTransfer.effectAllowed = 'move';
            dragEl.classList.add('table-dragging');
        });

        el.addEventListener('dragover', function(e) {
            e.preventDefault();
            const container = e.target.closest('.grammar-table-container');
            if (!container || container === dragEl) return;
            e.dataTransfer.dropEffect = 'move';
            const rect = container.getBoundingClientRect();
            const after = e.clientY > rect.top + rect.height / 2;
            clearDropIndicators(content);
            container.classList.add(after ? 'table-drop-after' : 'table-drop-before');
        });

        el.addEventListener('drop', function(e) {
            e.preventDefault();
            const target = e.target.closest('.grammar-table-container');
            clearDropIndicators(content);
            if (!dragEl || !target || target === dragEl) return;
            const rect = target.getBoundingClientRect();
            if (e.clientY > rect.top + rect.height / 2) {
                target.after(dragEl);
            } else {
                target.before(dragEl);
            }
        });

        el.addEventListener('dragend', function() {
            clearDropIndicators(content);
            dragEl = null;
        });
    });
}

function clearDropIndicators(content) {
    content.querySelectorAll('.table-drop-before, .table-drop-after, .table-dragging').forEach(el => {
        el.classList.remove('table-drop-before', 'table-drop-after', 'table-dragging');
    });
}

document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeTablePreview();
    }
});
