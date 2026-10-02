const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const {
  findDuplicateRule,
  buildDuplicateWarningContent,
  appendDuplicateWarning,
  readExistingRules,
} = require('../../static/js/chat_duplicate_warning.js');

const existingRule = {
  id: '0d3a6f0e-6f3b-4a1e-9b7c-6f4d2a1e9c33',
  name: 'Noun Gender',
  description: 'Every Spanish noun has a gender.',
};

// The two other ser/estar rules, best-fitting first after `existingRule`.
const secondRule = {
  id: 'a1b2c3d4-1111-4222-8333-444455556666',
  name: 'Usage of verb estar',
  description: 'Estar covers temporary states and locations.',
};

const thirdRule = {
  id: 'a1b2c3d4-1111-4222-8333-444455556667',
  name: 'Usage of verb ser',
  description: 'Ser covers permanent traits and facts.',
};

const proposedRule = {
  title: 'Masculine and feminine nouns',
  explanation: 'Nouns change form depending on gender.',
  canonical_rule_id: '6d1f0d2a-1c4b-4a7e-8c9d-0e1f2a3b4c5d',
};

// The warning card is built with plain DOM calls, so the tests drive it through a
// minimal stand-in for the browser document. Clicking a button means invoking the
// handler it registered.
function makeFakeElement(tagName) {
  const classes = new Set();
  const listeners = {};
  let className = '';

  return {
    tagName,
    get className() { return className; },
    // The real DOM keeps className and classList in step; the fake has to as well,
    // because the card is built by assigning className and queried via classList.
    set className(value) {
      className = value;
      classes.clear();
      value.split(/\s+/).filter(Boolean).forEach(name => classes.add(name));
    },
    get textContent() {
      // The real DOM concatenates text nodes and nested elements' text.
      return this.children
        .map(child => (typeof child === 'string' ? child : child.textContent))
        .join('');
    },
    set textContent(value) { this.children = [value]; },
    innerHTML: '',    children: [],
    removed: false,
    classList: {
      add: (...names) => names.forEach(name => classes.add(name)),
      remove: (...names) => names.forEach(name => classes.delete(name)),
      contains: name => classes.has(name),
    },
    append(...children) { this.children.push(...children); },
    appendChild(child) { this.children.push(child); },
    addEventListener(type, handler) { listeners[type] = handler; },
    remove() { this.removed = true; },
    scrollIntoView() {},
    click(type) { listeners[type](); },
  };
}

function findByClassName(root, className) {
  if (root.classList && root.classList.contains(className)) {
    return root;
  }
  for (const child of root.children) {
    if (typeof child === 'string') continue;
    const found = findByClassName(child, className);
    if (found) return found;
  }
  return null;
}

describe('findDuplicateRule', () => {
  let originalCallAgent;

  beforeEach(() => {
    originalCallAgent = globalThis.callAgent;
  });

  afterEach(() => {
    globalThis.callAgent = originalCallAgent;
  });

  function stubCheck(response) {
    const calls = [];
    globalThis.callAgent = async (payload) => {
      calls.push(payload);
      if (response instanceof Error) throw response;
      return response;
    };
    return calls;
  }

  it('asks the duplicate check about the proposed title and explanation', async () => {
    const calls = stubCheck({ similar: false, existing_rules: [] });

    await findDuplicateRule(proposedRule);

    assert.equal(calls.length, 1);
    assert.equal(calls[0].type, 'check_similar');
    assert.equal(calls[0].title, proposedRule.title);
    assert.equal(calls[0].explanation, proposedRule.explanation);
  });

  it('returns every matching rule when a duplicate is found', async () => {
    stubCheck({ similar: true, existing_rules: [existingRule] });

    const found = await findDuplicateRule(proposedRule);

    assert.deepEqual(found, [existingRule]);
  });

  it('keeps the ranking the check gave rather than reordering it', async () => {
    stubCheck({ similar: true, existing_rules: [existingRule, secondRule, thirdRule] });

    const found = await findDuplicateRule(proposedRule);

    assert.deepEqual(found.map(rule => rule.name), [
      'Noun Gender', 'Usage of verb estar', 'Usage of verb ser',
    ]);
  });

  it('returns null when no similar rule exists', async () => {
    stubCheck({ similar: false, existing_rules: [] });

    assert.equal(await findDuplicateRule(proposedRule), null);
  });

  it('returns null when the check reports a match without naming a rule', async () => {
    stubCheck({ similar: true, existing_rules: [] });

    assert.equal(await findDuplicateRule(proposedRule), null);
  });

  it('returns null when the duplicate check request fails', async () => {
    stubCheck(new Error('agent request failed'));

    assert.equal(await findDuplicateRule(proposedRule), null);
  });
});

describe('buildDuplicateWarningContent', () => {
  it('carries the proposed rule so a restored card can still create it', () => {
    const content = buildDuplicateWarningContent(proposedRule, [existingRule]);

    assert.deepEqual(content.proposed_rule, proposedRule);
  });

  it('names the existing rule that matched', () => {
    const content = buildDuplicateWarningContent(proposedRule, [existingRule]);

    assert.deepEqual(content.existing_rules, [existingRule]);
  });
});

describe('appendDuplicateWarning', () => {
  let stubs;

  beforeEach(() => {
    stubs = {
      appended: [],
      persisted: [],
      createdRules: [],
      originalDocument: globalThis.document,
      originalCreateContainer: globalThis.createRuleMessageContainer,
      originalAppendToChat: globalThis.appendToChat,
      originalPersist: globalThis.persistDuplicateWarningMessage,
      originalStartRuleCreation: globalThis.startRuleCreation,
    };

    globalThis.document = { createElement: () => makeFakeElement('div') };
    globalThis.createRuleMessageContainer = () => makeFakeElement('div');
    globalThis.appendToChat = (element) => stubs.appended.push(element);
    globalThis.persistDuplicateWarningMessage = (content) => stubs.persisted.push(content);
    globalThis.startRuleCreation = (rule) => stubs.createdRules.push(rule);
  });

  afterEach(() => {
    globalThis.document = stubs.originalDocument;
    globalThis.createRuleMessageContainer = stubs.originalCreateContainer;
    globalThis.appendToChat = stubs.originalAppendToChat;
    globalThis.persistDuplicateWarningMessage = stubs.originalPersist;
    globalThis.startRuleCreation = stubs.originalStartRuleCreation;
  });

  function lastCard() {
    const container = stubs.appended[stubs.appended.length - 1];
    return findByClassName(container, 'duplicate-warning');
  }

  it('names the existing rule that matched', () => {
    appendDuplicateWarning(proposedRule, [existingRule]);

    const card = lastCard();
    assert.equal(findByClassName(card, 'duplicate-warning-text').textContent,
      'You already have a rule called Noun Gender.');
  });

  it('persists the warning so a refresh can re-render it', () => {
    appendDuplicateWarning(proposedRule, [existingRule]);

    assert.equal(stubs.persisted.length, 1);
    assert.deepEqual(stubs.persisted[0], buildDuplicateWarningContent(proposedRule, [existingRule]));
  });

  it('offers Create anyway and Cancel', () => {
    appendDuplicateWarning(proposedRule, [existingRule]);

    const card = lastCard();
    assert.ok(findByClassName(card, 'duplicate-warning-actions'));
    assert.ok(findByClassName(card, 'save-button'));
    assert.ok(findByClassName(card, 'duplicate-warning-cancel'));
  });

  it('Create anyway dismisses the card and starts the creation', () => {
    appendDuplicateWarning(proposedRule, [existingRule]);

    const card = lastCard();
    findByClassName(card, 'save-button').click('click');

    assert.equal(stubs.appended[0].removed, true);
    assert.deepEqual(stubs.createdRules, [proposedRule]);
  });

  it('Cancel dismisses the card and creates nothing', () => {
    appendDuplicateWarning(proposedRule, [existingRule]);

    const card = lastCard();
    findByClassName(card, 'duplicate-warning-cancel').click('click');

    assert.equal(stubs.appended[0].removed, true);
    assert.deepEqual(stubs.createdRules, []);
  });

  it('runs the cancel handler so the caller can undo its own selection state', () => {
    let wasCancelled = false;
    appendDuplicateWarning(proposedRule, [existingRule], {
      onCancel: () => { wasCancelled = true; },
    });

    findByClassName(lastCard(), 'duplicate-warning-cancel').click('click');

    assert.equal(wasCancelled, true);
  });

  it('offers no buttons once the rule has been created anyway', () => {
    appendDuplicateWarning(proposedRule, [existingRule], { isResolved: true });

    const card = lastCard();
    assert.ok(card.classList.contains('duplicate-warning-resolved'));
    assert.equal(findByClassName(card, 'duplicate-warning-actions'), null);
  });

  it('skips a warning that is missing the proposed or existing rule', () => {
    appendDuplicateWarning(null, [existingRule]);

    assert.equal(stubs.appended.length, 0);
    assert.equal(stubs.persisted.length, 0);
  });
});

describe('the card when several rules match', () => {
  let stubs;

  beforeEach(() => {
    stubs = {
      appended: [],
      persisted: [],
      createdRules: [],
      originalDocument: globalThis.document,
      originalCreateContainer: globalThis.createRuleMessageContainer,
      originalAppendToChat: globalThis.appendToChat,
      originalPersist: globalThis.persistDuplicateWarningMessage,
      originalStartRuleCreation: globalThis.startRuleCreation,
    };

    globalThis.document = { createElement: (tag) => makeFakeElement(tag) };
    globalThis.createRuleMessageContainer = () => makeFakeElement('div');
    globalThis.appendToChat = (element) => stubs.appended.push(element);
    globalThis.persistDuplicateWarningMessage = (content) => stubs.persisted.push(content);
    globalThis.startRuleCreation = (rule) => stubs.createdRules.push(rule);
  });

  afterEach(() => {
    globalThis.document = stubs.originalDocument;
    globalThis.createRuleMessageContainer = stubs.originalCreateContainer;
    globalThis.appendToChat = stubs.originalAppendToChat;
    globalThis.persistDuplicateWarningMessage = stubs.originalPersist;
    globalThis.startRuleCreation = stubs.originalStartRuleCreation;
  });

  function lastCard() {
    const container = stubs.appended[stubs.appended.length - 1];
    return findByClassName(container, 'duplicate-warning');
  }

  function listNames(card) {
    const list = findByClassName(card, 'duplicate-warning-list');
    return list.children.map(item => item.textContent);
  }

  it('lists all three rules best-fitting first', () => {
    appendDuplicateWarning(proposedRule, [existingRule, secondRule, thirdRule]);

    assert.deepEqual(listNames(lastCard()), [
      'Noun Gender', 'Usage of verb estar', 'Usage of verb ser',
    ]);
  });

  it('counts the rules rather than naming one of them', () => {
    appendDuplicateWarning(proposedRule, [existingRule, secondRule, thirdRule]);

    assert.match(
      findByClassName(lastCard(), 'duplicate-warning-text').textContent,
      /^You already have 3 rules that may cover the same ground:/
    );
  });

  it('counts two rules as two', () => {
    appendDuplicateWarning(proposedRule, [existingRule, secondRule]);

    assert.match(
      findByClassName(lastCard(), 'duplicate-warning-text').textContent,
      /^You already have 2 rules that may cover the same ground:/
    );
  });

  it('keeps the singular wording when only one rule matches', () => {
    appendDuplicateWarning(proposedRule, [existingRule]);

    const card = lastCard();
    assert.equal(findByClassName(card, 'duplicate-warning-text').textContent,
      'You already have a rule called Noun Gender.');
    assert.equal(findByClassName(card, 'duplicate-warning-list'), null);
  });

  it('does not pad the list when the check named one of three', () => {
    appendDuplicateWarning(proposedRule, [existingRule]);

    assert.equal(findByClassName(lastCard(), 'duplicate-warning-list'), null);
  });

  it('persists the ranked list so a refresh re-renders it in order', () => {
    appendDuplicateWarning(proposedRule, [existingRule, secondRule, thirdRule]);

    assert.deepEqual(
      stubs.persisted[0].existing_rules.map(rule => rule.name),
      ['Noun Gender', 'Usage of verb estar', 'Usage of verb ser']
    );
  });

  it('skips a warning carrying an empty list', () => {
    appendDuplicateWarning(proposedRule, []);

    assert.equal(stubs.appended.length, 0);
    assert.equal(stubs.persisted.length, 0);
  });
});

describe('readExistingRules', () => {
  it('reads the ranked list a new message carries', () => {
    const content = { existing_rules: [existingRule, secondRule] };

    assert.deepEqual(readExistingRules(content), [existingRule, secondRule]);
  });

  it('reads the single rule a message persisted before #48 carries', () => {
    // Without this, every warning already in the database loses its content on
    // refresh and the admin sees an empty card.
    assert.deepEqual(readExistingRules({ existing_rule: existingRule }), [existingRule]);
  });

  it('prefers the list when a message somehow carries both shapes', () => {
    const content = { existing_rules: [existingRule], existing_rule: secondRule };

    assert.deepEqual(readExistingRules(content), [existingRule]);
  });

  it('returns nothing when neither shape is present', () => {
    assert.deepEqual(readExistingRules({}), []);
    assert.deepEqual(readExistingRules({ existing_rules: [] }), []);
  });
});
