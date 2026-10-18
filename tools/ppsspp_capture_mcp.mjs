// Protected controller mailbox only: this process never connects to PPSSPP.
import { lstat, realpath, open, link, unlink, readdir } from 'node:fs/promises';
import { resolve, dirname, join, isAbsolute, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { setTimeout as delay } from 'node:timers/promises';
import { Server } from '../local/mcp-ppsspp/node_modules/@modelcontextprotocol/sdk/dist/esm/server/index.js';
import { StdioServerTransport } from '../local/mcp-ppsspp/node_modules/@modelcontextprotocol/sdk/dist/esm/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '../local/mcp-ppsspp/node_modules/@modelcontextprotocol/sdk/dist/esm/types.js';

function reasonCheck(reason) {
  if (typeof reason !== 'string' || !reason.trim() || reason.length > 512 || /[\x00-\x1f]/.test(reason)) {
    throw new Error('A nonempty visual-evidence reason of at most 512 characters is required');
  }
}

async function safeDirectory(root) {
  let current = root;
  while (true) {
    const info = await lstat(current);
    if (!info.isDirectory() || info.isSymbolicLink() || resolve(await realpath(current)).toLowerCase() !== current.toLowerCase()) {
      throw new Error('Unsafe mailbox directory or linked parent');
    }
    const parent = dirname(current);
    if (parent === current) break;
    current = parent;
  }
}

async function readSafe(path) {
  const info = await lstat(path);
  if (!info.isFile() || info.isSymbolicLink() || info.nlink !== 1 || info.size > 16384) {
    throw new Error('Unsafe or oversized response');
  }
  const handle = await open(path, 'r');
  try {
    const actual = await handle.stat();
    if (actual.ino !== info.ino || actual.dev !== info.dev) throw new Error('Response replaced');
    const bytes = Buffer.alloc(16385);
    const { bytesRead } = await handle.read(bytes, 0, bytes.length, 0);
    if (bytesRead > 16384) throw new Error('Oversized response');
    const raw = new TextDecoder('utf-8', { fatal: true }).decode(bytes.subarray(0, bytesRead));
    const parsed = JSON.parse(raw);
    // JSON.parse accepts duplicate names. Scan its already-validated token stream
    // to reject those before trusting identity or metadata fields.
    const frames = [];
    for (const token of raw.match(/"(?:\\.|[^"\\])*"|[{}\[\],:]|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g) ?? []) {
      const frame = frames.at(-1);
      if (token === '{' || token === '[') frames.push({ object: token === '{', key: true, names: new Set() });
      else if (token === '}' || token === ']') frames.pop();
      else if (token === ',' && frame?.object) frame.key = true;
      else if (token.startsWith('"') && frame?.object && frame.key) {
        const name = JSON.parse(token);
        if (frame.names.has(name)) throw new Error('duplicate JSON response key');
        frame.names.add(name);
        frame.key = false;
      }
    }
    return parsed;
  } finally { await handle.close(); }
}

export async function createCaptureClient(mailbox, trialId, { timeoutMs = 15000 } = {}) {
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(trialId)) throw new Error('Invalid trial ID');
  if (!Number.isFinite(timeoutMs) || timeoutMs < 1 || timeoutMs > 15000) throw new Error('Invalid timeout');
  const root = resolve(mailbox);
  await safeDirectory(root);
  let busy = false;
  let disabled = false;
  return {
    async capture(reason) {
      reasonCheck(reason);
      if (disabled) throw new Error('Capture bridge disabled after uncertain or failed request');
      if (busy) throw new Error('Capture request already pending');
      busy = true;
      let published = false;
      try {
        await safeDirectory(root);
        if ((await readdir(root)).includes('capture-request.json')) throw new Error('Capture request pending');
        const requestId = randomUUID().replaceAll('-', '');
        const temporary = join(root, `.request-${requestId}.tmp`);
        const pending = join(root, 'capture-request.json');
        const destination = join(root, `capture-response-${requestId}.json`);
        const handle = await open(temporary, 'wx');
        try {
          await handle.writeFile(JSON.stringify({ trial_id: trialId, request_id: requestId, reason }));
          await handle.sync();
        } finally { await handle.close(); }
        try { await link(temporary, pending); published = true; }
        finally { await unlink(temporary); }
        const deadline = Date.now() + timeoutMs;
        while (Date.now() < deadline) {
          await safeDirectory(root);
          let value;
          try { value = await readSafe(destination); }
          catch (error) { if (error.code !== 'ENOENT') throw error; }
          if (value !== undefined) {
            if (!value || value.trial_id !== trialId || value.request_id !== requestId) throw new Error('Wrong capture response identity');
            if (typeof value.error === 'string') throw new Error(value.error);
            const result = value.result;
            if (!result || !isAbsolute(result.path ?? '') || !/^[0-9a-f]{64}$/.test(result.sha256 ?? '') ||
                result.trial_id !== trialId || result.reason !== reason || !Number.isSafeInteger(result.sequence) ||
                result.sequence < 1 || !Array.isArray(result.size) || result.size.length !== 2 ||
                !result.size.every(n => Number.isSafeInteger(n) && n > 0 && n <= 4096) ||
                typeof result.captured_at !== 'string' || !Number.isFinite(Date.parse(result.captured_at))) {
              throw new Error('Invalid capture metadata');
            }
            for (const path of [result.path, result.metadata_path].filter(path => path !== undefined)) {
              if (typeof path !== 'string' || !isAbsolute(path)) throw new Error('Invalid local capture path');
              const within = relative(dirname(root), resolve(path));
              if (within === '..' || within.startsWith('..\\') || within.startsWith('../') || isAbsolute(within)) {
                throw new Error('Path outside capture evidence');
              }
              await safeDirectory(dirname(path));
            }
            const imageInfo = await lstat(result.path);
            if (!imageInfo.isFile() || imageInfo.isSymbolicLink() || imageInfo.nlink !== 1) throw new Error('Unsafe capture image');
            return { content: [{ type: 'text', text: JSON.stringify(result) }] };
          }
          await delay(Math.min(25, Math.max(1, deadline - Date.now())));
        }
        throw new Error('Capture request timed out; no retry is permitted');
      } catch (error) {
        if (published) disabled = true;
        throw error;
      } finally { busy = false; }
    },
  };
}

export function createCaptureServer(client) {
  const server = new Server({ name: 'protected-ppsspp-capture', version: '1.0.0' }, { capabilities: { tools: {} } });
  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: [{
    name: 'ppsspp_capture_screen', description: 'Capture fresh visual evidence only when memory and retained evidence are insufficient. Returns local metadata.',
    inputSchema: { type: 'object', properties: { reason: { type: 'string', minLength: 1, maxLength: 512 } }, required: ['reason'], additionalProperties: false },
  }] }));
  server.setRequestHandler(CallToolRequestSchema, async ({ params }) => {
    if (params.name !== 'ppsspp_capture_screen') throw new Error('Unknown tool');
    if (!params.arguments || Object.keys(params.arguments).join() !== 'reason') throw new Error('Only reason is accepted');
    reasonCheck(params.arguments.reason);
    return client.capture(params.arguments.reason);
  });
  return server;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv.length !== 4) throw new Error('Usage: node tools/ppsspp_capture_mcp.mjs MAILBOX TRIAL_ID');
  const client = await createCaptureClient(process.argv[2], process.argv[3]);
  await createCaptureServer(client).connect(new StdioServerTransport());
}
