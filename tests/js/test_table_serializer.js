const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { tableToMarkdown } = require('../../static/js/table_serializer.js');

describe('tableToMarkdown', () => {
  it('serializes a single-row, two-column table', () => {
    const table = {
      title: 'Nouns',
      headers: ['Label', 'Noun: gato'],
      rows: [{ cells: ['Singular', 'gato'] }],
    };
    const md = tableToMarkdown(table);
    assert.equal(
      md,
      '## Nouns\n\n' +
      '| Label | Noun: gato |\n' +
      '| --- | --- |\n' +
      '| Singular | gato |',
    );
  });

  it('serializes multiple rows', () => {
    const table = {
      title: 'Nouns',
      headers: ['Label', 'Noun: gato'],
      rows: [
        { cells: ['Singular', 'gato'] },
        { cells: ['Plural', 'gatos'] },
      ],
    };
    const md = tableToMarkdown(table);
    assert.equal(
      md,
      '## Nouns\n\n' +
      '| Label | Noun: gato |\n' +
      '| --- | --- |\n' +
      '| Singular | gato |\n' +
      '| Plural | gatos |',
    );
  });

  it('serializes a table with three columns', () => {
    const table = {
      title: 'Verbs',
      headers: ['Label', 'Infinitive', 'Translation'],
      rows: [
        { cells: ['1st', 'hablar', 'to speak'] },
        { cells: ['2nd', 'comer', 'to eat'] },
      ],
    };
    const md = tableToMarkdown(table);
    assert.equal(
      md,
      '## Verbs\n\n' +
      '| Label | Infinitive | Translation |\n' +
      '| --- | --- | --- |\n' +
      '| 1st | hablar | to speak |\n' +
      '| 2nd | comer | to eat |',
    );
  });

  it('handles multi-word titles', () => {
    const table = {
      title: 'Noun Conjugation Table',
      headers: ['Form', 'Value'],
      rows: [{ cells: ['Nominative', 'el gato'] }],
    };
    const md = tableToMarkdown(table);
    assert.ok(md.startsWith('## Noun Conjugation Table\n\n'));
  });

  it('handles special characters in cells verbatim', () => {
    const table = {
      title: 'Accents',
      headers: ['Word', 'Meaning'],
      rows: [
        { cells: ['niño', 'child'] },
        { cells: ['año', 'year'] },
        { cells: ['señor', 'mister'] },
      ],
    };
    const md = tableToMarkdown(table);
    assert.ok(md.includes('| niño | child |'));
    assert.ok(md.includes('| año | year |'));
    assert.ok(md.includes('| señor | mister |'));
  });

  it('handles empty cell values', () => {
    const table = {
      title: 'Empty Cells',
      headers: ['A', 'B'],
      rows: [{ cells: ['', 'value'] }],
    };
    const md = tableToMarkdown(table);
    assert.ok(md.includes('|  | value |'));
  });

  it('handles table with no rows', () => {
    const table = {
      title: 'Empty',
      headers: ['Col A', 'Col B'],
      rows: [],
    };
    const md = tableToMarkdown(table);
    assert.equal(
      md,
      '## Empty\n\n' +
      '| Col A | Col B |\n' +
      '| --- | --- |',
    );
  });

  it('preserves pipe characters inside cell content', () => {
    const table = {
      title: 'Pipes',
      headers: ['Expr', 'Result'],
      rows: [{ cells: ['1 | 2', '3'] }],
    };
    const md = tableToMarkdown(table);
    assert.ok(md.includes('| 1 | 2 | 3 |'));
  });
});
