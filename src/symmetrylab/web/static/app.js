'use strict';
const $ = id => document.getElementById(id);
let token = '', selected = null, current = null, polling = false, reportVersion = '', activeRun = null, renderedVersion = '';
function el(tag, text, className) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (className) e.className = className; return e; }
function notice(text) { $('notice').textContent = text; $('notice').hidden = !text; }
async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-SymmetryLab-Token':token},body:JSON.stringify(data)});
  const value = await response.json(); if (!response.ok) throw new Error(value.error || 'Request failed'); return value;
}
function connection() { return {base_url:$('base-url').value.trim(), model:$('model').value.trim(), protocol:$('protocol').value, auth_mode:$('preset').value === 'cc_switch' ? 'cc_switch' : 'environment', api_key_env:$('key-env').value.trim()}; }
function connectionView() {
  const cc = $('preset').value === 'cc_switch'; $('key-field').hidden = cc;
  $('connection-help').textContent = cc ? 'Enable Codex routing in CC Switch and enter a supported model ID. CC Switch supplies the upstream key.' : 'Set the named environment variable before starting this server. Never paste API keys here. Base URL excludes /responses or /chat/completions.';
}
$('preset').addEventListener('change', () => { if ($('preset').value === 'cc_switch') { $('base-url').value = 'http://127.0.0.1:15721/v1'; $('protocol').value = 'responses'; } else { $('base-url').value = ''; $('protocol').value = 'chat_completions'; } connectionView(); });
$('mode').addEventListener('change', () => { const live = $('mode').value === 'live'; $('mode-note').textContent = live ? 'The model plans, generates candidates and chooses tools from observed feedback.' : 'Simulated decisions, real exact mathematics. No API calls.'; if (live) $('settings').open = true; });
$('connection-link').onclick = () => { $('settings').open = true; $('settings').scrollIntoView({behavior:'smooth',block:'center'}); };
$('new-run').onclick = () => { $('goal').focus(); $('goal').scrollIntoView({behavior:'smooth',block:'center'}); };
$('test').onclick = async () => {
  $('test').disabled = true; $('connection-status').textContent = 'Testing service…';
  try { const result = await api('/api/connection/test', connection()); $('connection-status').textContent = `Connected · ${result.model} · real request succeeded`; }
  catch (error) { $('connection-status').textContent = error.message; }
  finally { $('test').disabled = Boolean(activeRun); }
};
$('start').onclick = async () => {
  notice(''); $('start').disabled = true;
  try {
    if ($('mode').value === 'live' && !$('model').value.trim()) throw new Error('Enter your provider’s model ID in Model connection before starting live research.');
    const turns = Number($('calls').value); if (!Number.isInteger(turns) || turns < 1 || turns > 50) throw new Error('Model-turn budget must be between 1 and 50.');
    const result = await api('/api/runs', {goal:$('goal').value, mode:$('mode').value, connection:connection(), limits:{max_model_calls:turns}});
    selected = result.run_id; activeRun = selected; reportVersion = ''; await refresh();
  } catch (error) { notice(error.message); $('start').disabled = Boolean(activeRun); }
};
$('stop').onclick = async () => { try { await api(`/api/runs/${selected}/cancel`, {}); notice('Stop requested. Any in-flight model request may take up to 60 seconds to return.'); $('stop').disabled = true; } catch (e) { notice(e.message); } };
function details(parent, title, value) { const box = el('details'); box.append(el('summary',title),el('pre',JSON.stringify(value,null,2))); parent.append(box); }
function renderTimeline(state) {
  $('plan').replaceChildren(...state.plan.map(step => el('li',step))); $('plan').hidden = !state.plan.length;
  const events = state.events.filter(e => e.kind !== 'thinking' && e.kind !== 'tool');
  $('timeline').replaceChildren(...events.map(event => {
    const item = el('div',undefined,'event'); const d = event.data;
    item.append(el('small',`${event.kind.toUpperCase().replaceAll('_',' ')} · ${event.seconds}s`));
    if (event.kind === 'plan') { item.append(el('h3','Research plan updated'),el('p',d.action.reason || d.observation.steps.join(' → '))); }
    else if (event.kind === 'hypothesis') { item.append(el('h3',d.observation.id + ' · Unverified proposal'),el('p',d.observation.statement)); }
    else if (event.kind === 'tool_call') {
      item.append(el('h3',d.name.replaceAll('_',' ')),el('p',d.reason || 'Executing mathematical tool'));
      const resultEvent = state.events.find(e => e.index > event.index && ['tool','action_error'].includes(e.kind));
      details(item,'Tool arguments & observation',{arguments:d.arguments,observation:resultEvent?.data.observation || resultEvent?.data || 'In progress'});
      const observation = resultEvent?.data.observation;
      if (observation?.status === 'Counterexample found') item.append(el('p',`Counterexample found: ${observation.counterexamples.join(', ')}. Feedback retained for the next turn.`));
    } else if (event.kind === 'synthesis') { item.append(el('h3','Model synthesis · unverified'),el('p',d.text)); }
    else if (event.kind === 'action_error') { item.append(el('h3','Feedback returned to policy'),el('p',d.message)); }
    else if (event.kind === 'started') item.append(el('h3',d.policy));
    else if (event.kind === 'finished') item.append(el('h3',`Run ${d.status.replaceAll('_',' ')}`));
    return item;
  }));
}
function renderCandidates(state) {
  $('candidate-count').textContent = `${state.candidates.length} candidates`;
  if (!state.candidates.length) { $('candidates').replaceChildren(el('p','No candidates registered yet.','scope-note')); return; }
  $('candidates').replaceChildren(...state.candidates.map(candidate => {
    const result = [...state.evidence].reverse().find(e => e.candidate_id === candidate.case_id && !e.target_id);
    const item = el('div',undefined,'candidate'), top = el('div',undefined,'candidate-top'), title = el('div');
    title.append(el('small',`${candidate.case_id} · ${candidate.group.name} · ${candidate.dimension}D`),el('h3',candidate.label));
    top.append(title,el('span',result ? result.result.status.replaceAll('_',' ') : 'Awaiting check',result?.certificate_verified ? 'badge':'badge warn')); item.append(top);
    if (result) item.append(el('p',result.certificate_verified ? `Certificate verified · ${result.result.certificate.kind.replaceAll('_',' ')}` : 'No certified mathematical classification.'));
    const visual = el('div',undefined,'matrix-preview');
    for (const op of candidate.operations) { visual.append(el('pre',`${op.name}: R = ${JSON.stringify(op.R)}\ns = ${op.s}    q = ${JSON.stringify(op.q)}${result?.result.theta ? '\nθ = '+JSON.stringify(result.result.theta) : ''}`)); }
    item.append(visual); details(item,'Inspect exact evidence',{case:candidate,verification:result || null}); return item;
  }));
}
async function loadReport() {
  if (!selected || !current?.metrics) return;
  const audience = $('audience').value, url = `/api/runs/${selected}/report?audience=${audience}`;
  const runId = selected;
  const response = await fetch(url); const text = await response.text();
  if (runId !== selected || audience !== $('audience').value) return;
  if (response.ok) $('report').textContent = text;
  $('download-md').href = url + '&download=1'; $('download-json').href = `/api/runs/${selected}/download`;
  $('download-md').classList.remove('disabled'); $('download-json').classList.remove('disabled');
}
$('audience').onchange = () => loadReport().catch(e => notice(e.message));
function render(state) {
  current = state; if (!state.metrics) return;
  const renderKey = `${state.run_id}:${state.events.length}:${state.status}`;
  if (renderedVersion === renderKey) return;
  renderedVersion = renderKey;
  $('run-status').textContent = state.status.replaceAll('_',' ');
  $('run-mode').textContent = state.mode === 'live' ? 'Live model · iterative research' : 'Simulated policy · offline demo';
  $('model-calls').textContent = state.metrics.model_calls; $('policy-turns').textContent = `${state.metrics.policy_turns} policy turns`;
  $('tool-calls').textContent = state.metrics.tool_calls; $('verified').textContent = state.evidence.filter(e=>e.certificate_verified).length;
  $('elapsed').textContent = `${state.metrics.elapsed_seconds}s · ${state.metrics.reported_tokens} reported tokens${state.metrics.usage_missing_calls ? ' (partial)' : ''}`;
  $('activity-state').textContent = state.status === 'running' ? '● RUNNING' : state.status.toUpperCase().replaceAll('_',' ');
  $('stop').disabled = state.status !== 'running' || activeRun !== selected;
  renderTimeline(state); renderCandidates(state);
  if (state.limitations.length && state.status !== 'running') notice(state.limitations.join(' '));
  const version = `${state.run_id}:${state.events.length}`;
  if (reportVersion !== version) { reportVersion = version; loadReport().catch(e=>notice(e.message)); }
}
async function refresh() {
  if (polling) return; polling = true;
  try {
    const runs = await api('/api/runs'); activeRun = runs.find(r=>r.status==='running')?.run_id || null;
    $('start').disabled = Boolean(activeRun); $('test').disabled = Boolean(activeRun);
    if (!selected && runs.length) selected = runs[0].run_id;
    if (runs.length) $('history').replaceChildren(...runs.map(run => { const button = el('button',undefined,run.run_id===selected?'selected':''); button.append(el('strong',run.goal),el('small',`${run.mode.toUpperCase()} · ${run.status.replaceAll('_',' ')}`)); button.onclick = () => { selected=run.run_id; reportVersion=''; notice(''); refresh(); }; return button; }));
    if (selected) render(await api(`/api/runs/${selected}`));
  } catch (e) { notice('Workbench connection interrupted. Confirm the local server is running.'); }
  finally { polling = false; }
}
(async () => {
  try {
    const boot = await api('/api/bootstrap'); token = boot.token;
    $('base-url').value=boot.connection.base_url; $('model').value=boot.connection.model; $('protocol').value=boot.connection.protocol;
    $('preset').value=boot.connection.auth_mode==='cc_switch'?'cc_switch':'custom'; $('key-env').value=boot.connection.api_key_env;
    connectionView(); await refresh(); setInterval(refresh,1500);
  } catch(e) { notice(e.message); }
})();
