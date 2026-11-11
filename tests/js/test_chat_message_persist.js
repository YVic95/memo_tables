const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const PERSISTENCE_SCRIPT = fs.readFileSync(
  path.join(__dirname, '../../static/js/chat_message_persist.js'),
  'utf8',
);

function loadPersistence() {
  const requests = [];
  const sandbox = {
    console: { warn() {} },
    getOrCreateChatSession: () => Promise.resolve('session-1'),
    fetch: (url, options) => {
      requests.push({ url, body: JSON.parse(options.body) });
      return Promise.resolve({ ok: true });
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(PERSISTENCE_SCRIPT, sandbox);
  return { sandbox, requests };
}

async function flushPersistenceQueue() {
  await new Promise((resolve) => setImmediate(resolve));
}

describe('persistTableMessage', () => {
  it('persists a single generated table from general_tables', async () => {
    const { sandbox, requests } = loadPersistence();
    const table = { title: 'Presente', headers: [], rows: [] };

    sandbox.persistTableMessage({ general_tables: [table] });
    await flushPersistenceQueue();

    assert.equal(requests.length, 1);
    assert.equal(requests[0].body.content.table.title, 'Presente');
  });

  it('does not persist a table from the removed singular field', async () => {
    const { sandbox, requests } = loadPersistence();

    sandbox.persistTableMessage({
      general_table: { title: 'Legacy', headers: [], rows: [] },
    });
    await flushPersistenceQueue();

    assert.deepEqual(requests, []);
  });

  it('persists every generated table and the grouped fragments', async () => {
    const { sandbox, requests } = loadPersistence();
    const generalTables = [
      { title: 'Number', headers: [], rows: [] },
      { title: 'Gender', headers: [], rows: [] },
    ];
    const fragments = [{ title: 'Singular', headers: [], rows: [] }];

    sandbox.persistTableMessage({
      general_tables: generalTables,
      fragmented_tables: fragments,
    });
    await flushPersistenceQueue();

    assert.deepEqual(
      requests.map((request) => request.body.content.table?.title
        ?? request.body.content.tables[0].title),
      ['Number', 'Gender', 'Singular'],
    );
    assert.equal(requests[2].body.content.grouped_fragmentation, true);
  });
});
