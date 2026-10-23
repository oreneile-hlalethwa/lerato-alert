/* Evidence vault: saved on the phone first (IndexedDB), then backed up privately
   to the server (Cloudinary) so evidence survives if the phone is taken or broken.
   Anything that fails to upload is retried next time the vault or app opens. */
(function () {
  const DB_NAME = 'lerato-vault';
  const STORE = 'evidence';

  function open() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: 'id' });
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  async function tx(mode, fn) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const t = db.transaction(STORE, mode);
      const result = fn(t.objectStore(STORE));
      t.oncomplete = () => resolve(result && 'result' in result ? result.result : undefined);
      t.onerror = () => reject(t.error);
    });
  }
  const put = (record) => tx('readwrite', (s) => s.put(record));
  const get = (id) => tx('readonly', (s) => s.get(id));

  /* ---------- server backup ---------- */
  const uploading = new Set();

  function authHeaders() {
    const token = (window.LA && LA.user() || {}).token;
    return token ? { 'X-Lerato-Token': token } : null;
  }

  async function upload(record) {
    const headers = authHeaders();
    if (!headers || record.remoteId || uploading.has(record.id)) return record;
    uploading.add(record.id);
    try {
      let res;
      if (record.kind === 'note') {
        res = await fetch(LA.API_BASE + '/vault/', {
          method: 'POST',
          headers: Object.assign({ 'Content-Type': 'application/json' }, headers),
          body: JSON.stringify({ client_id: record.id, kind: 'note', title: record.title, text: record.text, created: record.created }),
        });
      } else {
        const ext = (record.blob.type.split('/')[1] || 'bin').split(';')[0];
        const form = new FormData();
        form.append('client_id', record.id);
        form.append('kind', record.kind);
        form.append('title', record.title);
        form.append('created', record.created);
        form.append('file', record.blob, record.kind + '.' + ext);
        res = await fetch(LA.API_BASE + '/vault/', { method: 'POST', headers, body: form });
      }
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      const fresh = await get(record.id);
      if (fresh) {
        fresh.remoteId = data.id;
        await put(fresh);
        document.dispatchEvent(new CustomEvent('vault:synced', { detail: fresh }));
        return fresh;
      }
    } catch (e) {
      // Offline or server busy: stays on the phone and retries later.
    } finally {
      uploading.delete(record.id);
    }
    return record;
  }

  async function syncAll() {
    const items = await tx('readonly', (s) => s.getAll());
    for (const it of items || []) if (!it.remoteId) await upload(it);
  }

  // Items in the cloud that aren't on this phone (e.g. browser data was cleared).
  async function remoteOnly() {
    const headers = authHeaders();
    if (!headers) return [];
    try {
      const res = await fetch(LA.API_BASE + '/vault/', { headers });
      if (!res.ok) return [];
      const data = await res.json();
      const local = new Set(((await tx('readonly', (s) => s.getAll())) || []).map((x) => x.id));
      return (data.results || []).filter((r) => !local.has(r.client_id)).map((r) => ({
        id: r.client_id, remoteId: r.id, kind: r.kind, title: r.title, text: r.text, created: r.created, url: r.url, cloudOnly: true,
      }));
    } catch (e) {
      return [];
    }
  }

  async function removeRemote(remoteId) {
    const headers = authHeaders();
    if (!headers || !remoteId) return;
    try { await fetch(LA.API_BASE + '/vault/' + remoteId + '/', { method: 'DELETE', headers }); } catch (e) {}
  }

  window.VaultDB = {
    async add(item) {
      const record = Object.assign({ id: Date.now() + '-' + Math.random().toString(36).slice(2, 7), created: new Date().toISOString() }, item);
      await put(record);
      upload(record);  // in the background; never blocks saving on the phone
      return record;
    },
    async all() {
      const items = await tx('readonly', (s) => s.getAll());
      return (items || []).sort((a, b) => b.created.localeCompare(a.created));
    },
    async remove(id, remoteId) {
      await tx('readwrite', (s) => s.delete(id));
      await removeRemote(remoteId);
    },
    syncAll,
    remoteOnly,
  };

  // Retry pending uploads whenever the app opens or the phone comes back online.
  window.addEventListener('online', () => syncAll().catch(() => {}));
  setTimeout(() => syncAll().catch(() => {}), 1500);
})();