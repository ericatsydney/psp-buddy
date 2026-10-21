// Protected controller mailbox only: this process never connects to PPSSPP.
import { lstat, realpath, open, link, unlink, readdir } from 'node:fs/promises';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { setTimeout as delay } from 'node:timers/promises';
import { Server } from '../local/mcp-ppsspp/node_modules/@modelcontextprotocol/sdk/dist/esm/server/index.js';
import { StdioServerTransport } from '../local/mcp-ppsspp/node_modules/@modelcontextprotocol/sdk/dist/esm/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '../local/mcp-ppsspp/node_modules/@modelcontextprotocol/sdk/dist/esm/types.js';

const CONTEXTS = ['map','unit_commands','info','move_range','weapon_list','target_select','attack_forecast','result','system_menu','enemy_phase'];
const PURPOSES = ['cursor','open_unit_menu','menu_direction','open_info','cancel','open_move','move_cursor','confirm_move','open_attack','select_weapon','select_target','choose_target','confirm_attack','standby_after_move','dismiss_result','open_system_menu','system_menu_move','end_turn','advance_dialog'];
const CIRCLE_PURPOSES = ['open_unit_menu','open_info','open_move','confirm_move','open_attack','select_weapon','choose_target','standby_after_move','dismiss_result','open_system_menu','end_turn','advance_dialog'];
function validate(operation, args) {
  if (!args || typeof args !== 'object' || Array.isArray(args)) throw new Error('Invalid arguments');
  if (operation === 'weapons') {
    if (Object.keys(args).length !== 2 || !Number.isSafeInteger(args.sequence) || args.sequence < 1 ||
        !Number.isSafeInteger(args.object) || args.object < 0x08800000 || args.object >= 0x0A000000) throw new Error('Invalid weapons request');
    return;
  }
  if (operation === 'targets') {
    const keys = Object.keys(args);
    if (!keys.includes('sequence') || !keys.includes('object') || keys.some(k => !['sequence','object','moved'].includes(k)) ||
        !Number.isSafeInteger(args.sequence) || args.sequence < 1 || !Number.isSafeInteger(args.object) ||
        args.object < 0x08800000 || args.object >= 0x0A000000 || (Object.hasOwn(args,'moved') && typeof args.moved !== 'boolean')) throw new Error('Invalid targets request');
    return;
  }
  if (operation === 'hit') {
    if (Object.keys(args).length !== 1 || !Number.isSafeInteger(args.sequence) || args.sequence < 1) throw new Error('Invalid hit request');
    return;
  }
  if (operation === 'state') {
    if (Object.keys(args).length !== 1 || !Number.isSafeInteger(args.sequence) || args.sequence < 1) throw new Error('Invalid state request');
    return;
  }
  if (operation === 'act') {
    const keys = Object.keys(args);
    const base = ['sequence','screen_file','screen_sha256','context','unit_object'];
    const objectOk = (n) => Number.isSafeInteger(n) && n >= 0x08800000 && n < 0x0A000000;
    const a = args.attack;
    if (keys.some(k => ![...base,'move_to','attack','commit','phase'].includes(k)) || !base.every(k => Object.hasOwn(args,k)) ||
        !Number.isSafeInteger(args.sequence) || args.sequence < 1 || typeof args.screen_file !== 'string' ||
        !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,254}\.(png|jpg|jpeg)$/i.test(args.screen_file) || !/^[0-9a-f]{64}$/.test(args.screen_sha256 ?? '') ||
        !['map','attack_forecast'].includes(args.context) || !objectOk(args.unit_object) ||
        (Object.hasOwn(args,'phase') && !['run','fire'].includes(args.phase)) ||
        (args.context === 'attack_forecast') !== (args.phase === 'fire') ||
        (Object.hasOwn(args,'commit') && typeof args.commit !== 'boolean') ||
        (Object.hasOwn(args,'move_to') && (!Array.isArray(args.move_to) || args.move_to.length !== 2 || !args.move_to.every(Number.isSafeInteger))) ||
        (Object.hasOwn(args,'attack') && (!a || typeof a !== 'object' || !['target_object,weapon','slot,target_object,weapon'].includes(Object.keys(a).sort().join()) || typeof a.weapon !== 'string' ||
          (Object.hasOwn(a,'slot') && (!Number.isSafeInteger(a.slot) || a.slot < 0 || a.slot > 20)) ||
          a.weapon.length < 1 || a.weapon.length > 64 || !objectOk(a.target_object))) ||
        (!Object.hasOwn(args,'move_to') && !Object.hasOwn(args,'attack'))) throw new Error('Invalid act request');
    return;
  }
  if (operation === 'plan_act') {
    const keys = Object.keys(args);
    const base = ['sequence','screen_file','screen_sha256','context','unit_object','policy'];
    const objectOk = (n) => Number.isSafeInteger(n) && n >= 0x08800000 && n < 0x0A000000;
    if (keys.some(k => ![...base,'bosses','min_hit'].includes(k)) || !base.every(k => Object.hasOwn(args,k)) ||
        !Number.isSafeInteger(args.sequence) || args.sequence < 1 || typeof args.screen_file !== 'string' ||
        !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,254}\.(png|jpg|jpeg)$/i.test(args.screen_file) || !/^[0-9a-f]{64}$/.test(args.screen_sha256 ?? '') ||
        args.context !== 'map' || !objectOk(args.unit_object) || typeof args.policy !== 'string' || args.policy.length > 400 ||
        (Object.hasOwn(args,'bosses') && (!Array.isArray(args.bosses) || args.bosses.length > 8 || !args.bosses.every(objectOk))) ||
        (Object.hasOwn(args,'min_hit') && (!Number.isSafeInteger(args.min_hit) || args.min_hit < 1 || args.min_hit > 100))) throw new Error('Invalid plan_act request');
    return;
  }
  const common = ['sequence','screen_file','screen_sha256','context'];
  const fields = operation === 'press' ? [...common,'button','duration','purpose','cursor_tile','highlighted_entry','destination_tile','weapon_name','target_name'] : operation === 'goto' ? [...common,'target'] : operation === 'probe_move' ? [...common,'tile'] : common;
  if (!['press','verify','observe','dump','state','targets','hit','goto','probe_move'].includes(operation) || Object.keys(args).some(k=>!fields.includes(k)) ||
      !common.every(k=>Object.hasOwn(args,k)) || !Number.isSafeInteger(args.sequence) || args.sequence < 1 ||
      typeof args.screen_file !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,254}\.(png|jpg|jpeg)$/i.test(args.screen_file) ||
      !/^[0-9a-f]{64}$/.test(args.screen_sha256 ?? '') || !CONTEXTS.includes(args.context)) throw new Error('Invalid navigation evidence');
  if (operation === 'verify' && args.context !== 'info') throw new Error('Info context required');
  if (operation === 'probe_move' && (args.context !== 'map' || !Array.isArray(args.tile) || args.tile.length !== 2 || !args.tile.every(Number.isSafeInteger))) throw new Error('probe_move needs the map context and an integer [x,y] tile');
  if (operation === 'goto' && (args.context !== 'map' || !Array.isArray(args.target) || args.target.length !== 2 || !args.target.every(Number.isSafeInteger))) throw new Error('goto needs the map context and an integer [x,y] target');
  if (operation === 'press') {
    if (!['up','down','left','right','circle','cross','start'].includes(args.button) || !Number.isSafeInteger(args.duration) || args.duration<1 || args.duration>3 ||
        !PURPOSES.includes(args.purpose)) throw new Error('Invalid bounded input');
    if (args.button === 'circle' && !CIRCLE_PURPOSES.includes(args.purpose)) throw new Error('Unsafe confirm');
    if (args.button === 'start' && args.purpose !== 'confirm_attack') throw new Error('Unsafe start');
    if (args.purpose === 'confirm_attack' && args.button !== 'start') throw new Error('Start required');
    if (args.purpose === 'open_unit_menu' && (!Array.isArray(args.cursor_tile) || args.cursor_tile.length!==2 || !args.cursor_tile.every(Number.isSafeInteger))) throw new Error('Cursor tile required');
    const entry = {open_info:'Info',open_move:'Move',open_attack:'Attack',standby_after_move:'Standby'}[args.purpose];
    if (entry && args.highlighted_entry !== entry) throw new Error('Command highlight required');
    if (args.destination_tile !== undefined && (!Array.isArray(args.destination_tile) || args.destination_tile.length!==2 || !args.destination_tile.every(Number.isSafeInteger))) throw new Error('Invalid destination tile');
    for (const k of ['weapon_name','target_name']) if (args[k] !== undefined && (typeof args[k] !== 'string' || args[k].length > 64)) throw new Error('Invalid name');
    if (args.cursor_tile !== undefined && (!Array.isArray(args.cursor_tile) || args.cursor_tile.length!==2 || !args.cursor_tile.every(Number.isSafeInteger))) throw new Error('Invalid cursor tile');
    if (args.highlighted_entry !== undefined && (typeof args.highlighted_entry !== 'string' || args.highlighted_entry.length < 1 || args.highlighted_entry.length > 64)) throw new Error('Invalid highlighted entry');
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

export async function createNavigationClient(mailbox, trialId, { timeoutMs = 125000 } = {}) {
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(trialId)) throw new Error('Invalid trial ID');
  if (!Number.isFinite(timeoutMs) || timeoutMs < 1 || timeoutMs > 125000) throw new Error('Invalid timeout');
  const root = resolve(mailbox);
  await safeDirectory(root);
  let busy = false;
  let disabled = false;
  return {
    async execute(operation, args) {
      validate(operation, args);
      if (disabled) throw new Error('Capture bridge disabled after uncertain or failed request');
      if (busy) throw new Error('Capture request already pending');
      busy = true;
      let published = false;
      try {
        await safeDirectory(root);
        if ((await readdir(root)).includes('nav-request.json')) throw new Error('Capture request pending');
        const requestId = randomUUID().replaceAll('-', '');
        const temporary = join(root, `.request-${requestId}.tmp`);
        const pending = join(root, 'nav-request.json');
        const destination = join(root, `nav-response-${requestId}.json`);
        const handle = await open(temporary, 'wx');
        try {
          await handle.writeFile(JSON.stringify({ trial_id: trialId, request_id: requestId, operation, arguments: args }));
          await handle.sync();
        } finally { await handle.close(); }
        try { await link(temporary, pending); published = true; }
        finally { await unlink(temporary); }
        const deadline = Date.now() + Math.min(timeoutMs, operation === 'press' ? 15000 : (operation === 'goto' || operation === 'probe_move' || operation === 'act' || operation === 'plan_act') ? 125000 : 65000);
        while (Date.now() < deadline) {
          await safeDirectory(root);
          let value;
          try { value = await readSafe(destination); }
          catch (error) { if (error.code !== 'ENOENT') throw error; }
          if (value !== undefined) {
            if (!value || value.trial_id !== trialId || value.request_id !== requestId) throw new Error('Wrong capture response identity');
            if (Object.keys(value).sort().join() !== 'request_id,result,trial_id' && Object.keys(value).sort().join() !== 'error,request_id,trial_id') throw new Error('Invalid response schema');
            if (Object.hasOwn(value,'error')) throw new Error(String(value.error).startsWith('refused: ') ? String(value.error) : 'Protected navigation failed');
            const result = value.result;
            if (!result || typeof result !== 'object' || Array.isArray(result)) throw new Error('Invalid navigation metadata');
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

export function createNavigationServer(client) {
  const server = new Server({ name: 'protected-ppsspp-navigation', version: '1.0.0' }, { capabilities: { tools: {} } });
  const common = {sequence:{type:'integer',minimum:1},screen_file:{type:'string'},screen_sha256:{type:'string',pattern:'^[0-9a-f]{64}$'},context:{enum:CONTEXTS}};
  const tools = [
    {name:'ppsspp_press_button',description:'One protected, screenshot-grounded input; battle actions only when declared for this trial.',inputSchema:{type:'object',properties:{...common,button:{enum:['up','down','left','right','circle','cross','start']},duration:{type:'integer',minimum:1,maximum:3},purpose:{enum:PURPOSES},cursor_tile:{type:'array',items:{type:'integer'},minItems:2,maxItems:2},highlighted_entry:{type:'string',minLength:1,maxLength:64},destination_tile:{type:'array',items:{type:'integer'},minItems:2,maxItems:2},weapon_name:{type:'string',maxLength:64},target_name:{type:'string',maxLength:64}},required:[...Object.keys(common),'button','duration','purpose'],additionalProperties:false}},
    {name:'ppsspp_observe',description:'Save one raw coherent memory sample for the current stage; sends no input.',inputSchema:{type:'object',properties:common,required:Object.keys(common),additionalProperties:false}},
    {name:'ppsspp_dump_ram',description:'Save one read-only dump of PSP user RAM for offline comparison; sends no input.',inputSchema:{type:'object',properties:common,required:Object.keys(common),additionalProperties:false}},
    {name:'ppsspp_read_state',description:'Read units, map terrain/cost, cursor tile and turn from memory; sends no input.',inputSchema:{type:'object',properties:{sequence:{type:'integer',minimum:1}},required:['sequence'],additionalProperties:false}},
    {name:'ppsspp_read_weapons',description:'Read the weapons of one unit (power, range, ammo, EN, flags) and pilot skills from memory by its unit object; sends no input.',inputSchema:{type:'object',properties:{sequence:{type:'integer',minimum:1},object:{type:'integer',minimum:0x08800000,maximum:0x09FFFFFF}},required:['sequence','object'],additionalProperties:false}},
    {name:'ppsspp_read_targets',description:'For each weapon of one unit, list the enemy units in range from its current tile (memory only, Manhattan distance). Set moved when the unit has already moved this turn.',inputSchema:{type:'object',properties:{sequence:{type:'integer',minimum:1},object:{type:'integer',minimum:0x08800000,maximum:0x09FFFFFF},moved:{type:'boolean'}},required:['sequence','object'],additionalProperties:false}},
    {name:'ppsspp_read_hit',description:'Read the hit chance under the cursor from memory; meaningful only while a weapon target select is open (-10000 = not a target). Sends no input.',inputSchema:{type:'object',properties:{sequence:{type:'integer',minimum:1}},required:['sequence'],additionalProperties:false}},
    {name:'ppsspp_goto_tile',description:'Walk the map cursor to a tile, verifying every step from the cursor field; cursor presses only.',inputSchema:{type:'object',properties:{...common,target:{type:'array',items:{type:'integer'},minItems:2,maxItems:2}},required:[...Object.keys(common),'target'],additionalProperties:false}},
    {name:'ppsspp_probe_move_range',description:'View only: walk to an ally, open its Move range, read the reachable tiles from memory, back out. Needs the probe declaration.',inputSchema:{type:'object',properties:{...common,tile:{type:'array',items:{type:'integer'},minItems:2,maxItems:2}},required:[...Object.keys(common),'tile'],additionalProperties:false}},
    {name:'ppsspp_plan_act',description:'From a policy text alone: pick one legal Move + Attack for one ready ally unit, run it to the attack forecast and fire only if the forecast agrees with the plan (otherwise back out and report why). min_hit (default 1) is the lowest forecast hit% it will fire at. Appends each fired attack to damage-log.jsonl. Needs the act declaration and a fresh map screenshot.',inputSchema:{type:'object',properties:{...common,unit_object:{type:'integer',minimum:0x08800000,maximum:0x09FFFFFF},policy:{type:'string',maxLength:400},bosses:{type:'array',items:{type:'integer',minimum:0x08800000,maximum:0x09FFFFFF},maxItems:8},min_hit:{type:'integer',minimum:1,maximum:100}},required:[...Object.keys(common),'unit_object','policy'],additionalProperties:false}},
    {name:'ppsspp_act',description:'Follow one tactical instruction for one ally unit with memory checks at every stage: select, optional Move to a tile, optional Attack with a named weapon on a target object. commit=false stops at the attack forecast; phase=fire (with an attack_forecast screenshot) presses Start and dismisses the result. Needs the act declaration.',inputSchema:{type:'object',properties:{...common,unit_object:{type:'integer',minimum:0x08800000,maximum:0x09FFFFFF},move_to:{type:'array',items:{type:'integer'},minItems:2,maxItems:2},attack:{type:'object',properties:{weapon:{type:'string',minLength:1,maxLength:64},slot:{type:'integer',minimum:0,maximum:20},target_object:{type:'integer',minimum:0x08800000,maximum:0x09FFFFFF}},required:['weapon','target_object'],additionalProperties:false},commit:{type:'boolean'},phase:{enum:['run','fire']}},required:[...Object.keys(common),'unit_object'],additionalProperties:false}},
    {name:'ppsspp_verify_info',description:'Verify selected Destiny Info through the protected controller.',inputSchema:{type:'object',properties:common,required:Object.keys(common),additionalProperties:false}},
  ];
  server.setRequestHandler(ListToolsRequestSchema, async()=>({tools}));
  server.setRequestHandler(CallToolRequestSchema,async({params})=>{
    const operation = {ppsspp_press_button:'press',ppsspp_verify_info:'verify',ppsspp_observe:'observe',ppsspp_dump_ram:'dump',ppsspp_read_state:'state',ppsspp_read_weapons:'weapons',ppsspp_read_targets:'targets',ppsspp_read_hit:'hit',ppsspp_goto_tile:'goto',ppsspp_probe_move_range:'probe_move',ppsspp_act:'act',ppsspp_plan_act:'plan_act'}[params.name] ?? null;
    validate(operation,params.arguments);
    return client.execute(operation,params.arguments);
  });
  return server;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv.length !== 4) throw new Error('Usage: node tools/ppsspp_navigation_mcp.mjs MAILBOX TRIAL_ID');
  const client = await createNavigationClient(process.argv[2], process.argv[3]);
  await createNavigationServer(client).connect(new StdioServerTransport());
}
