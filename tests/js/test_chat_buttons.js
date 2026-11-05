const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const CHAT_TAB_INIT_SCRIPT = fs.readFileSync(
  path.join(__dirname, '../../static/js/chat_tab_init.js'),
  'utf8',
);
const CHAT_SESSION_SCRIPT = fs.readFileSync(
  path.join(__dirname, '../../static/js/chat_session.js'),
  'utf8',
);

const CLOSE_BUTTON_LABEL = '<i class="fa-solid fa-power-off"></i> Close Chat Session';
const CLOSING_SPINNER = '<i class="fa-solid fa-spinner fa-spin-pulse"></i> Closing...';

function makeButton(initialClasses = []) {
  const classes = new Set(initialClasses);
  const listeners = {};
  const element = {
    dataset: {},
    disabled: false,
    innerHTML: '',
    value: '',
    listeners,
    classList: {
      add(...names) { names.forEach((name) => classes.add(name)); },
      remove(...names) { names.forEach((name) => classes.delete(name)); },
      contains(name) { return classes.has(name); },
    },
    addEventListener(type, handler) {
      listeners[type] = [...(listeners[type] || []), handler];
    },
    removeAttribute() {},
  };
  // Mirror real DOM semantics: className and classList stay in sync.
  Object.defineProperty(element, 'className', {
    get() { return [...classes].join(' '); },
    set(value) {
      classes.clear();
      String(value).split(/\s+/).filter(Boolean).forEach((name) => classes.add(name));
    },
  });
  return element;
}

function loadChatTabInit(overrides = {}) {
  const buttons = {
    '#add-language-pair': makeButton(),
    '#propose-missing-rules': makeButton(['save-button']),
    '#generate-table-btn': makeButton(['save-button', 'hidden-button']),
    '#language-pair-dropdown': makeButton(['hidden']),
    '#language-pair-select': makeButton(),
    '#close-chat-session-btn': makeButton(['panel-button', 'hidden-button']),
  };
  buttons['#generate-table-btn'].dataset.ruleId = 'rule-1';
  buttons['#generate-table-btn'].innerHTML = '<i class="fa-solid fa-table"></i> Generate the Table';
  buttons['#close-chat-session-btn'].innerHTML = CLOSE_BUTTON_LABEL;
  buttons['#language-pair-select'].value = 'pair-1';

  const registry = {
    loader: makeButton(),
    'edit-table-btn': makeButton(['panel-button', 'hidden-button']),
    'check-tables-before-save': makeButton(['panel-button', 'hidden-button']),
  };

  const docListeners = {};
  const sandbox = {
    console: { log() {}, error() {}, warn() {} },
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    document: {
      addEventListener(type, handler) { docListeners[type] = handler; },
      getElementById(id) { return registry[id] || null; },
      querySelectorAll() { return []; },
    },
    generateTable: async () => ({}),
    displayGeneratedTables() {},
    setWorkflowStep() {},
    loadLanguagePairs: async () => {},
    enableProposeMissingRulesButton() {},
    hideProposeMissingRulesButton() {},
    callAgent: async () => ({ rules: [] }),
    appendRuleMessage() {},
    restoreActiveChatIfAny() {},
    closeChatSession: async () => {},
    showToast() {},
    ...overrides,
  };
  vm.createContext(sandbox);
  vm.runInContext(CHAT_TAB_INIT_SCRIPT, sandbox);

  const container = {
    querySelector(selector) { return buttons[selector] || null; },
  };
  return { sandbox, buttons, registry, docListeners, container };
}

function initTab(ctx) {
  ctx.docListeners['htmx:load']({ target: ctx.container });
}

describe('chat tab button visibility', () => {
  it('keeps the generate button styling class across the hide/show cycle', async () => {
    const ctx = loadChatTabInit();
    initTab(ctx);
    const generateBtn = ctx.buttons['#generate-table-btn'];

    await generateBtn.listeners.click[0]();
    assert.equal(generateBtn.listeners.click.length, 1);

    // Hidden after click, but the styling class must survive so that a later
    // classList.remove('hidden-button') brings back a styled button.
    assert.equal(generateBtn.classList.contains('hidden-button'), true);
    assert.equal(generateBtn.classList.contains('save-button'), true);
  });

  it('keeps the propose button styling class when it is hidden', async () => {
    const ctx = loadChatTabInit();
    initTab(ctx);
    const proposeBtn = ctx.buttons['#propose-missing-rules'];

    await proposeBtn.listeners.click[0]();

    assert.equal(proposeBtn.classList.contains('hidden-button'), true);
    assert.equal(proposeBtn.classList.contains('save-button'), true);
  });

  it('does not duplicate click handlers when the tab re-initializes', () => {
    const ctx = loadChatTabInit();
    initTab(ctx);
    initTab(ctx);

    for (const selector of ['#close-chat-session-btn', '#generate-table-btn', '#propose-missing-rules', '#add-language-pair']) {
      assert.equal(ctx.buttons[selector].listeners.click.length, 1, selector);
    }
    assert.equal(ctx.buttons['#language-pair-select'].listeners.change.length, 1);
  });
});

describe('resetChatUI', () => {
  function loadChatSession(overrides = {}) {
    const registry = {
      'chat-messages': makeButton(),
      'chat-input': makeButton(),
      'send-message': makeButton(),
      'generate-table-btn': makeButton(['save-button', 'hidden-button']),
      'edit-table-btn': makeButton(['panel-button']),
      'reapply-edits-btn': makeButton(['panel-button']),
      'check-tables-before-save': makeButton(['panel-button']),
      'close-chat-session-btn': makeButton(['panel-button']),
      'propose-missing-rules': makeButton(['save-button']),
      'add-language-pair': makeButton(),
      'language-pair-dropdown': makeButton(),
      'language-pair-select': makeButton(),
    };
    const sandbox = {
      console: { log() {}, error() {}, warn() {} },
      localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
      document: {
        addEventListener() {},
        getElementById(id) { return registry[id] || null; },
        querySelectorAll() { return []; },
      },
      fetch: async () => { throw new Error('no network in tests'); },
      closeTablePreview() {},
      ...overrides,
    };
    vm.createContext(sandbox);
    vm.runInContext(CHAT_SESSION_SCRIPT, sandbox);
    return { sandbox, registry };
  }

  it('restores the close button label instead of leaving the spinner', () => {
    const { sandbox, registry } = loadChatSession();
    const closeBtn = registry['close-chat-session-btn'];
    closeBtn.innerHTML = CLOSING_SPINNER;
    closeBtn.disabled = true;

    vm.runInContext('resetChatUI()', sandbox);

    assert.equal(closeBtn.innerHTML, CLOSE_BUTTON_LABEL);
    assert.equal(closeBtn.disabled, false);
  });

  it('keeps the generate button styling class across click and reset', async () => {
    const tabCtx = loadChatTabInit();
    initTab(tabCtx);
    const generateBtn = tabCtx.buttons['#generate-table-btn'];
    await generateBtn.listeners.click[0]();

    const { sandbox } = loadChatSession();
    sandbox.document.getElementById = (id) => {
      if (id === 'generate-table-btn') return generateBtn;
      if (id === 'close-chat-session-btn') return tabCtx.buttons['#close-chat-session-btn'];
      return null;
    };
    vm.runInContext('resetChatUI()', sandbox);

    assert.equal(generateBtn.classList.contains('save-button'), true);
  });
});
