function renderTableData(tableData) {
    const container = document.createElement('div');
    container.className = 'grammar-table-container';
    container.dataset.tableTitle = tableData.title;
    container._tableData = tableData;
    container.addEventListener('click', () => onTableSelected(container));

    const title = document.createElement('h4');
    title.className = 'grammar-table-title';
    title.textContent = tableData.title;

    const toggleIcon = document.createElement('i');
    toggleIcon.className = 'fa-solid fa-chevron-down';
    title.appendChild(toggleIcon);

    title.addEventListener('click', (event) => {
        event.stopPropagation();
        onTableSelected(container);
    });

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

function displayGeneratedTables(response) {
    const main = renderTableData(response.general_table);
    appendToChat(main);

    if (response.fragmented_tables && response.fragmented_tables.length > 0) {
        const separator = document.createElement('hr');
        separator.className = 'grammar-table-separator';
        appendToChat(separator);

        const subHeading = document.createElement('p');
        subHeading.className = 'grammar-table-subheading';
        subHeading.textContent = 'Fragmented Tables';
        appendToChat(subHeading);

        response.fragmented_tables.forEach(table => {
            const el = renderTableData(table);
            appendToChat(el);
        });
    }
}
