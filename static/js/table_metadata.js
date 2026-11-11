(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.tableMetadata = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  function keepsNounRowPosition(table, row) {
    return Boolean(table && table.noun_table_layout && row && row.row_position != null);
  }

  function keepsGrammarRowPosition(table, row) {
    return Boolean(
      table && (table.noun_table_layout || table.adjective_table_layout) &&
      row && row.row_position != null
    );
  }

  function preserveTableMetadata(target, source) {
    if (!source) {
      return target;
    }

    for (const field of ['noun_table_layout', 'adjective_table_layout']) {
      if (source[field]) target[field] = source[field];
    }

    if (source.isFragmented) {
      target.isFragmented = true;
      target.fragmented_table_id = source.fragmented_table_id;
      target.rows.forEach((row, index) => {
        const sourceRow = source.rows && source.rows[index];
        row.row_position = keepsGrammarRowPosition(source, sourceRow)
          ? sourceRow.row_position
          : index;
      });
    }

    return target;
  }

  return { keepsNounRowPosition, keepsGrammarRowPosition, preserveTableMetadata };
});
