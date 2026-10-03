/* Resolve the preference before CSS paints; no external theme dependency. */
(() => {
  let saved;
  try { saved = localStorage.getItem('bookbridge-theme'); } catch (_) { /* Storage may be disabled. */ }
  const system = matchMedia('(prefers-color-scheme: dark)');
  const preferred = saved === 'dark' || saved === 'light' ? saved : null;
  document.documentElement.dataset.theme = preferred || (system.matches ? 'dark' : 'light');
  system.addEventListener('change', event => {
    let preference;
    try { preference = localStorage.getItem('bookbridge-theme'); } catch (_) { /* Use system preference. */ }
    if (!preference) document.documentElement.dataset.theme = event.matches ? 'dark' : 'light';
  });
})();
