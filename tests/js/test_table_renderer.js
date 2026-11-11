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
      general_tables: [generalTable],
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
    assert.deepEqual(calls.persisted[0].general_tables, [generalTable]);
    assert.equal(Object.hasOwn(calls.persisted[0], 'general_table'), false);
    assert.deepEqual(calls.persisted[0].fragmented_tables, [
      singularTable,
      pluralTable,
    ]);
  });

  it('ignores the removed singular generated-table field', () => {
    const { sandbox, calls } = loadTableRenderer();

    sandbox.displayGeneratedTables({
      general_table: { title: 'Legacy', headers: [], rows: [] },
      fragmented_tables: [],
    });

    assert.deepEqual(calls.rendered, []);
    assert.equal(calls.persisted[0].general_tables.length, 0);
    assert.equal(Object.hasOwn(calls.persisted[0], 'general_table'), false);
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
      general_tables: [{ title: 'Presente', headers: [], rows: [] }],
      fragmented_tables: [verbFragment],
    });

    assert.deepEqual(
      verbFragment.rows.map((row) => row.row_position),
      [0, 1],
    );
  });

  it('displays and persists both adjective general tables and all side fragments', () => {
    const { sandbox, calls } = loadTableRenderer();
    const numberTable = {
      title: 'Adjective number',
      adjective_table_layout: 'adj_number_gender',
      headers: ['Singular', 'Tr', 'Expl', 'Ex', 'Plural', 'Tr', 'Expl', 'Ex'],
      rows: [],
    };
    const genderTable = {
      title: 'Adjective gender',
      adjective_table_layout: 'adj_number_gender',
      headers: ['Masculine', 'Tr', 'Expl', 'Ex', 'Feminine', 'Tr', 'Expl', 'Ex'],
      rows: [],
    };
    const fragments = ['Singular', 'Plural', 'Masculine', 'Feminine'].map(
      (side, index) => ({
        title: `Adjective ${side}`,
        adjective_table_layout: 'adj_number_gender',
        headers: [side, 'Tr', 'Expl', 'Ex'],
        rows: [{ cells: [`form ${side}`, 'translation', 'note', 'example'], row_position: index + 2 }],
      }),
    );

    sandbox.displayGeneratedTables({
      general_tables: [numberTable, genderTable],
      fragmented_tables: fragments,
    });

    assert.deepEqual(
      calls.rendered.map((table) => table.title),
      [numberTable.title, genderTable.title, ...fragments.map((table) => table.title)],
    );
    assert.deepEqual(
      calls.persisted[0].general_tables.map((table) => table.title),
      [numberTable.title, genderTable.title],
    );
    assert.equal(fragments[2].rows[0].row_position, 4);
    assert.deepEqual(
      fragments.map((table) => table.fragmented_table_id),
      [1, 2, 3, 4],
    );
  });
});

describe('renderTableData cell content', () => {
  function loadRealRenderer() {
    const created = [];
    const sandbox = {
      console: { log() {}, error() {} },
      tableMetadata,
      onTableSelected() {},
      tableSerializer: { tableToMarkdown: () => '' },
      enterInsertMode() {},
      deleteTableFromChat() {},
      document: {
        createElement(tagName) {
          const el = {
            tagName,
            className: '',
            textContent: '',
            innerHTML: '',
            dataset: {},
            children: [],
            appendChild(child) { this.children.push(child); return child; },
            addEventListener() {},
            classList: { add() {}, remove() {}, toggle() { return false; } },
            querySelector() { return null; },
          };
          created.push(el);
          return el;
        },
        getElementById() { return null; },
      },
    };

    vm.createContext(sandbox);
    const root = path.join(__dirname, '../../static/js/');
    vm.runInContext(fs.readFileSync(path.join(root, 'markdown_to_html.js'), 'utf8'), sandbox);
    vm.runInContext(fs.readFileSync(path.join(root, 'table_renderer.js'), 'utf8'), sandbox);
    return { sandbox, created };
  }

  function cellHtml(created) {
    return created
      .filter((el) => el.tagName === 'td')
      .map((el) => el.innerHTML);
  }

  it('highlights marked adjectives and keeps cells injection-safe', () => {
    const { sandbox, created } = loadRealRenderer();

    sandbox.renderTableData({
      title: 'El número del adjetivo',
      headers: ['Singular', 'Traducción', 'Explicación', 'Ejemplo'],
      rows: [
        { cells: ['el libro *rojo*', 'the red book', 'note', 'El libro rojo es nuevo.'] },
        { cells: ['<img src=x onerror=alert(1)>', 'the red book', 'note', 'x'] },
      ],
    });

    const html = cellHtml(created);
    assert.match(html[0], /<em class="adj-highlight">rojo<\/em>/);
    assert.doesNotMatch(html[0], /\*rojo\*/);
    assert.doesNotMatch(html[4], /<img/);
    assert.match(html[4], /&lt;img/);
  });
});
