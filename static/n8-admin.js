/* N8-Hotspot – colour scheme, link menu, footer and updates.
 * Same building blocks as HBlink4-FreeRadioID and adn-frn-server (N8 Theme, link site icons, update check). */

// ---------------------------------------------------------------- theme, links, footer
function applyUI(info) {
    if (!info) return;
    if (info.theme && window.N8Theme) N8Theme.apply(info.theme);
    renderLinks(info.links);
    renderFooter(info.build);
}
function renderLinks(L) {
    const menu = $('linksMenu');
    const items = (L && L.enabled && Array.isArray(L.items)) ? L.items.filter(i => i && i.label && i.url) : [];
    if (!items.length) { menu.hidden = true; return; }
    menu.hidden = false;
    menu.querySelector('.links-label').textContent = L.label || '🔗 Links';
    const ic = i => i.icon_key
        ? `<span class="li-ic"><img class="li-fav" src="/api/link-icon/${encodeURIComponent(i.icon_key)}" alt="" loading="lazy"
               onerror="this.replaceWith(document.createTextNode(this.dataset.fb))" data-fb="${esc(i.icon || '🔗')}"></span>`
        : `<span class="li-ic">${esc(i.icon || '🔗')}</span>`;
    menu.querySelector('.links-pop').innerHTML = items.map(i =>
        `<a href="${esc(i.url)}" ${i.new_tab ? 'target="_blank" rel="noopener"' : ''}>${ic(i)}<span>${esc(i.label)}</span></a>`).join('');
}
function toggleLinks(ev) { ev.stopPropagation(); $('linksMenu').classList.toggle('open'); }
document.addEventListener('click', ev => { const m = $('linksMenu'); if (m && !m.contains(ev.target)) m.classList.remove('open'); });

function renderFooter(b) {
    $('footerYear').textContent = new Date().getFullYear();
    if (!b) return;
    $('ver').textContent = 'N8-Hotspot ' + (b.version ? 'v' + b.version : '') + (b.commit ? ` (${b.commit})` : '');
    $('footerDate').textContent = b.date ? new Date(b.date).toLocaleDateString('de-DE') : '';
    $('footerDate').previousElementSibling.hidden = !b.date;
}

// ---------------------------------------------------------------- admin: appearance
async function loadAppearance() {
    const d = await api('GET', '/api/admin/ui');
    S.admin.ui = d;
    $('admin-appearance').innerHTML = `<div class="grid g2 ap-grid">
        <form class="tile" onsubmit="event.preventDefault(); saveTheme()">
            <h3>🎨 Colour scheme</h3>
            <div class="subt">Pick a preset and change any colour you like. The preview is live – nothing is stored before “Save”.
                The same theme engine runs in HBlink4-FreeRadioID and the FRN dashboard, so one colour code looks the same everywhere.</div>
            ${N8Theme.editorHtml(d.theme, 'apTheme')}
            <div class="actions"><button type="button" class="btn" onclick="resetTheme()">↺ Default</button>
                <button type="button" class="btn" onclick="N8Theme.setEditor($('apTheme'), S.admin.ui.theme); N8Theme.apply(S.admin.ui.theme)">Undo</button>
                <button class="btn primary">Save</button></div>
        </form>
        <div class="tile"><h3>🧾 Export / import</h3>
            <div class="subt">Copy the scheme to another N8 dashboard (HBlink4-FreeRadioID → Appearance, FRN → Theme) or paste one from there.</div>
            <textarea id="apJson" spellcheck="false" style="min-height:190px">${esc(JSON.stringify(d.theme, null, 2))}</textarea>
            <div class="actions"><button type="button" class="btn" onclick="copyTheme()">📋 Copy</button>
                <button type="button" class="btn" onclick="importTheme()">⤵ Take over</button></div>
        </div>
    </div>`;
    N8Theme.bindEditor($('apTheme'), t => { $('apJson').value = JSON.stringify(t, null, 2); });
}
async function saveTheme() {
    try {
        const r = await api('POST', '/api/admin/ui/theme', N8Theme.readEditor($('apTheme')));
        S.admin.ui.theme = r.theme; S.info.theme = r.theme; N8Theme.apply(r.theme);
        $('apJson').value = JSON.stringify(r.theme, null, 2);
        toast('Colour scheme saved');
    } catch (e) { toast(e.message, true); }
}
function resetTheme() { const t = { preset: 'n8' }; N8Theme.setEditor($('apTheme'), t); N8Theme.apply(t); $('apJson').value = JSON.stringify(N8Theme.normalize(t), null, 2); }
function copyTheme() {
    const ta = $('apJson'); ta.select();
    (navigator.clipboard ? navigator.clipboard.writeText(ta.value) : Promise.reject()).then(() => toast('Copied'), () => { document.execCommand('copy'); toast('Copied'); });
}
function importTheme() {
    let t;
    try { t = JSON.parse($('apJson').value); } catch (e) { toast('That is not valid JSON.', true); return; }
    N8Theme.setEditor($('apTheme'), t); N8Theme.apply(N8Theme.readEditor($('apTheme')));
    toast('Taken over – press Save to keep it');
}

// ---------------------------------------------------------------- admin: links
let lnItems = [];
async function loadLinksAdmin() {
    const d = await api('GET', '/api/admin/ui');
    S.admin.ui = d;
    lnItems = d.links.items.map(i => ({ ...i }));
    $('admin-links').innerHTML = `<form class="tile" onsubmit="event.preventDefault(); saveLinks()">
        <h3>🔗 Link menu</h3>
        <div class="subt">Shown in the header for everybody. With “site icon” the hotspot fetches the favicon of the linked page once,
            keeps it in its database and shows it in the menu (the emoji is the fallback, e.g. while offline).</div>
        <div class="row"><label for="lnOn">Show the link menu</label><label class="switch"><input type="checkbox" id="lnOn" ${d.links.enabled ? 'checked' : ''}><span></span></label></div>
        <div class="row"><label for="lnLabel">Button text</label><input type="text" id="lnLabel" value="${esc(d.links.label)}" maxlength="30"></div>
        <div class="ln-head"><span>Icon</span><span>Name</span><span>Address</span><span title="Fetch the favicon of the page">Site icon</span><span title="Open in a new tab">New tab</span><span></span></div>
        <div id="lnList"></div>
        <div class="actions"><button type="button" class="btn" onclick="lnAdd()">＋ Link</button><button class="btn primary">Save</button>
            <button type="button" class="btn" onclick="refreshSiteIcons(this)">↻ Refresh site icons now</button></div>
    </form>`;
    lnRows();
}
function lnRows() {
    const st = (S.admin.ui && S.admin.ui.icons) || {};
    $('lnList').innerHTML = lnItems.map((i, n) => {
        const s = st[i.url];
        const state = !i.site_icon ? '' : s && s.ok ? '<span class="pill ok" title="Cached">✓</span>' : s ? '<span class="pill warn" title="No icon found – the emoji is shown">–</span>' : '';
        return `<div class="ln-row" data-n="${n}">
            <input type="text" data-k="icon" value="${esc(i.icon)}" maxlength="8" placeholder="🔗" aria-label="Icon">
            <input type="text" data-k="label" value="${esc(i.label)}" maxlength="40" placeholder="Name" aria-label="Name">
            <input type="text" data-k="url" value="${esc(i.url)}" maxlength="500" placeholder="https://…" aria-label="Address">
            <span class="ln-sw"><label class="switch"><input type="checkbox" data-k="site_icon" ${i.site_icon ? 'checked' : ''}><span></span></label>${state}</span>
            <span class="ln-sw"><label class="switch"><input type="checkbox" data-k="new_tab" ${i.new_tab ? 'checked' : ''}><span></span></label></span>
            <span class="ln-act"><button type="button" class="btn small" onclick="lnMove(${n},-1)" title="Up" ${n ? '' : 'disabled'}>↑</button><button type="button" class="btn small danger" onclick="lnDel(${n})" title="Remove">✕</button></span>
        </div>`; }).join('') || '<div class="empty">No links yet.</div>';
    $('lnList').querySelectorAll('input').forEach(inp => inp.addEventListener('input', () => {
        const it = lnItems[+inp.closest('.ln-row').dataset.n]; it[inp.dataset.k] = inp.type === 'checkbox' ? inp.checked : inp.value;
    }));
}
function lnAdd() { lnItems.push({ icon: '🔗', label: '', url: 'https://', site_icon: true, new_tab: true }); lnRows(); }
function lnDel(n) { lnItems.splice(n, 1); lnRows(); }
function lnMove(n, d) { const t = lnItems[n + d]; if (!t) return; lnItems[n + d] = lnItems[n]; lnItems[n] = t; lnRows(); }
async function saveLinks() {
    try {
        const r = await api('POST', '/api/admin/ui/links', { enabled: $('lnOn').checked, label: $('lnLabel').value, items: lnItems });
        toast('Links saved – site icons are fetched in the background');
        const info = await api('GET', '/api/info'); S.info = { ...S.info, ...info }; applyUI(S.info);
        setTimeout(() => { if (S.admin.tab === 'links') loadLinksAdmin(); }, 4000);
        lnItems = r.links.items;
    } catch (e) { toast(e.message, true); }
}
async function refreshSiteIcons(btn) {
    const label = btn.textContent;
    btn.disabled = true; btn.textContent = 'Refreshing…';
    try {
        const r = await api('POST', '/api/admin/site-icons/refresh', {});
        toast(`Site icons refreshed: ${r.cached}/${r.total} cached${r.unavailable ? `, ${r.unavailable} unavailable` : ''}.`, !!r.unavailable);
        await loadLinksAdmin();
    } catch (e) { toast(e.message, true); }
    finally { btn.disabled = false; btn.textContent = label; }
}

// ---------------------------------------------------------------- admin: updates
// N8 Kit state: same banner, tile and progress as in the other N8schicht projects
function kitUpdate(d) {
    if (!d) return null;
    const loc = d.local || {}, lat = d.latest || {};
    const notes = (d.release_notes || []).map(s => `<div class="upd-sec"><b>v${esc(s.version)}</b> <span class="dim">${esc(s.date || '')}</span>
        <ul>${s.body.split('\n').filter(x => /^\s*[-*]\s/.test(x)).slice(0, 12).map(x => `<li>${esc(x.replace(/^\s*[-*]\s+/, '').replace(/\*\*/g, ''))}</li>`).join('')}</ul></div>`).join('')
        || ((d.commits || []).length ? '<ul>' + d.commits.slice(0, 10).map(x => `<li><code>${esc(x.short)}</code> ${esc(x.message)}</li>`).join('') + '</ul>' : '');
    const c = d.config || {};
    return {
        available: !!(d.available && !d.error && lat.short), current: `v${loc.version || '?'} · ${loc.short || 'no git'}`,
        latest: lat.short ? `${d.remote_version ? 'v' + d.remote_version + ' · ' : ''}${lat.short}` : '', notes, checked: d.checked_at,
        can_install: !!(d.available && d.can_install), error: d.error || '', result: d.result || null,
        schedule: !d.enabled ? 'aus' : c.auto ? `stündlich zur vollen Stunde, automatisch installieren ${String(c.auto_hour).padStart(2, '0')}:00–${String(c.auto_hour).padStart(2, '0')}:59` : (c.interval_hours > 1 ? `alle ${c.interval_hours} Stunden zur vollen Stunde` : 'stündlich zur vollen Stunde'),
        reason: d.can_install ? '' : 'This installation is not a git checkout – update with <code>sudo /opt/n8hotspot/scripts/update.sh</code>.',
        extra: [['Source', `<span class="mono" style="font-size:12px">${esc(d.origin || d.url || '')}</span>`]],
    };
}
async function loadUpdates(force) {
    const el = $('admin-updates');
    let d;
    try { d = await api('GET', '/api/admin/update' + (force ? '?force=true' : '')); }
    catch (e) { el.innerHTML = `<div class="tile"><h3>⬆️ Updates</h3><div class="empty">${esc(e.message)}</div></div>`; return; }
    S.admin.update = d; renderUpdateBanner();
    const c = d.config;
    el.innerHTML = `<div class="grid g2">
        <div class="tile"><h3>⬆️ Updates</h3><div id="updPanel"></div></div>
        <div class="tile" id="updLogTile"><h3>📜 Update log</h3></div>
        <form class="tile" onsubmit="event.preventDefault(); saveUpdateCfg(this)"><h3>⚙️ Update settings</h3>
            <div class="row"><label for="upOn">Check for updates</label><label class="switch"><input type="checkbox" id="upOn" name="enabled" ${c.enabled ? 'checked' : ''}><span></span></label>
                <div class="help">Asks GitHub every full hour (no login, no data about your hotspot is sent).</div></div>
            <div class="row"><label for="upInt">Check every (hours)</label><input type="number" id="upInt" name="interval_hours" min="1" max="168" value="${c.interval_hours}"></div>
            <div class="row"><label for="upAuto">Install automatically</label><label class="switch"><input type="checkbox" id="upAuto" name="auto" ${c.auto ? 'checked' : ''}><span></span></label>
                <div class="help">Installs a new version by itself during the chosen hour – only when nobody is transmitting and no calibration runs.</div></div>
            <div class="row"><label for="upHour">Hour for automatic updates</label><select id="upHour" name="auto_hour">${Array.from({ length: 24 }, (_, h) => `<option value="${h}" ${h === c.auto_hour ? 'selected' : ''}>${String(h).padStart(2, '0')}:00–${String(h).padStart(2, '0')}:59</option>`).join('')}</select></div>
            <div class="row"><label for="upRadio">Restart MMDVMHost &amp; DMRGateway</label><label class="switch"><input type="checkbox" id="upRadio" name="restart_radio" ${c.restart_radio ? 'checked' : ''}><span></span></label>
                <div class="help">After an update the ini files are written again and both radio services restart, the web interface always restarts.</div></div>
            <div class="row"><label for="upRepo">Repository</label><input type="text" id="upRepo" name="repo" value="${esc(c.repo)}"></div>
            <div class="row"><label for="upBranch">Branch</label><input type="text" id="upBranch" name="branch" value="${esc(c.branch)}"></div>
            <div class="actions"><button class="btn primary">Save</button></div>
        </form>
    </div>`;
    N8Kit.update.panel($('updPanel'), kitUpdate(d), { onCheck: () => loadUpdates(true), onInstall: () => openUpdateNow() });
    loadUpdateLog();
}
async function saveUpdateCfg(form) {
    const v = {};
    form.querySelectorAll('[name]').forEach(i => { v[i.name] = i.type === 'checkbox' ? i.checked : i.type === 'number' || i.tagName === 'SELECT' ? Number(i.value) : i.value; });
    try { await api('POST', '/api/admin/ui/update', v); toast('Update settings saved'); loadUpdates(true); }
    catch (e) { toast(e.message, true); }
}
function openUpdateNow() {
    const d = S.admin.update, k = kitUpdate(d); if (!k) return;
    N8Kit.update.run({
        from: k.current, to: k.latest, password: true, timeout: 600000,
        text: `${k.notes}<div class="upd-facts"><span>1. Fast-forward to <code>${esc((d.latest || {}).short || '')}</code> (stops if files were changed by hand)</span>
            <span>2. Python packages, services and ini files, permissions and sudo (N8 Admin-Kit, as root)</span>
            <span>3. Restart MMDVMHost, DMRGateway and the web interface</span>
            <span>4. Check of the web interface – if it does not answer, back to the previous version; the page reloads by itself</span></div>`,
        install: async (password) => {
            const r = await api('POST', '/api/admin/update/install', { password, expected: (d.latest || {}).commit });
            $('updateBanner').hidden = true;
            const bad = (r.steps || []).filter(s => !s.ok);
            if (bad.length) toast(bad.map(s => `${s.step}${s.detail ? ' – ' + s.detail : ''}`).join(' · '), true);
            if (r.restart === 'n8') return r;                      // N8 Admin-Kit: runs as root, the kit dialog waits for the new version
            if (r.restart === 'manual') return { restart: false, message: 'Please restart N8-Hotspot by hand: sudo systemctl restart n8hotspot' };
            if (r.restart !== 'service') return { restart: false, message: 'Update installed.' };
            return r;
        },
        version: async () => {
            const r = await fetch('/api/info', { cache: 'no-store', credentials: 'same-origin' });
            if (!r.ok) throw new Error(r.status);
            const b = (await r.json()).build || {};
            return `v${b.version || '?'} · ${b.commit || ''}`;
        },
    });
}
function renderUpdateBanner() {
    const el = $('updateBanner');
    if (!isAdmin()) { el.hidden = true; return; }
    N8Kit.update.banner(el, kitUpdate(S.admin.update), { app: 'n8hs', onInstall: () => openUpdateNow(), onDetails: () => showTab('admin', 'updates') });
}
async function checkUpdateQuiet() {
    if (!isAdmin()) return;
    try { S.admin.update = await api('GET', '/api/admin/update'); renderUpdateBanner(); } catch (e) { }
}

// ---------------------------------------------------------------- services, permissions & sudo, update log (N8 Admin-Kit)
// Same building block as HobbyRadioPortal, adn-frn-server and HBlink4: scripts/n8-admin.sh runs as root via sudo.
const SVC_BTN = { start: ['▶', 'Start'], stop: ['■', 'Stop'], restart: ['↻', 'Restart'] };
async function loadServices() {
    const el = $('svcTile'); if (!el) return;
    let d;
    try { d = await api('GET', '/api/admin/services'); } catch (e) { el.innerHTML = `<h3>🧩 Services</h3><div class="empty">${esc(e.message)}</div>`; return; }
    if (!d.ready || !d.units.length) {
        el.innerHTML = `<h3>🧩 Services</h3><div class="subt">Not set up yet – run once on the console:</div>
            <div class="perm-cmd"><code>sudo /opt/n8hotspot/scripts/n8-admin.sh fix-perms</code></div>`; return;
    }
    const st = u => u.active === 'active' ? '<span class="pill ok">running</span>' : u.active === 'failed' ? '<span class="pill bad">failed</span>'
        : u.active === 'activating' ? '<span class="pill warn">starting</span>' : '<span class="pill">stopped</span>';
    el.innerHTML = `<h3>🧩 Services</h3><div class="subt">Status, autostart and start · stop · restart – only what this hotspot allows (sudo rules of the N8 Admin-Kit).</div>
        <div class="svc-list">${d.units.map(u => {
            const can = a => (u.actions || []).includes(a);
            const auto = can('enable') || can('disable')
                ? `<label class="switch sm" title="Autostart"><input type="checkbox" ${u.enabled === 'enabled' ? 'checked' : ''} ${can(u.enabled === 'enabled' ? 'disable' : 'enable') ? '' : 'disabled'}
                    onchange="svcAct('${esc(u.unit)}', this.checked ? 'enable' : 'disable')"><span></span></label><span class="dim svc-auto">Autostart</span>`
                : `<span class="dim svc-auto">${u.enabled === 'enabled' ? 'Autostart on' : u.enabled}</span>`;
            const btns = ['restart', 'start', 'stop'].filter(can).filter(a => !(a === 'start' && u.active === 'active') && !(a === 'stop' && u.active !== 'active'))
                .map(a => `<button class="btn small ${a === 'stop' ? 'danger' : ''}" title="${SVC_BTN[a][1]}" onclick="svcAct('${esc(u.unit)}','${a}')">${SVC_BTN[a][0]}</button>`).join('');
            return `<div class="svc-row"><div class="svc-name"><b>${esc(u.label)}</b><span class="mono dim">${esc(u.unit)}</span></div>
                <div>${st(u)}</div><div class="svc-auto-w">${auto}</div><div class="svc-btns">${btns}</div></div>`;
        }).join('')}</div>`;
}
async function svcAct(unit, action) {
    if (action === 'stop' && !await confirmBox({ title: `Stop ${unit}?`, body: 'The hotspot does not work without it until you start it again.' }, 'Stop', 'danger')) { loadServices(); return; }
    try { const r = await api('POST', `/api/admin/services/${encodeURIComponent(unit)}/${action}`, {}); toast(`${unit}: ${action}`);
          setTimeout(loadServices, unit === 'n8hotspot.service' ? 4000 : 900); }
    catch (e) { toast(e.message, true); loadServices(); }
}
function permList(c) {
    const area = { user: 'Service user', prog: 'Program', data: 'Data', systemd: 'systemd', sudo: 'sudo', hw: 'Modem port' };
    const icon = s => s === 'ok' ? '<span class="pill ok">✓</span>' : s === 'warn' ? '<span class="pill warn">!</span>' : '<span class="pill bad">✕</span>';
    const rows = (c.checks || []).filter(x => x.status !== 'ok');
    const okN = (c.checks || []).length - rows.length;
    return `${rows.map(x => `<div class="perm-row">${icon(x.status)}<div><b>${esc(area[x.area] || x.area)}</b><div class="dim">${esc(x.text)}</div></div></div>`).join('')}
        ${okN ? `<details class="perm-ok"><summary>${okN} checks in order</summary>${(c.checks || []).filter(x => x.status === 'ok').map(x =>
            `<div class="perm-row">${icon('ok')}<div><b>${esc(area[x.area] || x.area)}</b><div class="dim">${esc(x.text)}</div></div></div>`).join('')}</details>` : ''}`;
}
async function loadPerms(fixResult) {
    const el = $('permTile'); if (!el) return;
    el.innerHTML = '<h3>🔐 Permissions &amp; sudo</h3><div class="empty">Checking …</div>';
    let c;
    try { c = fixResult ? fixResult.check : await api('GET', '/api/admin/perms'); } catch (e) { el.innerHTML = `<h3>🔐 Permissions &amp; sudo</h3><div class="empty">${esc(e.message)}</div>`; return; }
    const badge = c.ok ? '<span class="pill ok">all fine</span>' : c.missing ? '<span class="pill warn">not set up</span>' : `<span class="pill bad">${c.bad || '?'} problem(s)</span>`;
    el.innerHTML = `<h3>🔐 Permissions &amp; sudo ${badge}</h3>
        <div class="subt"><span>Program (root, read-only for the service), data and passwords, services, sudo, “Update now” and the modem port.</span>
            <span>Console:</span> <code>sudo /opt/n8hotspot/scripts/n8-admin.sh check-perms</code> <span>or</span> <code>fix-perms</code></div>
        ${c.message ? `<div class="help">${esc(c.message)}</div>` : ''}
        <div class="perm-list">${permList(c)}</div>
        ${fixResult && fixResult.message ? `<pre class="term" style="max-height:220px">${esc(fixResult.message)}</pre>` : ''}
        <div class="actions"><button class="btn" onclick="loadPerms()">↻ Check again</button>
            <button class="btn primary" onclick="fixPerms(this)">🛠️ Fix</button></div>`;
}
async function fixPerms(btn) {
    btn.disabled = true; btn.textContent = 'Fixing …';
    try { const r = await api('POST', '/api/admin/perms/fix', {}); toast(r.ok ? 'Permissions fixed – all fine' : 'Some problems remain', !r.ok); loadPerms(r); }
    catch (e) { toast(e.message, true); btn.disabled = false; btn.textContent = '🛠️ Fix'; }
}
async function loadUpdateLog() {
    const el = $('updLogTile'); if (!el) return;
    let d;
    try { d = await api('GET', '/api/admin/update-log'); } catch (e) { el.innerHTML = `<h3>📜 Update log</h3><div class="empty">${esc(e.message)}</div>`; return; }
    const r = d.result;
    el.innerHTML = `<h3>📜 Update log ${d.running ? '<span class="pill warn">running</span>' : d.pending ? '<span class="pill warn">requested</span>' : ''}</h3>
        <div class="subt"><span>“Update now” runs as root through</span> <code>n8hotspot-update.path</code><span>: fast-forward only, packages, services and ini files, permissions and sudo, restart, check of the web interface – if it does not answer, back to the previous version.</span></div>
        ${r ? `<div class="kv"><div class="k">Last update</div><div class="v">${r.ok ? '<span class="pill ok">ok</span>' : '<span class="pill bad">failed</span>'}
            ${esc(r.from || '')} → ${esc(r.to || '')} · ${fmtDate(r.time)}</div>${r.message ? `<div class="k">Message</div><div class="v" style="white-space:normal">${esc(r.message)}</div>` : ''}</div>` : ''}
        ${d.log ? `<pre class="term" style="max-height:260px">${esc(d.log)}</pre>` : '<div class="empty">No update through the web interface yet.</div>'}
        <div class="actions"><button class="btn" onclick="loadUpdateLog()">↻ Reload</button></div>`;
    if (d.running || d.pending) setTimeout(() => { if (S.admin.tab === 'updates') loadUpdateLog(); }, 3000);
}

// ---------------------------------------------------------------- Keep-Alive (N8 Admin-Kit): Dienste-Wächter, Internet, Heartbeat
async function loadKeepalive() {
    const el = $('kaTile'); if (!el) return;
    let d;
    try { d = await api('GET', '/api/admin/keepalive'); } catch (e) { el.innerHTML = `<h3>💓 Keep-Alive</h3><div class="empty">${esc(e.message)}</div>`; return; }
    const c = d.conf || {};
    const paused = c.paused_until && c.paused_until * 1000 > Date.now();
    const badge = !d.ready ? '<span class="pill warn">not set up</span>' : !c.enabled ? '<span class="pill">off</span>' : paused ? '<span class="pill warn">paused</span>'
        : d.stale ? '<span class="pill bad">not running</span>' : '<span class="pill ok">active</span>';
    const icon = st => ({ ok: '<span class="pill ok">✓</span>', hold: '<span class="pill">⏸</span>', restarted: '<span class="pill warn">↻</span>', giveup: '<span class="pill bad">✕</span>' }[st] || '<span class="pill warn">!</span>');
    const rows = (d.checks || []).map(x => `<div class="perm-row">${icon(x.state)}<div><b>${esc(x.label)}</b> <span class="mono dim">${esc(x.unit)}</span>
        <div class="dim"><span>${x.state === 'ok' ? 'healthy' : x.state === 'hold' ? 'stopped by hand – Keep-Alive waits' : esc(x.why || '')}</span>${x.fails ? ` · <span>${x.fails} min</span>` : ''}${x.restarts ? ` · <span>${x.restarts}× restarted</span>${x.last_restart ? ` · <span>${fmtDate(x.last_restart)}</span>` : ''}` : ''}</div></div></div>`).join('');
    el.innerHTML = `<h3>💓 Keep-Alive ${badge}</h3>
        <div class="subt">Every minute as root: checks each service for real (web interface, MQTT, modem, login at the DMR server), restarts sick ones after 3 minutes (at most 4× per hour), notices internet outages and restarts the network services afterwards, and reports to a heartbeat address.</div>
        ${d.ready ? `<div class="kv"><div class="k">Internet</div><div class="v">${d.net ? '<span class="pill ok">reachable</span>' : `<span class="pill bad">down since ${fmtDate(d.net_down_since)}</span>`}</div>
            <div class="k">Last check</div><div class="v">${d.age != null ? (d.age < 120 ? 'just now' : fmtDate(d.time)) : '–'}</div>
            ${c.heartbeat_url ? `<div class="k">Heartbeat</div><div class="v">${esc(d.heartbeat || '–')}</div>` : ''}</div>
            <div class="perm-list">${rows}</div>` : '<div class="help">Set up once on the console: <code>sudo /opt/n8hotspot/scripts/n8-admin.sh fix-perms</code></div>'}
        <form class="ka-form" onsubmit="event.preventDefault(); saveKeepalive(this)">
            <div class="row"><label for="kaOn">Keep-Alive on</label><label class="switch"><input type="checkbox" id="kaOn" name="enabled" ${c.enabled ? 'checked' : ''}><span></span></label></div>
            <div class="row"><label for="kaNet">Restart network services after an internet outage</label><label class="switch"><input type="checkbox" id="kaNet" name="net_restart" ${c.net_restart ? 'checked' : ''}><span></span></label></div>
            <div class="row"><label for="kaHb">Heartbeat address</label><input type="text" id="kaHb" name="heartbeat_url" value="${esc(c.heartbeat_url || '')}" placeholder="https://hc-ping.com/… or https://kuma…/api/push/…">
                <div class="help">Called every minute while everything is fine (Uptime Kuma “Push”, Healthchecks.io …) – it alerts you when the calls stop.</div></div>
            <div class="row"><label for="kaHbF">Heartbeat on errors (optional)</label><input type="text" id="kaHbF" name="heartbeat_fail_url" value="${esc(c.heartbeat_fail_url || '')}" placeholder="https://hc-ping.com/…/fail"></div>
            <div class="actions"><button type="button" class="btn" onclick="pauseKeepalive(${paused ? 0 : 60})">${paused ? '▶ Resume' : '⏸ Pause 1 h (maintenance)'}</button><button class="btn primary">Save</button></div>
        </form>
        ${d.log ? `<details class="perm-ok"><summary>Keep-Alive log</summary><pre class="term" style="max-height:220px">${esc(d.log)}</pre></details>` : ''}`;
}
async function saveKeepalive(f) {
    try { await api('POST', '/api/admin/keepalive', { enabled: f.enabled.checked, net_restart: f.net_restart.checked, heartbeat_url: f.heartbeat_url.value.trim(), heartbeat_fail_url: f.heartbeat_fail_url.value.trim() });
          toast('Keep-Alive saved'); loadKeepalive(); }
    catch (e) { toast(e.message, true); }
}
async function pauseKeepalive(min) {
    try { await api('POST', '/api/admin/keepalive', { pause_minutes: min }); toast(min ? 'Keep-Alive paused for 1 hour' : 'Keep-Alive active again'); loadKeepalive(); }
    catch (e) { toast(e.message, true); }
}
