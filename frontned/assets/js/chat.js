(function () {
  function create(cfg) {
    const chat = document.getElementById('chat');
    const quick = document.getElementById('quick');
    const form = document.getElementById('composer');
    const input = document.getElementById('input');
    const history = [];
    const answers = [];
    let aiAvailable = true;
    let busy = false;

    function scrollDown() { chat.scrollTop = chat.scrollHeight; }

    function bubble(role, text) {
      const el = document.createElement('div');
      el.className = 'bubble ' + (role === 'user' ? 'bubble--me' : 'bubble--bot');
      el.textContent = text;
      chat.appendChild(el);
      scrollDown();
    }

    function actionButton(action) {
      const a = document.createElement('a');
      a.className = 'btn btn--sm';
      a.style.alignSelf = 'flex-start';
      a.href = action.href;
      a.textContent = action.label;
      chat.appendChild(a);
      scrollDown();
    }

    function setOptions(options) {
      quick.innerHTML = '';
      (options || []).forEach((o) => {
        const b = document.createElement('button');
        b.type = 'button';
        b.textContent = o;
        b.addEventListener('click', () => send(o));
        quick.appendChild(b);
      });
    }

    function typing(on) {
      const existing = chat.querySelector('.typing');
      if (!on) { if (existing) existing.remove(); return; }
      if (existing) return;
      const t = document.createElement('div');
      t.className = 'typing';
      t.setAttribute('role', 'img');
      t.setAttribute('aria-label', 'Typing');
      t.innerHTML = '<span></span><span></span><span></span>';
      chat.appendChild(t);
      scrollDown();
    }

    async function getReply(text) {
      if (aiAvailable) {
        try {
          const res = await LA.api(cfg.endpoint, { body: { messages: history, turn: answers.length, max_turns: cfg.maxTurns || null }, timeout: 45000 });
          if (res && res.reply) return res;
          throw new Error('empty');
        } catch (e) {
          aiAvailable = false;
        }
      }
      await LA.wait(700 + Math.random() * 600);
      return cfg.scripted(answers.slice(), text);
    }

    async function send(text) {
      text = (text || '').trim();
      if (!text || busy) return;
      busy = true;
      setOptions([]);
      bubble('user', text);
      history.push({ role: 'user', content: text });
      answers.push(text);
      if (cfg.onTurn) cfg.onTurn(answers.length);
      typing(true);
      const res = await getReply(text);
      typing(false);
      bubble('assistant', res.reply);
      history.push({ role: 'assistant', content: res.reply });
      if (res.action) actionButton(res.action);
      if (!res.done) setOptions(res.options);
      busy = false;
      input.focus();
    }

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const v = input.value;
      input.value = '';
      send(v);
    });

    if (cfg.opening) {
      if (cfg.opening.q) { bubble('assistant', cfg.opening.q); history.push({ role: 'assistant', content: cfg.opening.q }); }
      setOptions(cfg.opening.options);
    }
    if (cfg.onTurn) cfg.onTurn(0);
    return { send };
  }

  window.Chat = { create };
})();