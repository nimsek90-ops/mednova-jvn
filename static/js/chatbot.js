(() => {
  'use strict';
  const root = document.querySelector('#hospital-chat');
  if (!root) return;
  const log = document.querySelector('#chat-messages'), input = document.querySelector('#chat-input');
  const status = document.querySelector('#chat-status'), retry = document.querySelector('#chat-retry');
  const send = document.querySelector('#chat-send'), form = document.querySelector('#chat-compose');
  let busy = false, failed = null;
  function node(tag, text, cls) { const el = document.createElement(tag); if (text) el.textContent = text; if (cls) el.className = cls; return el; }
  function links(parent, items) {
    for (const item of items || []) {
      if (typeof item.url !== 'string' || !item.url.startsWith('/') || item.url.startsWith('//')) continue;
      const a = node('a', item.label); a.href = item.url; parent.append(a);
    }
  }
  function message(data, user = false) {
    const box = node('article', '', user ? 'chat-message chat-user' : 'chat-message');
    box.append(node('strong', user ? 'You' : 'MedNova assistant'), node('p', data.text));
    for (const card of data.cards || []) {
      const block = node('section', '', 'chat-result'); block.append(node('h3', card.title));
      for (const detail of card.details || []) block.append(node('p', detail));
      links(block, card.links); box.append(block);
    }
    links(box, data.links);
    const choices = node('div', '', 'chat-choices');
    for (const suggestion of data.suggestions || []) {
      const button = node('button', suggestion, 'secondary'); button.type = 'button';
      button.addEventListener('click', () => submit(suggestion)); choices.append(button);
    }
    box.append(choices);
    const time = node('time', new Date(data.timestamp || Date.now()).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}));
    time.dateTime = data.timestamp || new Date().toISOString(); box.append(time); log.append(box); log.scrollTop = log.scrollHeight;
  }
  async function api(payload) {
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(root.dataset.api, payload ? {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value}, body: JSON.stringify(payload), signal: controller.signal} : {credentials: 'same-origin', signal: controller.signal});
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || (response.status === 403 ? 'Your session changed. Reload this page and retry.' : 'The assistant is unavailable. Please retry shortly.'));
      return data;
    } catch (error) {
      if (error instanceof TypeError) throw new Error('Unable to reach the hospital server. Check your connection and retry.');
      throw error;
    } finally { clearTimeout(timer); }
  }
  function working(value) { busy = value; send.disabled = value; input.disabled = value; root.setAttribute('aria-busy', String(value)); }
  async function submit(text, repeat = false) {
    text = text.trim(); if (busy || !text || text.length > 500) return;
    if (!repeat) message({text}, true);
    working(true); retry.hidden = true; status.textContent = 'Checking hospital records…';
    try { message(await api({message: text})); failed = null; input.value = ''; status.textContent = ''; }
    catch (error) { failed = text; status.textContent = error.name === 'AbortError' ? 'The request timed out. Please retry.' : error.message; retry.hidden = false; }
    finally { working(false); input.focus(); }
  }
  form.addEventListener('submit', event => { event.preventDefault(); submit(input.value); });
  input.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); submit(input.value); } });
  retry.addEventListener('click', () => failed ? submit(failed, true) : load());
  document.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => submit(button.dataset.question)));
  document.querySelector('#chat-clear').addEventListener('click', async () => {
    if (busy) return; working(true);
    try { await api({action: 'clear'}); failed = null; await load(); }
    catch (error) { status.textContent = error.message; }
    finally { working(false); input.focus(); }
  });
  document.querySelector('#chat-close').addEventListener('click', () => { root.hidden = true; document.querySelector('#chat-reopen').hidden = false; document.querySelector('#chat-reopen').focus(); });
  document.querySelector('#chat-reopen').addEventListener('click', event => { root.hidden = false; event.currentTarget.hidden = true; input.focus(); });
  async function load() {
    try { const data = await api(); log.replaceChildren(); message(data.greeting); for (const item of data.history) message(item); status.textContent = ''; retry.hidden = true; }
    catch (error) { status.textContent = error.message; retry.hidden = false; }
  }
  load();
})();
