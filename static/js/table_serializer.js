(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.tableSerializer = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  function tableToMarkdown(table) {
    const titleLine = '## ' + table.title;
    const headerRow = '| ' + table.headers.join(' | ') + ' |';
    const separatorRow = '| ' + table.headers.map(() => '---').join(' | ') + ' |';
    const bodyRows = table.rows.map(
      (row) => '| ' + row.cells.join(' | ') + ' |',
    );
    return [titleLine, '', headerRow, separatorRow].concat(bodyRows).join('\n');
  }

  function parseMarkdownToTableData(markdown) {
    if (typeof markdown !== 'string' || !markdown.trim()) {
      return { error: 'empty input' };
    }

    const nonEmpty = markdown.split('\n').filter(l => l.trim());

    if (nonEmpty.length < 3) {
      return { error: 'need at least a title line, header row, and separator' };
    }

    const titleLine = nonEmpty[0].trim();
    if (!titleLine.startsWith('## ')) {
      return { error: 'missing ## title heading' };
    }
    const title = titleLine.slice(3).trim();

    const headerCells = splitPipeRow(nonEmpty[1]);
    const headers = headerCells.map(c => c.trim());
    const expectedCols = headers.length;

    const separatorCells = splitPipeRow(nonEmpty[2]);
    if (!separatorCells.every(c => /^-+$/.test(c.trim()))) {
      return { error: 'separator row is not all dashes' };
    }

    const rows = [];
    for (let i = 3; i < nonEmpty.length; i++) {
      const cells = splitPipeRow(nonEmpty[i]).map(c => c.trim());
      if (cells.length !== expectedCols) {
        return { error: 'row column count mismatch' };
      }
      rows.push({ cells });
    }

    if (rows.length === 0) {
      return { error: 'table has no data rows' };
    }

    return { title, headers, rows };
  }

  function splitPipeRow(line) {
    const trimmed = line.trim();
    const inner = trimmed.startsWith('|') ? trimmed.slice(1) : trimmed;
    const content = inner.endsWith('|') ? inner.slice(0, -1) : inner;
    return content.split('|');
  }

  return { tableToMarkdown, parseMarkdownToTableData };
});
