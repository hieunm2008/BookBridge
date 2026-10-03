/* Progressive enhancement: all data mutations remain standard Django forms. */
(() => {
  const themeButtons = document.querySelectorAll('[data-theme-toggle]');
  const syncThemeLabel = () => {
    const dark = document.documentElement.dataset.theme === 'dark';
    themeButtons.forEach(button => {
      const label = dark ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối';
      button.setAttribute('aria-label', label);
      button.title = label;
    });
  };
  themeButtons.forEach(button => button.addEventListener('click', () => {
    const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('bookbridge-theme', theme); } catch (_) { /* In-memory preference still works. */ }
    syncThemeLabel();
  }));
  syncThemeLabel();
  new MutationObserver(syncThemeLabel).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});

  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  if (!reducedMotion.matches && 'IntersectionObserver' in window) {
    const reveals = [...document.querySelectorAll('[data-reveal]')];
    const reveal = element => {
      element.classList.remove('reveal-pending');
      element.classList.add('reveal-visible');
    };
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) { reveal(entry.target); observer.unobserve(entry.target); }
      });
    }, {threshold: .08});
    reveals.forEach(element => {
      // Keep anything already on screen readable, even during a fast anchor jump.
      if (element.getBoundingClientRect().top < innerHeight) return;
      element.classList.add('reveal-pending');
      observer.observe(element);
      element.addEventListener('focusin', () => reveal(element));
    });
    reducedMotion.addEventListener('change', event => {
      if (event.matches) { reveals.forEach(reveal); observer.disconnect(); }
    });
  }
  const toggle = document.querySelector('[data-menu-toggle]');
  const sidebar = document.querySelector('#sidebar');
  const closeMenu = () => {
    document.body.classList.remove('menu-open');
    toggle?.setAttribute('aria-expanded', 'false');
    if (sidebar && window.innerWidth < 1024) sidebar.inert = true;
  };
  const syncMenu = () => {
    if (sidebar) sidebar.inert = window.innerWidth < 1024 && !document.body.classList.contains('menu-open');
    if (window.innerWidth >= 1024) closeMenu();
  };
  toggle?.addEventListener('click', () => {
    const opening = !document.body.classList.contains('menu-open');
    if (!opening) return closeMenu();
    document.body.classList.add('menu-open');
    toggle.setAttribute('aria-expanded', 'true');
    sidebar.inert = false;
    sidebar.querySelector('a')?.focus();
  });
  document.querySelectorAll('[data-menu-close]').forEach(button => button.addEventListener('click', () => { closeMenu(); toggle?.focus(); }));
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && document.body.classList.contains('menu-open')) { closeMenu(); toggle?.focus(); }
    if (e.key === 'Tab' && document.body.classList.contains('menu-open') && !document.querySelector('dialog[open]')) {
      const links = [...sidebar.querySelectorAll('a,button')];
      const first = links[0], last = links[links.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });
  window.addEventListener('resize', syncMenu);
  syncMenu();
  document.querySelector('[data-password-toggle]')?.addEventListener('click', e => {
    const input = document.getElementById(e.currentTarget.getAttribute('aria-controls'));
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    const label = e.currentTarget.querySelector('[data-password-label]');
    if (label) label.textContent = show ? 'Ẩn' : 'Hiện';
    else e.currentTarget.textContent = show ? 'Ẩn' : 'Hiện';
    e.currentTarget.setAttribute('aria-pressed', String(show));
  });
  const inventoryForm = document.querySelector('[data-inventory-form]');
  if (inventoryForm) {
    const preview = inventoryForm.querySelector('[data-available-preview]');
    const update = () => {
      const available = Number(inventoryForm.querySelector('[data-owned]').value || 0)
        - Number(inventoryForm.querySelector('[data-internal]').value || 0) - Number(inventoryForm.dataset.unavailable);
      preview.textContent = String(available);
      preview.parentElement.classList.toggle('invalid', available < 0);
    };
    inventoryForm.addEventListener('input', update);
    update();
  }
  const dialog = document.getElementById('confirm-dialog');
  let pending = null;
  dialog?.addEventListener('close', () => {
    const current = pending;
    pending = null;
    if (dialog.returnValue === 'accept' && current) {
      current.form.dataset.confirmed = 'true';
      current.form.requestSubmit(current.button);
    } else current?.button?.focus();
  });
  document.querySelectorAll('form[data-loading],form[data-confirm]').forEach(form => {
    form.addEventListener('submit', e => {
      const button = e.submitter;
      if (form.dataset.submitting === 'true') { e.preventDefault(); return; }
      let text = form.dataset.confirm;
      if (form.hasAttribute('data-loan-actions') && button) {
        if (['reject', 'cancel', 'issue', 'resolve'].includes(button.value) && !form.elements.notes.value.trim()) {
          e.preventDefault();
          form.elements.notes.setCustomValidity('Hãy ghi lý do hoặc cách xử lý.');
          form.elements.notes.reportValidity();
          return;
        }
        text = `${button.dataset.actionLabel}: ${form.dataset.quantity} cuốn ${form.dataset.book}?`;
      }
      if (text && form.dataset.confirmed !== 'true') {
        e.preventDefault();
        if (dialog?.showModal) {
          pending = {form, button};
          document.getElementById('confirm-message').textContent = text;
          dialog.returnValue = '';
          dialog.showModal();
        } else if (window.confirm(text)) { form.dataset.confirmed = 'true'; form.requestSubmit(button); }
        return;
      }
      // Disabled submitters are omitted by browsers. Preserve a named action explicitly.
      form.dataset.submitting = 'true';
      form.setAttribute('aria-busy', 'true');
      if (button) {
        if (button.name) {
          const action = document.createElement('input');
          action.type = 'hidden';
          action.name = button.name;
          action.value = button.value;
          form.append(action);
        }
        button.textContent = 'Đang lưu…';
        const spinner = document.createElement('span');
        spinner.className = 'loading-spinner';
        spinner.setAttribute('aria-hidden', 'true');
        button.prepend(spinner);
        button.classList.add('is-submitting');
        button.setAttribute('aria-disabled', 'true');
        button.disabled = true;
      }
      form.querySelectorAll('button[type=submit]').forEach(other => { if (other !== button) other.disabled = true; });
    });
  });
  document.querySelectorAll('textarea[name=notes]').forEach(field => field.addEventListener('input', () => field.setCustomValidity('')));
  document.querySelector('[data-go-back]')?.addEventListener('click', () => {
    if (history.length > 1) history.back(); else location.href = '/';
  });
  window.addEventListener('pageshow', e => { if (e.persisted) location.reload(); });
})();
