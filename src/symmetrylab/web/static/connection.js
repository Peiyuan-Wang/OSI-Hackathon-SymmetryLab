'use strict';
const $ = id => document.getElementById(id);
let token = '';
function notice(text) { $('notice').textContent = text; $('notice').hidden = !text; }
async function bootstrap() { const b = await fetch('/api/bootstrap').then(r => r.json()); token = b.token; return b; }
async function api(path, data, retried = false) {
  const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json','X-SymmetryLab-Token':token}, body:JSON.stringify(data)});
  const value = await response.json();
  if (response.status === 403 && !retried) { await bootstrap(); return api(path, data, true); }
  if (!response.ok) throw new Error(value.error || 'Request failed');
  return value;
}
function form() {
  const v = {base_url:$('base-url').value.trim(), model:$('model').value.trim(), protocol:$('protocol').value};
  if ($('api-key').value.trim()) v.api_key = $('api-key').value.trim();
  return v;
}
function show(c) {
  $('base-url').value = c.base_url; $('model').value = c.model; $('protocol').value = c.protocol; $('api-key').value = '';
  $('api-key').placeholder = c.key_saved ? `Saved key ••••${c.key_hint} — paste a new one to replace` : (c.key_source === 'environment' ? 'Using SYMMETRYLAB_API_KEY from the environment' : 'Paste your API key');
  $('saved-state').textContent = c.ready ? 'Saved · ready for Live research' : 'Incomplete';
  $('side-status').textContent = c.ready ? `${c.model}\n${c.key_source === 'saved' ? 'Key saved' : 'Key from environment'}` : 'Not configured';
  $('forget').disabled = !c.key_saved;
}
async function busy(button, label, work) {
  const old = button.textContent; button.disabled = true; $('status').textContent = label; notice('');
  try { await work(); } catch (e) { $('status').textContent = e.message; } finally { button.disabled = false; button.textContent = old; }
}
$('test').onclick = () => busy($('test'), 'Testing service…', async () => {
  const r = await api('/api/connection/test', form()); $('status').textContent = `Connected · ${r.model} · real request succeeded. Click Save to keep these settings.`;
});
$('save').onclick = () => busy($('save'), 'Saving…', async () => { show(await api('/api/connection', form())); $('status').textContent = 'Saved on this computer.'; });
$('forget').onclick = () => {
  if (!confirm('Delete the saved API key from this computer?')) return;
  busy($('forget'), 'Removing key…', async () => { show(await api('/api/connection', {forget_key:true})); $('status').textContent = 'Saved key removed.'; });
};
(async () => { try { show((await bootstrap()).connection); } catch { notice('Workbench connection interrupted. Restart SymmetryLab.'); } })();
