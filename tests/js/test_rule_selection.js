const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const { onRuleSelected } = require('../../static/js/chat_rule_generation.js');

const existingRule = {
  id: '0d3a6f0e-6f3b-4a1e-9b7c-6f4d2a1e9c33',
  name: 'Noun Gender',
  description: 'Every Spanish noun has a gender.',
};

const proposedRule = {
  title: 'Masculine and feminine nouns',
  explanation: 'Nouns change form depending on gender.',
  canonical_rule_id: '6d1f0d2a-1c4b-4a7e-8c9d-0e1f2a3b4c5d',
};

const PAIR_ID = '2c1b0a9e-8d7c-4b6a-9f5e-3d2c1b0a9e8f';

function makeFakeRuleItem() {
  const classes = new Set();
  return {
    classList: {
      add: name => classes.add(name),
      remove: name => classes.delete(name),
      contains: name => classes.has(name),
    },
    addEventListener() {},
  };
}

function makeFakeElement(tagName) {
  return {
    tagName,
    className: '',
    innerHTML: '',
    textContent: '',
    dataset: {},
    children: [],
    classList: { add() {}, remove() {}, contains: () => false },
    append(...children) { this.children.push(...children); },
    appendChild(child) { this.children.push(child); },
    addEventListener() {},
    remove() {},
    scrollIntoView() {},
  };
}

describe('onRuleSelected', () => {
  let stubs;
  let item;
  let list;
  let siblings;
  let originals;

  // startRuleCreation and the render helpers it drives live in the same script as
  // onRuleSelected, so they cannot be swapped out. The creation pipeline is observed
  // through the request it sends, with the document and the stream stubbed out.
  function stubCreationPipeline() {
    globalThis.document = {
      getElementById: id => (id === 'language-pair-select' ? { value: PAIR_ID } : null),
      createElement: tagName => makeFakeElement(tagName),
    };
    globalThis.createProgressContainer = () => ({ marker: 'progress-container' });
    globalThis.appendToChat = element => stubs.creationStarted.push(element);
    globalThis.callAgentStream = async (payload, onEvent) => {
      stubs.creationRequests.push(payload);
      onEvent('done', { grammar_rule_id: 'new-rule-1', full_content: '# rule' });
    };
    globalThis.markProgressComplete = () => {};
    globalThis.updateProgress = () => {};
    globalThis.markdownToHtml = () => '';
    globalThis.persistFullRuleMessage = () => {};
    globalThis.persistTextMessage = () => {};
  }

  beforeEach(() => {
    stubs = {
      calls: [],
      warnings: [],
      creationStarted: [],
      creationRequests: [],
      duplicateResult: null,
    };

    originals = {};
    [
      'findDuplicateRule', 'appendDuplicateWarning', 'persistUserRuleSelectedMessage',
      'setChatSessionTitle', 'document', 'createProgressContainer', 'appendToChat',
      'callAgentStream', 'markdownToHtml', 'persistFullRuleMessage', 'persistTextMessage',
      'markProgressComplete', 'updateProgress',
    ].forEach(name => { originals[name] = globalThis[name]; });

    item = makeFakeRuleItem();
    siblings = [makeFakeRuleItem(), makeFakeRuleItem()];
    list = {
      querySelector: (selector) =>
        selector === '.proposed-rule-selected' && item.classList.contains('proposed-rule-selected')
          ? item
          : null,
      querySelectorAll: (selector) => (selector === '.proposed-rule' ? [item, ...siblings] : []),
    };

    globalThis.findDuplicateRule = async (rule) => {
      stubs.calls.push(`check:${rule.title}`);
      return stubs.duplicateResult;
    };
    globalThis.appendDuplicateWarning = (rule, existing, options) => {
      stubs.calls.push('warn');
      stubs.warnings.push({ rule, existing, options });
    };
    globalThis.persistUserRuleSelectedMessage = () => stubs.calls.push('echo');
    globalThis.setChatSessionTitle = () => {};
    stubCreationPipeline();
  });

  afterEach(async () => {
    // Let any in-flight creation pipeline finish before the real globals come back.
    await new Promise(resolve => setImmediate(resolve));
    Object.entries(originals).forEach(([name, value]) => { globalThis[name] = value; });
  });

  function dismissedStates() {
    return siblings.map(sibling => sibling.classList.contains('proposed-rule-dismissed'));
  }

  it('runs the duplicate check before starting creation', async () => {
    stubs.duplicateResult = existingRule;

    await onRuleSelected(item, list, proposedRule);

    assert.deepEqual(stubs.calls, ['echo', `check:${proposedRule.title}`, 'warn']);
    assert.equal(stubs.creationRequests.length, 0);
  });

  it('creates the rule straight away when no duplicate is found', async () => {
    await onRuleSelected(item, list, proposedRule);

    assert.equal(stubs.warnings.length, 0);
    assert.deepEqual(stubs.creationRequests, [{
      type: 'initial_rule',
      title: proposedRule.title,
      explanation: proposedRule.explanation,
      canonical_rule_id: proposedRule.canonical_rule_id,
    }]);
  });

  it('names the existing rule on the warning', async () => {
    stubs.duplicateResult = existingRule;

    await onRuleSelected(item, list, proposedRule);

    assert.equal(stubs.warnings[0].existing.name, 'Noun Gender');
  });

  it('leaves the other suggestions in place while the warning is shown', async () => {
    stubs.duplicateResult = existingRule;

    await onRuleSelected(item, list, proposedRule);

    assert.deepEqual(dismissedStates(), [false, false]);
  });

  it('Create anyway dismisses the other suggestions and starts the creation', async () => {
    stubs.duplicateResult = existingRule;
    await onRuleSelected(item, list, proposedRule);

    stubs.warnings[0].options.onProceed();
    await new Promise(resolve => setImmediate(resolve));

    assert.equal(stubs.creationRequests.length, 1);
    assert.deepEqual(dismissedStates(), [true, true]);
  });

  it('Cancel creates nothing and leaves the rule pickable again', async () => {
    stubs.duplicateResult = existingRule;
    await onRuleSelected(item, list, proposedRule);

    stubs.warnings[0].options.onCancel();
    await new Promise(resolve => setImmediate(resolve));

    assert.equal(stubs.creationRequests.length, 0);
    assert.equal(item.classList.contains('proposed-rule-selected'), false);
  });

  it('ignores a second click on an already selected rule', async () => {
    await onRuleSelected(item, list, proposedRule);
    const callsAfterFirstClick = stubs.calls.length;

    await onRuleSelected(item, list, proposedRule);

    assert.equal(stubs.calls.length, callsAfterFirstClick);
    assert.equal(stubs.creationRequests.length, 1);
  });
});
