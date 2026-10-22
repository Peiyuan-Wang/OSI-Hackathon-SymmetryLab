'use strict';
const $ = id => document.getElementById(id);
const node = (tag, text, cls) => { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; };
let token = '', current = null, busy = false;
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-SymmetryLab-Token':token}, body:JSON.stringify(body)});
  const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Request failed'); return data;
}
function notice(message) { $('notice').textContent = message; $('notice').hidden = !message; }
function input() {
  const result = {material:$('material').value.trim(),conditions:$('conditions').value,space_group:$('space-group').value,msg:$('msg').value,ssg:$('ssg').value,preset:$('preset').value,component:$('component').value};
  if (result.preset === 'custom') { try { result.generators = JSON.parse($('generators').value); } catch (_) { throw new Error('Generators must be valid JSON. Use integers or fraction strings.'); } }
  return result;
}
function connection() { return {base_url:$('base-url').value.trim(),model:$('model').value.trim(),protocol:$('protocol').value,auth_mode:$('auth-mode').value,api_key_env:$('key-env').value.trim()}; }
function setBusy(value) { busy = value; for (const id of ['explore','live-plan','test-model','demo']) $(id).disabled = value; }
function renderCards() {
  if (!current) return;
  const cards = current.cards.filter(card => $('family-filter').value === 'all' || card.family === $('family-filter').value);
  $('cards').replaceChildren(...cards.map(card => {
    const box = node('section',undefined,'direction panel'); box.append(node('span',card.family,'eyebrow'),node('h3',card.phenomenon));
    box.append(node('span',card.status.replaceAll('_',' '),'tag '+(card.status === 'symmetry_forbidden' ? 'warn' : '')));
    box.append(node('p',card.requirements),node('p',card.next_step,'note'));
    const link = node('a','Search primary literature ↗'); link.href = card.literature.search_url; link.target = '_blank'; link.rel = 'noopener noreferrer'; box.append(link,node('p','External search link only; no paper retrieved.','tiny')); return box;
  }));
}
function render(result) {
  current = result; $('welcome').hidden = true; $('results').hidden = false;
  $('count').textContent = result.counts.directions; $('computed').textContent = result.counts.computed;
  $('result-title').textContent = result.material + ' · evidence notebook'; $('scope').textContent = result.disclaimer;
  $('profile').replaceChildren(...Object.entries(result.groups).map(([key,value]) => node('span',key.toUpperCase()+': '+(value.value || 'unknown')+' · '+value.status,'chip')));
  $('trace').replaceChildren(...result.trace.map(step => node('li',step.stage+': '+step.message)));
  const hall = result.hall; $('hall-result').replaceChildren();
  if (hall) {
    $('hall-result').append(node('h3','Linear AHE · h_'+hall.component+': '+hall.status.replaceAll('_',' ')),node('p',hall.input_origin.replaceAll('_',' '),'note'));
    const details = node('details'); details.append(node('summary','Exact constraints and checked certificate'),node('pre',JSON.stringify(hall,null,2))); $('hall-result').append(details);
  } else { $('hall-result').append(node('p','Magnetic structure unknown. No Hall result calculated.','tag warn')); }
  $('model-panel').hidden = !result.model_plan; $('model-text').textContent = result.model_plan ? result.model_plan.text : '';
  renderCards();
}
$('preset').onchange = () => { $('custom-box').hidden = $('preset').value !== 'custom'; };
$('auth-mode').onchange = () => { const cc = $('auth-mode').value === 'cc_switch'; $('key-label').hidden = cc; if (cc) { $('base-url').value = 'http://127.0.0.1:15721/v1'; $('protocol').value = 'responses'; } else { $('base-url').value = ''; $('protocol').value = 'chat_completions'; } };
$('family-filter').onchange = renderCards;
$('material-form').onsubmit = async event => { event.preventDefault(); if (busy) return; notice(''); setBusy(true); try { render(await api('/api/materials/explore',input())); } catch (error) { notice(error.message); } finally { setBusy(false); } };
$('test-model').onclick = async () => { if (busy) return; setBusy(true); $('connection-status').textContent = 'Testing one real request…'; try { const result = await api('/api/connection/test',connection()); $('connection-status').textContent = result.message+' Model: '+result.model; } catch (error) { $('connection-status').textContent = error.message; } finally { setBusy(false); } };
$('live-plan').onclick = async () => { if (busy) return; notice(''); setBusy(true); try { render(await api('/api/materials/plan',{...input(),connection:connection()})); } catch (error) { notice(error.message); } finally { setBusy(false); } };
$('demo').onclick = () => { $('material').value = 'Illustrative sample (not a real material assignment)'; $('conditions').value = 'Demonstration only: h_z is forbidden by C2z with time reversal. After viewing the certificate, change the preset to Identity only and rerun. This compares assumptions, not physically established phases.'; $('preset').value = 'c2z_time_reversal'; $('component').value = 'z'; $('custom-box').hidden = true; $('material-form').requestSubmit(); };
$('download').onclick = () => { if (!current) return; const url = URL.createObjectURL(new Blob([JSON.stringify(current,null,2)],{type:'application/json'})); const link = node('a'); link.href=url; link.download='symmetrylab-material-report.json'; link.click(); setTimeout(()=>URL.revokeObjectURL(url),1000); };
Promise.all([api('/api/bootstrap'),api('/api/materials/catalog')]).then(([boot,catalog])=>{
  token=boot.token;
  for (const [value,label] of Object.entries(catalog.presets)) { const option=node('option',label); option.value=value; $('preset').append(option); }
  const custom=node('option','Custom Cartesian generators'); custom.value='custom'; $('preset').append(custom);
  for (const family of Object.keys(catalog.families)) { $('family-preview').append(node('span',family,'chip')); const option=node('option',family); option.value=family; $('family-filter').append(option); }
  $('count').textContent = Object.values(catalog.families).reduce((sum,list)=>sum+list.length,0);
  const c=boot.connection; $('base-url').value=c.base_url; $('model').value=c.model; $('protocol').value=c.protocol; $('auth-mode').value=c.auth_mode; $('key-env').value=c.api_key_env; $('key-label').hidden=c.auth_mode==='cc_switch';
}).catch(error=>notice('Startup failed: '+error.message));
