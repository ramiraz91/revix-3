/*!
 * Revix Widget v1.0.0 — Presupuestador conversacional embeddable.
 * Uso:
 *   <script src="https://revix.es/widget/revix-widget.js" defer></script>
 * Opciones (atributos del <script>):
 *   data-backend-url   URL del backend Revix (default: origin del script)
 *   data-color         Color principal hex (default: #1d4ed8)
 *   data-position      "right" | "left" (default: "right")
 *   data-title         Título de la cabecera (default: "Asistente Revix")
 *   data-greeting      Saludo inicial (default texto en español)
 *   data-auto-open     "true" para abrir al cargar
 */
(function () {
  'use strict';
  if (window.__RevixWidgetLoaded) return;
  window.__RevixWidgetLoaded = true;

  // ── Resolver script tag y opciones ───────────────────────────────────────
  var scriptTag = (function () {
    var ss = document.getElementsByTagName('script');
    for (var i = ss.length - 1; i >= 0; i--) {
      var src = ss[i].src || '';
      if (/revix-widget\.js(\?.*)?$/.test(src)) return ss[i];
    }
    return document.currentScript || ss[ss.length - 1];
  })();

  var SCRIPT_ORIGIN = (function () {
    try { return new URL(scriptTag.src).origin; } catch (_) { return window.location.origin; }
  })();
  var BACKEND = (scriptTag.getAttribute('data-backend-url') || SCRIPT_ORIGIN).replace(/\/$/, '');
  var COLOR = scriptTag.getAttribute('data-color') || '#1d4ed8';
  var POSITION = scriptTag.getAttribute('data-position') || 'right';
  var TITLE = scriptTag.getAttribute('data-title') || 'Asistente Revix';
  var GREETING = scriptTag.getAttribute('data-greeting') ||
    'Hola 👋 Soy el asistente de Revix. Cuéntame qué le pasa a tu dispositivo y te doy un presupuesto orientativo. ¿Qué quieres reparar?';
  var AUTO_OPEN = scriptTag.getAttribute('data-auto-open') === 'true';

  // ── Utils ────────────────────────────────────────────────────────────────
  function $(sel, root) { return (root || document).querySelector(sel); }
  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === 'style') Object.assign(n.style, attrs[k]);
      else if (k === 'class') n.className = attrs[k];
      else if (k.indexOf('on') === 0 && typeof attrs[k] === 'function') n.addEventListener(k.slice(2), attrs[k]);
      else n.setAttribute(k, attrs[k]);
    }
    (children || []).forEach(function (c) {
      if (c == null) return;
      n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    });
    return n;
  }
  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, function (m) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m];
    });
  }
  function getSession() {
    try {
      var s = localStorage.getItem('revix_widget_session');
      if (s) return s;
    } catch (_) {}
    return null;
  }
  function setSession(s) {
    try { localStorage.setItem('revix_widget_session', s); } catch (_) {}
  }

  // ── Inyectar estilos (scope: #revix-widget) ──────────────────────────────
  var STYLE = '\
#revix-widget *{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Oxygen,Ubuntu,sans-serif;margin:0;padding:0}\
#revix-widget{position:fixed;bottom:20px;' + (POSITION === 'left' ? 'left' : 'right') + ':20px;z-index:2147483640}\
#rvx-toggle{width:60px;height:60px;border-radius:50%;background:' + COLOR + ';color:#fff;border:0;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.18);display:flex;align-items:center;justify-content:center;transition:transform .2s,box-shadow .2s}\
#rvx-toggle:hover{transform:scale(1.05);box-shadow:0 12px 30px rgba(0,0,0,.22)}\
#rvx-toggle svg{width:28px;height:28px}\
#rvx-panel{position:absolute;bottom:76px;' + (POSITION === 'left' ? 'left:0' : 'right:0') + ';width:380px;max-width:calc(100vw - 32px);height:560px;max-height:calc(100vh - 110px);background:#fff;border-radius:16px;box-shadow:0 20px 50px rgba(0,0,0,.22);display:none;flex-direction:column;overflow:hidden;animation:rvx-pop .25s ease-out}\
#rvx-panel.open{display:flex}\
@keyframes rvx-pop{from{opacity:0;transform:translateY(8px)scale(.97)}to{opacity:1;transform:translateY(0)scale(1)}}\
#rvx-header{background:linear-gradient(135deg,' + COLOR + ',' + shade(COLOR, -15) + ');color:#fff;padding:16px;display:flex;align-items:center;gap:12px}\
#rvx-header .rvx-avatar{width:36px;height:36px;border-radius:50%;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;font-size:18px}\
#rvx-header h3{font-size:15px;font-weight:600;line-height:1.2}\
#rvx-header p{font-size:12px;opacity:.85;margin-top:2px}\
#rvx-close{margin-left:auto;background:transparent;border:0;color:#fff;cursor:pointer;opacity:.8;padding:4px;line-height:0}\
#rvx-close:hover{opacity:1}\
#rvx-body{flex:1;overflow-y:auto;padding:16px;background:#f8fafc;display:flex;flex-direction:column;gap:10px}\
.rvx-msg{max-width:85%;padding:10px 14px;border-radius:14px;font-size:14px;line-height:1.45;white-space:pre-wrap;word-wrap:break-word}\
.rvx-msg.assistant{background:#fff;color:#1f2937;align-self:flex-start;border:1px solid #e5e7eb;border-bottom-left-radius:4px}\
.rvx-msg.user{background:' + COLOR + ';color:#fff;align-self:flex-end;border-bottom-right-radius:4px}\
.rvx-disclaimer{font-size:11px;color:#64748b;font-style:italic;margin-top:4px;padding:0 4px}\
.rvx-typing{display:flex;gap:4px;padding:12px 14px;background:#fff;border:1px solid #e5e7eb;border-radius:14px;border-bottom-left-radius:4px;align-self:flex-start;width:fit-content}\
.rvx-typing span{width:7px;height:7px;background:#cbd5e1;border-radius:50%;animation:rvx-bounce 1.2s infinite}\
.rvx-typing span:nth-child(2){animation-delay:.15s}.rvx-typing span:nth-child(3){animation-delay:.3s}\
@keyframes rvx-bounce{0%,60%,100%{transform:translateY(0);opacity:.5}30%{transform:translateY(-5px);opacity:1}}\
#rvx-form{padding:12px;border-top:1px solid #e5e7eb;background:#fff;display:flex;gap:8px}\
#rvx-input{flex:1;border:1px solid #e2e8f0;border-radius:22px;padding:10px 16px;font-size:14px;outline:none;transition:border-color .15s}\
#rvx-input:focus{border-color:' + COLOR + '}\
#rvx-send{background:' + COLOR + ';color:#fff;border:0;width:42px;height:42px;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center}\
#rvx-send:disabled{opacity:.5;cursor:not-allowed}\
#rvx-send svg{width:18px;height:18px}\
#rvx-lead{background:#fff;border-top:1px solid #e5e7eb;padding:14px;display:none}\
#rvx-lead.show{display:block}\
#rvx-lead h4{font-size:13px;font-weight:600;margin-bottom:8px;color:#0f172a}\
#rvx-lead .rvx-row{display:flex;flex-direction:column;gap:6px;margin-bottom:8px}\
#rvx-lead label{font-size:11px;color:#64748b;font-weight:500}\
#rvx-lead input{border:1px solid #e2e8f0;border-radius:8px;padding:8px 10px;font-size:13px;outline:none}\
#rvx-lead input:focus{border-color:' + COLOR + '}\
#rvx-lead .rvx-consent{font-size:11px;color:#475569;display:flex;gap:6px;align-items:flex-start;margin-bottom:10px}\
#rvx-lead .rvx-consent input{margin-top:2px;flex-shrink:0;border:0;width:14px;height:14px}\
#rvx-lead .rvx-actions{display:flex;gap:8px}\
#rvx-lead button{flex:1;padding:9px;border-radius:8px;border:0;font-size:13px;font-weight:500;cursor:pointer}\
#rvx-lead .rvx-submit{background:' + COLOR + ';color:#fff}\
#rvx-lead .rvx-submit:disabled{opacity:.5;cursor:wait}\
#rvx-lead .rvx-cancel{background:#f1f5f9;color:#475569}\
#rvx-lead .rvx-error{color:#dc2626;font-size:11px;margin-top:4px;display:none}\
.rvx-cta{align-self:flex-start;margin-top:4px}\
.rvx-cta button{background:' + COLOR + '15;color:' + COLOR + ';border:1px solid ' + COLOR + '40;border-radius:18px;padding:6px 14px;font-size:12px;font-weight:500;cursor:pointer;transition:all .15s}\
.rvx-cta button:hover{background:' + COLOR + ';color:#fff}\
@media(max-width:480px){#rvx-panel{width:100vw;height:calc(100vh - 80px);right:-20px;bottom:80px;border-radius:16px 16px 0 0;max-width:100vw}}\
';

  function shade(hex, percent) {
    var h = hex.replace('#', '');
    var r = parseInt(h.substring(0, 2), 16);
    var g = parseInt(h.substring(2, 4), 16);
    var b = parseInt(h.substring(4, 6), 16);
    var f = (percent + 100) / 100;
    r = Math.max(0, Math.min(255, Math.round(r * f)));
    g = Math.max(0, Math.min(255, Math.round(g * f)));
    b = Math.max(0, Math.min(255, Math.round(b * f)));
    return '#' + [r, g, b].map(function (x) { return x.toString(16).padStart(2, '0'); }).join('');
  }

  // ── Construir DOM ────────────────────────────────────────────────────────
  var styleEl = document.createElement('style');
  styleEl.textContent = STYLE;
  document.head.appendChild(styleEl);

  var root = el('div', { id: 'revix-widget' });
  root.innerHTML = '\
<button id="rvx-toggle" data-testid="revix-widget-toggle" aria-label="Abrir chat">\
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>\
</button>\
<div id="rvx-panel" role="dialog" aria-label="Asistente Revix">\
  <div id="rvx-header">\
    <div class="rvx-avatar">💬</div>\
    <div>\
      <h3>' + escapeHtml(TITLE) + '</h3>\
      <p>Presupuesto orientativo · responde en ~15s</p>\
    </div>\
    <button id="rvx-close" data-testid="revix-widget-close" aria-label="Cerrar"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>\
  </div>\
  <div id="rvx-body" data-testid="revix-widget-body"></div>\
  <div id="rvx-lead" data-testid="revix-widget-lead">\
    <h4>📋 Déjanos tus datos y te contactamos</h4>\
    <div class="rvx-row"><label for="rvx-lead-nombre">Nombre</label><input id="rvx-lead-nombre" type="text" placeholder="Tu nombre" data-testid="lead-nombre" maxlength="100"/></div>\
    <div class="rvx-row"><label for="rvx-lead-email">Email</label><input id="rvx-lead-email" type="email" placeholder="tu@email.com" data-testid="lead-email" maxlength="120"/></div>\
    <div class="rvx-row"><label for="rvx-lead-tel">Teléfono (opcional)</label><input id="rvx-lead-tel" type="tel" placeholder="600 000 000" data-testid="lead-telefono" maxlength="30"/></div>\
    <label class="rvx-consent"><input type="checkbox" id="rvx-lead-consent" data-testid="lead-consent"/><span>Acepto que Revix procese mis datos para responder a esta consulta (RGPD).</span></label>\
    <div class="rvx-error" id="rvx-lead-error"></div>\
    <div class="rvx-actions">\
      <button class="rvx-cancel" id="rvx-lead-cancel" data-testid="lead-cancel">Cancelar</button>\
      <button class="rvx-submit" id="rvx-lead-submit" data-testid="lead-submit">Enviar</button>\
    </div>\
  </div>\
  <form id="rvx-form" data-testid="revix-widget-form">\
    <input id="rvx-input" type="text" placeholder="Escribe tu pregunta…" autocomplete="off" data-testid="revix-widget-input" maxlength="1000"/>\
    <button id="rvx-send" type="submit" data-testid="revix-widget-send" aria-label="Enviar"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg></button>\
  </form>\
</div>';
  document.body.appendChild(root);

  // ── Estado / referencias ─────────────────────────────────────────────────
  var $panel = $('#rvx-panel', root);
  var $body = $('#rvx-body', root);
  var $form = $('#rvx-form', root);
  var $input = $('#rvx-input', root);
  var $send = $('#rvx-send', root);
  var $lead = $('#rvx-lead', root);
  var $leadError = $('#rvx-lead-error', root);
  var sessionId = getSession();
  var disclaimerShown = false;
  var hasGreeting = false;

  // ── Helpers UI ───────────────────────────────────────────────────────────
  function appendMsg(role, text) {
    var m = el('div', { class: 'rvx-msg ' + role, 'data-testid': 'rvx-msg-' + role });
    m.textContent = text;
    $body.appendChild(m);
    $body.scrollTop = $body.scrollHeight;
    return m;
  }
  function appendDisclaimer() {
    if (disclaimerShown) return;
    disclaimerShown = true;
    var d = el('div', { class: 'rvx-disclaimer' });
    d.textContent = '⚠️ Las respuestas son orientativas y no constituyen compromiso de precio ni plazo.';
    $body.appendChild(d);
  }
  function appendCta() {
    var w = el('div', { class: 'rvx-cta' });
    var btn = el('button', {
      'data-testid': 'rvx-cta-lead',
      onclick: function () { $lead.classList.add('show'); $body.scrollTop = $body.scrollHeight; },
    });
    btn.textContent = '📋 Quiero que me contactéis';
    w.appendChild(btn);
    $body.appendChild(w);
  }
  function showTyping() {
    var t = el('div', { class: 'rvx-typing', id: 'rvx-typing' });
    t.innerHTML = '<span></span><span></span><span></span>';
    $body.appendChild(t);
    $body.scrollTop = $body.scrollHeight;
  }
  function hideTyping() {
    var t = $('#rvx-typing', root);
    if (t) t.remove();
  }

  // ── API ──────────────────────────────────────────────────────────────────
  function postJson(path, body) {
    return fetch(BACKEND + '/api/public/widget' + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    }).then(function (r) {
      return r.json().then(function (j) { return { ok: r.ok, status: r.status, data: j }; });
    });
  }

  function sendMessage(message) {
    appendMsg('user', message);
    $input.value = '';
    $send.disabled = true;
    showTyping();

    postJson('/chat', { message: message, session_id: sessionId })
      .then(function (res) {
        hideTyping();
        $send.disabled = false;
        if (!res.ok) {
          appendMsg('assistant', '❌ ' + (res.data && res.data.detail ? res.data.detail : 'Error de conexión.'));
          return;
        }
        sessionId = res.data.session_id; setSession(sessionId);
        appendMsg('assistant', res.data.reply || '…');
        appendDisclaimer();
        // Mostrar CTA después del segundo turno
        if (!$lead.classList.contains('show') && $body.querySelectorAll('.rvx-msg.user').length >= 1 && !$('.rvx-cta', $body)) {
          appendCta();
        }
      })
      .catch(function () {
        hideTyping();
        $send.disabled = false;
        appendMsg('assistant', '❌ No pudimos conectar. Revisa tu conexión e intenta de nuevo.');
      });
  }

  // ── Eventos ──────────────────────────────────────────────────────────────
  $('#rvx-toggle', root).addEventListener('click', function () {
    $panel.classList.add('open');
    if (!hasGreeting) {
      hasGreeting = true;
      appendMsg('assistant', GREETING);
      appendDisclaimer();
    }
    setTimeout(function () { $input.focus(); }, 120);
  });
  $('#rvx-close', root).addEventListener('click', function () {
    $panel.classList.remove('open');
  });
  $form.addEventListener('submit', function (e) {
    e.preventDefault();
    var v = $input.value.trim();
    if (v) sendMessage(v);
  });
  $('#rvx-lead-cancel', root).addEventListener('click', function () {
    $lead.classList.remove('show');
    $leadError.style.display = 'none';
  });
  $('#rvx-lead-submit', root).addEventListener('click', function () {
    var nombre = $('#rvx-lead-nombre', root).value.trim();
    var email = $('#rvx-lead-email', root).value.trim();
    var tel = $('#rvx-lead-tel', root).value.trim();
    var consent = $('#rvx-lead-consent', root).checked;
    $leadError.style.display = 'none';
    if (nombre.length < 2) return showError('Indica tu nombre');
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return showError('Email no válido');
    if (!consent) return showError('Necesitamos tu consentimiento RGPD');
    var btn = $('#rvx-lead-submit', root);
    btn.disabled = true; btn.textContent = 'Enviando…';
    postJson('/lead', {
      nombre: nombre, email: email, telefono: tel || null,
      session_id: sessionId, consent: true,
    })
      .then(function (res) {
        btn.disabled = false; btn.textContent = 'Enviar';
        if (!res.ok) return showError(res.data.detail || 'Error al enviar');
        $lead.classList.remove('show');
        appendMsg('assistant',
          '✅ ¡Recibido, ' + nombre + '! Te contactaremos en horario laboral. ' +
          'Mientras tanto, si tienes más dudas pregúntame aquí.');
      })
      .catch(function () {
        btn.disabled = false; btn.textContent = 'Enviar';
        showError('No pudimos enviar tus datos. Inténtalo de nuevo.');
      });
  });

  function showError(msg) {
    $leadError.textContent = msg;
    $leadError.style.display = 'block';
  }

  // ── Auto-open ────────────────────────────────────────────────────────────
  if (AUTO_OPEN) {
    setTimeout(function () { $('#rvx-toggle', root).click(); }, 800);
  }

  // API pública mínima
  window.RevixWidget = {
    open: function () { $('#rvx-toggle', root).click(); },
    close: function () { $('#rvx-close', root).click(); },
    version: '1.0.0',
  };
})();
