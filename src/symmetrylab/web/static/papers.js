'use strict';
const $ = id => document.getElementById(id);
let token = '', view = null, busy = false, initialized = false;
function el(tag, text, className) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (className) e.className = className; return e; }
function notice(text) { $('notice').textContent = text; $('notice').hidden = !text; }
async function bootstrap() { token = (await fetch('/api/bootstrap').then(r => r.json())).token; }
async function api(path, data, retried = false) {
  const response = await fetch(path, data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-SymmetryLab-Token':token}, body:JSON.stringify(data)});
  const value = await response.json();
  if (response.status === 403 && data !== undefined && !retried) { await bootstrap(); return api(path, data, true); }
  if (!response.ok) throw new Error(value.error || 'Request failed');
  return value;
}
async function act(path, data, label) {
  if (busy) return; busy = true; notice(label || '');
  document.querySelectorAll('button').forEach(b => b.disabled = true);
  try { render(await api(path, data)); notice(''); return true; }
  catch (e) { notice(e.message); return false; }
  finally { busy = false; document.querySelectorAll('button').forEach(b => b.disabled = false); }
}
const lines = id => $(id).value.split('\n').map(x => x.trim()).filter(Boolean);
function profile() { return {keywords: lines('keywords'), papers: lines('papers'), physics_only: $('physics-only').checked,
  preferences:{problem:$('interest-problem').value, methods:$('interest-methods').value, current_goal:$('interest-goal').value, taste:$('interest-taste').value, share_with_agent:$('share-interests').checked}}; }
function writing() { return {audience:$('writing-audience').value, section:$('writing-section').value, detail:$('writing-detail').value, notes:$('writing-notes').value, samples:view?.writing.samples || []}; }
$('save-writing').onclick = () => act('/api/literature/writing', writing());
$('add-sample').onclick = async () => {
  const w = writing(); w.samples = [...w.samples, {section:$('sample-section').value, text:$('writing-sample').value}];
  await act('/api/literature/writing', w);
  if (view?.writing.samples.some(s => s.text === $('writing-sample').value.trim())) $('writing-sample').value = '';
};

$('save').onclick = () => act('/api/literature/profile', profile(), 'Resolving your papers…');
async function saveSources() {
  const data = {sources:$('search-sources').value.split(','), token:$('bond-token').value.trim()};
  const ok = await act('/api/literature/sources', data);
  if (ok) $('bond-token').value = '';
  return ok;
}
$('save-sources').onclick = saveSources;
$('test-bond').onclick = async () => {
  if (await saveSources()) await act('/api/literature/bond-test', {}, 'Calling Bond list_sources…');
};
$('forget-bond').onclick = async () => {
  if (await act('/api/literature/sources', {sources:$('search-sources').value.split(','), forget_token:true})) $('bond-token').value = '';
};
$('search').onclick = async () => {
  if (!await saveSources()) return;
  if (await act('/api/literature/profile', profile(), 'Resolving your papers…'))
    await act('/api/literature/search', {}, 'Searching selected sources and embedding abstracts…');
};
$('build-style').onclick = async () => {
  if (await act('/api/literature/writing', writing()))
    await act('/api/literature/style', {enabled:true}, 'Building voice profile…');
};
$('style-enabled').onchange = () => act('/api/literature/style-enabled', {enabled: $('style-enabled').checked});
$('clear').onclick = () => {
  if (!confirm('Delete your survey keywords, papers, candidates, votes and voice profile on this computer?\n\nThis cannot be undone.')) return;
  act('/api/literature/clear', {}, 'Clearing…');
};

function card(parent, title, small) { const c = el('div', undefined, 'candidate'); c.append(el('small', small), el('h3', title)); parent.append(c); return c; }

function render(v) {
  view = v;
  if (!initialized) {
    for (const [id, key] of [['interest-problem','problem'], ['interest-methods','methods'], ['interest-goal','current_goal'], ['interest-taste','taste']]) $(id).value = v.preferences[key];
    $('share-interests').checked = v.preferences.share_with_agent;
    for (const key of ['audience','section','detail','notes']) $('writing-' + key).value = v.writing[key];
    initialized = true;
  }
  $('search-sources').value = v.search_sources.join(',');
  if (!$('keywords').value && v.keywords.length) $('keywords').value = v.keywords.join('\n');
  if (!$('papers').value && v.papers.length) $('papers').value = v.papers.map(p => p.id.replace(/^arXiv:/, '').replace(/^doi:/, '')).join('\n');
  $('physics-only').checked = v.physics_only;
  $('bond-state').textContent = `Token: ${v.bond.token_source} · ${v.bond.test}`;
  const problems = [...v.problems, ...(v.last_search?.problems || [])];
  $('problems').hidden = !problems.length; $('problems').textContent = problems.join(' · ');
  const physbert = v.encoder.kind === 'physbert';
  $('m-encoder').textContent = physbert ? 'PhysBERT' : 'Lexicon';
  $('m-encoder-note').replaceChildren(document.createTextNode(physbert ? 'arXiv-physics BERT · local' : 'Offline fallback · '));
  if (!physbert) {
    const job = v.encoder_job || {};
    if (job.status === 'preparing') $('m-encoder-note').append('downloading PhysBERT…');
    else { const b = el('button', 'Prepare PhysBERT (~440 MB)', 'link-button'); b.onclick = () => act('/api/literature/prepare-encoder', {}, 'Downloading PhysBERT in the background; the encoder switches when ready.'); $('m-encoder-note').append(b); }
    if (job.status === 'failed') notice(job.message);
  }
  $('encoder-footer').textContent = v.encoder.version;
  $('m-candidates').textContent = v.candidate_count;
  $('m-search').textContent = v.last_search ? `Last search ${v.last_search.at.slice(0, 16).replace('T', ' ')} · +${v.last_search.new}` : 'No search yet';
  $('m-votes').textContent = `${v.votes.up} · ${v.votes.down}`;
  $('m-drift').textContent = `${Math.round(v.drift.unexplained_share * 100)}%`;
  $('m-drift-note').textContent = `of likes outside anchors · max anchor shift ${v.drift.max_angle}°`;

  // Ranked list
  $('ranked-count').textContent = `${v.ranked.length} of ${v.candidate_count} shown`;
  if (v.ranked.length) $('ranked').replaceChildren(...v.ranked.map(r => {
    const item = el('div', undefined, 'event paper' + (r.vote ? ' voted-' + r.vote : ''));
    const head = el('div', undefined, 'paper-head'); const score = el('span', r.score.toFixed(0), 'score');
    const a = el('a', r.title); a.href = r.url; a.target = '_blank'; a.rel = 'noopener noreferrer';
    const h = el('h3'); h.append(a); head.append(score, h); item.append(head);
    item.append(el('small', `Source: ${r.source || 'arXiv'} · retrieved via ${(r.retrieved_via || ['arxiv']).join(' + ')}`));
    item.append(el('small', `${(r.authors || []).slice(0, 3).join(', ')}${(r.authors || []).length > 3 ? ' et al.' : ''} · ${r.published || ''} · ${(r.categories || []).slice(0, 2).join(', ')}`));
    const why = r.match.slot_id ? `Closest interest: ${r.match.labels.join(' / ')} · cos ${r.match.cosine} · attention ${r.match.attention}` : `Outside your anchors (nearest: ${r.match.labels.join(' / ') || '—'}, cos ${r.match.cosine})`;
    item.append(el('p', why, 'why'));
    if (r.ranking_components) item.append(el('small', `Semantic ${r.ranking_components.semantic} · keyword match ${r.ranking_components.lexical} · heuristic score, not a probability`));
    const abs = el('details'); abs.append(el('summary', 'Abstract'), el('p', r.abstract || '')); item.append(abs);
    const votes = el('div', undefined, 'votes');
    for (const [kind, label] of [['up', '▲ Like'], ['down', '▼ Not for me']]) {
      const b = el('button', label, 'secondary' + (r.vote === kind ? ' on' : ''));
      b.setAttribute('aria-pressed', String(r.vote === kind));
      b.onclick = () => act('/api/literature/vote', {paper_id: r.id, vote: r.vote === kind ? 'none' : kind});
      votes.append(b);
    }
    const styleVote = el('button', r.style_selected ? '✓ Writing style selected' : 'Use writing style', 'secondary' + (r.style_selected ? ' on' : ''));
    styleVote.setAttribute('aria-pressed', String(r.style_selected));
    styleVote.onclick = () => act('/api/literature/style-vote', {paper_id:r.id, selected:!r.style_selected});
    votes.append(styleVote);
    item.append(votes); return item;
  }));

  // Interest map
  $('interest-count').textContent = `${v.interests.length} anchors`;
  const root = $('interests'); root.replaceChildren();
  for (const s of v.interests) {
    const c = card(root, s.labels.join(' / '), `${s.kinds.join(' + ').toUpperCase()} · ${s.observations} VOTES`);
    const bar = el('div', undefined, 'drift-bar'); const fill = el('span'); fill.style.width = Math.min(100, s.angle / 25 * 100) + '%'; bar.append(fill);
    c.append(bar, el('p', `Shifted ${s.angle}° of 25° by feedback · liked ${s.liked} · disliked ${s.disliked}`));
  }
  for (const e of v.drift.emerging) {
    const c = card(root, e.terms.join(' · '), `${e.papers.length < 2 ? 'TENTATIVE SIGNAL' : 'POSSIBLE EMERGING INTEREST'} · ${e.papers.length} LIKED PAPER(S)`);
    c.classList.add('emerging');
    const b = el('button', 'Add as keyword', 'secondary'); b.onclick = () => act('/api/literature/adopt', {term: e.terms[0]}); c.append(b);
  }
  $('side-interests').replaceChildren(...(v.interests.length ? v.interests.map(s => { const d = el('button'); d.append(el('strong', s.labels[0]), el('small', `${s.kinds[0]} · ${s.angle}°`)); return d; }) : [el('p', 'No interests yet.')]));
  $('facets').replaceChildren();
  for (const f of v.facets.slice(0, 12)) {
    const c = card($('facets'), f.value, `${f.kind.toUpperCase()} · ${f.paper_id}`);
    c.append(el('p', f.excerpt), el('small', f.status));
  }

  // Voice profile
  $('style-enabled').checked = v.style_enabled;
  $('style-state').textContent = v.style_stale ? 'Profile out of date — rebuild before the next run.' : (v.style ? 'Profile current · effect on writing quality has not yet been benchmarked.' : 'No learned writing profile yet. Keywords alone are insufficient.');
  $('writing-samples').replaceChildren(...v.writing.samples.map((sample, i) => {
    const item = el('div'); item.append(el('strong', sample.section), el('p', sample.text));
    const remove = el('button', 'Remove example', 'secondary');
    remove.onclick = () => act('/api/literature/writing', {...writing(), samples:v.writing.samples.filter((_, j) => j !== i)});
    item.append(remove); return item;
  }));
  if (v.style) {
    const box = $('style'); box.replaceChildren(el('p', `Profile ${v.style.hash} · built ${v.style.built_at.slice(0, 16).replace('T', ' ')} · ${v.style.sources.own.length} own papers / approved paragraphs and ${v.style.sources.liked.length} selected writing sources`, 'placeholder'), el('pre', v.style.prompt));
    const blob = new Blob([v.style.prompt], {type: 'text/markdown'}); $('download-style').href = URL.createObjectURL(blob);
    $('download-style').download = `symmetrylab_voice_${v.style.hash}.md`; $('download-style').classList.remove('disabled');
  }
}

(async () => {
  try { await bootstrap(); render(await api('/api/literature')); }
  catch (e) { notice('Workbench connection interrupted. Confirm the local server is running.'); }
  setInterval(async () => { if (!busy && view?.encoder_job?.status === 'preparing') { try { render(await api('/api/literature')); } catch {} } }, 3000);
})();
