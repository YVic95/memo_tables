const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

function loadMarkdown() {
  const sandbox = {};
  vm.createContext(sandbox);
  vm.runInContext(
    fs.readFileSync(
      path.join(__dirname, '../../static/js/markdown_to_html.js'),
      'utf8',
    ),
    sandbox,
  );
  return sandbox;
}

describe('markdownInline', () => {
  it('marks adjectives inside bold phrases with the highlight class', () => {
    const { markdownInline } = loadMarkdown();

    assert.equal(
      markdownInline('**el libro *rojo* / los libros *rojos***'),
      '<strong>el libro <em class="adj-highlight">rojo</em> / los libros <em class="adj-highlight">rojos</em></strong>',
    );
  });

  it('keeps standalone italics (translations) unhighlighted', () => {
    const { markdownInline } = loadMarkdown();

    assert.equal(
      markdownInline('*the red book*'),
      '<em>the red book</em>',
    );
  });

  it('keeps plain bold phrases working', () => {
    const { markdownInline } = loadMarkdown();

    assert.equal(
      markdownInline('**el libro / los libros**'),
      '<strong>el libro / los libros</strong>',
    );
  });

  it('escapes raw HTML instead of passing it through', () => {
    const { markdownInline } = loadMarkdown();

    assert.equal(
      markdownInline('a <script>alert(1)</script> b'),
      'a &lt;script&gt;alert(1)&lt;/script&gt; b',
    );
  });

  it('leaves unmatched markers literal', () => {
    const { markdownInline } = loadMarkdown();

    assert.equal(markdownInline('a * b'), 'a * b');
    assert.equal(markdownInline('**oops'), '**oops');
  });
});

describe('markdownToHtml rule bodies', () => {
  it('highlights adjectives in numbered examples with clean nesting', () => {
    const { markdownToHtml } = loadMarkdown();

    const html = markdownToHtml(
      '## Grammar Rule: Plurals\n\n### Examples:\n1. **el libro *rojo* / los libros *rojos*** — the red book',
    );

    assert.match(html, /<li>.*<strong>el libro <em class="adj-highlight">rojo<\/em>/);
    assert.doesNotMatch(html, /<\/strong><\/em>|<\/em><\/strong><\/em>/);
  });
});
