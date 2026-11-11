const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const CHAT_TABLE_PREVIEW_SCRIPT = fs.readFileSync(
  path.join(__dirname, '../../static/js/chat_table_preview.js'),
  'utf8',
);

function loadPreview(tables) {
  const sandbox = {
    document: {
      addEventListener() {},
      querySelectorAll() {
        return tables.map(_tableData => ({ _tableData }));
      },
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(CHAT_TABLE_PREVIEW_SCRIPT, sandbox);
  return sandbox;
}

describe('getLatestTables', () => {
  it('excludes source tables replaced by a later LLM edit', () => {
    const sandbox = loadPreview([
      { tableId: 10, title: 'Singular', adjective_table_layout: 'adj_number_gender' },
      { tableId: 11, title: 'Plural', adjective_table_layout: 'adj_number_gender' },
      { tableId: 12, title: 'Singular edited', edited_from: 10, isFragmented: true },
    ]);

    assert.deepEqual(
      Array.from(sandbox.getLatestTables(), table => table.tableId),
      [11, 12],
    );
  });
});
