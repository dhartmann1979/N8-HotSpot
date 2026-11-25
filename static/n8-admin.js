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
// ---------------------------------------------------------------- Admin → System (N8 Kit: the same views in every N8 system)
async function loadUpdates(force) {
    const d = await api('GET', '/api/admin/update' + (force ? '?force=true' : ''));
    S.admin.update = d; renderUpdateBanner();
    return d;
}
function updateSettingsForm(d) {
    const c = d.config;
    return `<div class="grid g2">
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
}
function loadSysView(name) {
    N8Kit.sys.view($('admin-sys'), name, {
        req: api, console: 'sudo /opt/n8hotspot/scripts/n8-admin.sh',
        update: { load: async (force) => kitUpdate(await loadUpdates(force)), onInstall: () => openUpdateNow() },
        extra: box => { if (S.admin.update && S.admin.update.config) box.innerHTML = updateSettingsForm(S.admin.update); },
    });
}
async function saveUpdateCfg(form) {
    const v = {};
    form.querySelectorAll('[name]').forEach(i => { v[i.name] = i.type === 'checkbox' ? i.checked : i.type === 'number' || i.tagName === 'SELECT' ? Number(i.value) : i.value; });
    try { await api('POST', '/api/admin/ui/update', v); toast('Update settings saved'); loadSysView('update'); }
    catch (e) { toast(e.message, true); }
}
function openUpdateNow() {
    const d = S.admin.update, k = kitUpdate(d); if (!k) return;
    N8Kit.update.run({
        from: k.current, to: k.latest, password: false, timeout: 600000,
        text: `${k.notes}<div class="upd-facts"><span>1. Fast-forward to <code>${esc((d.latest || {}).short || '')}</code> (stops if files were changed by hand)</span>
            <span>2. Python packages, services and ini files, permissions and sudo (N8 Admin-Kit, as root)</span>
            <span>3. Restart MMDVMHost, DMRGateway and the web interface</span>
            <span>4. Check of the web interface – if it does not answer, back to the previous version; the page reloads by itself</span></div>`,
        install: async () => {
            const r = await api('POST', '/api/admin/update/install', { expected: (d.latest || {}).commit });
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
    N8Kit.update.banner(el, kitUpdate(S.admin.update), { app: 'n8hs', onInstall: () => openUpdateNow(), onDetails: () => showTab('admin', 'sys-update') });
}
async function checkUpdateQuiet() {
    if (!isAdmin()) return;
    try { S.admin.update = await api('GET', '/api/admin/update'); renderUpdateBanner(); } catch (e) { }
}
