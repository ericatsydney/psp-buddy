import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile, unlink, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { createCaptureClient, createCaptureServer } from '../../tools/ppsspp_capture_mcp.mjs';

test('demand-only request returns local metadata and never embeds image', async () => {
  const root = await mkdtemp(join(tmpdir(), 'capture-mcp-'));
  try {
    const client = await createCaptureClient(root, 'trial-1', { timeoutMs: 500 });
    const image = join(root, 'image.png');
    await writeFile(image, 'synthetic');
    const timer = setInterval(async () => {
      try {
        const request = JSON.parse(await readFile(join(root, 'capture-request.json'), 'utf8'));
        clearInterval(timer);
        const result = { path: image, sha256: 'a'.repeat(64), trial_id: 'trial-1',
          sequence: 1, reason: request.reason, size: [480, 272], captured_at: new Date().toISOString() };
        await writeFile(join(root, `capture-response-${request.request_id}.json`),
          JSON.stringify({ trial_id: 'trial-1', request_id: request.request_id, result }));
        await unlink(join(root, 'capture-request.json'));
      } catch (error) { if (error.code !== 'ENOENT') throw error; }
    }, 5);
    const result = await client.capture('new menu');
    assert.equal(result.content[0].type, 'text');
    assert.equal(JSON.parse(result.content[0].text).path, image);
    assert.equal(result.content.length, 1);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('invalid reason and pending request never publish another request', async () => {
  const root = await mkdtemp(join(tmpdir(), 'capture-mcp-'));
  try {
    const client = await createCaptureClient(root, 'trial-1');
    await assert.rejects(client.capture(''), /reason/);
    await writeFile(join(root, 'capture-request.json'), 'preserve');
    await assert.rejects(client.capture('new menu'), /pending/);
    assert.equal(await readFile(join(root, 'capture-request.json'), 'utf8'), 'preserve');
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('timeout is bounded and disables further requests', async () => {
  const root = await mkdtemp(join(tmpdir(), 'capture-mcp-'));
  try {
    const client = await createCaptureClient(root, 'trial-1', { timeoutMs: 30 });
    await assert.rejects(client.capture('ambiguous state'), /timed out/);
    await assert.rejects(client.capture('again'), /disabled/);
  } finally { await rm(root, { recursive: true, force: true }); }
});

for (const mode of ['duplicate', 'wrong-trial', 'outside']) {
  test(`rejects ${mode} response and disables requests`, async () => {
    const root = await mkdtemp(join(tmpdir(), 'capture-mcp-'));
    try {
      const client = await createCaptureClient(root, 'trial-1', { timeoutMs: 500 });
      const image = mode === 'outside' ? join(dirname(tmpdir()), 'outside.png') : join(root, 'image.png');
      if (mode !== 'outside') await writeFile(image, 'synthetic');
      const timer = setInterval(async () => {
        try {
          const request = JSON.parse(await readFile(join(root, 'capture-request.json'), 'utf8'));
          clearInterval(timer);
          const result = { path: image, sha256: 'a'.repeat(64), trial_id: 'trial-1',
            sequence: 1, reason: request.reason, size: [480, 272], captured_at: new Date().toISOString() };
          let raw = JSON.stringify({ trial_id: mode === 'wrong-trial' ? 'other' : 'trial-1', request_id: request.request_id, result });
          if (mode === 'duplicate') raw = raw.replace('{', '{"trial_id":"wrong",');
          await writeFile(join(root, `capture-response-${request.request_id}.json`), raw);
        } catch (error) { if (error.code !== 'ENOENT') throw error; }
      }, 5);
      await assert.rejects(client.capture('menu'), /duplicate|identity|outside capture evidence/);
      await assert.rejects(client.capture('again'), /disabled/);
    } finally { await rm(root, { recursive: true, force: true }); }
  });
}

test('MCP SDK lists exactly one tool and validates inputs over in-memory transport', async () => {
  const { InMemoryTransport } = await import('../../local/mcp-ppsspp/node_modules/@modelcontextprotocol/sdk/dist/esm/inMemory.js');
  const { Client } = await import('../../local/mcp-ppsspp/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js');
  const server = createCaptureServer({ capture: async () => ({ content: [{ type: 'text', text: '{}' }] }) });
  const [a, b] = InMemoryTransport.createLinkedPair();
  await server.connect(a);
  const client = new Client({ name: 'test', version: '1' });
  await client.connect(b);
  try {
    const tools = await client.listTools();
    assert.deepEqual(tools.tools.map(tool => tool.name), ['ppsspp_capture_screen']);
    await assert.rejects(client.callTool({ name: 'ppsspp_capture_screen', arguments: { reason: '' } }));
    const result = await client.callTool({ name: 'ppsspp_capture_screen', arguments: { reason: 'menu' } });
    assert.equal(result.content[0].type, 'text');
    await assert.rejects(client.callTool({ name: 'input', arguments: {} }));
  } finally { await client.close(); await server.close(); }
});
