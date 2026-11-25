import assert from 'node:assert/strict';
import { afterEach, beforeEach, test } from 'node:test';
import { clearSession, createSession, currentSession, request } from '../src/services/api.js';

const originalFetch = globalThis.fetch;
const originalStorage = globalThis.localStorage;

function response(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  };
}

beforeEach(() => {
  const values = new Map();
  globalThis.localStorage = {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  globalThis.localStorage = originalStorage;
});

test('creates a session, then sends its token for private API requests', async () => {
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/sessions')) return response(200, { token: 'test-token' });
    if (url.endsWith('/households')) {
      return response(200, { household_id: 7, name: 'Gia đình thử' });
    }
    return response(200, { data: [] });
  };

  const session = await createSession('Gia đình thử');
  await request('/members?householdId=7');

  assert.deepEqual(session, { token: 'test-token', householdId: 7, name: 'Gia đình thử' });
  assert.equal(currentSession().householdId, 7);
  assert.equal(calls[0].options.headers.Authorization, undefined);
  assert.equal(calls[1].options.headers.Authorization, 'Bearer test-token');
  assert.equal(calls[2].options.headers.Authorization, 'Bearer test-token');
  clearSession();
  assert.equal(currentSession(), null);
});

test('keeps image uploads multipart without adding a JSON content type', async () => {
  let sent;
  globalThis.fetch = async (_url, options) => {
    sent = options;
    return response(201, { data: { mealId: 4, status: 'draft' } });
  };
  const body = new FormData();
  body.set('householdId', '7');

  const result = await request('/meals/analyze', { method: 'POST', body });

  assert.equal(sent.body, body);
  assert.equal(sent.headers['Content-Type'], undefined);
  assert.deepEqual(result.data, { mealId: 4, status: 'draft' });
});

test('explains a blocked confirmation without reporting success', async () => {
  globalThis.fetch = async () => response(409, {
    error: { code: 'HARD_CONSTRAINT_VIOLATION', message: 'Assessment lacks verified evidence' },
  });

  await assert.rejects(
    request('/meals/4/confirm', { method: 'POST', body: { eatenBy: [2] } }),
    (error) => error.status === 409 && error.message.includes('bản nháp'),
  );
});

test('clears an expired session on HTTP 401', async () => {
  globalThis.localStorage.setItem('nutriplan-session', JSON.stringify({ token: 'old-token' }));
  globalThis.fetch = async () => response(401, { error: { code: 'UNAUTHORIZED' } });

  await assert.rejects(request('/members'), (error) => error.status === 401);
  assert.equal(currentSession(), null);
});
