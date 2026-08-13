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
