const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const {
  analyzeRestoreMessages,
  renderRestoredMessage,
} = require('../../static/js/chat_restore.js');
// The restore path reads both persisted shapes through the real helper, the same
// one the browser gets from the script tag, so the legacy branch is what is
// under test rather than a stub that agrees with it.
const { readExistingRules } = require('../../static/js/chat_duplicate_warning.js');

const proposedRules = {
  position: 1,
  role: 'assistant',
  message_type: 'proposed_rules',
  content: {
    rules: [
      { title: 'Masculine and feminine nouns', explanation: 'Nouns change form.', canonical_rule_id: 'canon-1' },
    ],
  },
};

const selectionEcho = {
  position: 2,
  role: 'user',
  message_type: 'text',
  content: { text: 'Masculine and feminine nouns: Nouns change form.' },
};

function duplicateWarning(position, existingRuleNames) {
  return {
    position,
    role: 'assistant',
    message_type: 'duplicate_warning',
    content: {
      proposed_rule: {
        title: 'Masculine and feminine nouns',
        explanation: 'Nouns change form.',
        canonical_rule_id: 'canon-1',
      },
      existing_rules: existingRuleNames.map((name, i) => ({ id: `rule-${i + 1}`, name, description: null })),
    },
  };
}

// Exactly the shape cards in chat_sessions carry from before #48.
function legacyDuplicateWarning(position, existingRuleName) {
  const message = duplicateWarning(position, [existingRuleName]);
  return {
    ...message,
    content: {
      proposed_rule: message.content.proposed_rule,
      existing_rule: { id: 'rule-1', name: existingRuleName, description: null },
    },
  };
}

const fullRule = {
  position: 4,
  role: 'assistant',
  message_type: 'full_rule',
  content: { grammar_rule_id: 'new-rule-1', full_content: '# rule' },
};

describe('analyzeRestoreMessages', () => {
  it('leaves a warning unresolved when no rule was created after it', () => {
    const restored = analyzeRestoreMessages([
      proposedRules,
      selectionEcho,
      duplicateWarning(3, ['Noun Gender']),
    ]);

    assert.deepEqual(Array.from(restored.resolvedWarningPositions), []);
  });

  it('resolves a warning once a full rule follows it', () => {
    const restored = analyzeRestoreMessages([
      proposedRules,
      selectionEcho,
      duplicateWarning(3, ['Noun Gender']),
      fullRule,
    ]);

    assert.deepEqual(Array.from(restored.resolvedWarningPositions), [3]);
  });

  it('only resolves the warnings a full rule came after', () => {
    const restored = analyzeRestoreMessages([
      proposedRules,
      selectionEcho,
      duplicateWarning(3, ['Noun Gender']),
      fullRule,
      duplicateWarning(6, ['Noun Gender']),
    ]);

    assert.deepEqual(Array.from(restored.resolvedWarningPositions), [3]);
  });

  it('still reads the selection echo when a warning sits between it and the rule', () => {
    const restored = analyzeRestoreMessages([
      proposedRules,
      selectionEcho,
      duplicateWarning(3, ['Noun Gender']),
      fullRule,
    ]);

    assert.deepEqual(Array.from(restored.selectionEchoPositions), [2]);
    assert.equal(
      restored.selectedTitleByList.get(1),
      'Masculine and feminine nouns'
    );
    assert.deepEqual(Array.from(restored.consumedLists), [1]);
  });

  it('leaves the proposed rules selectable when the warning was cancelled', () => {
    const restored = analyzeRestoreMessages([
      proposedRules,
      selectionEcho,
      duplicateWarning(3, ['Noun Gender']),
    ]);

    assert.deepEqual(Array.from(restored.consumedLists), []);
    assert.equal(restored.hasProposedRules, true);
  });
});

describe('renderRestoredMessage', () => {
  let originalAppendDuplicateWarning;
  let originalDocument;
  let renderedWarnings;
  let originalReadExistingRules;

  beforeEach(() => {
    originalAppendDuplicateWarning = globalThis.appendDuplicateWarning;
    originalDocument = globalThis.document;
    originalReadExistingRules = globalThis.readExistingRules;

    renderedWarnings = [];
    globalThis.appendDuplicateWarning = (proposedRule, existingRules, options) => {
      renderedWarnings.push({ proposedRule, existingRules, options });
    };
    globalThis.readExistingRules = readExistingRules;
    globalThis.document = {
      createElement: (tag) => makeFakeElement(tag),
      getElementById: () => makeFakeElement('div'),
    };
  });

  afterEach(() => {
    globalThis.appendDuplicateWarning = originalAppendDuplicateWarning;
    globalThis.document = originalDocument;
    globalThis.readExistingRules = originalReadExistingRules;
  });

  function makeFakeElement(tagName) {
    return {
      tagName,
      className: '',
      textContent: '',
      innerHTML: '',
      children: [],
      classList: { add() {}, remove() {}, contains() { return false; } },
      append(...children) { this.children.push(...children); },
      appendChild(child) { this.children.push(child); },
      addEventListener() {},
      remove() {},
      scrollIntoView() {},
    };
  }

  it('renders the warning from its persisted content', () => {
    const message = duplicateWarning(3, ['Noun Gender']);
    const restored = analyzeRestoreMessages([message]);

    renderRestoredMessage(message, restored, false, []);

    assert.equal(renderedWarnings.length, 1);
    assert.equal(renderedWarnings[0].proposedRule.title, 'Masculine and feminine nouns');
    assert.deepEqual(renderedWarnings[0].existingRules, [{ id: 'rule-1', name: 'Noun Gender', description: null }]);
  });

  it('renders a warning stored with the singular key from before #48', () => {
    // Without this, chat_restore.js could read `content.existing_rules` directly
    // and every card already in the database would restore empty. Asserting the
    // normaliser's own behaviour elsewhere is not the same as pinning the branch
    // that is only reachable from here.
    const message = legacyDuplicateWarning(3, 'Noun Gender');
    const restored = analyzeRestoreMessages([message]);

    renderRestoredMessage(message, restored, false, []);

    assert.equal(renderedWarnings.length, 1);
    assert.deepEqual(renderedWarnings[0].existingRules, [{ id: 'rule-1', name: 'Noun Gender', description: null }]);
  });

  it('renders a stored warning naming several rules in order', () => {
    const message = duplicateWarning(3, ['Usage of verb estar', 'Usage of verb ser']);
    const restored = analyzeRestoreMessages([message]);

    renderRestoredMessage(message, restored, false, []);

    assert.deepEqual(
      renderedWarnings[0].existingRules.map(rule => rule.name),
      ['Usage of verb estar', 'Usage of verb ser']
    );
  });

  it('marks a warning as resolved when the rule was created anyway', () => {
    const warning = duplicateWarning(3, ['Noun Gender']);
    const restored = analyzeRestoreMessages([warning, fullRule]);

    renderRestoredMessage(warning, restored, false, []);

    assert.equal(renderedWarnings[0].options.isResolved, true);
  });

  it('leaves a warning actionable when the creation never happened', () => {
    const warning = duplicateWarning(3, ['Noun Gender']);
    const restored = analyzeRestoreMessages([warning]);

    renderRestoredMessage(warning, restored, false, []);

    assert.equal(renderedWarnings[0].options.isResolved, false);
  });
});
