/* N8-Hotspot web interface. No build step, no external libraries. */
'use strict';

const $ = id => document.getElementById(id);
const S = { info: null, me: null, live: null, ws: null, wsOk: false, lhFilter: 'all', today: null,
            stats: { range: 'today', metric: 'duration', by: 'tg', data: null, slots: {} },
            admin: { tab: 'settings', settings: null, cal: null, logs: [], logFilter: 'all' }, tab: 'live' };

// ---------------------------------------------------------------- helpers
function esc(v) { return String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
async function api(method, url, body) {
    const opt = { method, credentials: 'same-origin', headers: { 'X-N8': '1' } };
    if (body !== undefined) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
    const r = await fetch(url, opt);
    let j = {};
    try { j = await r.json(); } catch (e) {}
    if (!r.ok) { const err = new Error(j.error || r.statusText); err.status = r.status; throw err; }
    return j;
}
function fmtDur(s, short) {
    s = Math.round(s || 0);
    if (s < 60) return `${s} s`;
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    if (h) return short ? `${h} h${m ? ' ' + m + ' m' : ''}` : `${h} h ${m} m`;
    return short || !sec ? `${m} m` : `${m} m ${sec} s`;
}
function fmtClock(sec) { sec = Math.max(0, Math.floor(sec)); return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`; }
function fmtFreq(hz) { if (!hz) return '–'; return (hz / 1e6).toFixed(4) + ' MHz'; }
function fmtFreqLong(hz) { const s = String(hz).padStart(9, '0'); return `${s.slice(0, 3)}.${s.slice(3, 6)} ${s.slice(6)} MHz`; }
function fmtTime(ts) { return new Date(ts * 1000).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' }); }
function fmtDate(ts) { return ts ? new Date(ts * 1000).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '–'; }
function ago(ts) {
    const d = Date.now() / 1000 - ts;
    if (d < 60) return 'just now'; if (d < 3600) return `${Math.floor(d / 60)} min ago`;
    if (d < 86400) return `${Math.floor(d / 3600)} h ago`; return fmtDate(ts);
}
function fmtBytes(b) { if (b == null) return '–'; const u = ['B', 'KB', 'MB', 'GB', 'TB']; let i = 0; while (b >= 1024 && i < 4) { b /= 1024; i++; } return `${b.toFixed(b < 10 && i ? 1 : 0)} ${u[i]}`; }
function initials(c) { return esc((c || '?').replace(/[^A-Za-z0-9]/g, '').slice(0, 2).toUpperCase() || '?'); }
function avatarColor(id) { const h = (Number(id) * 47) % 360; return `linear-gradient(135deg, hsl(${h} 70% 50%), hsl(${(h + 40) % 360} 75% 42%))`; }
function avatar(id, call, frid, cls) {
    const img = frid && S.info && S.info.avatars && id ? `<img src="/api/avatar/${id}" alt="" loading="lazy" onerror="this.remove()">` : '';
    return `<span class="avatar ${cls || ''}" style="background:${avatarColor(id)}">${initials(call)}${img}</span>`;
}
function fridBadge(on) { return on ? '<span class="frid" title="Registered at FreeRadioID.net">FRID</span>' : ''; }
function tgName(tg) { return (S.info && S.info.tg_names && S.info.tg_names[tg]) || ''; }
function target(e) {
    if (!e.group) return `👤 ${esc(e.dst_id)}`;
    const n = tgName(e.dst_id);
    return `<span class="pill tg">TG ${esc(e.dst_id)}${n ? ` <span class="dim" style="font-weight:500">${esc(n)}</span>` : ''}</span>`;
}
function toast(msg, bad) {
    const t = document.createElement('div');
    t.className = 'chip ' + (bad ? 'bad' : 'ok');
    t.style.cssText = 'position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:4000;box-shadow:0 10px 30px rgba(0,0,0,.4)';
    t.textContent = msg; document.body.appendChild(t); setTimeout(() => t.remove(), 3200);
}
function isAdmin() { return S.me && S.me.role === 'admin'; }

// ---------------------------------------------------------------- boot
async function boot() {
    try {
        const info = await api('GET', '/api/info');
        S.info = info; S.me = info.user || null;
        applyUI(info);
        if (info.login_required && !S.me) { renderHeader(); openLogin(true); return; }
        renderAll();
        connectWS();
        loadToday();
        checkUpdateQuiet();
        const h = location.hash.replace('#', '');
        if (h) { const [t, a] = h.split('/'); if (t === 'stats' || t === 'tgs') showTab(t); else if (t === 'admin' && isAdmin()) showTab('admin', a); }
    } catch (e) { console.error(e); setTimeout(boot, 3000); }
}
function renderAll() { renderHeader(); renderUser(); renderInfo(); renderSlots(); renderLH(); renderFooter(S.info.build); }

function renderHeader() {
    const i = S.info || {};
    $('title').textContent = i.title || 'N8 Hotspot';
    document.title = i.title || 'N8 Hotspot';
    if (i.callsign) $('subtitle').textContent = `${i.callsign} · ${i.hotspot_id} · ${fmtFreq(i.rx_freq)} · CC${i.color_code}${i.demo ? ' · Demo' : ''}`;
    $('tabAdminBtn').classList.toggle('hidden', !isAdmin());
    $('defaultBanner').classList.toggle('hidden', !(isAdmin() && S.me.default_pw));
}
function renderUser() {
    const el = $('userArea');
    if (!S.me) { el.innerHTML = '<button class="btn primary" onclick="openLogin()">🔐 Login</button>'; return; }
    el.innerHTML = `<button class="btn" onclick="userMenu(event)" title="${esc(S.me.display_name || S.me.username)}">👤 <span class="u-name">${esc(S.me.display_name || S.me.username)}</span> ▾</button>`;
}
function userMenu(ev) {
    ev.stopPropagation();
    closeModal();
    const r = ev.target.getBoundingClientRect();
    const m = document.createElement('div');
    m.className = 'glass'; m.id = 'umenu';
    m.style.cssText = `position:fixed;top:${r.bottom + 8}px;right:${Math.max(8, innerWidth - r.right)}px;z-index:300;border-radius:16px;padding:6px;min-width:200px;background:var(--surface-2, rgba(22,28,48,.95))`;
    m.innerHTML = `<div style="padding:8px 12px" class="dim">${esc(S.me.username)} · ${esc(S.me.role)}</div>
        ${isAdmin() ? '<button class="btn" style="width:100%;border-radius:10px;margin:2px 0" onclick="showTab(\'admin\')">⚙️ Admin</button>' : ''}
        <button class="btn" style="width:100%;border-radius:10px;margin:2px 0" onclick="openAccount()">🔑 My account</button>
        <button class="btn" style="width:100%;border-radius:10px;margin:2px 0" onclick="logout()">🚪 Log out</button>`;
    document.body.appendChild(m);
    setTimeout(() => document.addEventListener('click', () => m.remove(), { once: true }), 0);
}

// ---------------------------------------------------------------- modals
function modal(html, locked) {
    $('modalRoot').innerHTML = `<div class="overlay" id="ov"><div class="modal">${html}</div></div>`;
    if (!locked) $('ov').addEventListener('click', e => { if (e.target.id === 'ov') closeModal(); });
}
function closeModal() { $('modalRoot').innerHTML = ''; }
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !$('ov')?.dataset.locked) closeModal(); });

function openLogin(locked) {
    modal(`<img class="logo" src="/static/n8schicht-icon.svg" alt="">
        <h2 style="text-align:center">${esc((S.info && S.info.title) || 'N8 Hotspot')}</h2>
        <p class="dim" style="text-align:center;margin:0 0 12px">${locked ? 'This hotspot is private. Please log in.' : 'Log in to change settings.'}</p>
        <form onsubmit="event.preventDefault(); doLogin(this)">
            <div class="row"><label>Username</label><input type="text" name="username" autocomplete="username" required autofocus></div>
            <div class="row"><label>Password</label><input type="password" name="password" autocomplete="current-password" required></div>
            <label style="display:flex;gap:8px;align-items:center;margin-top:6px" class="dim"><input type="checkbox" name="remember"> Stay logged in (30 days)</label>
            <div class="err" id="loginErr"></div>
            <div class="actions">${locked ? '' : '<button type="button" class="btn" onclick="closeModal()">Cancel</button>'}<button class="btn primary">Log in</button></div>
        </form>`, locked);
    if (locked) $('ov').dataset.locked = '1';
    setTimeout(() => document.querySelector('#ov input[name=username]')?.focus(), 50);
}
async function doLogin(f) {
    try {
        const r = await api('POST', '/api/auth/login', { username: f.username.value, password: f.password.value, remember: f.remember.checked });
        S.me = r.user; closeModal();
        if (S.ws) { try { S.ws.close(); } catch (e) {} }
        await boot();
        if (r.default_login) openAccount(true);
    } catch (e) { $('loginErr').textContent = e.message; }
}
async function logout() { await api('POST', '/api/auth/logout', {}); location.hash = ''; location.reload(); }
function openAccount(force) {
    modal(`<h2>🔑 My account</h2>
        ${force ? '<p class="dim" style="margin:4px 0 10px">You are using the factory login. Choose your own username and password – the factory login stops working then.</p>' : ''}
        <form onsubmit="event.preventDefault(); saveAccount(this)">
            <div class="row"><label>Username</label><input type="text" name="username" value="${esc(S.me.username)}" autocomplete="username"></div>
            <div class="row"><label>Current password</label><input type="password" name="old" required autocomplete="current-password"></div>
            <div class="row"><label>New password (min. 8)</label><input type="password" name="new" required minlength="8" autocomplete="new-password"></div>
            <div class="row"><label>Repeat</label><input type="password" name="rep" required minlength="8" autocomplete="new-password"></div>
            <div class="err" id="accErr"></div>
            <div class="actions"><button type="button" class="btn" onclick="closeModal()">Later</button><button class="btn primary">Save</button></div>
        </form>`);
}
async function saveAccount(f) {
    if (f.new.value !== f.rep.value) { $('accErr').textContent = 'The new passwords differ.'; return; }
    try {
        const r = await api('POST', '/api/auth/password', { old: f.old.value, new: f.new.value, username: f.username.value.trim() });
        closeModal(); toast('Saved. Please log in again.');
        setTimeout(() => location.reload(), 1200);
    } catch (e) { $('accErr').textContent = e.message; }
}
function confirmBox(text, okLabel, cls) {
    return new Promise(res => {
        modal(`<h2>${esc(text.title)}</h2><p class="dim">${text.body}</p>
            <div class="actions"><button class="btn" id="cNo">Cancel</button><button class="btn ${cls || 'primary'}" id="cYes">${esc(okLabel)}</button></div>`);
        $('cNo').onclick = () => { closeModal(); res(false); };
        $('cYes').onclick = () => { closeModal(); res(true); };
    });
}

// ---------------------------------------------------------------- station view
async function openStation(id) {
    if (!id) return;
    modal('<div class="empty">Loading …</div>');
    $('ov').querySelector('.modal').classList.add('wide');
    let d;
    try { d = await api('GET', `/api/station/${id}`); } catch (e) { $('ov').querySelector('.modal').innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
    const p = d.profile || {}, h = d.heard;
    const place = [p.city, p.state, p.country].filter(Boolean).join(', ');
    const big = `<span class="avatar xl" style="background:${avatarColor(id)}">${initials(d.callsign)}${d.avatar ? `<img src="${d.avatar}" alt="" onerror="this.remove()">` : ''}</span>`;
    const recent = d.recent.map(r => `<tr><td>${fmtDate(r.ts)}</td><td><span class="pill ${r.source === 'rf' ? 'rf' : 'net'}">${r.source === 'rf' ? '📻 RF' : '🌐 Net'}</span></td>
        <td>${r.group ? 'TG ' + esc(r.dst_id) + (tgName(r.dst_id) ? ` <span class="dim">${esc(tgName(r.dst_id))}</span>` : '') : '👤 ' + esc(r.dst_id)}</td><td class="num">${r.duration.toFixed(1)} s</td>
        <td class="num hide-sm">${r.source === 'rf' && r.ber != null ? r.ber.toFixed(1) + ' %' : r.loss != null ? r.loss.toFixed(0) + ' % loss' : '–'}</td></tr>`).join('');
    $('ov').querySelector('.modal').innerHTML = `
        <div class="st-head">${big}<div style="min-width:0">
            <div class="st-call">${esc(d.callsign || id)} ${fridBadge(d.frid)}</div>
            <div class="dim">${esc(p.name || '')}${p.name && place ? ' · ' : ''}${esc(place)}</div>
            <div class="dim mono" style="font-size:12.5px;margin-top:2px">DMR ID ${esc(id)}</div></div>
            <button class="btn small" style="margin-left:auto;align-self:flex-start" onclick="closeModal()">✕</button></div>
        ${d.frid ? `<div class="banner" style="margin:12px 0 0;background:linear-gradient(135deg,rgba(48,209,88,.2),rgba(48,209,88,.05));border:1px solid rgba(48,209,88,.4)">
            <span>🛡️ <b>Registered at FreeRadioID.net</b>${p.remarks ? ' · ' + esc(p.remarks) : ''}</span>
            <a class="btn small" target="_blank" rel="noopener" href="https://freeradioid.net/api/dmr/user/?id=${encodeURIComponent(id)}">freeradioid.net ↗</a></div>` : ''}
        <div class="kpis" style="margin:14px 0 10px">
            <div class="kpi"><div class="k">📞 Calls (30 d)</div><div class="v">${h.calls}</div></div>
            <div class="kpi"><div class="k">⏱️ Airtime</div><div class="v">${fmtDur(h.duration, true)}</div></div>
            <div class="kpi"><div class="k">📻 Via RF</div><div class="v">${h.rf_calls}</div></div>
            <div class="kpi"><div class="k">🕑 Last heard</div><div class="v" style="font-size:15px">${h.last ? ago(h.last) : '–'}</div></div></div>
        ${d.talkgroups.length ? `<div class="dim" style="font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin:6px 0">Talkgroups</div>
            <div style="display:flex;flex-wrap:wrap;gap:6px">${d.talkgroups.map(t => `<span class="pill tg">TG ${t.tg}${t.name ? ` <span class="dim" style="font-weight:500">${esc(t.name)}</span>` : ''} · ${fmtDur(t.duration, true)}</span>`).join('')}</div>` : ''}
        ${recent ? `<div class="tbl-wrap" style="margin-top:12px"><table class="tbl"><thead><tr><th>Time</th><th>Source</th><th>Target</th><th class="num">Duration</th><th class="num hide-sm">BER / Loss</th></tr></thead><tbody>${recent}</tbody></table></div>`
                 : '<div class="empty">Not heard on this hotspot yet.</div>'}`;
}

// ---------------------------------------------------------------- tabs
function showTab(tab, sub) {
    S.tab = tab;
    document.querySelectorAll('#mainTabs button').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    ['live', 'stats', 'tgs', 'admin'].forEach(t => $('tab-' + t).classList.toggle('hidden', t !== tab));
    if (tab === 'stats') loadStats();
    if (tab === 'tgs') loadTalkgroups();
    if (tab === 'admin') showAdmin(sub || S.admin.tab);
    history.replaceState(null, '', tab === 'live' ? location.pathname : '#' + tab + (tab === 'admin' ? '/' + (sub || S.admin.tab) : ''));
    hideTip();
}
$('mainTabs').addEventListener('click', e => { const b = e.target.closest('button[data-tab]'); if (b) showTab(b.dataset.tab); });

// ---------------------------------------------------------------- websocket
function connectWS() {
    const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
    S.ws = ws;
    ws.onopen = () => { S.wsOk = true; renderChips(); };
    ws.onclose = () => { S.wsOk = false; renderChips(); setTimeout(() => { if (S.ws === ws) connectWS(); }, 3000); };
    ws.onmessage = m => { try { onEvent(JSON.parse(m.data)); } catch (e) { console.error(e); } };
}
let todayTimer = null;
function onEvent(ev) {
    switch (ev.type) {
        case 'hello': case 'status': S.live = ev.status; renderChips(); renderSlots(); renderInfo(); if (ev.type === 'hello') renderLH(); break;
        case 'slot': if (S.live) { S.live.slots[String(ev.slot)] = ev.call; renderSlots(); } break;
        case 'heard':
            if (S.live) { S.live.last_heard.unshift(ev.entry); S.live.last_heard.length = Math.min(S.live.last_heard.length, 40); renderLH(ev.entry.id); }
            clearTimeout(todayTimer); todayTimer = setTimeout(() => { loadToday(); if (S.tab === 'stats') loadStats(); }, 1500);
            break;
        case 'info': S.info = { ...S.info, ...ev.info }; renderHeader(); renderInfo(); break;
        case 'ui': S.info = { ...S.info, theme: ev.theme, links: ev.links, build: ev.build };
            if (!(S.tab === 'admin' && S.admin.tab === 'appearance')) applyUI(S.info); else { renderLinks(ev.links); renderFooter(ev.build); } break;
        case 'update': checkUpdateQuiet(); break;
        case 'log': S.admin.logs.push(ev.entry); if (S.admin.logs.length > 600) S.admin.logs.shift(); appendLog(ev.entry); break;
        case 'cal': S.admin.cal = ev.cal; renderCalState(); break;
        case 'cal_line': appendCalLine(ev.line); break;
    }
}

// ---------------------------------------------------------------- live
function renderChips() {
    const L = S.live || {};
    const set = (id, cls, text) => { const e = $(id); e.className = 'chip ' + cls + (id === 'chipLive' || id === 'chipModem' ? ' st' : ''); e.textContent = text; e.title = text; };
    set('chipLive', S.wsOk ? 'ok' : 'bad', S.wsOk ? '✓ Live data' : '✕ Live data');
    const svc = L.services || {};
    if (svc.mmdvmhost && svc.mmdvmhost !== 'active') set('chipModem', 'bad', '✕ MMDVMHost stopped');
    else if (L.modem && L.modem.open === true) set('chipModem', 'ok', '✓ Modem');
    else if (L.modem && L.modem.open === false) set('chipModem', 'bad', '✕ Modem');
    else set('chipModem', 'warn', '… Modem');
    const ln = L.link || {};
    const net = S.info && S.info.network;
    if (!net) set('chipNet', '', '🛰️ No network');
    else if (svc.dmrgateway && svc.dmrgateway !== 'active') set('chipNet', 'bad', `✕ ${net} (gateway stopped)`);
    else if (ln.state === 'connected') set('chipNet', 'ok', `✓ ${net}`);
    else if (ln.state === 'failed') set('chipNet', 'bad', `✕ ${net}${ln.reason === 'auth' ? ': password wrong' : ln.reason ? ': ' + ln.reason : ''}`);
    else set('chipNet', 'warn', `… ${net}`);
    const mode = svc.mmdvmhost && svc.mmdvmhost !== 'active' ? 'Stopped' : (L.mode || 'Idle');
    set('chipMode', mode === 'Idle' ? '' : ['Lockout', 'Error', 'Stopped'].includes(mode) ? 'bad' : 'info', mode === 'Idle' ? '💤 Idle' : mode === 'Stopped' ? '⏸ Stopped' : `📡 ${mode}`);
}
function renderInfo() {
    const i = S.info; if (!i) return;
    const L = S.live || {};
    const ln = L.link || {};
    const linkTxt = !i.network ? 'off' : ln.state === 'connected' ? `<span class="pill ok">connected</span>` :
        ln.state === 'failed' ? `<span class="pill bad">failed${ln.reason ? ' · ' + esc(ln.reason) : ''}</span>` : `<span class="pill warn">connecting</span>`;
    const rows = [
        ['Callsign', `${esc(i.callsign)}`], ['Hotspot ID', esc(i.hotspot_id)],
        ['Frequency', i.duplex ? `RX ${fmtFreq(i.rx_freq)}<br>TX ${fmtFreq(i.tx_freq)}` : fmtFreq(i.rx_freq)],
        ['Mode', `${i.duplex ? 'Duplex' : 'Simplex'} · CC${esc(i.color_code)}`],
        ['Modem', esc(((L.modem && L.modem.description) || i.modem || '').split(' ')[0] || '–')],
        ['DMR server', i.network ? `${esc(i.network)}<br><span class="dim mono" style="font-size:12px">${esc(i.network_host)}</span>` : 'off'],
        ['Connection', linkTxt],
    ];
    if (i.location) rows.splice(2, 0, ['Location', esc(i.location)]);
    $('hsInfo').innerHTML = rows.map(([k, v]) => `<div class="k">${k}</div><div class="v" style="white-space:normal">${v}</div>`).join('');
}
function renderSlots() {
    const i = S.info || {}, L = S.live || { slots: {} };
    const slots = i.duplex ? [1, 2] : [2];
    $('slots').innerHTML = slots.map(n => {
        const c = L.slots && L.slots[String(n)];
        if (!c) {
            const last = (L.last_heard || []).find(e => e.slot === n);
            return `<div class="slot idle"><div class="lbl"><span>Time slot ${n}</span><span class="pill">Idle</span></div>
                <div class="idle-text">${last ? `Last: <b style="color:var(--text)">${esc(last.callsign || last.src_id)}</b> → ${last.group ? 'TG ' : ''}${esc(last.dst_id)} · ${ago(last.ts + last.duration)}` : 'Nothing heard yet'}</div></div>`;
        }
        const src = c.source === 'rf' ? 'rf' : 'network';
        const ber = c.ber_live != null ? `<span class="pill">BER ${Number(c.ber_live).toFixed(1)} %</span>` : '';
        const rssi = c.rssi_live != null ? `<span class="pill">${c.rssi_live} dBm</span>` : '';
        return `<div class="slot active ${src}"><div class="lbl"><span>Time slot ${n}</span><span class="pill air">ON AIR</span></div>
            <div class="who station-link" onclick="openStation(${c.src_id})">${avatar(c.src_id, c.callsign, c.frid)}
              <div style="min-width:0"><div class="call">${esc(c.callsign || c.src_id)} ${fridBadge(c.frid)}</div>
              <div class="name">${esc([c.name, c.city].filter(Boolean).join(' · ') || ('ID ' + c.src_id))}</div></div>
              <div class="timer" data-start="${c.start}">${fmtClock(Date.now() / 1000 - c.start)}</div></div>
            <div class="meta"><span class="pill ${src === 'rf' ? 'rf' : 'net'}">${src === 'rf' ? '📻 RF' : '🌐 Network'}</span>${target(c)}${c.is_data ? '<span class="pill">📟 Data</span>' : ''}${ber}${rssi}</div></div>`;
    }).join('');
}
setInterval(() => document.querySelectorAll('.timer[data-start]').forEach(t => t.textContent = fmtClock(Date.now() / 1000 - Number(t.dataset.start))), 1000);

function renderLH(newId) {
    const L = S.live; if (!L) return;
    let rows = L.last_heard || [];
    if (S.lhFilter !== 'all') rows = rows.filter(e => e.source === S.lhFilter);
    rows = rows.slice(0, 20);
    if (!rows.length) { $('lhBody').innerHTML = '<tr><td colspan="8" class="empty">Nothing heard yet.</td></tr>'; return; }
    $('lhBody').innerHTML = rows.map(e => {
        const q = e.source === 'rf' ? (e.ber != null ? `${Number(e.ber).toFixed(1)} %` : '–') : (e.loss != null ? `${Number(e.loss).toFixed(0)} % loss` : '–');
        const berCls = e.source === 'rf' && e.ber != null ? (e.ber < 1 ? 'ok' : e.ber < 3 ? 'warn' : 'bad') : '';
        return `<tr class="${e.id === newId ? 'new' : ''}"><td>${fmtTime(e.ts)}</td>
            <td><span class="who station-link" onclick="openStation(${e.src_id})">${avatar(e.src_id, e.callsign, e.frid, 'sm')}<span><b>${esc(e.callsign || e.src_id)}</b> ${fridBadge(e.frid)}<small>${esc(e.name || ('ID ' + (e.src_id || '?')))}</small></span></span></td>
            <td><span class="pill ${e.source === 'rf' ? 'rf' : 'net'}">${e.source === 'rf' ? '📻 RF' : '🌐 Net'}</span></td>
            <td class="hide-sm">TS${e.slot}</td><td>${target(e)}${e.is_data ? ' <span class="pill">📟</span>' : ''}</td>
            <td class="num">${e.duration.toFixed(1)} s</td><td class="num hide-sm">${berCls ? `<span class="pill ${berCls}">${q}</span>` : q}</td>
            <td class="num hide-sm">${e.rssi != null ? e.rssi + ' dBm' : '–'}</td></tr>`;
    }).join('');
}
$('lhFilter').addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    S.lhFilter = b.dataset.v; document.querySelectorAll('#lhFilter button').forEach(x => x.classList.toggle('active', x === b)); renderLH();
});
async function loadToday() {
    try {
        const d = await api('GET', '/api/stats?range=today');
        const T = d.totals;
        $('sCalls').textContent = T.calls.toLocaleString('de-DE');
        $('sAir').textContent = fmtDur(T.duration, true);
        $('sRf').innerHTML = `${T.rf_calls}<small>${fmtDur(T.rf_duration, true)}</small>`;
        $('sNet').innerHTML = `${T.net_calls}<small>${fmtDur(T.net_duration, true)}</small>`;
        $('sBer').textContent = T.rf_ber != null ? T.rf_ber.toFixed(2) + ' %' : '–';
    } catch (e) {}
}

// ---------------------------------------------------------------- statistics (same charts as the N8schicht dashboard)
const COLORS = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181'];   // validated for the dark surface
const OTHER = '#6b7385';
const SRC_COLORS = { rf: '#d95926', net: '#3987e5' };
function tgColor(tg) { const st = S.stats.slots; return tg != null && st[tg] != null ? COLORS[st[tg]] : OTHER; }
function assignColors(series) {
    const keep = {}, used = new Set(), old = S.stats.slots;
    series.forEach(s => { if (s.tg != null && old[s.tg] != null && !used.has(old[s.tg])) { keep[s.tg] = old[s.tg]; used.add(keep[s.tg]); } });
    series.forEach(s => { if (s.tg == null || keep[s.tg] != null) return; const f = COLORS.findIndex((_, i) => !used.has(i)); keep[s.tg] = f; used.add(f); });
    S.stats.slots = keep;
}
async function loadStats() {
    try { S.stats.data = await api('GET', `/api/stats?range=${S.stats.range}`); renderStats(); } catch (e) { console.warn(e); }
}
function bindSeg(id, fn) {
    $(id).addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; document.querySelectorAll(`#${id} button`).forEach(x => x.classList.toggle('active', x === b)); fn(b.dataset.v); });
}
bindSeg('stRange', v => { S.stats.range = v; loadStats(); });
bindSeg('stMetric', v => { S.stats.metric = v; renderStats(); });
bindSeg('stBy', v => { S.stats.by = v; renderStats(); });
function sFmt(v) { return S.stats.metric === 'calls' ? Math.round(v).toLocaleString('de-DE') : fmtDur(v, true); }
function renderStats() {
    const d = S.stats.data; if (!d) return;
    assignColors(d.series || []);
    const T = d.totals;
    $('kCalls').textContent = T.calls.toLocaleString('de-DE');
    $('kAir').textContent = fmtDur(T.duration, true);
    $('kRf').textContent = T.duration ? Math.round(T.rf_duration / T.duration * 100) + ' %' : '–';
    $('kSt').textContent = T.stations;
    renderBars(d); renderTime(d); renderStatTables(d);
}
function empty(el) { el.innerHTML = '<div class="empty">No calls in this period yet.</div>'; }
function renderBars(d) {
    const el = $('stBars'), m = S.stats.metric;
    const rows = [...(d.talkgroups || [])].sort((a, b) => b[m] - a[m] || b.duration - a.duration).slice(0, 10);
    $('stTopNote').textContent = m === 'calls' ? 'by calls' : 'by airtime';
    if (!rows.length) return empty(el);
    const W = Math.max(280, el.clientWidth || 420), rowH = 30, barH = 14, labelW = Math.min(150, Math.max(92, W * 0.32)), valW = 64;
    const max = Math.max(...rows.map(r => r[m])) || 1, plotW = W - labelW - valW;
    let svg = `<svg viewBox="0 0 ${W} ${rows.length * rowH}" role="img" aria-label="Top talkgroups">`;
    rows.forEach((r, i) => {
        const y = i * rowH + (rowH - barH) / 2, w = Math.max(3, (r[m] / max) * plotW), rr = Math.min(4, w / 2);
        const room = Math.floor((labelW - 16 - String(r.tg).length * 8.4) / 7.2);
        const name = r.name && room >= 3 ? esc(r.name.length > room ? r.name.slice(0, room - 1) + '…' : r.name) : '';
        svg += `<g class="hit" data-i="${i}"><rect x="0" y="${i * rowH}" width="${W}" height="${rowH}" fill="transparent"/>
            <text x="0" y="${i * rowH + rowH / 2 + 1}" dominant-baseline="middle" font-size="12.5" font-weight="700" fill="#f5f7fb">${r.tg}${name ? `<tspan font-weight="500" fill="rgba(235,240,250,0.62)" dx="6">${name}</tspan>` : ''}</text>
            <path d="M${labelW},${y} h${w - rr} a${rr},${rr} 0 0 1 ${rr},${rr} v${barH - 2 * rr} a${rr},${rr} 0 0 1 -${rr},${rr} h-${w - rr} z" fill="${tgColor(r.tg)}"/>
            <text x="${labelW + w + 8}" y="${i * rowH + rowH / 2 + 1}" dominant-baseline="middle" font-size="12" fill="rgba(235,240,250,0.8)">${sFmt(r[m])}</text></g>`;
    });
    el.innerHTML = svg + '</svg>';
    el.querySelectorAll('.hit').forEach(g => {
        const r = rows[+g.dataset.i];
        g.addEventListener('mousemove', ev => tip(ev, `<b>TG ${r.tg}${r.name ? ' · ' + esc(r.name) : ''}</b>` + tipRow(null, 'Airtime', fmtDur(r.duration)) +
            tipRow(null, 'Calls', r.calls) + tipRow(null, 'Stations', r.users) + tipRow(null, 'Share', Math.round(r.share * 100) + ' %')));
        g.addEventListener('mouseleave', hideTip);
    });
}
function bucketLabel(d, i, long) {
    const t = new Date(d.buckets[i] * 1000);
    if (d.bucket === 'hour') { const h = String(t.getHours()).padStart(2, '0'); return long ? `${t.toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit' })} ${h}:00–${String((t.getHours() + 1) % 24).padStart(2, '0')}:00` : h; }
    return long ? t.toLocaleDateString('de-DE', { weekday: 'long', day: '2-digit', month: '2-digit' }) : t.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' }).replace(/\.$/, '');
}
function niceMax(v) {
    if (S.stats.metric === 'duration') { for (const s of [60, 120, 300, 600, 900, 1200, 1800, 3600, 7200, 10800, 18000, 36000, 72000]) if (s * 4 >= v) return s * 4; return Math.ceil(v / 4 / 3600) * 3600 * 4; }
    const p = Math.pow(10, Math.floor(Math.log10(Math.max(1, v / 4))));
    for (const k of [1, 2, 2.5, 5, 10]) if (k * p * 4 >= v) return Math.max(4, k * p * 4);
    return v;
}
function renderTime(d) {
    const el = $('stTime'), lg = $('stLegend'), m = S.stats.metric, n = d.buckets.length;
    const bySrc = S.stats.by === 'src';
    const series = bySrc ? d.sources : d.series;
    const color = s => bySrc ? SRC_COLORS[s.tg] : tgColor(s.tg);
    const label = s => bySrc ? s.name : (s.tg == null ? s.name : `TG ${s.tg}${s.name ? ' ' + s.name : ''}`);
    if (!series.length || !d.totals.calls) { lg.innerHTML = ''; return empty(el); }
    lg.innerHTML = series.map(s => `<span><i style="background:${color(s)}"></i>${esc(label(s))}</span>`).join('');
    const totals = Array.from({ length: n }, (_, i) => series.reduce((a, s) => a + (s[m][i] || 0), 0));
    const yMax = niceMax(Math.max(...totals) || 1);
    const W = Math.max(300, el.clientWidth || 600), H = 210, L = 44, R = 6, T = 6, B = 22, pw = W - L - R, ph = H - T - B;
    const cw = pw / n, bw = Math.max(3, Math.min(26, cw * 0.68)), y = v => T + ph - (v / yMax) * ph;
    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Activity">`;
    for (let k = 0; k <= 4; k++) { const v = yMax * k / 4, yy = y(v);
        svg += `<line x1="${L}" x2="${W - R}" y1="${yy}" y2="${yy}" stroke="rgba(255,255,255,${k ? 0.07 : 0.18})"/><text x="${L - 6}" y="${yy}" text-anchor="end" dominant-baseline="middle" font-size="10.5" fill="rgba(235,240,250,0.55)">${k ? sFmt(v) : '0'}</text>`; }
    const every = n <= 8 ? 1 : n <= 24 ? 3 : 5;
    for (let i = 0; i < n; i++) {
        const cx = L + cw * i + cw / 2;
        if (i % every === 0 || (n > 24 && i === n - 1)) svg += `<text x="${cx}" y="${H - 6}" text-anchor="middle" font-size="10.5" fill="rgba(235,240,250,0.55)">${bucketLabel(d, i)}</text>`;
        let acc = 0;
        const segs = series.map(s => ({ s, v: s[m][i] || 0 })).filter(x => x.v > 0);
        segs.forEach((x, j) => {
            const y1 = y(acc); acc += x.v; const top = j === segs.length - 1;
            let h = y1 - y(acc) - (top ? 0 : 2); if (h < 1) h = 1;
            const xx = cx - bw / 2, r = top ? Math.min(4, bw / 2, h) : 0;
            svg += `<path class="col c${i}" d="M${xx},${y1} v-${h - r} a${r},${r} 0 0 1 ${r},-${r} h${bw - 2 * r} a${r},${r} 0 0 1 ${r},${r} v${h - r} z" fill="${color(x.s)}"/>`;
        });
        svg += `<rect class="hc" data-i="${i}" x="${L + cw * i}" y="${T}" width="${cw}" height="${ph}" fill="transparent"/>`;
    }
    el.innerHTML = svg + '</svg>';
    const cols = el.querySelectorAll('.col');
    el.querySelectorAll('.hc').forEach(h => {
        const i = +h.dataset.i;
        h.addEventListener('mousemove', ev => {
            cols.forEach(c => c.style.opacity = c.classList.contains('c' + i) ? '1' : '0.35');
            let html = `<b>${bucketLabel(d, i, true)}</b>`;
            series.forEach(s => { if (s[m][i]) html += tipRow(color(s), label(s), sFmt(s[m][i])); });
            html += totals[i] ? tipRow(null, 'Total', sFmt(totals[i])) : '<div class="r"><span>no calls</span></div>';
            tip(ev, html);
        });
        h.addEventListener('mouseleave', () => { cols.forEach(c => c.style.opacity = ''); hideTip(); });
    });
}
function renderStatTables(d) {
    const rows = d.talkgroups.slice(0, 12), maxS = Math.max(...d.talkgroups.map(r => r.share), 0) || 1;
    $('stTgTable').innerHTML = rows.length ? rows.map(r => `<tr><td><b>${r.tg}</b> <span class="dim">${esc(r.name)}</span></td><td class="num">${r.calls}</td><td class="num">${fmtDur(r.duration, true)}</td>
        <td class="hide-sm"><span class="share"><span class="bar"><div style="width:${r.share / maxS * 100}%;background:${tgColor(r.tg)}"></div></span>${Math.round(r.share * 100)} %</span></td></tr>`).join('')
        : '<tr><td colspan="4" class="empty">–</td></tr>';
    $('stStTable').innerHTML = d.stations.length ? d.stations.map(s => `<tr><td><span class="who station-link" onclick="openStation(${s.id})">${avatar(s.id, s.callsign, s.frid, 'sm')}<span><b>${esc(s.callsign || s.id)}</b> ${fridBadge(s.frid)}<small>${esc(s.name || s.id)}</small></span></span></td>
        <td class="num">${s.calls}</td><td class="num">${fmtDur(s.duration, true)}</td><td class="hide-sm">${fmtDate(s.last)}</td></tr>`).join('')
        : '<tr><td colspan="4" class="empty">–</td></tr>';
}
function tipRow(c, l, v) { return `<div class="r"><span>${c ? `<i style="background:${c}"></i>` : ''}${esc(String(l))}</span><span>${v}</span></div>`; }
function tip(ev, html) {
    const t = $('tip'); t.innerHTML = html; t.style.display = 'block';
    let x = ev.clientX + 14, y = ev.clientY + 14;
    if (x + t.offsetWidth > innerWidth - 8) x = ev.clientX - t.offsetWidth - 14;
    if (y + t.offsetHeight > innerHeight - 8) y = ev.clientY - t.offsetHeight - 14;
    t.style.left = Math.max(8, x) + 'px'; t.style.top = Math.max(8, y) + 'px';
}
function hideTip() { $('tip').style.display = 'none'; }
let rsT = null; addEventListener('resize', () => { clearTimeout(rsT); rsT = setTimeout(() => { if (S.tab === 'stats') renderStats(); }, 150); });

// ---------------------------------------------------------------- talkgroup directory
const TGV = { data: null, filter: 'all', limit: 150 };
async function loadTalkgroups() {
    try { TGV.data = await api('GET', '/api/talkgroups'); } catch (e) { toast(e.message, true); return; }
    S.info.tg_names = TGV.data.names;
    renderTalkgroups();
}
function renderTalkgroups() {
    const d = TGV.data; if (!d) return;
    const q = $('tgSearch').value.trim().toLowerCase();
    const own = new Set(d.own);
    const all = new Set([...Object.keys(d.names), ...Object.keys(d.activity)]);
    let rows = [...all].map(tg => ({ tg, name: d.names[tg] || '', a: d.activity[tg], own: own.has(tg) }));
    if (TGV.filter === 'heard') rows = rows.filter(r => r.a);
    if (TGV.filter === 'own') rows = rows.filter(r => r.own);
    if (q) rows = rows.filter(r => r.tg.startsWith(q) || r.name.toLowerCase().includes(q));
    rows.sort((x, y) => TGV.filter === 'heard' ? (y.a.duration - x.a.duration) : (Number(x.tg) - Number(y.tg)));
    $('tgCount').textContent = rows.length.toLocaleString('de-DE');
    const shown = rows.slice(0, TGV.limit);
    $('tgBody').innerHTML = shown.length ? shown.map(r => `<tr><td><b class="mono">${esc(r.tg)}</b></td>
        <td style="white-space:normal">${esc(r.name) || '<span class="dim">–</span>'} ${r.own ? '<span class="pill" style="font-size:10.5px;padding:1px 7px">own</span>' : ''}</td>
        <td class="num">${r.a ? r.a.calls : '<span class="dim">–</span>'}</td><td class="num hide-sm">${r.a ? fmtDur(r.a.duration, true) : ''}</td>
        <td class="hide-sm">${r.a ? ago(r.a.last) : ''}</td></tr>`).join('') : '<tr><td colspan="5" class="empty">No talkgroup found.</td></tr>';
    $('tgMore').classList.toggle('hidden', rows.length <= TGV.limit);
    $('tgMore').textContent = `Show all ${rows.length.toLocaleString('de-DE')}`;
    $('tgSource').innerHTML = d.list.enabled ? `List of the N8schicht: ${d.list.count.toLocaleString('de-DE')} names${d.list.updated ? ', updated ' + fmtDate(d.list.updated) : ''} · <a href="https://github.com/dhartmann1979/n8schicht/blob/main/talkgroup_ids.json" target="_blank" rel="noopener">talkgroup_ids.json</a>` : 'Talkgroup list switched off (Admin → Settings → Dashboard)';
}
let tgT = null;
$('tgSearch').addEventListener('input', () => { clearTimeout(tgT); tgT = setTimeout(() => { TGV.limit = 150; renderTalkgroups(); }, 120); });
$('tgMore').addEventListener('click', () => { TGV.limit = 100000; renderTalkgroups(); });
bindSeg('tgFilter', v => { TGV.filter = v; TGV.limit = 150; renderTalkgroups(); });

// ---------------------------------------------------------------- admin
function showAdmin(a) {
    S.admin.tab = a;
    document.querySelectorAll('#adminTabs button').forEach(b => b.classList.toggle('active', b.dataset.a === a));
    const ab = document.querySelector(`#adminTabs button[data-a="${a}"]`);
    if (ab && ab.scrollIntoView) ab.scrollIntoView({ block: 'nearest', inline: 'center' });
    ['settings', 'cal', 'users', 'appearance', 'links', 'system', 'updates', 'logs', 'files', 'audit'].forEach(x => $('admin-' + x).classList.toggle('hidden', x !== a));
    ({ settings: loadSettings, cal: loadCal, users: loadUsers, appearance: loadAppearance, links: loadLinksAdmin,
       updates: () => loadUpdates(false), system: loadSystem, logs: loadLogs, files: loadFiles, audit: loadAudit })[a]();
    if (S.tab === 'admin') history.replaceState(null, '', '#admin/' + a);
}
$('adminTabs').addEventListener('click', e => { const b = e.target.closest('button[data-a]'); if (b) showAdmin(b.dataset.a); });
function setRestart(on) { $('restartBanner').classList.toggle('hidden', !on); }
async function applyRestart(btn) {
    btn.disabled = true; btn.textContent = 'Restarting …';
    try { await api('POST', '/api/admin/apply', {}); setRestart(false); toast('MMDVMHost and DMRGateway restarted'); }
    catch (e) { toast(e.message, true); }
    btn.disabled = false; btn.textContent = 'Restart now';
}

// settings
async function loadSettings() {
    const d = await api('GET', '/api/admin/settings');
    S.admin.settings = d; setRestart(d.restart_needed);
    $('admin-settings').innerHTML = `<div class="tiles">${d.sections.map(sec => `
        <form class="tile" data-sec="${sec.id}" onsubmit="event.preventDefault(); saveSection(this)">
            <h3>${esc(sec.title)}</h3><div class="subt">${esc(sec.subtitle)}</div>
            ${sec.fields.map(fieldHtml).join('')}
            <div class="actions"><button class="btn primary">Save</button></div>
        </form>`).join('')}</div>`;
    const portIn = document.querySelector('[name="modem.port"]');
    if (portIn) {
        const w = document.createElement('div'); w.className = 'pw-wrap';
        portIn.replaceWith(w); w.appendChild(portIn);
        w.insertAdjacentHTML('beforeend', '<button type="button" class="btn small" title="Find the modem" onclick="openSerialScan()">🔍 Find</button>');
    }
    const preset = document.querySelector('[name="modem.preset"]');
    if (preset) preset.addEventListener('change', () => {
        const p = d.modem_presets[preset.value]; if (!p || !p.port) return;
        document.querySelector('[name="modem.port"]').value = p.port;
        document.querySelector('[name="modem.speed"]').value = String(p.speed);
        document.querySelector('[name="modem.duplex"]').checked = p.duplex;
    });
    const mp = document.querySelector('[name="network.preset"]');
    if (mp) mp.addEventListener('change', () => {
        const p = d.master_presets[mp.value]; if (!p || !p.host) return;
        document.querySelector('[name="network.host"]').value = p.host;
        document.querySelector('[name="network.port"]').value = p.port;
        document.querySelector('[name="network.name"]').value = p.label.replace('DMR Die ', '');
    });
}
function fieldHtml(f) {
    const tag = f.restart ? '' : '';
    const lbl = `<label for="f_${f.key}">${esc(f.label)}${tag}</label>`;
    const help = f.help ? `<div class="help">${esc(f.help)}</div>` : '';
    let input;
    if (f.kind === 'bool') input = `<label class="switch"><input type="checkbox" id="f_${f.key}" name="${f.key}" ${f.value ? 'checked' : ''}><span></span></label>`;
    else if (f.kind === 'choice') input = `<select id="f_${f.key}" name="${f.key}">${f.choices.map(c => `<option value="${esc(c[0])}" ${String(c[0]) === String(f.value) ? 'selected' : ''}>${esc(c[1])}</option>`).join('')}</select>`;
    else if (f.kind === 'longtext') return `<div class="row wide">${lbl}<textarea id="f_${f.key}" name="${f.key}" spellcheck="false">${esc(f.value)}</textarea>${help}</div>`;
    else if (f.kind === 'password') input = `<div class="pw-wrap"><input type="password" id="f_${f.key}" name="${f.key}" value="${esc(f.value)}" autocomplete="new-password"><button type="button" class="btn small" onclick="const i=this.previousElementSibling;i.type=i.type==='password'?'text':'password';if(i.value==='••••••••')i.value=''">👁</button></div>`;
    else if (f.kind === 'freq') input = `<input type="text" inputmode="decimal" id="f_${f.key}" name="${f.key}" value="${(f.value / 1e6).toFixed(4)}">`;
    else if (f.kind === 'time') input = `<input type="time" id="f_${f.key}" name="${f.key}" value="${esc(f.value)}">`;
    else if (f.kind === 'int' || f.kind === 'float') input = `<input type="number" id="f_${f.key}" name="${f.key}" value="${esc(f.value)}" ${f.kind === 'float' ? 'step="any"' : ''} ${f.min != null ? `min="${f.min}"` : ''} ${f.max != null ? `max="${f.max}"` : ''}>`;
    else input = `<input type="text" id="f_${f.key}" name="${f.key}" value="${esc(f.value)}">`;
    return `<div class="row">${lbl}${input}${help}</div>`;
}
async function saveSection(form) {
    const changes = {};
    form.querySelectorAll('[name]').forEach(i => { changes[i.name] = i.type === 'checkbox' ? i.checked : i.value; });
    try {
        const r = await api('POST', '/api/admin/settings', { changes });
        toast(r.changed.length ? `Saved (${r.changed.length})` : 'No changes');
        setRestart(r.restart_needed);
        const info = await api('GET', '/api/info'); S.info = { ...S.info, ...info }; renderHeader(); renderInfo(); renderSlots();
    } catch (e) { toast(e.message, true); }
}

// find the modem (serial port scan)
const PORT_INFO = [
    ['/dev/ttyAMA0', 'Hat on the GPIO header (MMDVM_HS_Hat, Dual Hat, …). Needs the UART switched on and Bluetooth off – the installer does that.'],
    ['/dev/serial0', 'Alias of the GPIO UART; points to ttyAMA0 (or ttyS0 while Bluetooth is on).'],
    ['/dev/ttyS0', 'Mini UART of the Pi. A hat only lands here while Bluetooth is on – unreliable, re-run the installer.'],
    ['/dev/ttyACM0', 'USB with native USB serial: ZUMspot, MMDVM_HS via USB, STM32 repeater boards.'],
    ['/dev/ttyUSB0', 'Board behind a USB-serial adapter (CH340, CP210x, FTDI).'],
];
async function openSerialScan() {
    modal(`<h2>🔍 Where is the modem?</h2>
        <p class="dim" style="margin:4px 0 10px">The scan lists all serial ports and asks each free one for its MMDVM firmware. The port MMDVMHost already uses is not touched; its modem info comes from MMDVMHost.</p>
        <div class="tbl-wrap"><table class="tbl" style="font-size:12.5px"><tbody>${PORT_INFO.map(([p, t]) => `<tr><td class="mono" style="vertical-align:top"><b>${p}</b></td><td style="white-space:normal">${t}</td></tr>`).join('')}</tbody></table></div>
        <div id="scanOut" style="margin-top:14px"><div class="empty">⏳ Scanning … (up to 15 seconds)</div></div>
        <div class="actions"><button class="btn" onclick="openSerialScan()">↻ Scan again</button><button class="btn primary" onclick="closeModal()">Close</button></div>`);
    $('ov').querySelector('.modal').classList.add('wide');
    let d;
    try { d = await api('POST', '/api/admin/serial/scan', {}); } catch (e) { $('scanOut').innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
    const st = p => ({ modem: `<span class="pill ok">✓ MMDVM modem</span>`, busy: `<span class="pill ${p.modem ? 'ok' : 'warn'}">in use by ${esc(p.users.map(u => u.name).join(', '))}</span>`,
        silent: '<span class="pill">no answer</span>', alias: `<span class="pill">→ ${esc(p.alias_of)}</span>`, 'no-permission': '<span class="pill bad">no permission</span>',
        error: `<span class="pill bad">error</span>` }[p.status] || `<span class="pill">${esc(p.status)}</span>`);
    const kind = p => ({ gpio: 'GPIO UART', 'gpio-mini': 'GPIO mini UART', usb: 'USB', other: 'serial' }[p.kind] || p.kind);
    const usb = p => p.usb && (p.usb.product || p.usb.idVendor) ? `<br><span class="dim">${esc([p.usb.manufacturer, p.usb.product].filter(Boolean).join(' ') || '')} ${p.usb.idVendor ? `(${esc(p.usb.idVendor)}:${esc(p.usb.idProduct || '')}${p.usb.driver ? ', ' + esc(p.usb.driver) : ''})` : ''}</span>` : '';
    const found = d.ports.filter(p => p.modem);
    $('scanOut').innerHTML = (found.length ? `<div class="banner" style="margin:0 0 10px;background:linear-gradient(135deg,rgba(48,209,88,.2),rgba(48,209,88,.05));border:1px solid rgba(48,209,88,.4)">
            <span>✓ Modem found on <b class="mono">${esc(found[0].port)}</b>: ${esc(found[0].modem.description)}</span></div>` :
            `<div class="banner warn" style="margin:0 0 10px"><span>No modem answered. Is the board plugged in? On a GPIO hat: reboot once after the installation.</span></div>`) +
        `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Port</th><th>Type</th><th>Status</th><th class="hide-sm">Firmware</th><th></th></tr></thead><tbody>${d.ports.map(p => `
        <tr><td class="mono"><b>${esc(p.port)}</b>${p.port === d.configured ? ' <span class="pill tg" style="font-size:10.5px;padding:1px 7px">set</span>' : ''}</td>
        <td style="white-space:normal">${kind(p)}${usb(p)}</td><td>${st(p)}</td>
        <td class="hide-sm" style="white-space:normal;font-size:12px">${p.modem ? esc(p.modem.description) + (p.speed ? ` <span class="dim">@ ${p.speed}</span>` : '') : ''}</td>
        <td class="num">${p.status === 'alias' ? '' : `<button class="btn small" onclick='usePort(${JSON.stringify({ port: p.port, speed: p.speed, kind: p.kind, desc: p.modem ? p.modem.description : "" })})'>Use</button>`}</td></tr>`).join('')}
        </tbody></table></div>`;
}
function usePort(p) {
    const set = (n, v) => { const e = document.querySelector(`[name="${n}"]`); if (e) { if (e.type === 'checkbox') e.checked = v; else e.value = v; } };
    set('modem.port', p.port);
    if (p.speed) set('modem.speed', String(p.speed));
    const dual = /dual|duplex|repeater/i.test(p.desc || '');
    set('modem.preset', p.kind === 'usb' ? (dual ? 'rpt_usb' : 'hs_usb') : (dual ? 'hs_dual' : 'hs_hat'));
    set('modem.duplex', dual);
    closeModal(); toast(`${p.port} set – press Save in “Modem”`);
}

// calibration
async function loadCal() {
    const d = await api('GET', '/api/admin/cal');
    S.admin.cal = d.cal; S.admin.calCfg = d;
    $('admin-cal').innerHTML = `
    <div class="grid g2">
        <div class="tile">
            <h3>🎛️ Frequency calibration</h3><div class="subt">Finds the offset of your modem with the BER test of MMDVMCal.</div>
            <ol class="cal-steps">
                <li><span>Program a <b>simplex channel</b> in your radio on <b>${fmtFreq(d.rx_freq)}</b>, color code 1, any talkgroup.</span></li>
                <li><span>Press <b>Start</b>. MMDVMHost and DMRGateway stop while the calibration runs.</span></li>
                <li><span>Transmit with your radio for a few seconds (no need to talk). The BER on the right appears.</span></li>
                <li><span>Move the frequency with <b>◀ / ▶</b> until the BER is lowest (ideally below 1 %). Transmit again after each step.</span></li>
                <li><span>Press <b>Save offset</b>, then <b>Stop</b>. The hotspot starts again with the new offset.</span></li>
            </ol>
            <div class="kv" style="margin-top:14px"><div class="k">Port</div><div class="v mono">${esc(d.port)} @ ${esc(d.speed)}</div>
                <div class="k">Saved offsets</div><div class="v">RX ${d.rx_offset} Hz · TX ${d.tx_offset} Hz</div></div>
            <div class="actions" style="justify-content:flex-start">
                <input type="text" id="calStartFreq" value="${(d.rx_freq / 1e6).toFixed(4)}" style="max-width:150px" title="Start frequency (MHz)">
                <button class="btn good" id="calStart" onclick="calStart()">▶ Start</button>
                <button class="btn danger" id="calStop" onclick="calStop()">■ Stop</button>
            </div>
        </div>
        <div class="tile" id="calLive"></div>
    </div>
    <div class="tile" style="margin-top:14px">
        <h3>More tests</h3><div class="subt">For experienced users: deviation, RSSI and test patterns (the modem transmits!).</div>
        <div class="btnrow" style="justify-content:flex-start">
            <button class="btn small" onclick="calKey('b')">BER DMR simplex (b)</button><button class="btn small" onclick="calKey('B')">BER 1031 Hz (B)</button>
            <button class="btn small" onclick="calKey('D')">DMR deviation (D)</button><button class="btn small" onclick="calKey('M')">1031 Hz pattern (M)</button>
            <button class="btn small" onclick="calKey('S')">RSSI (S)</button><button class="btn small" onclick="calKey(' ')">TX on/off (space)</button>
            <button class="btn small" onclick="calKey('t')">Deviation −</button><button class="btn small" onclick="calKey('T')">Deviation +</button>
            <button class="btn small" onclick="calKey('p')">Power −</button><button class="btn small" onclick="calKey('P')">Power +</button>
        </div>
        <div class="term" id="calTerm"></div>
    </div>`;
    (S.admin.cal.lines || []).forEach(appendCalLine);
    renderCalState();
}
function berClass(b) { return b == null ? 'none' : b < 1 ? 'good' : b < 3 ? 'mid' : 'bad'; }
function renderCalState() {
    const c = S.admin.cal, el = $('calLive'); if (!c || !el) return;
    $('calStart').disabled = c.running; $('calStop').disabled = !c.running;
    const hist = c.ber_hist || [];
    const W = 360, H = 70, bw = W / 40;
    const top = Math.max(2, ...hist);
    const bars = hist.map((b, i) => { const h = Math.max(3, Math.min(1, b / top) * (H - 4)); return `<rect x="${i * bw + 1}" y="${H - h}" width="${bw - 2}" height="${h}" rx="2" fill="${b < 1 ? '#30d158' : b < 3 ? '#ffd60a' : '#ff453a'}"/>`; }).join('');
    const off = c.offset;
    el.innerHTML = `<h3 style="display:flex;justify-content:space-between">Live <span class="pill ${c.running ? 'ok' : ''}">${c.running ? '● running' : 'stopped'}</span></h3>
        <div class="subt">${esc(c.mode || (c.running ? 'Choose a test mode' : 'Press Start'))}${c.tx ? ' · <b style="color:#ff8a80">TX ON</b>' : ''}</div>
        <div class="cal-freq">${c.freq ? fmtFreqLong(c.freq) : '–'}</div>
        <div class="cal-off">Offset <b>${off != null ? (off > 0 ? '+' : '') + off + ' Hz' : '–'}</b> · Step ${c.step} Hz</div>
        <div class="btnrow">
            <button class="btn" onclick="calKey('f')" ${c.running ? '' : 'disabled'}>◀ −${c.step}</button>
            <select id="calStep" style="width:auto" onchange="calStep(this.value)" ${c.running ? '' : 'disabled'}>${[10, 25, 50, 100, 250, 500].map(s => `<option ${s === c.step ? 'selected' : ''}>${s}</option>`).join('')}</select>
            <button class="btn" onclick="calKey('F')" ${c.running ? '' : 'disabled'}>+${c.step} ▶</button>
        </div>
        <div class="cal-ber ${berClass(c.ber)}">${c.ber != null ? c.ber.toFixed(2) + ' %' : '–'}</div>
        <div class="cal-off">BER now${c.ber_end != null ? ` · last transmission <b>${c.ber_end.toFixed(2)} %</b>` : ''}</div>
        <svg viewBox="0 0 ${W} ${H}" style="width:100%;height:70px;margin-top:10px;display:block">${bars || `<text x="${W / 2}" y="${H / 2}" text-anchor="middle" fill="rgba(235,240,250,.4)" font-size="12">Transmit with your radio – the BER appears here</text>`}</svg>
        ${c.best ? `<div class="cal-off" style="margin-top:6px">Best so far: <b>${c.best.ber.toFixed(2)} %</b> at offset <b>${c.best.offset > 0 ? '+' : ''}${c.best.offset} Hz</b></div>` : ''}
        <div class="actions" style="justify-content:center">
            <button class="btn primary" onclick="calSave(${off ?? 'null'})" ${off == null ? 'disabled' : ''}>💾 Save offset ${off != null ? (off > 0 ? '+' : '') + off + ' Hz' : ''} (RX &amp; TX)</button>
            ${c.best && c.best.offset !== off ? `<button class="btn" onclick="calSave(${c.best.offset})">Save best (${c.best.offset > 0 ? '+' : ''}${c.best.offset} Hz)</button>` : ''}
        </div>`;
}
function appendCalLine(line) {
    const t = $('calTerm'); if (!t) return;
    t.textContent += line + '\n';
    if (t.textContent.length > 20000) t.textContent = t.textContent.slice(-15000);
    t.scrollTop = t.scrollHeight;
}
async function calStart() {
    const ok = await confirmBox({ title: 'Start calibration?', body: 'MMDVMHost and DMRGateway are stopped until you press Stop. The hotspot is off the air meanwhile.' }, 'Start');
    if (!ok) return;
    $('calStart').disabled = true; $('calTerm').textContent = '';
    try {
        const v = $('calStartFreq').value.replace(',', '.'); const hz = Math.round(parseFloat(v) * 1e6);
        const r = await api('POST', '/api/admin/cal/start', { freq: hz }); S.admin.cal = r.cal; renderCalState();
        await api('POST', '/api/admin/cal/key', { key: 'b' });
    } catch (e) { toast(e.message, true); $('calStart').disabled = false; }
}
async function calStop() { try { const r = await api('POST', '/api/admin/cal/stop', {}); S.admin.cal = r.cal; renderCalState(); toast('Calibration stopped, hotspot started'); } catch (e) { toast(e.message, true); } }
async function calKey(k) { try { await api('POST', '/api/admin/cal/key', { key: k }); } catch (e) { toast(e.message, true); } }
async function calStep(v) { try { await api('POST', '/api/admin/cal/freq', { step: Number(v) }); } catch (e) { toast(e.message, true); } }
async function calSave(off) {
    if (off == null) return;
    try { await api('POST', '/api/admin/cal/save', { offset: off }); toast(`Offset ${off} Hz saved`); const d = await api('GET', '/api/admin/cal'); S.admin.calCfg = d; }
    catch (e) { toast(e.message, true); }
}

// users
async function loadUsers() {
    const d = await api('GET', '/api/admin/users');
    $('admin-users').innerHTML = `<div class="grid users-grid">
        <div class="tile"><h3>👥 Users</h3><div class="subt">Admins change everything, viewers only see the dashboard (also when it is private).</div>
        <div class="tbl-wrap"><table class="tbl"><thead><tr><th>User</th><th>Role</th><th class="hide-sm">Last login</th><th></th></tr></thead><tbody>
        ${d.users.map(u => `<tr><td><b>${esc(u.username)}</b> ${u.default_pw ? '<span class="pill warn">factory password</span>' : ''} ${u.disabled ? '<span class="pill bad">locked</span>' : ''}<br><span class="dim">${esc(u.display_name)}</span></td>
            <td><span class="pill ${u.role === 'admin' ? 'ok' : ''}">${u.role}</span></td><td class="hide-sm">${u.last_login ? fmtDate(u.last_login) : '–'}</td>
            <td class="num"><button class="btn small" onclick='editUser(${JSON.stringify(u)})'>Edit</button></td></tr>`).join('')}
        </tbody></table></div></div>
        <form class="tile" onsubmit="event.preventDefault(); createUser(this)"><h3>➕ New user</h3>
            <div class="row"><label>Username</label><input type="text" name="username" required></div>
            <div class="row"><label>Name</label><input type="text" name="display_name"></div>
            <div class="row"><label>Password</label><input type="password" name="password" required minlength="8" autocomplete="new-password"></div>
            <div class="row"><label>Role</label><select name="role"><option value="viewer">Viewer</option><option value="admin">Admin</option></select></div>
            <div class="actions"><button class="btn primary">Create</button></div></form></div>`;
}
async function createUser(f) {
    try { await api('POST', '/api/admin/users', { username: f.username.value, display_name: f.display_name.value, password: f.password.value, role: f.role.value }); toast('User created'); loadUsers(); }
    catch (e) { toast(e.message, true); }
}
function editUser(u) {
    modal(`<h2>Edit ${esc(u.username)}</h2><form onsubmit="event.preventDefault(); saveUser(${u.id}, this)">
        <div class="row"><label>Username</label><input type="text" name="username" value="${esc(u.username)}"></div>
        <div class="row"><label>Name</label><input type="text" name="display_name" value="${esc(u.display_name)}"></div>
        <div class="row"><label>Role</label><select name="role"><option value="viewer" ${u.role === 'viewer' ? 'selected' : ''}>Viewer</option><option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option></select></div>
        <div class="row"><label>New password (empty = keep)</label><input type="password" name="password" minlength="8" autocomplete="new-password"></div>
        <label style="display:flex;gap:8px;align-items:center" class="dim"><input type="checkbox" name="disabled" ${u.disabled ? 'checked' : ''}> Locked</label>
        <div class="err" id="uErr"></div>
        <div class="actions"><button type="button" class="btn danger" onclick="delUser(${u.id}, '${esc(u.username)}')">Delete</button><span style="flex:1"></span>
        <button type="button" class="btn" onclick="closeModal()">Cancel</button><button class="btn primary">Save</button></div></form>`);
}
async function saveUser(id, f) {
    const b = { username: f.username.value, display_name: f.display_name.value, role: f.role.value, disabled: f.disabled.checked };
    if (f.password.value) b.password = f.password.value;
    try { await api('PATCH', `/api/admin/users/${id}`, b); closeModal(); toast('Saved'); loadUsers(); } catch (e) { $('uErr').textContent = e.message; }
}
async function delUser(id, name) {
    closeModal();
    if (!await confirmBox({ title: `Delete ${name}?`, body: 'The user and all sessions are removed.' }, 'Delete', 'danger')) return;
    try { await api('DELETE', `/api/admin/users/${id}`); toast('Deleted'); loadUsers(); } catch (e) { toast(e.message, true); }
}

// system
async function loadSystem() {
    const d = await api('GET', '/api/admin/system'), i = d.info;
    const svcNames = { mmdvmhost: 'MMDVMHost', dmrgateway: 'DMRGateway', mosquitto: 'MQTT broker (mosquitto)', n8hotspot: 'N8-Hotspot web interface' };
    const memUsed = i.mem_total ? (i.mem_total - i.mem_available) : null;
    $('admin-system').innerHTML = `<div class="grid g2">
        <div class="tile"><h3>🖥️ Hardware</h3><div class="kv" style="margin-top:10px">
            <div class="k">Board</div><div class="v">${esc(i.model)}</div><div class="k">System</div><div class="v">${esc(i.os)}</div>
            <div class="k">Hostname / IP</div><div class="v">${esc(i.hostname)} · ${esc((i.ips || []).join(', '))}</div>
            <div class="k">CPU temperature</div><div class="v">${i.cpu_temp != null ? `<span class="pill ${i.cpu_temp < 60 ? 'ok' : i.cpu_temp < 75 ? 'warn' : 'bad'}">${i.cpu_temp} °C</span>` : '–'}</div>
            <div class="k">Load</div><div class="v">${i.load.join(' · ')} (${i.cpus} cores)</div>
            <div class="k">Memory</div><div class="v">${fmtBytes(memUsed)} of ${fmtBytes(i.mem_total)}</div>
            <div class="k">SD card</div><div class="v">${fmtBytes(i.disk_total - i.disk_free)} of ${fmtBytes(i.disk_total)}</div>
            <div class="k">Uptime</div><div class="v">${fmtDur(i.uptime, true)}</div></div>
            <div class="actions"><button class="btn" onclick="power('reboot')">🔄 Reboot</button><button class="btn danger" onclick="power('poweroff')">⏻ Shut down</button></div></div>
        <div class="tile"><h3>⚙️ Services</h3><div class="tbl-wrap"><table class="tbl" style="margin-top:6px"><tbody>
            ${Object.entries(svcNames).map(([k, n]) => { const st = d.services[k] || 'unknown';
                return `<tr><td><span class="dot ${st === 'active' ? 'on' : st === 'unknown' ? 'unk' : 'off'}"></span>${n}<br><span class="dim" style="font-size:12px">${st}</span></td>
                <td class="num">${k === 'n8hotspot' ? `<button class="btn small" onclick="svc('${k}','restart')">Restart</button>` : `<button class="btn small" onclick="svc('${k}','start')">Start</button> <button class="btn small" onclick="svc('${k}','stop')">Stop</button> <button class="btn small" onclick="svc('${k}','restart')">Restart</button>`}</td></tr>`; }).join('')}
            </tbody></table></div>
            <div class="kv" style="margin-top:12px"><div class="k">MQTT live data</div><div class="v">${d.mqtt ? '<span class="pill ok">connected</span>' : '<span class="pill bad">not connected</span>'}</div>
                <div class="k">MMDVMHost</div><div class="v mono" style="font-size:12px">${esc(d.versions.mmdvmhost)}</div>
                <div class="k">DMRGateway</div><div class="v mono" style="font-size:12px">${esc(d.versions.dmrgateway)}</div>
                <div class="k">MMDVMCal</div><div class="v">${esc(d.versions.mmdvmcal)}</div>
                <div class="k">N8-Hotspot</div><div class="v">${esc(d.app_version)}${d.demo ? ' (demo)' : ''}</div></div></div>
        <div class="tile"><h3>📘 DMR ID list</h3><div class="subt">Callsigns and names for the dashboard and MMDVMHost (DMRIds.dat).</div>
            <div class="kv"><div class="k">IDs</div><div class="v">${d.idlist.count.toLocaleString('de-DE')}</div><div class="k">Updated</div><div class="v">${d.idlist.updated ? fmtDate(d.idlist.updated) : 'never'}</div>
            ${d.idlist.error ? `<div class="k">Error</div><div class="v" style="color:#ff8a80;white-space:normal">${esc(d.idlist.error)}</div>` : ''}</div>
            <div class="actions"><button class="btn" onclick="refreshIds(this)">⟳ Update now</button></div></div>
        <div class="tile"><h3>🗂️ Talkgroup list</h3><div class="subt">Names from github.com/dhartmann1979/n8schicht, plus your own.</div>
            <div class="kv"><div class="k">Names</div><div class="v">${d.talkgroups.enabled ? d.talkgroups.count.toLocaleString('de-DE') : 'off'}${d.talkgroups.own ? ` <span class="dim">+ ${d.talkgroups.own} own</span>` : ''}</div>
            <div class="k">Updated</div><div class="v">${d.talkgroups.updated ? fmtDate(d.talkgroups.updated) : 'copy shipped with N8-Hotspot'}</div>
            ${d.talkgroups.error ? `<div class="k">Error</div><div class="v" style="color:#ff8a80;white-space:normal">${esc(d.talkgroups.error)}</div>` : ''}</div></div>
        <div class="tile"><h3>🛡️ FreeRadioID.net</h3><div class="subt">Registered IDs (FRID badge) and avatars, loaded with the ID list.</div>
            <div class="kv"><div class="k">Registered IDs</div><div class="v">${d.frid.enabled ? d.frid.registered.toLocaleString('de-DE') : 'off'}</div>
            <div class="k">Avatars cached</div><div class="v">${d.frid.avatars.with_avatar} <span class="dim">(${d.frid.avatars.without} without picture)</span></div>
            <div class="k">Updated</div><div class="v">${d.frid.updated ? fmtDate(d.frid.updated) : 'with the next ID list update'}</div>
            ${d.frid.error ? `<div class="k">Error</div><div class="v" style="color:#ff8a80;white-space:normal">${esc(d.frid.error)}</div>` : ''}</div></div>
        <div class="tile"><h3>🗄️ Data</h3><div class="kv"><div class="k">Calls stored</div><div class="v">${d.calls.toLocaleString('de-DE')}</div>
            <div class="k">Since</div><div class="v">${d.calls_since ? fmtDate(d.calls_since) : '–'}</div><div class="k">Folder</div><div class="v mono" style="font-size:12px">${esc(d.data_dir)}</div></div></div>
    </div>`;
}
async function svc(s, a) {
    if (a === 'stop' && !await confirmBox({ title: `Stop ${s}?`, body: 'The hotspot does not work without it until you start it again.' }, 'Stop', 'danger')) return;
    try { await api('POST', '/api/admin/service', { service: s, action: a }); toast(`${s}: ${a}`); setTimeout(loadSystem, 800); } catch (e) { toast(e.message, true); }
}
async function power(a) {
    if (!await confirmBox({ title: a === 'reboot' ? 'Reboot the hotspot?' : 'Shut down the hotspot?', body: a === 'reboot' ? 'It is back after about a minute.' : 'Unplug and replug the power to start it again.' }, a === 'reboot' ? 'Reboot' : 'Shut down', 'danger')) return;
    try { await api('POST', '/api/admin/power', { action: a }); toast(a === 'reboot' ? 'Rebooting …' : 'Shutting down …'); } catch (e) { toast(e.message, true); }
}
async function refreshIds(btn) {
    btn.disabled = true; btn.textContent = 'Loading …';
    try { const r = await api('POST', '/api/admin/idlist/refresh', {}); toast(`${r.count.toLocaleString('de-DE')} IDs${r.talkgroups ? ', ' + r.talkgroups.toLocaleString('de-DE') + ' talkgroups' : ''} loaded`); loadSystem(); } catch (e) { toast(e.message, true); btn.disabled = false; btn.textContent = '⟳ Update now'; }
}

// logs
async function loadLogs() {
    const d = await api('GET', '/api/admin/logs'); S.admin.logs = d.entries;
    $('admin-logs').innerHTML = `<div class="tile"><h3 style="display:flex;justify-content:space-between;align-items:center">📜 Live log
        <span class="seg" id="logF"><button data-v="all" class="active">All</button><button data-v="mmdvm">MMDVMHost</button><button data-v="gateway">DMRGateway</button></span></h3>
        <div class="term logview" id="logView"></div>
        <div class="actions" style="justify-content:flex-start"><select id="jSvc" style="width:auto"><option>mmdvmhost</option><option>dmrgateway</option><option>mosquitto</option><option>n8hotspot</option></select>
        <button class="btn" onclick="loadJournal()">Show system journal</button></div>
        <pre class="term hidden" id="jView" style="height:320px"></pre></div>`;
    bindSeg('logF', v => { S.admin.logFilter = v; renderLogs(); });
    renderLogs();
}
function logLine(e) {
    const cls = { warning: 'w', error: 'e', fatal: 'e', debug: 't' }[e.level] || '';
    return `<div class="${cls}"><span class="t">${fmtTime(e.ts)}</span> <span class="g">${e.app === 'gateway' ? 'GW ' : 'MMDVM'}</span> ${esc(e.text)}</div>`;
}
function renderLogs() {
    const v = $('logView'); if (!v) return;
    v.innerHTML = S.admin.logs.filter(e => S.admin.logFilter === 'all' || e.app === S.admin.logFilter).slice(-400).map(logLine).join('') || '<div class="t">No log lines yet.</div>';
    v.scrollTop = v.scrollHeight;
}
function appendLog(e) {
    const v = $('logView'); if (!v || (S.admin.logFilter !== 'all' && e.app !== S.admin.logFilter)) return;
    const atEnd = v.scrollTop + v.clientHeight >= v.scrollHeight - 30;
    v.insertAdjacentHTML('beforeend', logLine(e));
    if (atEnd) v.scrollTop = v.scrollHeight;
}
async function loadJournal() { const j = $('jView'); j.classList.remove('hidden'); j.textContent = 'Loading …'; try { j.textContent = (await api('GET', `/api/admin/journal?service=${$('jSvc').value}&lines=300`)).text; j.scrollTop = j.scrollHeight; } catch (e) { j.textContent = e.message; } }

// files
async function loadFiles() {
    const d = await api('GET', '/api/admin/config-files');
    $('admin-files').innerHTML = `<div class="grid g2">${Object.entries(d).map(([n, t]) => `<div class="tile"><h3>🧾 ${esc(n)}</h3>
        <div class="subt">Generated from the settings. Additional lines: Settings → Expert.</div><pre class="term ini">${esc(t)}</pre></div>`).join('')}</div>`;
}

// sessions & audit
async function loadAudit() {
    const [s, a] = await Promise.all([api('GET', '/api/admin/sessions'), api('GET', '/api/admin/audit')]);
    const lbl = { login: '🔓 Login', login_failed: '⛔ Login failed', settings_changed: '⚙️ Settings', services_restarted: '🔄 Restart', user_created: '➕ User',
        user_changed: '✏️ User', user_deleted: '🗑️ User', password_changed: '🔑 Password', calibration_started: '🎛️ Calibration', calibration_saved: '💾 Offset',
        calibration_stopped: '🎛️ Calibration end', service: '⚙️ Service', reboot: '🔄 Reboot', poweroff: '⏻ Shutdown', idlist_refresh: '📘 ID list', session_revoked: '🚫 Session' };
    $('admin-audit').innerHTML = `<div class="grid g2">
        <div class="tile"><h3>🔑 Active sessions</h3><div class="tbl-wrap"><table class="tbl"><thead><tr><th>User</th><th>IP</th><th class="hide-sm">Since</th><th></th></tr></thead><tbody>
        ${s.sessions.map(x => `<tr><td>${esc(x.username)}</td><td class="mono">${esc(x.ip)}</td><td class="hide-sm">${fmtDate(x.created_at)}</td><td class="num"><button class="btn small" onclick="revokeS('${x.id}')">End</button></td></tr>`).join('')}
        </tbody></table></div></div>
        <div class="tile"><h3>📜 Change log</h3><div class="tbl-wrap" style="max-height:520px;overflow:auto"><table class="tbl"><thead><tr><th>Time</th><th>What</th><th>Who</th><th class="hide-sm">Details</th></tr></thead><tbody>
        ${a.entries.map(x => `<tr><td>${fmtDate(x.ts)}</td><td>${lbl[x.action] || esc(x.action)}</td><td>${esc(x.username)}</td><td class="hide-sm dim" style="white-space:normal;max-width:300px">${esc(x.detail)}${x.ip ? ` · ${esc(x.ip)}` : ''}</td></tr>`).join('')}
        </tbody></table></div></div></div>`;
}
async function revokeS(id) { try { await api('DELETE', `/api/admin/sessions/${id}`); loadAudit(); } catch (e) { toast(e.message, true); } }

boot();
