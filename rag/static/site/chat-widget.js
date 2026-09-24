/* Auburn Engineering Giving Assistant — drop-in chat widget.
 *
 * Add to any page with one tag:
 *   <script src="http://<backend-host>/chat-widget.js" defer></script>
 *
 * The widget posts to /chat on the same server it was loaded from (override with
 * data-endpoint="https://.../chat" on the script tag). All styles are scoped under
 * #aug-chat so they can't clash with the host page's CSS.
 *
 * Privacy: the conversation lives only in this page's memory. It is never written to
 * localStorage, sessionStorage, or cookies, and it is gone on reload, navigation, tab close, or
 * "Clear". Recent turns are sent with each request so the assistant can follow up; the server
 * uses them for that answer and does not store them.
 */
(function () {
  const script = document.currentScript;
  const ENDPOINT = (script && script.dataset.endpoint) ||
    new URL('/chat', script ? script.src : location.href).href;
  const FALLBACK_REPLY = "I'm having trouble reaching the assistant right now. For help, please contact the Auburn Engineering giving office at augiving@auburn.edu or 334-844-1427.";
  const TEASER_KEY = 'aug-chat-teaser-dismissed'; // the only thing stored: a yes/no UI flag
  const HISTORY_SENT = 6; // most recent messages sent with each request

  const css = `
  #aug-chat{--navy:#0b2341;--navy-deep:#071830;--orange:#cc4e0b;--orange-hi:#e86100;
    font-family:'Source Sans 3',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;line-height:1.5;}
  #aug-chat *{box-sizing:border-box;}
  #aug-chat .launcher{position:fixed;right:26px;bottom:26px;z-index:2147483000;display:flex;align-items:flex-end;gap:12px;}
  #aug-chat .teaser{background:#fff;color:#1d232c;max-width:250px;padding:14px 34px 14px 16px;border-radius:14px;
    box-shadow:0 10px 30px rgba(11,35,65,.22);font-size:15px;line-height:1.4;position:relative;cursor:pointer;
    opacity:0;transform:translateY(8px) scale(.97);transition:opacity .35s ease,transform .35s ease;pointer-events:none;}
  #aug-chat .teaser.show{opacity:1;transform:none;pointer-events:auto;}
  #aug-chat .teaser::after{content:"";position:absolute;right:26px;bottom:-7px;width:14px;height:14px;background:#fff;transform:rotate(45deg);}
  #aug-chat .teaser-close{position:absolute;top:6px;right:8px;border:none;background:none;color:#8a93a0;font-size:16px;line-height:1;cursor:pointer;padding:4px;}
  #aug-chat .teaser-close:hover{color:#1d232c;}
  #aug-chat .toggle{width:60px;height:60px;border-radius:50%;background:var(--orange);border:none;cursor:pointer;flex:none;
    box-shadow:0 8px 22px rgba(204,78,11,.4);display:flex;align-items:center;justify-content:center;position:relative;
    transition:transform .15s ease,background .15s ease;}
  #aug-chat .toggle:hover{background:var(--orange-hi);transform:translateY(-2px);}
  #aug-chat .toggle svg{width:26px;height:26px;}
  #aug-chat .ping{position:absolute;top:-2px;right:-2px;width:14px;height:14px;border-radius:50%;background:#2bb673;border:2px solid #fff;}
  #aug-chat .panel{position:fixed;right:26px;bottom:26px;width:380px;max-width:calc(100vw - 32px);height:560px;
    max-height:calc(100vh - 52px);min-width:300px;min-height:340px;background:var(--navy-deep);border-radius:16px;
    box-shadow:0 24px 60px rgba(0,0,0,.35);z-index:2147483001;display:flex;flex-direction:column;overflow:hidden;
    transform:translateY(24px) scale(.96);opacity:0;pointer-events:none;transition:opacity .25s ease,transform .25s ease;}
  #aug-chat .panel.open{opacity:1;transform:none;pointer-events:auto;}
  #aug-chat .panel.resizing{transition:none;}
  #aug-chat .resize{position:absolute;left:6px;top:6px;width:16px;height:16px;cursor:nwse-resize;z-index:5;opacity:.55;}
  #aug-chat .resize svg{width:100%;height:100%;stroke:#8aa0c4;stroke-width:1.5;}
  #aug-chat .resize:hover{opacity:.9;}
  #aug-chat .head{padding:18px 18px 16px;display:flex;align-items:center;gap:12px;
    background:linear-gradient(135deg,#153a66 0%,var(--navy) 60%);border-bottom:1px solid rgba(255,255,255,.08);}
  #aug-chat .avatar{width:38px;height:38px;border-radius:50%;background:var(--orange);display:flex;align-items:center;justify-content:center;flex:none;}
  #aug-chat .avatar svg{width:20px;height:20px;stroke:#fff;fill:none;stroke-width:2;}
  #aug-chat .head-text{flex:1;min-width:0;}
  #aug-chat .name{color:#fff;font-weight:700;font-size:16px;}
  #aug-chat .status{color:#9fd8b8;font-size:12.5px;display:flex;align-items:center;gap:5px;}
  #aug-chat .status::before{content:"";width:6px;height:6px;border-radius:50%;background:#2bb673;}
  #aug-chat .close{border:none;background:none;color:#b9c4d6;font-size:22px;cursor:pointer;padding:4px;line-height:1;}
  #aug-chat .close:hover{color:#fff;}
  #aug-chat .messages{flex:1;overflow-y:auto;padding:20px 18px;display:flex;flex-direction:column;gap:14px;}
  #aug-chat .msg{max-width:86%;font-size:15px;line-height:1.5;}
  #aug-chat .msg.bot{align-self:flex-start;}
  #aug-chat .msg.user{align-self:flex-end;}
  #aug-chat .bubble{padding:12px 15px;border-radius:14px;white-space:pre-wrap;overflow-wrap:anywhere;}
  #aug-chat .msg.bot .bubble{background:#122e52;color:#edeff3;border-bottom-left-radius:4px;}
  #aug-chat .msg.user .bubble{background:var(--orange);color:#fff;border-bottom-right-radius:4px;}
  #aug-chat .bubble a{color:#ffb48a;}
  #aug-chat .meta{font-size:11.5px;color:#7c8aa0;margin-top:5px;padding:0 3px;}
  #aug-chat .msg.user .meta{text-align:right;}
  #aug-chat .sources{font-size:12px;color:#9aabc4;margin-top:6px;padding:0 3px;overflow-wrap:anywhere;}
  #aug-chat .sources a{color:#ffb48a;text-decoration:underline;}
  #aug-chat .quick{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;}
  #aug-chat .quick button{background:transparent;border:1px solid #2e4c71;color:#cbd6e6;font:inherit;font-size:13px;
    padding:7px 12px;border-radius:20px;cursor:pointer;transition:background .15s ease,border-color .15s ease;}
  #aug-chat .quick button:hover{background:#122e52;border-color:var(--orange);color:#fff;}
  #aug-chat .typing .bubble{color:#9aabc4;}
  #aug-chat .input-row{border-top:1px solid rgba(255,255,255,.08);padding:12px 14px;}
  #aug-chat .field{display:flex;align-items:center;background:#0c1f3c;border-radius:10px;padding:6px 8px 6px 14px;gap:8px;}
  #aug-chat .field input{flex:1;background:none;border:none;outline:none;color:#fff;font:inherit;font-size:15px;padding:8px 0;min-width:0;}
  #aug-chat .field input::placeholder{color:#6f80a3;}
  #aug-chat .send{width:34px;height:34px;border-radius:8px;background:var(--orange);border:none;display:flex;
    align-items:center;justify-content:center;cursor:pointer;flex:none;}
  #aug-chat .send:hover{background:var(--orange-hi);}
  #aug-chat .send:disabled{opacity:.5;cursor:default;}
  #aug-chat .send svg{width:16px;height:16px;fill:#fff;}
  #aug-chat .foot{display:flex;justify-content:space-between;gap:8px;font-size:11px;color:#6a7a97;padding-top:8px;}
  #aug-chat .foot button{background:none;border:none;color:#8aa0c4;font:inherit;font-size:11px;cursor:pointer;padding:0;text-decoration:underline;}
  @media (max-width:460px){
    #aug-chat .panel{right:0;bottom:0;left:0;width:100%;max-width:100%;height:100%;max-height:100%;border-radius:0;}
    #aug-chat .launcher{right:16px;bottom:16px;}
    #aug-chat .resize{display:none;}
    #aug-chat .teaser{max-width:200px;}
  }
  @media (prefers-reduced-motion:reduce){#aug-chat .teaser,#aug-chat .panel,#aug-chat .toggle{transition:none;}}`;

  const BUBBLE_ICON = '<path d="M21 11.5c0 4.14-4.03 7.5-9 7.5-1.06 0-2.08-.15-3.02-.43L4 20l1.06-3.18C4.4 15.6 4 14.6 4 13.5 4 9.36 8.03 6 13 6s9 3.36 9 5.5z"/>';
  const GREETING = "Hi! I'm the Auburn Engineering giving assistant. I can help with ways to give, supporting a specific department, the EAGLE Society, or finding the right person on our advancement team.";
  const QUICK = ['How do I make a gift?', 'Can I give to my department?', 'Who can I talk to about a gift?'];

  const root = document.createElement('div');
  root.id = 'aug-chat';
  root.innerHTML = `
    <style>${css}</style>
    <div class="launcher">
      <div class="teaser" role="button" tabindex="0" aria-label="Open chat with the Auburn Engineering giving assistant">
        <button class="teaser-close" aria-label="Dismiss">&times;</button>
        Questions about giving to Auburn Engineering? I can help.
      </div>
      <button class="toggle" aria-label="Open Auburn Engineering giving assistant" aria-haspopup="dialog" aria-expanded="false">
        <span class="ping"></span>
        <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${BUBBLE_ICON}</svg>
      </button>
    </div>
    <div class="panel" role="dialog" aria-modal="false" aria-label="Auburn Engineering Giving Assistant">
      <div class="resize" title="Drag to resize" aria-hidden="true"><svg viewBox="0 0 16 16"><path d="M14 2 L2 14 M9 2 L2 9 M14 7 L7 14"/></svg></div>
      <div class="head">
        <div class="avatar"><svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">${BUBBLE_ICON}</svg></div>
        <div class="head-text"><div class="name">Engineering Giving Assistant</div><div class="status">Online now</div></div>
        <button class="close" aria-label="Close chat">&times;</button>
      </div>
      <div class="messages" aria-live="polite"></div>
      <div class="input-row">
        <div class="field">
          <input type="text" placeholder="Ask about giving to Auburn Engineering..." autocomplete="off" maxlength="1000" aria-label="Your question">
          <button class="send" aria-label="Send message"><svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></svg></button>
        </div>
        <div class="foot"><span>Answers come from official Auburn Engineering giving pages. Verify details at the linked source.</span><button class="reset" title="Clear this conversation">Clear</button></div>
      </div>
    </div>`;
  document.body.appendChild(root);

  const $ = (sel) => root.querySelector(sel);
  const teaser = $('.teaser'), toggle = $('.toggle'), panel = $('.panel');
  const messages = $('.messages'), input = $('.field input'), sendBtn = $('.send');

  // ---- State: conversation in memory only ----
  const state = { history: [] };
  function teaserDismissed() {
    try { return sessionStorage.getItem(TEASER_KEY) === '1'; } catch (e) { return false; }
  }
  function dismissTeaser() {
    try { sessionStorage.setItem(TEASER_KEY, '1'); } catch (e) { /* storage unavailable */ }
  }

  // ---- Rendering ----
  function linkify(text) {
    // Build DOM nodes (never innerHTML) so answers can't inject markup.
    const frag = document.createDocumentFragment();
    const re = /https?:\/\/[^\s<>()]+[^\s<>().,;:!?'"]/g;
    let last = 0, m;
    while ((m = re.exec(text))) {
      frag.append(text.slice(last, m.index));
      const a = document.createElement('a');
      a.href = m[0]; a.textContent = m[0]; a.target = '_blank'; a.rel = 'noopener';
      frag.append(a);
      last = m.index + m[0].length;
    }
    frag.append(text.slice(last));
    return frag;
  }

  function render(entry, withQuick) {
    const wrap = document.createElement('div');
    wrap.className = 'msg ' + entry.from;
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.append(entry.from === 'bot' ? linkify(entry.text) : entry.text);
    wrap.append(bubble);
    const links = (entry.sources || []).filter((u) => /^https?:\/\//.test(u));
    if (links.length) {
      const src = document.createElement('div');
      src.className = 'sources';
      src.append('Sources: ');
      links.forEach((u, i) => {
        const a = document.createElement('a');
        a.href = u; a.target = '_blank'; a.rel = 'noopener';
        a.textContent = u.replace(/^https?:\/\//, '').replace(/\/$/, '');
        if (i) src.append(' · ');
        src.append(a);
      });
      wrap.append(src);
    }
    const meta = document.createElement('div');
    meta.className = 'meta';
    meta.textContent = entry.from === 'bot' ? 'Giving Assistant' : 'You';
    wrap.append(meta);
    if (withQuick) {
      const q = document.createElement('div');
      q.className = 'quick';
      QUICK.forEach((text) => {
        const b = document.createElement('button');
        b.type = 'button'; b.textContent = text;
        b.addEventListener('click', () => ask(text));
        q.append(b);
      });
      wrap.append(q);
    }
    messages.append(wrap);
    messages.scrollTop = messages.scrollHeight;
    return wrap;
  }

  function renderAll() {
    messages.textContent = '';
    render({ from: 'bot', text: GREETING }, state.history.length === 0);
    state.history.forEach((e) => render(e));
  }

  // ---- Talking to the backend ----
  async function fetchReply(text, history) {
    try {
      const res = await fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        cache: 'no-store',
        body: JSON.stringify({ message: text, history }),
      });
      if (!res.ok) throw new Error('Backend returned ' + res.status);
      const data = await res.json();
      return { from: 'bot', text: (data.answer || '').trim() || FALLBACK_REPLY, sources: data.sources || [] };
    } catch (err) {
      console.error('Giving assistant request failed:', err);
      return { from: 'bot', text: FALLBACK_REPLY, sources: [], failed: true };
    }
  }

  let busy = false;
  async function ask(text) {
    text = (text || '').trim();
    if (!text || busy) return;
    busy = true; sendBtn.disabled = true;
    const quick = messages.querySelector('.quick');
    if (quick) quick.remove();
    // Earlier turns for context; connection-error replies aren't part of the conversation.
    const history = state.history.filter((e) => !e.failed).slice(-HISTORY_SENT)
      .map((e) => ({ role: e.from === 'user' ? 'user' : 'assistant', content: e.text }));
    const userEntry = { from: 'user', text };
    state.history.push(userEntry);
    render(userEntry);
    const typing = render({ from: 'bot', text: 'Typing…' });
    typing.classList.add('typing');
    const reply = await fetchReply(text, history);
    typing.remove();
    state.history.push(reply);
    render(reply);
    busy = false; sendBtn.disabled = false;
    input.focus();
  }

  // ---- Open / close / teaser ----
  function openChat() {
    teaser.classList.remove('show');
    dismissTeaser();
    panel.classList.add('open');
    toggle.setAttribute('aria-expanded', 'true');
    setTimeout(() => input.focus(), 200);
  }
  function closeChat() {
    panel.classList.remove('open');
    toggle.setAttribute('aria-expanded', 'false');
  }
  toggle.addEventListener('click', () => (panel.classList.contains('open') ? closeChat() : openChat()));
  $('.close').addEventListener('click', closeChat);
  teaser.addEventListener('click', openChat);
  teaser.addEventListener('keydown', (e) => { if (e.key === 'Enter') openChat(); });
  $('.teaser-close').addEventListener('click', (e) => {
    e.stopPropagation();
    dismissTeaser();
    teaser.classList.remove('show');
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && panel.classList.contains('open')) closeChat(); });

  sendBtn.addEventListener('click', () => { const v = input.value; input.value = ''; ask(v); });
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { const v = input.value; input.value = ''; ask(v); } });
  $('.reset').addEventListener('click', () => { state.history = []; renderAll(); });

  // ---- Drag-to-resize (panel is anchored bottom-right, so the grip is top-left) ----
  const MIN_W = 300, MIN_H = 340;
  let drag = null;
  $('.resize').addEventListener('pointerdown', (e) => {
    if (window.innerWidth <= 460) return;
    const r = panel.getBoundingClientRect();
    drag = { x: e.clientX, y: e.clientY, w: r.width, h: r.height };
    panel.classList.add('resizing');
    e.preventDefault();
  });
  document.addEventListener('pointermove', (e) => {
    if (!drag) return;
    const w = Math.min(Math.max(drag.w + drag.x - e.clientX, MIN_W), Math.min(640, window.innerWidth - 32));
    const h = Math.min(Math.max(drag.h + drag.y - e.clientY, MIN_H), Math.min(window.innerHeight - 32, 760));
    panel.style.width = w + 'px';
    panel.style.height = h + 'px';
  });
  document.addEventListener('pointerup', () => { drag = null; panel.classList.remove('resizing'); });

  // ---- Start ----
  renderAll();
  if (!teaserDismissed()) setTimeout(() => { if (!panel.classList.contains('open')) teaser.classList.add('show'); }, 1800);
})();
