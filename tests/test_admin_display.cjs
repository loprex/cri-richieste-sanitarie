const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('app/static/admin.js','utf8');
const section=source.split("let csrf='';")[0];
assert.ok(section.includes('function humanValue('),'formatter missing');
const context={};
vm.runInNewContext(section,context);
assert.equal(context.humanValue([{date:'2026-10-25',start:'14:00',end:'18:00'}],'event_slots'),
 '25/10/2026 dalle 14:00–18:00');
assert.equal(context.humanValue([{date:'2026-10-25',start:'14:00',end:'18:00'},{date:'2026-10-26',start:'09:00',end:'12:00'}],'event_slots'),
 '25/10/2026 dalle 14:00–18:00; 26/10/2026 dalle 09:00–12:00');
assert.equal(context.humanValue([],'venue_context'),'Nessuno');
assert.equal(context.humanValue(true),'Sì');
assert.equal(context.humanValue(false),'No');
assert.equal(context.humanLabel('event_slots'),'Date e fasce orarie');
assert.equal(context.humanValue({date:'2026-10-25',start:'14:00',end:'18:00'}).includes('[object Object]'),false);
assert.equal(context.humanValue([{a:'<script>',b:2}]).includes('[object Object]'),false);
assert.ok(source.includes('esc(humanValue(v,k))'),'detail must HTML-escape displayed value');
assert.ok(source.includes('response.arrayBuffer()'),'download must fetch bytes');
assert.ok(source.includes('magic[0]!==0x50'),'download must check ZIP header');
assert.ok(source.includes("link.download="),'download must force a file save');
console.log('CRI_ADMIN_DISPLAY_AND_DOWNLOAD=PASS');
