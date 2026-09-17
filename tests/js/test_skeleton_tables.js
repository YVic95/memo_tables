const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const {
  splitPipeTableBlocks,
  tableBlockColumnCount,
  tableElementToMarkdown,
} = require('../../static/js/skeleton_tables.js');

const singleTable =
  '| Label | Noun: gato |\n' +
  '| --- | --- |\n' +
  '| Singular | gato |';

const secondTable =
  '| Label | Noun: perro |\n' +
  '| --- | --- |\n' +
  '| Singular | perro |';

describe('splitPipeTableBlocks', () => {
  it('returns a single verbatim table block for a lone pipe table', () => {
    const blocks = splitPipeTableBlocks(singleTable);
    assert.equal(blocks.length, 1);
    assert.equal(blocks[0].isTable, true);
    assert.equal(blocks[0].content, singleTable);
  });

  it('splits multiple tables separated by blank lines into verbatim blocks', () => {
    const markdown = singleTable + '\n\n' + secondTable;
    const blocks = splitPipeTableBlocks(markdown);
    assert.equal(blocks.length, 2);
    assert.deepEqual(blocks.map(b => b.isTable), [true, true]);
    assert.equal(blocks[0].content, singleTable);
    assert.equal(blocks[1].content, secondTable);
  });

  it('keeps pre/postamble text as non-table blocks around table blocks', () => {
    const markdown = 'Note:\n\n' + singleTable + '\n\nDone';
    const blocks = splitPipeTableBlocks(markdown);
    assert.equal(blocks.length, 3);
    assert.equal(blocks[0].isTable, false);
    assert.equal(blocks[1].isTable, true);
    assert.equal(blocks[1].content, singleTable);
    assert.equal(blocks[2].isTable, false);
  });

  it('does not treat a pipe-prefixed line without a separator as a table', () => {
    const markdown = '| just a line\nplain text';
    const blocks = splitPipeTableBlocks(markdown);
    assert.equal(blocks.length, 1);
    assert.equal(blocks[0].isTable, false);
    assert.equal(blocks[0].content, markdown);
  });

  it('returns no blocks for empty input', () => {
    assert.deepEqual(splitPipeTableBlocks(''), []);
    assert.deepEqual(splitPipeTableBlocks('   \n\n'), []);
  });
});

describe('tableBlockColumnCount', () => {
  it('counts columns in the first table block', () => {
    assert.equal(tableBlockColumnCount(singleTable), 2);
    assert.equal(tableBlockColumnCount(singleTable + '\n\n' + secondTable), 2);
  });

  it('returns 0 when there is no table block', () => {
    assert.equal(tableBlockColumnCount('just prose'), 0);
    assert.equal(tableBlockColumnCount(''), 0);
  });
});

function fakeRow(cells) {
  return { children: cells.map(c => ({ textContent: c })) };
}

function fakeTable(headers, rows) {
  const theadRow = fakeRow(headers);
  return {
    querySelectorAll(sel) {
      if (sel === 'thead tr') return [theadRow];
      if (sel === 'tbody tr') return rows.map(fakeRow);
      return [];
    },
  };
}

describe('tableElementToMarkdown', () => {
  it('serializes a rendered table to skeleton pipe-table markdown', () => {
    const table = fakeTable(['Label', 'Noun: gato'], [['Singular', 'gato']]);
    assert.equal(tableElementToMarkdown(table), singleTable);
  });

  it('serializes a table with no body rows to header + separator only', () => {
    const table = fakeTable(['A', 'B'], []);
    assert.equal(tableElementToMarkdown(table), '| A | B |\n| --- | --- |');
  });

  it('serializes multiple rows', () => {
    const table = fakeTable(['Label', 'Noun: gato'], [
      ['Singular', 'gato'],
      ['Plural', 'gatos'],
    ]);
    assert.equal(
      tableElementToMarkdown(table),
      singleTable + '\n| Plural | gatos |',
    );
  });

  it('returns empty markdown when the table has no header row', () => {
    const table = { querySelectorAll: () => [] };
    assert.equal(tableElementToMarkdown(table), '');
  });
});