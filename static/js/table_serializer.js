(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.tableToMarkdown = factory();
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

  return tableToMarkdown;
});
