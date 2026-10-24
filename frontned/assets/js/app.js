(function () {
  const SAME_ORIGIN = location.protocol.startsWith('http') && location.port !== '5500';
  const API_BASE = window.LA_API_BASE || (SAME_ORIGIN ? location.origin + '/api' : 'http://127.0.0.1:8000/api');

  const ROOT = new URL('../../', document.currentScript.src).href;
  const url = (p) => ROOT + p;

  /* ---------- storage (always wrapped: private mode can throw) ---------- */
  const store = {
    get(key, fallback) {
      try { const v = localStorage.getItem('la_' + key); return v === null ? fallback : JSON.parse(v); }
      catch (e) { return fallback; }
    },
    set(key, value) { try { localStorage.setItem('la_' + key, JSON.stringify(value)); } catch (e) {} },
    remove(key) { try { localStorage.removeItem('la_' + key); } catch (e) {} },
  };
  const session = {
    isUnlocked() { try { return sessionStorage.getItem('la_unlocked') === '1'; } catch (e) { return false; } },
    unlock() { try { sessionStorage.setItem('la_unlocked', '1'); } catch (e) {} },
    lock() { try { sessionStorage.removeItem('la_unlocked'); sessionStorage.removeItem('la_vault'); } catch (e) {} },
  };

  /* ---------- user + disguise ---------- */
  const DEFAULT_DISGUISE = { type: 'calculator' };
  const user = () => store.get('user', null);
  const disguise = () => Object.assign({}, DEFAULT_DISGUISE, store.get('disguise', {}));
  const disguisePage = () => url('disguise/' + disguise().type + '.html');

  const HOME_ICON = {
    calculator: { title: 'Calculator', icon: 'icon-calculator' },
    messages: { title: 'Chats', icon: 'icon-messages' },
    browser: { title: 'Search', icon: 'icon-browser' },
  };
  function setHead(selector, tag, attrs) {
    let el = document.head.querySelector(selector);
    if (!el) { el = document.createElement(tag); document.head.appendChild(el); }
    Object.keys(attrs).forEach((k) => el.setAttribute(k, attrs[k]));
  }
  function applyHomeIcon() {
    if (!document.head) return;
    const h = user() ? (HOME_ICON[disguise().type] || HOME_ICON.calculator) : { title: 'Lerato Alert', icon: 'icon-lerato' };
    setHead('link[rel="apple-touch-icon"]', 'link', { rel: 'apple-touch-icon', href: url('assets/img/' + h.icon + '-180.png') });
    setHead('link[rel="icon"]', 'link', { rel: 'icon', type: 'image/png', href: url('assets/img/' + h.icon + '-192.png') });
    setHead('meta[name="apple-mobile-web-app-title"]', 'meta', { name: 'apple-mobile-web-app-title', content: h.title });
    setHead('meta[name="apple-mobile-web-app-capable"]', 'meta', { name: 'apple-mobile-web-app-capable', content: 'yes' });
  }
  applyHomeIcon();

  /* ---------- secrets: salted PBKDF2, checked on the phone, synced as hashes only ---------- */
  const ITER = 150000;
  const hex = (buf) => Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, '0')).join('');
  async function pbkdf2(value, salt, iter) {
    const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(value), 'PBKDF2', false, ['deriveBits']);
    const bits = await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt: new TextEncoder().encode(salt), iterations: iter }, key, 256);
    return hex(bits);
  }
  const secure = {
    async make(value) {
      const salt = hex(crypto.getRandomValues(new Uint8Array(16)));
      return { salt, iter: ITER, hash: await pbkdf2(value, salt, ITER) };
    },
    async check(value, lock) {
      if (!lock || !lock.salt || !lock.hash) return false;
      try { return (await pbkdf2(value, lock.salt, lock.iter || ITER)) === lock.hash; } catch (e) { return false; }
    },
  };
  // One spelling per secret: "47 x 12" and "47×12" are the same sum; words ignore case.
  function normSecret(type, value) {
    const v = String(value || '').trim();
    if (type !== 'calculator') return v.toLowerCase();
    return v.replace(/\s+/g, '').replace(/[x*]/gi, '×').replace(/\//g, '÷').replace(/-/g, '−').replace(/,/g, '.');
  }
  async function setSecret(type, value) {
    const lock = await secure.make(normSecret(type, value));
    store.set('disguise', { type, lock });
    return lock;
  }
  async function checkSecret(value) {
    const d = disguise();
    const v = normSecret(d.type, value);
    if (d.lock) return secure.check(v, d.lock);
    if (d.secret) return v === normSecret(d.type, d.secret);   // older installs kept it in plain text
    return false;
  }

  // Safe word, disguise and the two hashes follow the account to a new phone.
  async function syncSettings() {
    if (!(user() || {}).token) return;
    const d = disguise();
    const body = { safe_word: store.get('safeword', '') || '', disguise_type: d.type };
    if (d.lock) body.secret_lock = d.lock;
    const pin = store.get('vault_pin', null);
    if (pin && typeof pin === 'object') body.vault_pin = pin;
    try { await api('/users/settings/', { method: 'PUT', body }); } catch (e) {}
  }
  function restoreSettings(s) {
    s = s || {};
    store.set('safeword', s.safe_word || '');
    const d = { type: s.disguise_type || 'calculator' };
    if (s.secret_lock) d.lock = s.secret_lock;
    store.set('disguise', d);
    if (s.vault_pin) store.set('vault_pin', s.vault_pin); else store.remove('vault_pin');
    return !!s.secret_lock;
  }

  function safeNext(next, fallback) {
    if (!next || /^[a-z]+:|^\/\//i.test(next) || next.includes('..')) return fallback;
    return next.replace(/^\/+/, '');
  }

  function enterApp() {
    session.unlock();
    location.replace(url('onboarding/loading.html?next=alert/index.html'));
  }

  function guard() {
    if (!user()) { location.replace(url('index.html')); return false; }
    if (!session.isUnlocked()) { location.replace(disguisePage()); return false; }
    ensureToken();
    return true;
  }

  // Accounts need a password now, so a missing token means: sign in again.
  function ensureToken() { return Promise.resolve((user() || {}).token || null); }

  // Wipe everything Lerato keeps on this phone. The account stays on the server for signing in again.
  async function signOut() {
    try {
      Object.keys(localStorage).filter((k) => k.startsWith('la_')).forEach((k) => localStorage.removeItem(k));
    } catch (e) {}
    try { sessionStorage.clear(); } catch (e) {}
    await new Promise((done) => {
      try {
        const req = indexedDB.deleteDatabase('lerato-vault');
        req.onsuccess = req.onerror = req.onblocked = () => done();
      } catch (e) { done(); }
      setTimeout(done, 1500);
    });
    location.replace(url('onboarding/login.html'));
  }

  function quickExit() {
    session.lock();
    location.replace(disguisePage());
  }

  /* ---------- API with demo fallback ---------- */
  async function api(path, options) {
    const opts = options || {};
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), opts.timeout || 8000);
    const headers = { 'Content-Type': 'application/json' };
    const token = (user() || {}).token;
    if (token) headers['X-Lerato-Token'] = token;
    try {
      const res = await fetch(API_BASE + path, {
        method: opts.method || (opts.body ? 'POST' : 'GET'),
        headers,
        body: opts.body ? JSON.stringify(opts.body) : undefined,
        signal: ctrl.signal,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const err = new Error('HTTP ' + res.status);
        err.status = res.status;
        err.data = data;
        throw err;
      }
      if (res.status === 204) return null;
      return await res.json();
    } finally {
      clearTimeout(timer);
    }
  }
  // First readable message from a DRF error body.
  function errorText(e, fallback) {
    const d = e && e.data;
    if (!d) return fallback;
    if (typeof d.detail === 'string') return d.detail;
    for (const v of Object.values(d)) {
      if (typeof v === 'string') return v;
      if (Array.isArray(v) && typeof v[0] === 'string') return v[0];
    }
    return fallback;
  }
  async function apiOr(path, options, demo) {
    try { return await api(path, options); }
    catch (e) { return typeof demo === 'function' ? demo() : demo; }
  }

  /* ---------- small UI helpers ---------- */
  function toast(message, ms) {
    document.querySelectorAll('.toast').forEach((t) => t.remove());
    const el = document.createElement('div');
    el.className = 'toast';
    el.setAttribute('role', 'status');
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), ms || 2600);
  }
  const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  /* ---------- icons ---------- */
  const P = {
    shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6l8-3z"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 018 0v4"/>',
    phone: '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 005 5L15 13l5 2v4a2 2 0 01-2 2A16 16 0 013 6a2 2 0 012-2z"/>',
    wallet: '<rect x="3" y="6" width="18" height="14" rx="2"/><path d="M3 10h18M16 15h2"/>',
    book: '<path d="M4 5a2 2 0 012-2h13v16H6a2 2 0 00-2 2V5z"/><path d="M4 19a2 2 0 012-2h13"/>',
    exit: '<path d="M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10"/>',
    back: '<path d="M15 6l-6 6 6 6"/>',
    check: '<path d="M6 12l4 4 8-8"/>',
    mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0014 0M12 18v3"/>',
    send: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    pin: '<path d="M12 21s7-6 7-11a7 7 0 00-14 0c0 5 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    eyeoff: '<path d="M3 12s3.5-6 9-6c1.6 0 3 .5 4.2 1.2M21 12s-3.5 6-9 6c-1.6 0-3-.5-4.2-1.2"/><path d="M4 20L20 4"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    chevron: '<path d="M9 6l6 6-6 6"/>',
    trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
    sparkle: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>',
    verified: '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6l8-3z"/><path d="M9 12l2 2 4-4"/>',
  };
  function icon(name, size, stroke) {
    return '<svg width="' + (size || 22) + '" height="' + (size || 22) + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="' + (stroke || 2) +
      '" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (P[name] || '') + '</svg>';
  }

  /* ---------- bottom nav ---------- */
  const TABS = [
    { id: 'alert', label: 'Alert', icon: 'shield', href: 'alert/index.html' },
    { id: 'vault', label: 'Vault', icon: 'lock', href: 'vault/pin.html' },
    { id: 'help', label: 'Help', icon: 'phone', href: 'help/index.html' },
    { id: 'fund', label: 'Fund', icon: 'wallet', href: 'fund/index.html' },
    { id: 'learn', label: 'Learn', icon: 'book', href: 'learn/index.html' },
  ];
  function renderNav(active) {
    const nav = document.createElement('nav');
    nav.className = 'nav';
    nav.setAttribute('aria-label', 'Main');
    nav.innerHTML = TABS.map((t) => t.id === active
      ? '<a href="' + url(t.href) + '" class="is-active" aria-current="page">' + icon(t.icon) + t.label + '</a>'
      : '<a href="' + url(t.href) + '" aria-label="' + t.label + '">' + icon(t.icon) + '</a>'
    ).join('');
    document.body.appendChild(nav);
  }

  /* ---------- wire common things on every page ---------- */
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-quick-exit]').forEach((b) => {
      b.innerHTML = icon('exit');
      b.setAttribute('aria-label', 'Quick exit');
      b.addEventListener('click', quickExit);
    });
    document.querySelectorAll('[data-icon]').forEach((el) => {
      el.insertAdjacentHTML('afterbegin', icon(el.dataset.icon, el.dataset.size, el.dataset.stroke));
    });
    const tab = document.body.dataset.tab;
    if (tab) renderNav(tab);
  });

  window.LA = { API_BASE, url, store, session, user, disguise, disguisePage, safeNext, enterApp, guard, ensureToken, quickExit, signOut, api, apiOr, errorText, secure, normSecret, setSecret, checkSecret, syncSettings, restoreSettings, toast, escapeHtml, wait, icon };
})();