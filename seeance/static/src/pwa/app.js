/* Seeance kiosk PWA. Vanilla JS, no build step: talks to the plain-JSON
 * /seeance/kiosk/api/* endpoints, caches reference data + a submission
 * outbox in IndexedDB (via idb.js) so sign in/out keeps working offline,
 * and flushes the outbox whenever the network is reachable again. */
(function () {
  'use strict';

  const Idb = window.SeeanceIdb;
  const HEARTBEAT_INTERVAL_MS = 60 * 1000;

  const appEl = document.getElementById('app');
  const checkPointId = appEl.dataset.checkPointId;
  const urlPin = appEl.dataset.pin || null;

  const state = {
    pin: null,
    payload: null,
    online: navigator.onLine,
    screen: 'loading',
    search: '',
    selectedPerson: null,
    pendingMechanism: null,
    error: null,
    outboxCount: 0,
    deferredInstallPrompt: null,
  };

  // -- Networking -----------------------------------------------------------

  async function postJson(url, body) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    let data = null;
    try { data = await res.json(); } catch (e) { /* no body */ }
    if (!res.ok || (data && data.ok === false)) {
      throw new Error((data && data.error) || `Request failed (${res.status})`);
    }
    return data;
  }

  function getConnectionType() {
    const conn = navigator.connection || navigator.webkitConnection || navigator.mozConnection;
    if (!conn) return null;
    return conn.type || conn.effectiveType || null;
  }

  function osInfo() {
    return navigator.userAgent;
  }

  // -- Sync / offline cache --------------------------------------------------

  async function resolvePin() {
    if (urlPin) {
      await Idb.put('meta', { key: 'pin', value: urlPin });
      return urlPin;
    }
    const stored = await Idb.get('meta', 'pin');
    return stored ? stored.value : null;
  }

  async function syncNow() {
    const payload = await postJson('/seeance/kiosk/api/sync', {
      pin: state.pin, os_info: osInfo(), connection_type: getConnectionType(),
    });
    await Idb.put('meta', { key: 'payload', value: payload });
    await Idb.put('meta', { key: 'lastSync', value: new Date().toISOString() });
    return payload;
  }

  async function loadCachedPayload() {
    const record = await Idb.get('meta', 'payload');
    return record ? record.value : null;
  }

  async function refreshOutboxCount() {
    const items = await Idb.getAll('outbox');
    state.outboxCount = items.length;
  }

  async function heartbeat() {
    try {
      await postJson('/seeance/kiosk/api/heartbeat', {
        pin: state.pin, os_info: osInfo(), connection_type: getConnectionType(),
      });
      setOnline(true);
      await flushOutbox();
    } catch (e) {
      setOnline(false);
    }
  }

  function setOnline(isOnline) {
    if (state.online !== isOnline) {
      state.online = isOnline;
      render();
    }
  }

  async function queueOutboxItem(kind, body) {
    await Idb.put('outbox', { uuid: body.origin_uuid, kind, body, createdAt: Date.now() });
    await refreshOutboxCount();
  }

  async function flushOutbox() {
    const items = await Idb.getAll('outbox');
    items.sort((a, b) => a.createdAt - b.createdAt);
    for (const item of items) {
      const url = item.kind === 'visitor'
        ? '/seeance/kiosk/api/visitor_register'
        : '/seeance/kiosk/api/checkin';
      try {
        await postJson(url, item.body);
        await Idb.del('outbox', item.uuid);
      } catch (e) {
        break; // stay offline-ish: keep order, retry the rest next time
      }
    }
    await refreshOutboxCount();
    render();
  }

  // -- Submissions ------------------------------------------------------------

  function newUuid() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  async function submitCheckin(person, mechanism, imageDataUrl) {
    const body = {
      pin: state.pin,
      mechanism,
      datetime: new Date().toISOString(),
      origin_uuid: newUuid(),
    };
    if (imageDataUrl) body.image = imageDataUrl.split(',')[1];
    body[state.payload.identity_field] = person.id;
    try {
      await postJson('/seeance/kiosk/api/checkin', body);
      return { queued: false };
    } catch (e) {
      await queueOutboxItem('checkin', body);
      return { queued: true };
    }
  }

  async function submitVisitorRegistration(name, answers, imageDataUrl) {
    const body = {
      pin: state.pin,
      name,
      answers,
      datetime: new Date().toISOString(),
      origin_uuid: newUuid(),
    };
    if (imageDataUrl) body.image = imageDataUrl.split(',')[1];
    try {
      await postJson('/seeance/kiosk/api/visitor_register', body);
      return { queued: false };
    } catch (e) {
      await queueOutboxItem('visitor', body);
      return { queued: true };
    }
  }

  // -- Camera capture ----------------------------------------------------------

  let cameraStream = null;

  async function startCamera(videoEl) {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user' }, audio: false,
    });
    videoEl.srcObject = cameraStream;
    await videoEl.play();
  }

  function stopCamera() {
    if (cameraStream) {
      cameraStream.getTracks().forEach((t) => t.stop());
      cameraStream = null;
    }
  }

  function capturePhoto(videoEl) {
    const canvas = document.createElement('canvas');
    canvas.width = videoEl.videoWidth;
    canvas.height = videoEl.videoHeight;
    canvas.getContext('2d').drawImage(videoEl, 0, 0);
    return canvas.toDataURL('image/jpeg', 0.85);
  }

  // -- People list ---------------------------------------------------------

  function getPeople() {
    if (!state.payload) return [];
    const list = state.payload.identity_field === 'employee_id'
      ? (state.payload.employees || [])
      : (state.payload.users || []);
    const term = state.search.trim().toLowerCase();
    if (!term) return list;
    return list.filter((p) => p.name.toLowerCase().includes(term));
  }

  // -- Rendering -------------------------------------------------------------

  function h(html) {
    const div = document.createElement('div');
    div.innerHTML = html.trim();
    return div.firstElementChild;
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderBanner() {
    const cp = state.payload && state.payload.check_point;
    const statusClass = state.online ? 'seeance-online' : 'seeance-offline';
    const statusText = state.online ? 'Online' : 'Offline';
    const outbox = state.outboxCount
      ? `<span class="seeance-outbox-badge">${state.outboxCount} queued</span>` : '';
    const brand = cp ? `
        <div class="seeance-brand">
          <img class="seeance-company-logo" src="${cp.company_logo_url}" alt=""
               onerror="this.style.visibility='hidden'"/>
          <span class="seeance-company-name">${escapeHtml(cp.company_name || '')}</span>
        </div>` : '';
    return `
      <header class="seeance-header">
        ${brand}
        <div class="seeance-header-title">
          <div class="seeance-cp-name">${escapeHtml(cp ? cp.work_location_name || cp.name : 'Seeance')}</div>
          <div class="seeance-cp-sub">${escapeHtml(cp ? cp.name : '')}</div>
        </div>
        <div class="seeance-status ${statusClass}">
          <span class="seeance-dot"></span>${statusText}${outbox}
        </div>
      </header>`;
  }

  function renderLoading() {
    appEl.innerHTML = '<div class="seeance-boot">Loading Seeance…</div>';
  }

  function renderPinEntry() {
    appEl.innerHTML = `
      <div class="seeance-centered">
        <div class="seeance-card">
          <h1>Provision this Kiosk</h1>
          <p>Scan the QR code or open the Kiosk URL from the Check Point's
             configuration page in Odoo to provision this device.</p>
          <form id="seeance-pin-form">
            <input type="text" inputmode="text" placeholder="Kiosk PIN" id="seeance-pin-input" required="required"/>
            <button type="submit">Connect</button>
          </form>
          ${state.error ? `<p class="seeance-error">${escapeHtml(state.error)}</p>` : ''}
        </div>
      </div>`;
    document.getElementById('seeance-pin-form').addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const pin = document.getElementById('seeance-pin-input').value.trim();
      if (!pin) return;
      state.pin = pin;
      await boot();
    });
  }

  const ID_METHODS = [
    { key: 'pin', flag: 'allow_identification_pin', screen: 'idPin',
      icon: '🔢', label: 'Enter PIN', instructions: 'Enter your personal PIN on the keypad.' },
    { key: 'qr', flag: 'allow_identification_qr', screen: 'idQr',
      icon: '📷', label: 'Scan QR Code', instructions: "Hold your ID card's QR code up to the camera." },
    { key: 'rfid', flag: 'allow_identification_rfid', screen: 'idRfid',
      icon: '📶', label: 'Tap RFID Card', instructions: 'Tap or hold your RFID card on the reader.' },
  ];

  function getEnabledIdMethods() {
    const cp = state.payload.check_point;
    return ID_METHODS.filter((m) => cp[m.flag]);
  }

  function renderHome() {
    const people = getPeople();
    const installBtn = state.deferredInstallPrompt
      ? '<button id="seeance-install-btn" class="seeance-link-btn">Install App</button>' : '';
    const visitorBtn = (state.payload.features.visitor_registration
        && state.payload.check_point.allow_visitor_registration)
      ? '<button id="seeance-visitor-btn" class="seeance-secondary-btn">Register a Visitor</button>' : '';
    const methods = getEnabledIdMethods();
    const methodsSection = methods.length ? `
        <div class="seeance-id-methods">
          <p class="seeance-instructions">${methods.map((m) => escapeHtml(m.instructions)).join(' · ')}</p>
          <div class="seeance-id-buttons">
            ${methods.map((m) => `
              <button class="seeance-method-btn" data-screen="${m.screen}">
                <span class="seeance-method-icon">${m.icon}</span>${escapeHtml(m.label)}
              </button>`).join('')}
          </div>
          <p class="seeance-instructions seeance-muted">Or find your name below</p>
        </div>` : '';

    appEl.innerHTML = `
      ${renderBanner()}
      <main class="seeance-main">
        ${methodsSection}
        <input type="search" id="seeance-search" placeholder="Search your name…"
               value="${escapeHtml(state.search)}" autofocus="autofocus"/>
        <div class="seeance-people">
          ${people.length ? people.map((p) => `
            <button class="seeance-person" data-id="${p.id}">${escapeHtml(p.name)}</button>
          `).join('') : '<p class="seeance-empty">No matches</p>'}
        </div>
        <div class="seeance-footer">
          ${visitorBtn}
          ${installBtn}
        </div>
      </main>`;

    document.getElementById('seeance-search').addEventListener('input', (ev) => {
      state.search = ev.target.value;
      render();
    });
    appEl.querySelectorAll('.seeance-person').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = Number(btn.dataset.id);
        state.selectedPerson = getPeople().find((p) => p.id === id)
          || (state.payload.identity_field === 'employee_id' ? state.payload.employees : state.payload.users)
            .find((p) => p.id === id);
        state.screen = 'confirm';
        render();
      });
    });
    appEl.querySelectorAll('.seeance-method-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        state.error = null;
        state.screen = btn.dataset.screen;
        render();
      });
    });
    const visitorBtnEl = document.getElementById('seeance-visitor-btn');
    if (visitorBtnEl) visitorBtnEl.addEventListener('click', () => { state.screen = 'visitor'; render(); });
    const installBtnEl = document.getElementById('seeance-install-btn');
    if (installBtnEl) installBtnEl.addEventListener('click', async () => {
      if (!state.deferredInstallPrompt) return;
      state.deferredInstallPrompt.prompt();
      await state.deferredInstallPrompt.userChoice;
      state.deferredInstallPrompt = null;
      render();
    });
  }

  // -- Identification: PIN keypad / QR scan / RFID scan ----------------------

  function findPersonByBadgeCode(code) {
    const list = state.payload.identity_field === 'employee_id'
      ? (state.payload.employees || []) : (state.payload.users || []);
    return list.find((p) => p.badge_code && p.badge_code === code) || null;
  }

  function handleScannedCode(code) {
    const person = findPersonByBadgeCode(code);
    if (!person) {
      state.error = 'Card not recognized.';
      state.screen = 'home';
      render();
      return;
    }
    state.selectedPerson = person;
    state.error = null;
    state.screen = 'confirm';
    render();
  }

  async function submitIdPin(code) {
    if (!state.online) {
      state.error = 'PIN sign-in needs an internet connection. Try QR/RFID, or search your name, while offline.';
      render();
      return;
    }
    try {
      const res = await postJson('/seeance/kiosk/api/identify_by_pin', { pin: state.pin, code });
      state.selectedPerson = res.person;
      state.error = null;
      state.screen = 'confirm';
      render();
    } catch (e) {
      state.error = e.message || 'PIN not recognized.';
      render();
    }
  }

  function renderIdPin() {
    appEl.innerHTML = `
      ${renderBanner()}
      <main class="seeance-main seeance-centered">
        <div class="seeance-card seeance-keypad-card">
          <h2>Enter your PIN</h2>
          <p class="seeance-instructions">Enter your personal PIN, then press the checkmark.</p>
          <div class="seeance-pin-display" id="seeance-pin-display">—</div>
          <div class="seeance-keypad">
            ${['1', '2', '3', '4', '5', '6', '7', '8', '9', 'clear', '0', 'ok'].map((k) => {
              if (k === 'clear') return '<button class="seeance-key seeance-key-clear" data-key="clear">⌫</button>';
              if (k === 'ok') return '<button class="seeance-key seeance-key-ok" data-key="ok">✓</button>';
              return `<button class="seeance-key" data-key="${k}">${k}</button>`;
            }).join('')}
          </div>
          ${state.error ? `<p class="seeance-error">${escapeHtml(state.error)}</p>` : ''}
          <button id="seeance-id-cancel" class="seeance-link-btn">Back</button>
        </div>
      </main>`;

    let entered = '';
    const display = document.getElementById('seeance-pin-display');
    const updateDisplay = () => { display.textContent = entered ? entered.split('').map(() => '•').join(' ') : '—'; };
    appEl.querySelectorAll('.seeance-key').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const key = btn.dataset.key;
        if (key === 'clear') {
          entered = entered.slice(0, -1);
          updateDisplay();
        } else if (key === 'ok') {
          if (!entered) return;
          await submitIdPin(entered);
        } else if (entered.length < 8) {
          entered += key;
          updateDisplay();
        }
      });
    });
    document.getElementById('seeance-id-cancel').addEventListener('click', () => {
      state.error = null;
      state.screen = 'home';
      render();
    });
  }

  let qrDetectionActive = false;

  function renderIdQr() {
    appEl.innerHTML = `
      ${renderBanner()}
      <main class="seeance-main seeance-centered">
        <div class="seeance-card seeance-camera-card">
          <h2>Scan QR Code</h2>
          <p class="seeance-instructions">Hold your ID card's QR code up to the camera.</p>
          <div class="seeance-viewport">
            <video id="seeance-qr-video" playsinline="playsinline" autoplay="autoplay" muted="muted"></video>
            <div class="seeance-viewport-frame"></div>
          </div>
          ${state.error ? `<p class="seeance-error">${escapeHtml(state.error)}</p>` : ''}
          <button id="seeance-id-cancel" class="seeance-link-btn">Back</button>
        </div>
      </main>`;
    document.getElementById('seeance-id-cancel').addEventListener('click', () => {
      stopQrScan();
      state.screen = 'home';
      render();
    });
    startQrScan();
  }

  async function startQrScan() {
    const video = document.getElementById('seeance-qr-video');
    if (!('BarcodeDetector' in window)) {
      state.error = 'QR scanning is not supported on this device. Try another sign-in method.';
      render();
      return;
    }
    try {
      await startCamera(video);
    } catch (e) {
      state.error = 'Camera unavailable: ' + e.message;
      render();
      return;
    }
    const detector = new window.BarcodeDetector({ formats: ['qr_code'] });
    qrDetectionActive = true;
    const loop = async () => {
      if (!qrDetectionActive) return;
      try {
        const codes = await detector.detect(video);
        if (codes.length) {
          const value = codes[0].rawValue;
          stopQrScan();
          handleScannedCode(value);
          return;
        }
      } catch (e) { /* transient decode errors are normal mid-scan, keep looping */ }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  function stopQrScan() {
    qrDetectionActive = false;
    stopCamera();
  }

  let ndefController = null;

  function renderIdRfid() {
    appEl.innerHTML = `
      ${renderBanner()}
      <main class="seeance-main seeance-centered">
        <div class="seeance-card">
          <h2>Scan RFID Card</h2>
          <p class="seeance-instructions">Tap or hold your RFID card on the reader.</p>
          <div class="seeance-rfid-indicator">📶</div>
          <input type="text" id="seeance-rfid-input" class="seeance-rfid-hidden-input"
                 autocomplete="off" inputmode="none" autofocus="autofocus"/>
          ${state.error ? `<p class="seeance-error">${escapeHtml(state.error)}</p>` : ''}
          <button id="seeance-id-cancel" class="seeance-link-btn">Back</button>
        </div>
      </main>`;
    const input = document.getElementById('seeance-rfid-input');
    input.focus();
    // Most RFID/barcode reader peripherals (built-in or external) behave as a
    // keyboard "wedge": they type the card code followed by Enter into
    // whatever input is focused. This works regardless of the specific
    // hardware, since there's no generic Web RFID API to call directly.
    input.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter') {
        ev.preventDefault();
        const value = input.value.trim();
        input.value = '';
        if (value) handleScannedCode(value);
      }
    });
    input.addEventListener('blur', () => {
      if (state.screen === 'idRfid') setTimeout(() => input.focus(), 50);
    });
    startNfcScan();
    document.getElementById('seeance-id-cancel').addEventListener('click', () => {
      stopNfcScan();
      state.screen = 'home';
      render();
    });
  }

  async function startNfcScan() {
    // Best-effort: many RFID-labelled access cards are actually NFC, and
    // Chrome on Android exposes those via the Web NFC API. Falls back
    // silently to the keyboard-wedge input above when unavailable.
    if (!('NDEFReader' in window)) return;
    try {
      ndefController = new window.NDEFReader();
      await ndefController.scan();
      ndefController.onreading = (event) => {
        if (state.screen !== 'idRfid') return;
        if (event.serialNumber) handleScannedCode(event.serialNumber);
      };
    } catch (e) { /* NFC not available or permission denied - wedge input still works */ }
  }

  function stopNfcScan() {
    ndefController = null;
  }

  function renderConfirm() {
    const capturePhotoEnabled = !!(state.payload.check_point && state.payload.check_point.capture_photo);
    appEl.innerHTML = `
      ${renderBanner()}
      <main class="seeance-main seeance-centered">
        <div class="seeance-card">
          <h2>${escapeHtml(state.selectedPerson.name)}</h2>
          <div class="seeance-mechanism-buttons">
            <button class="seeance-primary-btn" data-mechanism="sign_in">Sign In</button>
            <button class="seeance-primary-btn seeance-sign-out" data-mechanism="sign_out">Sign Out</button>
          </div>
          <button id="seeance-cancel-btn" class="seeance-link-btn">Back</button>
        </div>
      </main>`;
    appEl.querySelectorAll('[data-mechanism]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const mechanism = btn.dataset.mechanism;
        if (capturePhotoEnabled) {
          state.pendingMechanism = mechanism;
          state.screen = 'camera';
          render();
        } else {
          await finishCheckin(mechanism, null);
        }
      });
    });
    document.getElementById('seeance-cancel-btn').addEventListener('click', () => {
      state.selectedPerson = null;
      state.screen = 'home';
      render();
    });
  }

  async function finishCheckin(mechanism, imageDataUrl) {
    const person = state.selectedPerson;
    const result = await submitCheckin(person, mechanism, imageDataUrl);
    state.selectedPerson = null;
    state.search = '';
    state.screen = 'done';
    render();
    setTimeout(() => {
      if (state.screen === 'done') { state.screen = 'home'; render(); }
    }, 2500);
    return result;
  }

  function renderCamera() {
    appEl.innerHTML = `
      ${renderBanner()}
      <main class="seeance-main seeance-centered">
        <div class="seeance-card seeance-camera-card">
          <video id="seeance-video" playsinline="playsinline" autoplay="autoplay"></video>
          <div class="seeance-camera-actions">
            <button id="seeance-capture-btn" class="seeance-primary-btn">Take Photo</button>
            <button id="seeance-camera-cancel" class="seeance-link-btn">Cancel</button>
          </div>
          ${state.error ? `<p class="seeance-error">${escapeHtml(state.error)}</p>` : ''}
        </div>
      </main>`;
    const video = document.getElementById('seeance-video');
    startCamera(video).catch((e) => {
      state.error = 'Camera unavailable: ' + e.message;
      render();
    });
    document.getElementById('seeance-capture-btn').addEventListener('click', async () => {
      const dataUrl = capturePhoto(video);
      stopCamera();
      await finishCheckin(state.pendingMechanism, dataUrl);
    });
    document.getElementById('seeance-camera-cancel').addEventListener('click', () => {
      stopCamera();
      state.screen = 'confirm';
      render();
    });
  }

  function renderVisitor() {
    const questions = (state.payload.visitor_questions || []).slice()
      .sort((a, b) => a.sequence - b.sequence);
    appEl.innerHTML = `
      ${renderBanner()}
      <main class="seeance-main seeance-centered">
        <div class="seeance-card">
          <h2>Visitor Registration</h2>
          <form id="seeance-visitor-form">
            <label>Name<input type="text" name="visitor_name" required="required"/></label>
            ${questions.map((q) => `
              <label>${escapeHtml(q.name)}${q.is_required ? ' *' : ''}
                <input type="text" name="q_${q.id}" ${q.is_required ? 'required="required"' : ''}/>
              </label>`).join('')}
            <button type="submit" class="seeance-primary-btn">Register</button>
          </form>
          <button id="seeance-visitor-cancel" class="seeance-link-btn">Back</button>
        </div>
      </main>`;
    document.getElementById('seeance-visitor-form').addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const form = ev.target;
      const name = form.visitor_name.value.trim();
      const answers = questions.map((q) => ({
        question_id: q.id, answer: form[`q_${q.id}`] ? form[`q_${q.id}`].value : '',
      }));
      await submitVisitorRegistration(name, answers, null);
      state.screen = 'done';
      render();
      setTimeout(() => {
        if (state.screen === 'done') { state.screen = 'home'; render(); }
      }, 2500);
    });
    document.getElementById('seeance-visitor-cancel').addEventListener('click', () => {
      state.screen = 'home';
      render();
    });
  }

  function renderDone() {
    appEl.innerHTML = `
      ${renderBanner()}
      <main class="seeance-main seeance-centered">
        <div class="seeance-card seeance-done">
          <div class="seeance-checkmark">✓</div>
          <p>${state.online ? 'Recorded.' : 'Saved offline. Will sync automatically once back online.'}</p>
        </div>
      </main>`;
  }

  function renderFatalError() {
    appEl.innerHTML = `
      <div class="seeance-centered">
        <div class="seeance-card">
          <h1>Unable to Load</h1>
          <p>${escapeHtml(state.error || 'This kiosk has never synced and no network connection is available.')}</p>
        </div>
      </div>`;
  }

  function render() {
    switch (state.screen) {
      case 'loading': return renderLoading();
      case 'pin': return renderPinEntry();
      case 'home': return renderHome();
      case 'idPin': return renderIdPin();
      case 'idQr': return renderIdQr();
      case 'idRfid': return renderIdRfid();
      case 'confirm': return renderConfirm();
      case 'camera': return renderCamera();
      case 'visitor': return renderVisitor();
      case 'done': return renderDone();
      case 'fatal': return renderFatalError();
      default: return renderLoading();
    }
  }

  // -- Boot -------------------------------------------------------------------

  async function boot() {
    state.screen = 'loading';
    render();

    if (!state.pin) {
      state.pin = await resolvePin();
    }
    if (!state.pin) {
      state.screen = 'pin';
      state.error = null;
      render();
      return;
    }

    try {
      state.payload = await syncNow();
      setOnline(true);
    } catch (e) {
      const cached = await loadCachedPayload();
      if (cached) {
        state.payload = cached;
        setOnline(false);
      } else {
        state.error = 'Could not reach the server and this kiosk has no offline data yet. '
          + 'Connect it to the network at least once before using it offline.';
        state.screen = 'fatal';
        render();
        return;
      }
    }

    await refreshOutboxCount();
    state.screen = 'home';
    render();
    flushOutbox();
  }

  window.addEventListener('online', () => { setOnline(true); flushOutbox(); syncNow().catch(() => {}); });
  window.addEventListener('offline', () => setOnline(false));
  window.addEventListener('beforeinstallprompt', (ev) => {
    ev.preventDefault();
    state.deferredInstallPrompt = ev;
    if (state.screen === 'home') render();
  });

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/seeance/kiosk/service-worker.js', { scope: '/seeance/kiosk/' })
      .catch(() => { /* offline install fallback still works via cache */ });
  }

  setInterval(heartbeat, HEARTBEAT_INTERVAL_MS);
  boot();
})();
