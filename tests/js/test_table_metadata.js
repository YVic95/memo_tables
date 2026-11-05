const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const {
  preserveTableMetadata,
} = require('../../static/js/table_metadata.js');

const CHAT_TABLE_EDIT_SCRIPT = fs.readFileSync(
  path.join(__dirname, '../../static/js/chat_table_edit.js'),
  'utf8',
);

function loadChatTableEdit() {
  const calls = {
    rendered: [],
    persisted: [],
    appended: [],
  };

  const sandbox = {
    console: { log() {}, error() {}, warn() {} },
    tableMetadata: { preserveTableMetadata },
    document: {
      addEventListener() {},
      querySelectorAll() {
        return [];
      },
      getElementById() {
        return { classList: { add() {}, remove() {} } };
      },
    },
    window: {},
    setTimeout,
  };

  vm.createContext(sandbox);
  vm.runInContext(CHAT_TABLE_EDIT_SCRIPT, sandbox);

  sandbox.appendUserMessage = () => {};
  sandbox.appendAssistantMessage = () => {};
  sandbox.appendToChat = (element) => calls.appended.push(element);
  sandbox.renderTableData = (data) => {
    calls.rendered.push(data);
    return { _tableData: data };
  };
  sandbox.persistTableMessage = (payload) => calls.persisted.push(payload);
  sandbox.persistTableReplacement = (data) =>
    calls.persisted.push({ replacement: data });
  sandbox.createGoToTableAction = () => ({});
  sandbox.assignTableId = (data) => {
    data.tableId = 99;
    return data;
  };
  sandbox.enterTableEditMode = () => {};

  return { sandbox, calls };
}

function runInSandbox(sandbox, code) {
  return vm.runInContext(code, sandbox);
}

describe('chat table edit metadata preservation', () => {
  it('keeps noun_table_layout and row_position through the LLM edit path', async () => {
    const { sandbox, calls } = loadChatTableEdit();
    const editedTable = {
      title: 'El género del sustantivo — Masculino',
      headers: ['Masculino', 'Traducción', 'Explicación', 'Ejemplo'],
      rows: [
        { cells: ['el libro', 'the book', 'Masculine', 'El libro es nuevo.'] },
        { cells: ['el problema', 'the problem', 'Exception', 'El problema es difícil.'] },
      ],
    };

    sandbox.editTable = async () => ({
      edited_table: editedTable,
      edit_history: [],
    });

    runInSandbox(
      sandbox,
      `
        tableEditElements = {
          input: { value: '', disabled: false },
          sendBtn: { disabled: false },
          reapplyBtn: { classList: { add() {}, remove() {} } },
          editTableBtn: { classList: { add() {}, remove() {} } },
        };
        selectedTable = {
          tableId: 1,
          title: 'El género del sustantivo — Masculino',
          isFragmented: true,
          fragmented_table_id: 1,
          noun_table_layout: 'noun_gender',
          rows: [{ row_position: 3 }, { row_position: 8 }],
        };
        hasEditHistory = false;
      `,
    );

    await runInSandbox(sandbox, 'submitEdit("Use a different noun")');

    assert.equal(editedTable.noun_table_layout, 'noun_gender');
    assert.equal(editedTable.isFragmented, true);
    assert.equal(editedTable.fragmented_table_id, 1);
    assert.deepEqual(
      editedTable.rows.map((row) => row.row_position),
      [3, 8],
    );
    assert.equal(calls.rendered[0], editedTable);
    assert.equal(calls.persisted[0].edited_table, editedTable);
  });

  it('keeps noun_table_layout and row_position through the markdown insert path', async () => {
    const { sandbox, calls } = loadChatTableEdit();
    const parsedTable = {
      title: 'El número del sustantivo — Plural',
      headers: ['Plural', 'Traducción', 'Explicación', 'Ejemplo'],
      rows: [
        { cells: ['las mesas', 'the tables', 'Plural adds -s', 'Las mesas son grandes.'] },
      ],
    };
    const originalTable = {
      tableId: 2,
      title: 'El número del sustantivo — Plural',
      isFragmented: true,
      fragmented_table_id: 2,
      noun_table_layout: 'noun_number',
      rows: [{ row_position: 5 }],
    };
    const targetContainer = {
      _tableData: originalTable,
      replaceWith() {},
    };

    sandbox.tableSerializer = {
      parseMarkdownToTableData: () => parsedTable,
    };

    runInSandbox(
      sandbox,
      `
        tableEditElements = {
          input: { value: '## El número del sustantivo — Plural' },
          sendBtn: { disabled: false },
          editTableBtn: { classList: { remove() {} } },
        };
        insertTarget = {};
      `,
    );

    sandbox.targetContainer = targetContainer;
    await runInSandbox(sandbox, 'submitInsert(targetContainer)');

    assert.equal(parsedTable.noun_table_layout, 'noun_number');
    assert.equal(parsedTable.isFragmented, true);
    assert.equal(parsedTable.fragmented_table_id, 2);
    assert.equal(parsedTable.tableId, 2);
    assert.equal(parsedTable.rows[0].row_position, 5);
    assert.equal(calls.rendered[0], parsedTable);
    assert.equal(calls.persisted[0].replacement, parsedTable);
  });
});

describe('preserveTableMetadata', () => {
  it('keeps verb fragmentation behaviour unchanged', () => {
    const edited = {
      title: 'Presente — Primera persona',
      headers: ['Forma', 'Ejemplo'],
      rows: [{ cells: ['hablo', 'Hablo mucho.'] }, { cells: ['hablas', 'Hablas mucho.'] }],
    };
    const source = {
      isFragmented: true,
      fragmented_table_id: 1,
      rows: [{ row_position: 7 }, { row_position: 9 }],
    };

    preserveTableMetadata(edited, source);

    assert.equal('noun_table_layout' in edited, false);
    assert.equal(edited.isFragmented, true);
    assert.equal(edited.fragmented_table_id, 1);
    assert.deepEqual(
      edited.rows.map((row) => row.row_position),
      [0, 1],
    );
  });

  it('leaves a regular noun table without fragmentation metadata', () => {
    const edited = {
      title: 'El género del sustantivo',
      headers: ['Masculino', 'Femenino'],
      rows: [{ cells: ['el libro', 'la mesa'] }],
    };
    const source = { noun_table_layout: 'noun_gender' };

    preserveTableMetadata(edited, source);

    assert.equal(edited.noun_table_layout, 'noun_gender');
    assert.equal('isFragmented' in edited, false);
    assert.equal('row_position' in edited.rows[0], false);
  });

  it('does not clear an existing layout when the source has none', () => {
    const edited = { title: 'Nouns', noun_table_layout: 'noun_number' };

    preserveTableMetadata(edited, {});

    assert.equal(edited.noun_table_layout, 'noun_number');
  });
});
