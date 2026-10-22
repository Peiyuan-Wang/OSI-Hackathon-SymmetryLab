'use strict';
const $ = id => document.getElementById(id);
let token = '', view = null, busy = false;
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
  try { render(await api(path, data)); notice(''); }
  catch (e) { notice(e.message); }
  finally { busy = false; document.querySelectorAll('button').forEach(b => b.disabled = false); }
}
const lines = id => $(id).value.split('\n').map(x => x.trim()).filter(Boolean);
function profile() { return {keywords: lines('keywords'), papers: lines('papers'), physics_only: $('physics-only').checked}; }

$('save').onclick = () => act('/api/literature/profile', profile(), 'Resolving your papers…');
$('search').onclick = async () => {
  await act('/api/literature/profile', profile(), 'Resolving your papers…');
  await act('/api/literature/search', {}, 'Searching arXiv (requests are spaced 3 s apart) and embedding abstracts…');
};
$('build-style').onclick = () => act('/api/literature/style', {enabled: $('style-enabled').checked || true}, 'Building voice profile…');
$('style-enabled').onchange = () => act('/api/literature/style-enabled', {enabled: $('style-enabled').checked});
$('clear').onclick = () => {
  if (!confirm('Delete your survey keywords, papers, candidates, votes and voice profile on this computer?\n\nThis cannot be undone.')) return;
  act('/api/literature/clear', {}, 'Clearing…');
};

function card(parent, title, small) { const c = el('div', undefined, 'candidate'); c.append(el('small', small), el('h3', title)); parent.append(c); return c; }

function render(v) {
  view = v;
  if (!$('keywords').value && v.keywords.length) $('keywords').value = v.keywords.join('\n');
  if (!$('papers').value && v.papers.length) $('papers').value = v.papers.map(p => p.id.replace(/^arXiv:/, '').replace(/^doi:/, '')).join('\n');
  $('physics-only').checked = v.physics_only;
  $('problems').hidden = !v.problems.length; $('problems').textContent = v.problems.join(' · ');
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
    item.append(el('small', `${(r.authors || []).slice(0, 3).join(', ')}${(r.authors || []).length > 3 ? ' et al.' : ''} · ${r.published || ''} · ${(r.categories || []).slice(0, 2).join(', ')}`));
    const why = r.match.slot_id ? `Closest interest: ${r.match.labels.join(' / ')} · cos ${r.match.cosine} · attention ${r.match.attention}` : `Outside your anchors (nearest: ${r.match.labels.join(' / ') || '—'}, cos ${r.match.cosine})`;
    item.append(el('p', why, 'why'));
    const abs = el('details'); abs.append(el('summary', 'Abstract'), el('p', r.abstract || '')); item.append(abs);
    const votes = el('div', undefined, 'votes');
    for (const [kind, label] of [['up', '▲ Like'], ['down', '▼ Not for me']]) {
      const b = el('button', label, 'secondary' + (r.vote === kind ? ' on' : ''));
      b.setAttribute('aria-pressed', String(r.vote === kind));
      b.onclick = () => act('/api/literature/vote', {paper_id: r.id, vote: r.vote === kind ? 'none' : kind});
      votes.append(b);
    }
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
    const c = card(root, e.terms.join(' · '), `EMERGING INTEREST · ${e.papers.length} LIKED PAPER(S) NO ANCHOR EXPLAINS`);
    c.classList.add('emerging');
    const b = el('button', 'Add as keyword', 'secondary'); b.onclick = () => act('/api/literature/adopt', {term: e.terms[0]}); c.append(b);
  }
  $('side-interests').replaceChildren(...(v.interests.length ? v.interests.map(s => { const d = el('button'); d.append(el('strong', s.labels[0]), el('small', `${s.kinds[0]} · ${s.angle}°`)); return d; }) : [el('p', 'No interests yet.')]));

  // Voice profile
  $('style-enabled').checked = v.style_enabled;
  if (v.style) {
    const box = $('style'); box.replaceChildren(el('p', `Profile ${v.style.hash} · built ${v.style.built_at.slice(0, 16).replace('T', ' ')} · from ${v.style.sources.own.length} own and ${v.style.sources.liked.length} liked paper(s)`, 'placeholder'), el('pre', v.style.prompt));
    const blob = new Blob([v.style.prompt], {type: 'text/markdown'}); $('download-style').href = URL.createObjectURL(blob);
    $('download-style').download = `symmetrylab_voice_${v.style.hash}.md`; $('download-style').classList.remove('disabled');
  }
}

(async () => {
  try { await bootstrap(); render(await api('/api/literature')); }
  catch (e) { notice('Workbench connection interrupted. Confirm the local server is running.'); }
  setInterval(async () => { if (!busy && view?.encoder_job?.status === 'preparing') { try { render(await api('/api/literature')); } catch {} } }, 3000);
})();
