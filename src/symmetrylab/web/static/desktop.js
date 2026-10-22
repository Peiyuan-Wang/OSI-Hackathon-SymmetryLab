'use strict';
// In the desktop app (pywebview), route file downloads to a native Save dialog and
// external links to the system browser. In a normal browser this file does nothing.
document.addEventListener('click', async event => {
  const a = event.target.closest && event.target.closest('a');
  const api = window.pywebview && window.pywebview.api;
  if (!a || !api || !a.href) return;
  const name = a.dataset.filename || a.getAttribute('download');
  if (name && !a.classList.contains('disabled')) {
    event.preventDefault();
    try { const text = await (await fetch(a.href)).text(); await api.save_file(name, text); }
    catch (e) { alert('Could not save the file: ' + e.message); }
    return;
  }
  let url; try { url = new URL(a.href); } catch { return; }
  if (['http:', 'https:'].includes(url.protocol) && url.host !== location.host) { event.preventDefault(); api.open_external(url.href); }
}, true);
window.addEventListener('pywebviewready', () => document.body.classList.add('desktop'));
