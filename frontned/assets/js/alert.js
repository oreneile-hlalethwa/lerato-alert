(function () {
  const $ = (id) => document.getElementById(id);
  const user = LA.user() || {};
  const DISTRESS = ['leave me alone', 'help me', 'get off me', "don't touch me", 'dont touch me', 'let me go', 'stop it', 'somebody help'];
  const SCREAM_LEVEL = 0.32;   // RMS loudness 0..1
  const SCREAM_MS = 600;       // must stay that loud this long
  const CANCEL_SECONDS = 5;

  let mode = LA.store.get('mode', 'jogging');
  let active = false;
  let triggered = false;
  let recognition = null;
  let stream = null, audioCtx = null, analyser = null, rafId = null, loudSince = 0;
  let watchId = null, lastPosition = null;
  let countdownTimer = null;

  /* ---------- header + status ---------- */
  const hour = new Date().getHours();
  $('greeting').textContent = (hour < 12 ? 'Morning' : hour < 18 ? 'Afternoon' : 'Evening') + ', ' + (user.name || 'there');
  $('initial').textContent = (user.name || 'L').charAt(0).toUpperCase();

  function contacts() { return LA.store.get('contacts', []); }
  function safeWord() { return (LA.store.get('safeword', '') || '').trim().toLowerCase(); }

  function renderStatus() {
    const n = contacts().length;
    const word = safeWord();
    $('statWord').textContent = word ? 'Set & ready' : 'Not set';
    $('statContacts').textContent = n + ' linked';
    $('statLocation').textContent = lastPosition ? 'On' : (active ? 'Finding…' : 'Off');
    $('ring1').setAttribute('stroke-dasharray', (word ? 352 : 40) + ' 352');
    $('ring2').setAttribute('stroke-dasharray', Math.min(258, n * 86) + ' 258');
    $('ring3').setAttribute('stroke-dasharray', (lastPosition ? 163 : 20) + ' 163');
  }

  /* ---------- modes ---------- */
  const MODE_NAMES = { jogging: 'Jogging mode', commute: 'Commute mode', home: 'At-home mode' };
  function renderModes() {
    document.querySelectorAll('.mode').forEach((b) => {
      const on = b.dataset.mode === mode;
      b.setAttribute('aria-checked', on);
      b.querySelector('.mark').innerHTML = on ? '<span class="check">' + LA.icon('check', 16, 3) + '</span>' : '';
    });
    $('liveMode').textContent = MODE_NAMES[mode];
  }
  document.querySelectorAll('.mode').forEach((b) => b.addEventListener('click', () => {
    mode = b.dataset.mode;
    LA.store.set('mode', mode);
    renderModes();
  }));

  /* ---------- location ---------- */
  function startLocation() {
    if (!('geolocation' in navigator)) return;
    watchId = navigator.geolocation.watchPosition(
      (p) => { lastPosition = { lat: p.coords.latitude, lng: p.coords.longitude, accuracy: Math.round(p.coords.accuracy) }; renderStatus(); },
      () => renderStatus(),
      { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 }
    );
  }

  /* ---------- voice: safe word + distress phrases ---------- */
  function startSpeech() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { LA.toast('Voice detection is not supported in this browser. Scream detection is still on.'); return; }
    recognition = new SR();
    recognition.lang = 'en-ZA';
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      let text = '';
      for (let i = event.resultIndex; i < event.results.length; i++) text += event.results[i][0].transcript + ' ';
      text = text.toLowerCase().trim();
      $('heard').textContent = text ? '“' + text + '”' : '';
      const word = safeWord();
      if (word && text.includes(word)) return trigger('Safe word heard');
      const phrase = DISTRESS.find((p) => text.includes(p));
      if (phrase) trigger('Heard “' + phrase + '”');
    };
    recognition.onerror = (e) => {
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') LA.toast('Please allow microphone access.');
    };
    recognition.onend = () => {
      if (active && !triggered) { try { recognition.start(); } catch (e) {} }
    };
    try { recognition.start(); } catch (e) {}
  }

  /* ---------- sound: scream / sudden loud noise ---------- */
  async function startAudio() {
    stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false } });
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const src = audioCtx.createMediaStreamSource(stream);
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 1024;
    src.connect(analyser);
    const data = new Float32Array(analyser.fftSize);

    const loop = () => {
      analyser.getFloatTimeDomainData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i++) sum += data[i] * data[i];
      const rms = Math.sqrt(sum / data.length);
      $('meter').style.width = Math.min(100, rms * 250) + '%';
      const now = performance.now();
      if (rms > SCREAM_LEVEL) {
        if (!loudSince) loudSince = now;
        if (now - loudSince > SCREAM_MS) trigger('Scream detected');
      } else loudSince = 0;
      rafId = requestAnimationFrame(loop);
    };
    loop();
  }

  /* ---------- session on / off ---------- */
  async function startSession() {
    try {
      await startAudio();
    } catch (e) {
      LA.toast('Microphone permission is needed to listen for danger.');
      return;
    }
    active = true;
    triggered = false;
    startSpeech();
    startLocation();
    $('livePanel').classList.remove('hidden');
    $('startLabel').textContent = 'Stop session';
    $('startBtn').classList.add('btn--dark', 'listening');
    renderStatus();
    if (!safeWord()) LA.toast('Tip: set a safe word in Edit contacts.');
  }

  function stopSession() {
    active = false;
    if (recognition) { recognition.onend = null; try { recognition.stop(); } catch (e) {} recognition = null; }
    if (rafId) cancelAnimationFrame(rafId);
    if (audioCtx) audioCtx.close();
    if (stream) stream.getTracks().forEach((t) => t.stop());
    if (watchId !== null) navigator.geolocation.clearWatch(watchId);
    stream = audioCtx = analyser = null; watchId = null; loudSince = 0;
    $('livePanel').classList.add('hidden');
    $('heard').textContent = '';
    $('startLabel').textContent = 'Start safe session';
    $('startBtn').classList.remove('btn--dark', 'listening');
    renderStatus();
  }

  $('startBtn').addEventListener('click', () => (active ? stopSession() : startSession()));

  /* ---------- trigger → silent cancel window → send ---------- */
  function trigger(reason) {
    if (triggered || !active) return;
    triggered = true;
    let left = CANCEL_SECONDS;
    $('overlay').classList.remove('hidden');
    $('sheetCountdown').classList.remove('hidden');
    $('sheetSent').classList.add('hidden');
    $('count').textContent = left;
    $('reason').textContent = reason;
    $('cancelBtn').focus();
    countdownTimer = setInterval(() => {
      left -= 1;
      $('count').textContent = left;
      if (left <= 0) { clearInterval(countdownTimer); sendAlert(reason); }
    }, 1000);
  }

  $('cancelBtn').addEventListener('click', () => {
    clearInterval(countdownTimer);
    $('overlay').classList.add('hidden');
    triggered = false;
    loudSince = 0;
    if (active && recognition) { try { recognition.start(); } catch (e) {} }
    LA.toast('Cancelled. Still listening.');
  });

  $('doneBtn').addEventListener('click', () => {
    $('overlay').classList.add('hidden');
    triggered = false;
    loudSince = 0;
    if (active && recognition) { try { recognition.start(); } catch (e) {} }
  });

  function currentPosition() {
    if (lastPosition) return Promise.resolve(lastPosition);
    return new Promise((resolve) => {
      if (!('geolocation' in navigator)) return resolve(null);
      navigator.geolocation.getCurrentPosition(
        (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude, accuracy: Math.round(p.coords.accuracy) }),
        () => resolve(null),
        { enableHighAccuracy: true, timeout: 6000 }
      );
    });
  }

  function recordEvidence() {
    if (!stream || !window.MediaRecorder) return;
    try {
      const chunks = [];
      const rec = new MediaRecorder(stream);
      rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      rec.onstop = () => {
        const blob = new Blob(chunks, { type: rec.mimeType || 'audio/webm' });
        if (window.VaultDB) VaultDB.add({ kind: 'audio', title: 'Auto-recording · alert', blob });
      };
      rec.start();
      setTimeout(() => rec.state !== 'inactive' && rec.stop(), 60000);
    } catch (e) {}
  }

  async function sendAlert(reason) {
    recordEvidence();
    const position = await currentPosition();
    let list = contacts();
    if (mode === 'home') {
      const outside = list.filter((c) => c.type !== 'kin');
      if (outside.length) list = outside;
    }
    const payload = {
      user: { id: user.id, name: user.name, surname: user.surname, phone: user.phone },
      mode, reason,
      location: position,
      maps_link: position ? 'https://maps.google.com/?q=' + position.lat + ',' + position.lng : null,
      contacts: list,
      sent_at: new Date().toISOString(),
    };
    await LA.ensureToken();
    const res = await LA.apiOr('/alerts/', { body: payload, timeout: 20000 }, { demo: true });

    const names = list.map((c) => c.name).join(', ');
    $('sentText').textContent = (list.length
      ? 'We sent your live location to ' + names + '.'
      : 'Add trusted contacts so we can alert someone next time.') +
      (res && res.note ? ' ' + res.note : res && res.demo ? ' (Demo mode: server not connected yet.)' : '') +
      ' Audio is being saved to your vault.';
    $('sheetCountdown').classList.add('hidden');
    $('sheetSent').classList.remove('hidden');
  }

  window.addEventListener('pagehide', () => { if (active) stopSession(); });

  function homeScreenTip() {
    const standalone = window.navigator.standalone || window.matchMedia('(display-mode: standalone)').matches;
    if (standalone || LA.store.get('home_tip_seen', false)) return;
    const names = { calculator: 'Calculator', messages: 'Chats', browser: 'Search' };
    const tip = document.createElement('section');
    tip.className = 'card card--soft';
    tip.style.cssText = 'margin-bottom:16px;display:flex;gap:12px;align-items:flex-start';
    tip.innerHTML = '<div class="grow"><div style="font-weight:700;font-size:15px">Add to your Home Screen now</div>' +
      '<div class="small" style="margin-top:4px;line-height:1.5">Tap the exit button at the top right to open your <strong>' +
      names[LA.disguise().type] + '</strong> screen. Then tap Share and <strong>Add to Home Screen</strong>. Nobody will be able to tell it is Lerato Alert. If you change your disguise later, remove it and add it again.</div></div>' +
      '<button class="icon-btn" style="width:36px;height:36px;background:#fff" aria-label="Dismiss">' + LA.icon('check', 16, 3) + '</button>';
    tip.querySelector('button').addEventListener('click', () => { LA.store.set('home_tip_seen', true); tip.remove(); });
    document.getElementById('greeting').insertAdjacentElement('afterend', tip);
  }

  renderModes();
  renderStatus();
  homeScreenTip();
})();