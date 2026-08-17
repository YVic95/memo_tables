function renderTableData(tableData, readOnly = false) {
    const container = document.createElement('div');
    container.className = 'grammar-table-container';
    container.dataset.tableTitle = tableData.title;
    container._tableData = tableData;
    if (!readOnly) {
        container.addEventListener('click', () => onTableSelected(container));
    }

    const title = document.createElement('h4');
    title.className = 'grammar-table-title';
    title.textContent = tableData.title;

    if (!readOnly) {
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'grammar-table-delete';
        deleteBtn.innerHTML = '<i class="fa-solid fa-trash-can"></i>';
        deleteBtn.title = 'Delete table';
        deleteBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            deleteTableFromChat(container);
        });
        title.appendChild(deleteBtn);
    }

    const toggleIcon = document.createElement('i');
    toggleIcon.className = 'fa-solid fa-chevron-down table-collapse-toggle';
    title.appendChild(toggleIcon);

    if (!readOnly) {
        title.addEventListener('click', (event) => {
            event.stopPropagation();
            onTableSelected(container);
        });
    }

    toggleIcon.addEventListener('click', (event) => {
        event.stopPropagation();
        const collapsed = container.classList.toggle('grammar-table-collapsed');
        toggleIcon.className = collapsed ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down';
    });

    container.appendChild(title);

    const table = document.createElement('table');
    table.className = 'grammar-table';

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    tableData.headers.forEach(header => {
        const th = document.createElement('th');
        th.textContent = header;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    tableData.rows.forEach(row => {
        const tr = document.createElement('tr');
        row.cells.forEach(cell => {
            const td = document.createElement('td');
            td.textContent = cell;
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    container.appendChild(table);
    return container;
}

let nextTableId = 0;
function assignTableId(tableData) {
    tableData.tableId = ++nextTableId;
    return tableData;
}

function displayGeneratedTables(response) {
    const main = renderTableData(assignTableId(response.general_table));
    appendToChat(main);

    if (response.fragmented_tables && response.fragmented_tables.length > 0) {
        const separator = document.createElement('hr');
        separator.className = 'grammar-table-separator';
        appendToChat(separator);

        const subHeading = document.createElement('p');
        subHeading.className = 'grammar-table-subheading';
        subHeading.textContent = 'Fragmented Tables';
        appendToChat(subHeading);

        response.fragmented_tables.forEach((table, index) => {
            table.isFragmented = true;
            table.fragmented_table_id = index + 1;
            table.rows.forEach((row, rowIndex) => {
                row.row_position = rowIndex;
            });
            console.log('[Fragmented Table]', {
                fragmented_table_id: table.fragmented_table_id,
                title: table.title,
                rows: table.rows.map(r => ({ row_position: r.row_position, cells: r.cells })),
            });
            const el = renderTableData(assignTableId(table));
            appendToChat(el);
        });
    }
}
