import test from 'node:test';
import assert from 'node:assert/strict';
import { createNavigationServer } from '../../tools/ppsspp_navigation_mcp.mjs';
import { InMemoryTransport } from '../../local/mcp-ppsspp/node_modules/@modelcontextprotocol/sdk/dist/esm/inMemory.js';
import { Client } from '../../local/mcp-ppsspp/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js';
const args = {sequence:1,screen_file:'frame.png',screen_sha256:'a'.repeat(64),context:'map',button:'left',duration:2,purpose:'cursor'};
test('SDK exposes only bounded navigation tools and rejects unsafe arguments', async () => {
 const calls=[]; const server=createNavigationServer({execute:async (...values)=>{calls.push(values);return {content:[{type:'text',text:'{}'}]};}});
 const [a,b]=InMemoryTransport.createLinkedPair(); await server.connect(a);const client=new Client({name:'test',version:'1'});await client.connect(b);
 try {assert.deepEqual((await client.listTools()).tools.map(t=>t.name),['ppsspp_press_button','ppsspp_observe','ppsspp_dump_ram','ppsspp_read_state','ppsspp_verify_info']);
 await client.callTool({name:'ppsspp_press_button',arguments:args});assert.equal(calls.length,1);
 for (const changed of [{button:'start'},{duration:0},{extra:1},{screen_file:'../x.png'},{button:'circle',purpose:'cursor'},{button:'start',purpose:'cursor'},{button:'circle',purpose:'confirm_attack'}]) await assert.rejects(client.callTool({name:'ppsspp_press_button',arguments:{...args,...changed}}));
 await client.callTool({name:'ppsspp_read_state',arguments:{sequence:3}});assert.equal(calls.length,2);
 for (const bad of [{},{sequence:0},{sequence:1,screen_file:'x.png'},{sequence:'1'}]) await assert.rejects(client.callTool({name:'ppsspp_read_state',arguments:bad}));
 } finally {await client.close();await server.close();}
});
