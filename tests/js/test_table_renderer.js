const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const tableMetadata = require('../../static/js/table_metadata.js');

const TABLE_RENDERER_SCRIPT = fs.readFileSync(
  path.join(__dirname, '../../static/js/table_renderer.js'),
  'utf8',
);

function loadTableRenderer() {
  const calls = {
    rendered: [],
    appended: [],
    persisted: [],
  };

  const sandbox = {
    console: { log() {}, error() {} },
    tableMetadata,
    document: {
      createElement(tagName) {
        return {
          tagName,
          className: '',
          textContent: '',
          appendChild() {},
          addEventListener() {},
          classList: { add() {}, remove() {}, toggle() { return false; } },
        };
      },
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(TABLE_RENDERER_SCRIPT, sandbox);

  sandbox.renderTableData = (data) => {
    calls.rendered.push(data);
    return { _tableData: data };
  };
  sandbox.appendToChat = (element) => calls.appended.push(element);
  sandbox.persistTableMessage = (payload) => calls.persisted.push(payload);

  return { sandbox, calls };
}

describe('displayGeneratedTables', () => {
  it('shows the general table and both noun side fragments', () => {
    const { sandbox, calls } = loadTableRenderer();
    const generalTable = {
      title: 'El número del sustantivo',
      headers: ['Singular', 'Traducción', 'Explicación', 'Ejemplo', 'Plural', 'Traducción', 'Explicación', 'Ejemplo'],
      rows: [],
    };
    const singularTable = {
      title: 'El número del sustantivo — Singular',
      noun_table_layout: 'noun_number',
      headers: ['Singular', 'Traducción', 'Explicación', 'Ejemplo'],
      rows: [
        { cells: ['la mesa', 'the table', 'Feminine', 'La mesa es grande.'], row_position: 3 },
      ],
    };
    const pluralTable = {
      title: 'El número del sustantivo — Plural',
      noun_table_layout: 'noun_number',
      headers: ['Plural', 'Traducción', 'Explicación', 'Ejemplo'],
      rows: [
        { cells: ['las mesas', 'the tables', 'Plural adds -s', 'Las mesas son grandes.'], row_position: 3 },
      ],
    };

    sandbox.displayGeneratedTables({
      general_table: generalTable,
      fragmented_tables: [singularTable, pluralTable],
    });

    assert.deepEqual(
      calls.rendered.map((table) => table.title),
      [generalTable.title, singularTable.title, pluralTable.title],
    );
    assert.equal(calls.appended.length, 5);
    assert.equal(singularTable.isFragmented, true);
    assert.equal(singularTable.fragmented_table_id, 1);
    assert.equal(pluralTable.fragmented_table_id, 2);
    assert.equal(singularTable.rows[0].row_position, 3);
    assert.equal(pluralTable.rows[0].row_position, 3);
    assert.equal(calls.persisted[0].general_table, generalTable);
    assert.deepEqual(calls.persisted[0].fragmented_tables, [
      singularTable,
      pluralTable,
    ]);
  });

  it('still reindexes verb fragment rows', () => {
    const { sandbox } = loadTableRenderer();
    const verbFragment = {
      title: 'Presente — Primera persona',
      headers: ['Forma', 'Ejemplo'],
      rows: [
        { cells: ['hablo', 'Hablo mucho.'], row_position: 7 },
        { cells: ['hablas', 'Hablas mucho.'], row_position: 9 },
      ],
    };

    sandbox.displayGeneratedTables({
      general_table: { title: 'Presente', headers: [], rows: [] },
      fragmented_tables: [verbFragment],
    });

    assert.deepEqual(
      verbFragment.rows.map((row) => row.row_position),
      [0, 1],
    );
  });
});
