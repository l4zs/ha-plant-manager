// Shared presentation for the collection and individual floor-plan cards.
export const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// The backend works out the name: translated from the species, and numbered if it is shared.
export const plantName = p => p.display_name || p.name || '';
const PATHS = {
 leaf:'M20 4C10 2 3 6 4 14c1 7 12 9 15 0 1-3 1-7 1-10ZM5 20l10-10',
 drop:'M12 3c-2 4-7 9-7 13a7 7 0 0 0 14 0c0-4-5-9-7-13ZM8 16a4 4 0 0 0 4 4',
 clock:'M12 8v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z',
 sun:'M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5M17 12a5 5 0 1 1-10 0 5 5 0 0 1 10 0Z',
 pin:'M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0ZM14 10a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z',
 check:'m5 12 4 4L19 6',
 search:'M15.5 15.5 21 21M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
 photo:'M8 5l2-2h4l2 2h5v15H3V5h5ZM16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
 temp:'M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0ZM12 8v9',
 bug:'M8 9h8v8a4 4 0 0 1-8 0V9Zm2 0V6h4v3M3 9l5 3m-5 5h5m13-8-5 3m5 5h-5M9 3l1 3m5-3-1 3M12 12v8',
};
export const icon = name => `<svg class="g-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${PATHS[name] || PATHS.leaf}"/></svg>`;
export function countdown(care, now = Date.now()) {
  if(!care) return 'Noch kein Termin';
  if(care.needs_water) return 'Jetzt Boden prüfen';
  const end = Date.parse(care.next_watering);
  if(!Number.isFinite(end)) return 'Noch kein Termin';
  const mins = Math.max(0, Math.ceil((end-now)/60000));
  if(!mins) return 'Jetzt Boden prüfen';
  const d=Math.floor(mins/1440), h=Math.floor(mins%1440/60), m=mins%60;
  return d ? `${d} ${d===1?'Tag':'Tage'} · ${h} Std.` : h ? `${h} Std. · ${m} Min.` : `${m} Min.`;
}
export const dateText = iso => {
  const d = new Date(iso);
  return iso && Number.isFinite(+d) ? new Intl.DateTimeFormat('de-DE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}).format(d) : 'Noch nicht erfasst';
};
export const lightText = key => ({low:'Wenig Licht',medium:'Mittleres Licht',bright_indirect:'Hell, ohne direkte Sonne',direct:'Direkte Sonne'}[key] || 'Licht nicht erfasst');
export function updateCountdowns(root) {
  root.querySelectorAll('[data-garden-until]').forEach(el=>{
    el.textContent=countdown({next_watering:el.dataset.gardenUntil,needs_water:el.dataset.due==='true'});
  });
}
export function plantTile(p, area='', compact=false, busy=false) {
  const e=escapeHTML, c=p.care || {}, reserve=Math.max(0,Math.min(100,Number(c.water_reserve)||0));
  const problems=(c.problems||[]).filter(x=>x!=='watering_overdue');
  return `<article class="g-plant ${compact?'g-compact':''} ${c.needs_water?'g-due':''}">
    <button class="g-picture" data-action="open-plant" data-id="${e(p.id)}" aria-label="${e(plantName(p))}: Details öffnen">${p.photos?.[0]?`<img src="${e(p.photos[0].url)}" alt="${e(plantName(p))}" loading="lazy">`:icon('leaf')}
      <span class="g-room">${icon('pin')}${e(area || 'Raum noch offen')}</span>
    </button>
    <div class="g-body"><button class="g-name" data-action="open-plant" data-id="${e(p.id)}">${e(plantName(p))}</button><div class="g-species">${e(p.species)}</div>
      <div class="g-count"><span class="g-caption">${icon('clock')} ${c.needs_water?'Gießprüfung fällig':'Bis zur nächsten Gießprüfung'}</span><strong data-garden-until="${e(c.next_watering || '')}" data-due="${!!c.needs_water}">${countdown(p.care)}</strong><span class="g-small">${c.needs_water?'Erde vor dem Gießen prüfen':`Voraussichtlich ${dateText(c.next_watering)}`}</span></div>
      <div class="g-reserve" aria-label="Geschätzter Wasservorrat ${Math.round(reserve)} Prozent"><span style="width:${reserve}%"></span></div>
      <div class="g-details"><span>${icon('drop')} ${c.moisture!=null?`Boden: ${e(c.moisture)} %`:`${Math.round(reserve)} % · geschätzt`}</span><span>${icon('sun')}${e(lightText(p.light))}</span></div>
      <div class="g-last">Zuletzt gegossen: ${dateText(p.last_watered)}</div>
      ${problems.length?`<div class="g-warning">${problems.length} Pflegehinweis${problems.length===1?'':'e'} · Details öffnen</div>`:''}
      <div class="g-buttons"><button class="g-water" data-action="water" data-id="${e(p.id)}" ${busy?'disabled':''}>${icon('check')}${busy?'Wird gespeichert …':'Jetzt gegossen'}</button><button class="g-health" data-action="health-open" data-id="${e(p.id)}" title="Foto auf Krankheiten und Befall prüfen">${icon('bug')}Pflanze prüfen</button></div>
    </div></article>`;
}
// Follows the Home Assistant theme, not the browser's or the system's setting.
export const applyGardenTheme = (el, hass) => el.toggleAttribute('data-garden-dark', !!hass?.themes?.darkMode);
export const GARDEN_STYLES = `
 :host{--g-leaf:var(--plant-manager-leaf,#285747);--g-button:var(--plant-manager-button,#285747);--g-soft:var(--plant-manager-soft,#eaf0e9);--g-due:var(--plant-manager-due,#b47a37);--g-warning:var(--plant-manager-warning,#91601c);--g-focus:var(--plant-manager-focus,#bd8e4d);--g-bar:var(--plant-manager-bar,#669a80);--g-label-bg:var(--plant-manager-label-background,#ffffffed);--g-label:var(--plant-manager-label,#294a38);--g-overlay:var(--plant-manager-overlay,#14281e99);--g-shadow:var(--plant-manager-shadow,#0002);--g-shadow-soft:var(--plant-manager-shadow-soft,#203c2910);--g-paper:var(--ha-card-background,var(--card-background-color,#fff));--g-muted:var(--secondary-text-color,#64716a);--g-line:var(--divider-color,#dce4dc);color:var(--primary-text-color,#21362d);font-family:var(--paper-font-body1_-_font-family,Roboto,Arial,sans-serif)}
 *{box-sizing:border-box}.g-icon{width:20px;height:20px;flex:none;vertical-align:middle}.g-heading{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:26px 0 24px}.g-kicker{color:var(--g-leaf);font-size:12px;letter-spacing:.14em;text-transform:uppercase;margin-bottom:9px}.g-heading h2{font-size:clamp(26px,3vw,38px);font-weight:500;letter-spacing:-.03em;margin:0 0 9px}.g-heading p{margin:0;color:var(--g-muted);font-size:14px;max-width:570px;line-height:1.6}.g-heading>.g-icon{width:76px;height:76px;padding:18px;color:var(--g-leaf);background:var(--g-soft);border-radius:50%}.g-summary{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:24px}.g-summary span{display:flex;gap:8px;align-items:center;background:var(--g-paper);border:1px solid var(--g-line);padding:10px 14px;border-radius:12px;font-size:13px}.g-summary b{font-size:17px;color:var(--g-leaf)}
 .g-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,265px),1fr));gap:22px}.g-plant{background:var(--g-paper);border:1px solid var(--g-line);border-radius:21px;overflow:hidden;box-shadow:0 5px 18px var(--g-shadow-soft);min-width:0}.g-due{border-color:var(--g-due)}.g-picture{position:relative;width:100%;height:204px;padding:0;display:flex;align-items:center;justify-content:center;border:0;background:var(--g-soft);cursor:pointer;color:var(--g-leaf)}.g-picture>.g-icon{width:72px;height:72px}.g-picture img{width:100%;height:100%;object-fit:cover}.g-room{position:absolute;left:12px;bottom:12px;display:flex;align-items:center;gap:5px;border-radius:20px;background:var(--g-label-bg);color:var(--g-label);padding:5px 9px;font-size:11px}.g-room .g-icon{width:14px;height:14px}.g-body{padding:17px}.g-name{background:none;border:0;color:inherit;font:inherit;font-size:19px;font-weight:500;padding:0;text-align:left;cursor:pointer;line-height:1.3}.g-species{font-size:12px;color:var(--g-muted);font-style:italic;margin-top:4px;min-height:16px}.g-count{display:flex;flex-direction:column;gap:7px;margin:19px 0 14px}.g-caption{font-size:11px;color:var(--g-muted);display:flex;align-items:center;gap:6px}.g-caption .g-icon{width:15px;height:15px}.g-count strong{font-size:25px;font-weight:500;letter-spacing:-.04em;line-height:1.2;font-variant-numeric:tabular-nums}.g-small{font-size:11px;color:var(--g-muted)}.g-reserve{height:5px;background:var(--g-soft);border-radius:3px;overflow:hidden}.g-reserve span{display:block;height:100%;background:var(--g-bar);border-radius:3px}.g-details{display:flex;flex-wrap:wrap;gap:7px 14px;margin:12px 0;color:var(--g-muted);font-size:11px}.g-details>span{display:flex;align-items:center;gap:5px}.g-details .g-icon{width:15px;height:15px}.g-last{font-size:11px;color:var(--g-muted);line-height:1.6}.g-buttons{display:grid;grid-template-columns:1fr;gap:8px;margin-top:16px}.g-buttons button,.g-button{display:flex;justify-content:center;align-items:center;gap:7px;min-height:42px;border:1px solid var(--g-line);border-radius:11px;font:inherit;font-size:13px;cursor:pointer;padding:9px 11px}.g-buttons .g-water,.g-button.primary{background:var(--g-button);color:white;border-color:var(--g-button)}.g-health,.g-button{background:var(--g-paper);color:inherit}.g-buttons button:disabled,.g-button:disabled{opacity:.5;cursor:wait}button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid var(--g-focus);outline-offset:3px}.g-warning{font-size:12px;color:var(--g-warning);margin-top:9px;line-height:1.5}.g-footnote{font-size:12px;color:var(--g-muted);line-height:1.65;margin:23px 0}.g-empty{padding:45px 20px;text-align:center;color:var(--g-muted)}
 .g-compact .g-picture{height:110px}.g-compact .g-body{padding:12px}.g-compact .g-count{margin:12px 0}.g-compact .g-count strong{font-size:21px}.g-compact .g-details,.g-compact .g-last,.g-compact .g-small{display:none}.g-compact .g-name{font-size:16px}.g-compact .g-buttons{margin-top:12px}.g-compact .g-buttons button{font-size:12px;padding:7px;min-height:38px}
 .g-overlay{position:fixed;inset:0;z-index:25;background:var(--g-overlay);display:flex;align-items:flex-start;justify-content:center;padding:28px 14px;overflow:auto}.g-dialog{background:var(--g-paper);color:var(--primary-text-color);width:min(100%,760px);border-radius:22px;box-shadow:0 20px 80px var(--g-shadow);overflow:hidden}.g-dialog-head{display:flex;align-items:center;gap:14px;border-bottom:1px solid var(--g-line);padding:18px 22px}.g-dialog-head h2{font-size:20px;margin:0;font-weight:500}.g-dialog-body{padding:22px;line-height:1.6;font-size:14px}.g-dialog-body h3{font-size:15px;margin:24px 0 8px}.g-dialog-body p{margin:0 0 13px}.g-dialog-body .g-preview{max-height:240px;max-width:100%;border-radius:12px;display:block;margin:14px 0}.g-actions{display:flex;flex-wrap:wrap;gap:9px;margin:16px 0}.g-status{padding:12px 14px;background:var(--g-soft);color:var(--primary-text-color);border-radius:12px;font-size:13px}.g-result{border-top:1px solid var(--g-line);padding:14px 0}.g-result b{font-weight:500}.g-result a{color:var(--g-leaf)}.g-error{color:var(--error-color,#b84435);font-size:13px}.g-dialog code{display:block;white-space:pre-wrap;padding:13px;background:var(--g-soft);border-radius:10px;font-size:12px}.g-dialog label.g-button{cursor:pointer}.g-dialog .g-checkbox{display:flex;gap:10px;font-size:13px;margin-top:12px;align-items:flex-start}.g-checkbox input{margin-top:5px}.g-notice{font-size:12px;color:var(--g-muted)}
 :host([data-garden-dark]){--g-soft:var(--plant-manager-soft,#293c32);--g-leaf:var(--plant-manager-leaf,#91bda0);--g-button:var(--plant-manager-button,#35624b);--g-warning:var(--plant-manager-warning,#e3b778)}@media(max-width:600px){.g-grid{gap:14px}.g-heading{padding-top:12px;gap:10px}.g-heading>.g-icon{width:56px;height:56px;padding:13px}.g-summary{gap:6px;margin-bottom:16px}.g-summary span{padding:8px 10px;font-size:12px}.g-overlay{padding:10px}.g-dialog-body{padding:17px}.g-picture{height:210px}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
`;
