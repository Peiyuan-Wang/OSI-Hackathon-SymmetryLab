'use strict';
const $ = id => document.getElementById(id);
const track = location.pathname === '/experiment' ? 'experiment' : 'theory';
let token = '', selected = null, current = null, polling = false, reportVersion = '', activeRun = null, renderedVersion = '';
function el(tag, text, className) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (className) e.className = className; return e; }
function notice(text) { $('notice').textContent = text; $('notice').hidden = !text; }
async function api(path, data, retried = false) {
  const response = await fetch(path, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-SymmetryLab-Token':token},body:JSON.stringify(data)});
  const value = await response.json();
  // The server issues a new token on every restart; fetch it once and retry instead of failing.
  if (response.status === 403 && data !== undefined && !retried) {
    const boot = await fetch('/api/bootstrap').then(r => r.json()); token = boot.token || token;
    return api(path, data, true);
  }
  if (!response.ok) throw new Error(response.status === 403 ? 'Local request token expired (server restarted). Reload the page.' : (value.error || 'Request failed')); return value;
}
function connection() { return {base_url:$('base-url').value.trim(), model:$('model').value.trim(), protocol:$('protocol').value, auth_mode:$('preset').value === 'cc_switch' ? 'cc_switch' : 'environment', api_key_env:$('key-env').value.trim()}; }
function connectionView() {
  const cc = $('preset').value === 'cc_switch'; $('key-field').hidden = cc;
  $('connection-help').textContent = cc ? 'Enable Codex routing in CC Switch and enter a supported model ID. CC Switch supplies the upstream key.' : 'Set the named environment variable before starting this server. Never paste API keys here. Base URL excludes /responses or /chat/completions.';
}
$('preset').addEventListener('change', () => { if ($('preset').value === 'cc_switch') { $('base-url').value = 'http://127.0.0.1:15721/v1'; $('protocol').value = 'responses'; } else { $('base-url').value = ''; $('protocol').value = 'chat_completions'; } connectionView(); });
$('mode').addEventListener('change', () => { const live = $('mode').value === 'live'; $('mode-note').textContent = live ? 'The model plans, generates candidates and chooses tools from observed feedback.' : 'Scripted walkthrough with exact calculations. Live mode uses your brief and public source retrieval.'; if (live) $('settings').open = true; });
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
    const result = await api('/api/runs', {goal:$('goal').value, research_profile:researchProfile(), mode:$('mode').value, connection:connection(), limits:{max_model_calls:turns}, use_style:$('use-style').checked});
    selected = result.run_id; activeRun = selected; reportVersion = ''; await refresh();
  } catch (error) { notice(error.message); $('start').disabled = Boolean(activeRun); }
};
$('stop').onclick = async () => { try { await api(`/api/runs/${selected}/cancel`, {}); notice('Stop requested. Any in-flight model request may take up to 120 seconds to return.'); $('stop').disabled = true; } catch (e) { notice(e.message); } };
function details(parent, title, value) { const box = el('details'); box.append(el('summary',title),el('pre',JSON.stringify(value,null,2))); parent.append(box); }
function renderTimeline(state) {
  $('plan').replaceChildren(...state.plan.map(step => el('li',step))); $('plan').hidden = !state.plan.length;
  const events = state.events.filter(e => e.kind !== 'thinking' && e.kind !== 'tool');
  const memory = [];
  if (state.recalled_lessons?.length) {
    const m = el('div',undefined,'event memory'); m.append(el('small','MEMORY · BEFORE PLANNING'),el('h3',`${state.recalled_lessons.length} rechecked lesson(s) from a similar earlier question`),el('p',state.mode==='demo'?'The plan below was changed accordingly: refuted claims are not re-proposed and known degenerate measurements are skipped.':'Given to the model as scope-limited hints. Clear history & memory in the sidebar to start without them.'));
    memory.push(m);
  }
  $('timeline').replaceChildren(...memory, ...events.map(event => {
    const item = el('div',undefined,'event'); const d = event.data;
    item.append(el('small',`${event.kind.toUpperCase().replaceAll('_',' ')} · ${event.seconds}s`));
    if (event.kind === 'plan') { item.append(el('h3','Research plan updated'),el('p',d.action.reason || d.observation.steps.join(' → '))); }
    else if (event.kind === 'hypothesis') { item.append(el('h3',d.observation.id + ' · Unverified proposal'),el('p',d.observation.statement)); }
    else if (event.kind === 'tool_call') {
      item.append(el('h3',d.name.replaceAll('_',' ')),el('p',d.reason || 'Run a registered exact tool.'));
      const resultEvent = state.events.find(e => e.index > event.index && ['tool','action_error'].includes(e.kind));
      details(item,'Tool arguments & observation',{arguments:d.arguments,observation:resultEvent?.data.observation || resultEvent?.data || 'In progress'});
      const observation = resultEvent?.data.observation;
      if (observation?.status === 'Counterexample found') item.append(el('p',`Counterexample found: ${observation.counterexamples.join(', ')}. Feedback retained for the next turn.`));
    } else if (event.kind === 'synthesis') { item.append(el('h3','Model synthesis · unverified'),el('p',d.text)); }
    else if (event.kind === 'protocol_notice') { item.append(el('h3','Policy format recovered'),el('p',d.message)); }
    else if (event.kind === 'action_error') { item.append(el('h3','Feedback returned to policy'),el('p',d.message)); }
    else if (event.kind === 'started') item.append(el('h3',d.policy));
    else if (event.kind === 'finished') item.append(el('h3',`Run ${d.status.replaceAll('_',' ')}`));
    return item;
  }));
}
function renderCandidates(state) {
  renderDiscovery(state);
  $('candidate-count').textContent = `${state.candidates.length + (state.calculations || []).length} records`;
  $('candidates').hidden = !state.candidates.length;
  if (!state.candidates.length) { $('candidates').replaceChildren(); return; }
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
  if (response.ok) $('report').replaceChildren(...markdown(text));
  $('download-md').href = url + '&download=1'; $('download-json').href = `/api/runs/${selected}/download`;
  $('download-md').classList.remove('disabled'); $('download-json').classList.remove('disabled');
}
$('clear-history').onclick = async () => {
  const label = track === 'experiment' ? 'Experimental research' : 'Theory exploration';
  if (!confirm(`Delete all stored ${label} runs on this computer?\n\nThis removes their reports, evidence, reusable lessons and saved preferences. It cannot be undone.`)) return;
  try { const r = await api('/api/runs/clear', {track}); selected = null; current = null; reportVersion = ''; renderedVersion = '';
    $('history').replaceChildren(el('p','No experiments yet.')); $('timeline').replaceChildren(); $('discovery-evidence').replaceChildren(); $('candidates').replaceChildren();
    $('report').replaceChildren(el('p','History cleared. Start a new run.','placeholder')); $('run-status').textContent='Ready';
    notice(`Removed ${r.removed} run(s) and their memory from ${label}.`); await refresh(); }
  catch (e) { notice(e.message); }
};
$('audience').onchange = () => loadReport().catch(e => notice(e.message));
function render(state) {
  current = state; if (!state.metrics) return;
  const renderKey = `${state.run_id}:${state.events.length}:${state.status}`;
  if (renderedVersion === renderKey) return;
  renderedVersion = renderKey;
  $('run-status').textContent = state.status.replaceAll('_',' ');
  $('run-mode').textContent = state.mode === 'live' ? 'Live model · iterative research' : 'Simulated policy · offline demo';
  const live = state.mode === 'live';
  $('model-calls').textContent = live ? state.metrics.model_calls : 'Offline';
  $('policy-turns').textContent = live ? `${state.metrics.reported_tokens} reported tokens${state.metrics.usage_missing_calls ? ' (partial)' : ''}` : `No model used · ${state.metrics.policy_turns} scripted steps`;
  $('tool-calls').textContent = state.metrics.tool_calls;
  const checks = [...state.evidence, ...(state.calculations || [])];
  $('verified').textContent = `${checks.filter(e=>e.certificate_verified).length} / ${checks.length}`;
  $('elapsed').textContent = `Conditional calculations · ${state.metrics.elapsed_seconds}s`;
  $('activity-state').textContent = state.status === 'running' ? '● RUNNING' : state.status.toUpperCase().replaceAll('_',' ');
  $('stop').disabled = state.status !== 'running' || activeRun !== selected;
  renderTimeline(state); renderCandidates(state);
  if (state.limitations.length && !['running','completed'].includes(state.status)) notice(`Run ${state.status.replaceAll('_',' ')}: ${state.limitations.join(' ')}`);
  const version = `${state.run_id}:${state.events.length}`;
  if (reportVersion !== version) { reportVersion = version; loadReport().catch(e=>notice(e.message)); }
}
async function refresh() {
  if (polling) return; polling = true;
  try {
    const allRuns = await api('/api/runs'); activeRun = allRuns.find(r=>r.status==='running')?.run_id || null;
    const runs = allRuns.filter(r => (r.track === 'experiment' ? 'experiment' : 'theory') === track);
    $('start').disabled = Boolean(activeRun); $('test').disabled = Boolean(activeRun);
    if (!selected && runs.length) selected = runs[0].run_id;
    if (runs.length) $('history').replaceChildren(...runs.map(run => { const button = el('button',undefined,run.run_id===selected?'selected':''); button.append(el('strong',run.goal),el('small',`${run.mode.toUpperCase()} · ${run.status.replaceAll('_',' ')}`)); button.onclick = () => { selected=run.run_id; reportVersion=''; notice(''); refresh(); }; return button; }));
    if (selected) render(await api(`/api/runs/${selected}`));
  } catch (e) { notice('Workbench connection interrupted. Confirm the local server is running.'); }
  finally { polling = false; }
}

function researchProfile() {
  return {track,material:track==='experiment'?$('material').value.trim():'',conditions:$('conditions').value.trim(),instruments:$('instruments').value.trim(),keywords:$('keywords').value.trim(),papers:$('papers').value,taste_notes:$('taste-notes').value,reuse_lessons:$('reuse-lessons').checked};
}
function setupTrack() {
  document.body.classList.toggle('experiment',track==='experiment');
  $(track+'-link').classList.add('active');
  $('track-label').textContent=track==='experiment'?'Experimental research':'Theory exploration';
  if(track==='experiment') {
    for(const id of ['material-field','conditions-field','instruments-field']) $(id).hidden=false;
    $('keywords-field').hidden=true;
    $('hero-title').replaceChildren(document.createTextNode('From material to '),el('em','measurement.'));
    $('hero-description').textContent='Compare magnetic hypotheses exactly, find which measurements can tell them apart, and design the experiment.';
    $('scope-text').textContent='Conditional single-domain axis constraints and collinear neutron orientation factors. Sample symmetry, energy stability and feasibility need additional evidence.';
    $('scope-formula').textContent='P(n,Q) = 1 − (n·Q)² / (|n|²|Q|²)';
    $('goal').value='Determine the Neel-axis orientation of L10 MnPt. Compare c-axis and basal-plane hypotheses, search for ambiguous signals, and propose a controlled measurement with conditional predictions.';
    document.title='SymmetryLab · Experimental research';
  } else {
    document.title='SymmetryLab · Theory exploration';
  }
}
$('paper-file').onchange=async()=>{
  const file=$('paper-file').files[0]; if(!file)return;
  if(file.size>32000 || !/\.(md|txt)$/i.test(file.name)){notice('Choose a Markdown or text reading list under 32 KB.');return;}
  try { const content=await file.text(); if(content.length>8000)throw new Error('Selected text exceeds 8,000 characters. Please select the relevant excerpts.'); $('papers').value=content; $('researcher-context').open=true; }
  catch(e){notice(e.message);}
};
function renderDiscovery(state) {
  const root=$('discovery-evidence'); root.replaceChildren();
  const card=(title,status)=>{const c=el('div',undefined,'candidate'); c.append(el('small',status),el('h3',title));root.append(c);return c;};
  if(state.recalled_lessons?.length) {
    const c=card('Lessons carried forward',`${state.recalled_lessons.length} rechecked counterexamples`);
    c.append(el('p','Only scope-limited strategies are recalled. Previous model conclusions are not treated as facts.'));details(c,'Provenance',state.recalled_lessons);
  }
  if(state.taste_profile?.length){const c=card('Research taste','INFERRED · REVIEW PENDING');for(const pref of state.taste_profile)c.append(el('p',pref.preference));details(c,'Preference evidence',state.taste_profile);}
  if(state.sources?.length){const shown=state.sources.filter(x=>x.mentions_material!==false),other=state.sources.length-shown.length;
    const c=card('Source ledger',`${shown.length} RELEVANT SOURCES${other?` · ${other} OFF-TOPIC HIDDEN`:''} · SAMPLE UNRESOLVED`);for(const source of shown){
    let url;try{url=new URL(source.url);}catch{continue;}if(!['https:','http:'].includes(url.protocol))continue;
    const a=el('a',source.source_id+' · '+(source.provider==='arXiv'?'[arXiv] ':'')+[].concat(source.fields.title || source.record_id).join('; '),'source-link');a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';c.append(a);
  } details(c,'Retrieval scope and source records',state.sources);}
  for(const retrieval of state.retrievals||[]) {
    if(retrieval.status==='retrieved')continue;
    const c=card('Source search · '+retrieval.kind,retrieval.status.replaceAll('_',' ').toUpperCase());
    c.append(el('p',retrieval.query),el('p',retrieval.message||'No matching metadata returned; no physical conclusion follows.'));
  }
  for(const assessment of state.structure_assessments||[]) {
    const c=card('Structure assessment','SOURCE-LINKED INTERPRETATION · SAMPLE UNVERIFIED');
    c.append(el('p',assessment.phase),el('p',assessment.chemical_group),el('p',assessment.magnetic_order));
    details(c,'Conditions and unresolved requirements',assessment);
  }
  const axisName=v=>({'0,0,1':'[001] c','0,0,-1':'[00-1] c','1,0,0':'[100]','0,1,0':'[010]','1,1,0':'[110]','1,-1,0':'[1-10]'})[v.join(',')]||'['+v.join(v.every(x=>String(x).replace('-','').length===1)?'':',')+']';
  for(const c of state.calculations||[]) {
    const r=c.result,axisKernel=r.kernel==='single_domain_director_v1';
    const box=card(c.calculation_id+' · '+(axisKernel?'Allowed axes':'Neutron orientation factors'),c.certificate_verified?'CONDITIONAL EXACT CHECK PASSED':'UNVERIFIED');
    if(r.factors){
      const name=l=>l.startsWith('n')?axisName(r.inputs.directions[Number(l.slice(1))-1]):'domain mix '+l.slice(10);
      const table=el('table',undefined,'evidence-table'),head=el('tr');head.append(el('th','Candidate n'));r.inputs.probes.forEach(q=>head.append(el('th','Q '+axisName(q).split(' ')[0])));table.append(head);
      r.factors.forEach((row,i)=>{const tr=el('tr');tr.append(el('td',name(r.labels[i])));row.forEach(v=>tr.append(el('td',v)));table.append(tr);});box.append(table);
      const parent=Object.fromEntries(r.labels.map(l=>[l,l])),find=x=>parent[x]===x?x:find(parent[x]);
      r.identical_pairs.forEach(([a,b])=>{parent[find(a)]=find(b);});
      const groups={};r.labels.forEach(l=>(groups[find(l)]??=[]).push(name(l)));
      const tied=Object.values(groups).filter(g=>g.length>1);
      box.append(el('p',`${r.labels.length} candidates → ${Object.keys(groups).length} distinguishable responses.`+(tied.length?' Still tied: '+tied.map(g=>g.join(' = ')).join('; '):'')));
    } else {
      const ok=r.outcomes.filter(x=>x.compatible).map(x=>axisName(x.direction)),no=r.outcomes.filter(x=>!x.compatible).map(x=>axisName(x.direction));
      box.append(el('p','Allowed: '+(ok.join(', ')||'none')),el('p','Excluded: '+(no.join(', ')||'none')));
    }
    box.append(el('p','Conditional model; material assignment and accessible reflections remain unresolved.'));details(box,'Inputs, assumptions & exact evidence',c);
  }
  for(const d of state.directions||[]) {const c=card(d.title,d.direction_id+' · PROPOSED DIRECTION');c.append(el('p',d.mechanism),el('p','Next: '+d.next_test));details(c,'Falsifier, taste and evidence',d);}
  if((state.directions||[]).length>=2 && state.status==='completed') {
    const c=card('Which direction would you pursue?','RESEARCHER PREFERENCE · NOT A CORRECTNESS LABEL');
    const left=state.directions[0],right=state.directions[1],select=el('select');select.setAttribute('aria-label','Preferred research direction');
    for(const [value,label] of [[left.direction_id,left.title],[right.direction_id,right.title],['tie','Both equally interesting'],['defer','Neither / insufficient evidence']]){const option=el('option',label);option.value=value;select.append(option);}
    const reason=el('textarea');reason.placeholder='Why? Identify the mechanism, method, or limitation that matters to you.';reason.maxLength=1500;reason.setAttribute('aria-label','Preference reason');
    const save=el('button','Save preference','secondary'),status=el('p');save.onclick=async()=>{save.disabled=true;try{const r=await api(`/api/runs/${state.run_id}/preference`,{left:left.direction_id,right:right.direction_id,choice:select.value,reason:reason.value});status.textContent=r.message;}catch(e){status.textContent=e.message;}finally{save.disabled=false;}};
    c.append(select,reason,save,status);
  }
  for(const d of state.experiment_designs||[]){const c=card(d.method,d.design_id+' · CONDITIONAL DESIGN');c.append(el('p',d.hypothesis));for(const prediction of d.predictions)c.append(el('p',prediction));details(c,'Protocol, controls & requirements',d);}
}
// Minimal Markdown renderer for the project's own reports. Builds DOM nodes; never uses innerHTML.
function inline(text) {
  const nodes = [], re = /\*\*(.+?)\*\*|`([^`]+)`|\[([^\]]+)\]\((https?:[^)\s]+)\)/g; let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) nodes.push(document.createTextNode(text.slice(last, m.index)));
    if (m[1] !== undefined) nodes.push(el('strong', m[1]));
    else if (m[2] !== undefined) nodes.push(el('code', m[2]));
    else { const a = el('a', m[3]); a.href = m[4]; a.target = '_blank'; a.rel = 'noopener noreferrer'; nodes.push(a); }
    last = re.lastIndex;
  }
  if (last < text.length) nodes.push(document.createTextNode(text.slice(last)));
  return nodes;
}
function markdown(text) {
  const out = [], lines = text.split('\n'); let i = 0;
  const withInline = (tag, t) => { const e = el(tag); e.append(...inline(t)); return e; };
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    if (line.startsWith('```')) { const buf = []; i++; while (i < lines.length && !lines[i].startsWith('```')) buf.push(lines[i++]); i++; out.push(el('pre', buf.join('\n'))); continue; }
    const h = /^(#{1,3}) (.*)/.exec(line); if (h) { out.push(withInline('h' + (h[1].length + 1), h[2])); i++; continue; }
    if (line === '---') { out.push(el('hr')); i++; continue; }
    if (line.startsWith('> ')) { out.push(withInline('blockquote', line.slice(2))); i++; continue; }
    if (line.startsWith('|')) {
      const table = el('table', undefined, 'evidence-table'); let header = true;
      while (i < lines.length && lines[i].startsWith('|')) {
        const cells = lines[i].slice(1, -1).split(' | ').map(c => c.trim());
        if (!cells.every(c => /^-+$/.test(c))) { const tr = el('tr'); cells.forEach(c => tr.append(withInline(header ? 'th' : 'td', c))); table.append(tr); header = false; }
        i++;
      }
      out.push(table); continue;
    }
    const list = /^(- |\d+\. )/.exec(line);
    if (list) {
      const ordered = list[1] !== '- ', ul = el(ordered ? 'ol' : 'ul');
      while (i < lines.length && /^(- |\d+\. )/.test(lines[i])) { ul.append(withInline('li', lines[i].replace(/^(- |\d+\. )/, ''))); i++; }
      out.push(ul); continue;
    }
    out.push(withInline('p', line)); i++;
  }
  return out;
}
setupTrack();

(async () => {
  try {
    const boot = await api('/api/bootstrap'); token = boot.token;
    $('base-url').value=boot.connection.base_url; $('model').value=boot.connection.model; $('protocol').value=boot.connection.protocol;
    $('preset').value=boot.connection.auth_mode==='cc_switch'?'cc_switch':'custom'; $('key-env').value=boot.connection.api_key_env;
    connectionView(); await refresh(); setInterval(refresh,1500);
  } catch(e) { notice(e.message); }
})();
