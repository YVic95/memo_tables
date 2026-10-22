const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const {
  CANONICAL_RULES_PAIR_STORAGE_KEY,
  initCanonicalRulesPairPersistence,
} = require('../../static/js/canonical_rules_pair.js');

const PAIR_ID = '2c1b0a9e-8d7c-4b6a-9f5e-3d2c1b0a9e8f';
const OTHER_PAIR_ID = '9f8e7d6c-5b4a-3928-1716-0f1e2d3c4b5a';
const PANEL_URL = '/admin-panel/canonical-rules/panel';

// A stand-in for the browser: the select carries the pair the server rendered,
// the panel says what the server already shows, and the document holds the
// listeners the script registers.
function makeFakeBrowser({ renderedPairId = '', selectedPairId = '' } = {}) {
  const listeners = { change: [], 'htmx:load': [] };
  const panelRequests = [];
  const replacedUrls = [];

  const select = {
    id: 'canonical-rules-pair-select',
    value: selectedPairId,
    options: [PAIR_ID, OTHER_PAIR_ID].map(pairId => ({ value: pairId })),
    getAttribute: name => (name === 'hx-get' ? PANEL_URL : null),
    dispatchEvent: event => {
      if (event.type === 'change') {
        listeners.change.forEach(handler => handler({ type: 'change', target: select }));
      }
      return true;
    },
  };

  const panel = { id: 'canonical-rules-panel', dataset: { pairId: renderedPairId } };

  const doc = {
    getElementById: id => {
      if (id === 'canonical-rules-pair-select') return select;
      if (id === 'canonical-rules-panel') return panel;
      return null;
    },
    addEventListener: (type, handler) => { listeners[type].push(handler); },
    dispatch: (type, target = doc) => {
      listeners[type].forEach(handler => handler({ type, target }));
    },
  };

  const storage = {
    entries: new Map(),
    getItem: key => (storage.entries.has(key) ? storage.entries.get(key) : null),
    setItem: (key, value) => { storage.entries.set(key, String(value)); },
    removeItem: key => { storage.entries.delete(key); },
  };

  const sessionStorage = {
    entries: new Map(),
    getItem: key => (sessionStorage.entries.has(key) ? sessionStorage.entries.get(key) : null),
    setItem: (key, value) => { sessionStorage.entries.set(key, String(value)); },
  };

  const window = {
    location: { href: 'http://testserver/admin-panel/canonical-rules' },
    history: {
      state: null,
      replaceState: (state, title, url) => { replacedUrls.push(url); },
    },
    sessionStorage,
  };

  // htmx would issue GET PANEL_URL and swap the response into the panel.
  const browser = { failRequests: false };
  const htmx = {
    ajax: (verb, path, options) => {
      panelRequests.push({ verb, path, options });
      if (browser.failRequests) {
        return Promise.reject(new Error('network down'));
      }
      panel.dataset.pairId = options.values.pair_id;
      return Promise.resolve();
    },
  };

  return Object.assign(browser, {
    doc, select, panel, storage, window, sessionStorage, htmx, panelRequests, replacedUrls,
  });
}

describe('canonical rules language pair persistence', () => {
  let originals;
  let browser;

  function startBrowser(options) {
    const started = makeFakeBrowser(options);
    globalThis.localStorage = started.storage;
    globalThis.window = started.window;
    globalThis.document = started.doc;
    globalThis.htmx = started.htmx;
    initCanonicalRulesPairPersistence(started.doc);
    return started;
  }

  function selectPair(pairId) {
    browser.select.value = pairId;
    browser.select.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function storedPairId() {
    return browser.storage.getItem(CANONICAL_RULES_PAIR_STORAGE_KEY);
  }

  beforeEach(() => {
    originals = {};
    ['document', 'localStorage', 'window', 'htmx'].forEach(name => {
      originals[name] = globalThis[name];
    });
    browser = startBrowser();
  });

  afterEach(() => {
    Object.entries(originals).forEach(([name, value]) => { globalThis[name] = value; });
  });

  it('remembers the pair the admin selects', () => {
    selectPair(PAIR_ID);

    assert.equal(storedPairId(), PAIR_ID);
    assert.match(browser.replacedUrls[0], new RegExp(`pair_id=${PAIR_ID}`));
  });

  it('remembers a different pair when the admin changes the selection', () => {
    selectPair(PAIR_ID);
    selectPair(OTHER_PAIR_ID);

    assert.equal(storedPairId(), OTHER_PAIR_ID);
    assert.match(browser.replacedUrls[1], new RegExp(`pair_id=${OTHER_PAIR_ID}`));
  });

  it("keeps htmx's history cache key in step with the mirrored pair", () => {
    browser.sessionStorage.setItem(
      'htmx-current-path-for-history',
      '/admin-panel/canonical-rules'
    );

    selectPair(PAIR_ID);

    assert.equal(
      browser.sessionStorage.getItem('htmx-current-path-for-history'),
      `/admin-panel/canonical-rules?pair_id=${PAIR_ID}`
    );
  });

  it('forgets the selection when it is cleared', () => {
    browser.storage.setItem(CANONICAL_RULES_PAIR_STORAGE_KEY, PAIR_ID);
    selectPair('');

    assert.equal(storedPairId(), null);
    assert.doesNotMatch(browser.replacedUrls[0], /pair_id=/);
  });

  it('ignores changes to other controls', () => {
    browser.doc.dispatch('change', { id: 'some-other-select', value: PAIR_ID });

    assert.equal(storedPairId(), null);
    assert.equal(browser.replacedUrls.length, 0);
  });

  it('asks the server for the rules of the remembered pair', () => {
    browser.storage.setItem(CANONICAL_RULES_PAIR_STORAGE_KEY, PAIR_ID);

    browser.doc.dispatch('htmx:load');

    assert.equal(browser.select.value, PAIR_ID);
    assert.equal(browser.panelRequests.length, 1);
    assert.deepEqual(browser.panelRequests[0], {
      verb: 'GET',
      path: PANEL_URL,
      options: {
        target: browser.panel,
        swap: 'outerHTML',
        values: { pair_id: PAIR_ID },
      },
    });
    assert.match(browser.replacedUrls[0], new RegExp(`pair_id=${PAIR_ID}`));
  });

  it('asks only once when htmx processes the same section several times', () => {
    browser.storage.setItem(CANONICAL_RULES_PAIR_STORAGE_KEY, PAIR_ID);

    browser.doc.dispatch('htmx:load');
    browser.doc.dispatch('htmx:load');
    browser.doc.dispatch('htmx:load');

    assert.equal(browser.panelRequests.length, 1);
  });

  it('leaves the section empty when no pair was ever selected', () => {
    browser.doc.dispatch('htmx:load');

    assert.equal(browser.select.value, '');
    assert.equal(browser.panelRequests.length, 0);
    assert.equal(browser.replacedUrls.length, 0);
    assert.equal(storedPairId(), null);
  });

  it('does not ask for the rules the server already rendered', () => {
    browser = startBrowser({ renderedPairId: PAIR_ID, selectedPairId: PAIR_ID });
    browser.storage.setItem(CANONICAL_RULES_PAIR_STORAGE_KEY, PAIR_ID);

    browser.doc.dispatch('htmx:load');

    assert.equal(browser.select.value, PAIR_ID);
    assert.equal(browser.panelRequests.length, 0);
    assert.equal(browser.replacedUrls.length, 0);
  });

  it('asks for the rules again when the server rendered another pair', () => {
    browser = startBrowser({ renderedPairId: OTHER_PAIR_ID, selectedPairId: OTHER_PAIR_ID });
    browser.storage.setItem(CANONICAL_RULES_PAIR_STORAGE_KEY, PAIR_ID);

    browser.doc.dispatch('htmx:load');

    assert.equal(browser.select.value, PAIR_ID);
    assert.equal(browser.panelRequests.length, 1);
    assert.equal(browser.panelRequests[0].options.values.pair_id, PAIR_ID);
    assert.match(browser.replacedUrls[0], new RegExp(`pair_id=${PAIR_ID}`));
  });

  it('tries again when the rules request fails', async () => {
    browser.storage.setItem(CANONICAL_RULES_PAIR_STORAGE_KEY, PAIR_ID);
    browser.failRequests = true;

    browser.doc.dispatch('htmx:load');
    await Promise.resolve();
    await Promise.resolve();

    assert.equal(browser.panel.dataset.pairId, '');

    browser.failRequests = false;
    browser.doc.dispatch('htmx:load');

    assert.equal(browser.panelRequests.length, 2);
    assert.equal(browser.panel.dataset.pairId, PAIR_ID);
  });

  it('ignores a remembered pair that is not on offer', () => {
    browser.storage.setItem(CANONICAL_RULES_PAIR_STORAGE_KEY, 'a-pair-that-is-gone');

    browser.doc.dispatch('htmx:load');

    assert.equal(browser.select.value, '');
    assert.equal(browser.panelRequests.length, 0);
  });
});
