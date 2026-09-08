const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { parseMarkdownToTableData } = require('../../static/js/table_serializer.js');

describe('parseMarkdownToTableData', () => {
  it('parses a single-row, two-column table', () => {
    const md =
      '## Nouns\n\n' +
      '| Label | Noun: gato |\n' +
      '| --- | --- |\n' +
      '| Singular | gato |';
    const result = parseMarkdownToTableData(md);
    assert.equal(result.error, undefined);
    assert.deepEqual(result, {
      title: 'Nouns',
      headers: ['Label', 'Noun: gato'],
      rows: [{ cells: ['Singular', 'gato'] }],
    });
  });

  it('parses multiple rows', () => {
    const md =
      '## Nouns\n\n' +
      '| Label | Noun: gato |\n' +
      '| --- | --- |\n' +
      '| Singular | gato |\n' +
      '| Plural | gatos |';
    const result = parseMarkdownToTableData(md);
    assert.equal(result.error, undefined);
    assert.deepEqual(result, {
      title: 'Nouns',
      headers: ['Label', 'Noun: gato'],
      rows: [
        { cells: ['Singular', 'gato'] },
        { cells: ['Plural', 'gatos'] },
      ],
    });
  });

  it('parses a table with three columns', () => {
    const md =
      '## Verbs\n\n' +
      '| Label | Infinitive | Translation |\n' +
      '| --- | --- | --- |\n' +
      '| 1st | hablar | to speak |\n' +
      '| 2nd | comer | to eat |';
    const result = parseMarkdownToTableData(md);
    assert.equal(result.error, undefined);
    assert.deepEqual(result, {
      title: 'Verbs',
      headers: ['Label', 'Infinitive', 'Translation'],
      rows: [
        { cells: ['1st', 'hablar', 'to speak'] },
        { cells: ['2nd', 'comer', 'to eat'] },
      ],
    });
  });

  it('returns error for a table with no data rows (empty body)', () => {
    const md =
      '## Empty\n\n' +
      '| Col A | Col B |\n' +
      '| --- | --- |';
    const result = parseMarkdownToTableData(md);
    assert.ok(result.error);
    assert.match(result.error, /body|row|empty/i);
  });

  it('preserves empty cell values', () => {
    const md =
      '## Empty Cells\n\n' +
      '| A | B |\n' +
      '| --- | --- |\n' +
      '|  | value |';
    const result = parseMarkdownToTableData(md);
    assert.equal(result.error, undefined);
    assert.deepEqual(result, {
      title: 'Empty Cells',
      headers: ['A', 'B'],
      rows: [{ cells: ['', 'value'] }],
    });
  });

  it('trims whitespace around cell values', () => {
    const md =
      '## Trimmed\n\n' +
      '| A | B |\n' +
      '| --- | --- |\n' +
      '|  hello  |  world  |';
    const result = parseMarkdownToTableData(md);
    assert.equal(result.error, undefined);
    assert.deepEqual(result, {
      title: 'Trimmed',
      headers: ['A', 'B'],
      rows: [{ cells: ['hello', 'world'] }],
    });
  });

  it('handles special characters and accented text', () => {
    const md =
      '## Accents\n\n' +
      '| Word | Meaning |\n' +
      '| --- | --- |\n' +
      '| niño | child |\n' +
      '| señor | mister |';
    const result = parseMarkdownToTableData(md);
    assert.equal(result.error, undefined);
    assert.deepEqual(result, {
      title: 'Accents',
      headers: ['Word', 'Meaning'],
      rows: [
        { cells: ['niño', 'child'] },
        { cells: ['señor', 'mister'] },
      ],
    });
  });

  it('returns error for empty input', () => {
    assert.deepEqual(parseMarkdownToTableData(''), { error: 'empty input' });
    assert.deepEqual(parseMarkdownToTableData('   '), { error: 'empty input' });
  });

  it('returns error for non-string input', () => {
    assert.deepEqual(parseMarkdownToTableData(null), { error: 'empty input' });
    assert.deepEqual(parseMarkdownToTableData(undefined), { error: 'empty input' });
  });

  it('returns error when title heading is missing', () => {
    const md =
      'Nouns\n\n' +
      '| Label | Noun |\n' +
      '| --- | --- |\n' +
      '| Singular | gato |';
    const result = parseMarkdownToTableData(md);
    assert.ok(result.error);
    assert.match(result.error, /title/i);
  });

  it('returns error when separator row has non-dash content', () => {
    const md =
      '## Bad\n\n' +
      '| A | B |\n' +
      '| foo | bar |\n' +
      '| 1 | 2 |';
    const result = parseMarkdownToTableData(md);
    assert.ok(result.error);
    assert.match(result.error, /separator/i);
  });

  it('returns error on row column count mismatch', () => {
    const md =
      '## Mismatched\n\n' +
      '| A | B |\n' +
      '| --- | --- |\n' +
      '| 1 | 2 | 3 |';
    const result = parseMarkdownToTableData(md);
    assert.ok(result.error);
    assert.match(result.error, /column/i);
  });

  it('returns error when input has fewer than 3 non-empty lines', () => {
    const md =
      '## Title\n\n' +
      '| A | B |';
    const result = parseMarkdownToTableData(md);
    assert.ok(result.error);
  });
});
