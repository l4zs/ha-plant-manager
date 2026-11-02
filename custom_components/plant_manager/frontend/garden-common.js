// Shared presentation for the collection and individual floor-plan cards, and the language.

// Texts are written in English and looked up here, with {placeholders}.
const GERMAN = {
  "No date yet": "Noch kein Termin",
  "Check the soil now": "Jetzt Boden prüfen",
  "{d} day · {h} h": "{d} Tag · {h} Std.",
  "{d} days · {h} h": "{d} Tage · {h} Std.",
  "{h} h · {m} min": "{h} Std. · {m} Min.",
  "{m} min": "{m} Min.",
  "Not recorded yet": "Noch nicht erfasst",
  "Low light": "Wenig Licht",
  "Medium light": "Mittleres Licht",
  "Bright, no direct sun": "Hell, ohne direkte Sonne",
  "Direct sun": "Direkte Sonne",
  "Light not recorded": "Licht nicht erfasst",
  "{name}: open details": "{name}: Details öffnen",
  "Room not set": "Raum noch offen",
  "Watering check due": "Gießprüfung fällig",
  "Until the next watering check": "Bis zur nächsten Gießprüfung",
  "Check the soil before watering": "Erde vor dem Gießen prüfen",
  "Expected {date}": "Voraussichtlich {date}",
  "Estimated water reserve {n} percent": "Geschätzter Wasservorrat {n} Prozent",
  "Soil: {n} %": "Boden: {n} %",
  "{n} % · estimated": "{n} % · geschätzt",
  "Last watered: {date}": "Zuletzt gegossen: {date}",
  "{n} care note · open details": "{n} Pflegehinweis · Details öffnen",
  "{n} care notes · open details": "{n} Pflegehinweise · Details öffnen",
  "Saving …": "Wird gespeichert …",
  "Watered now": "Jetzt gegossen",
  "Check a photo for diseases and pests": "Foto auf Krankheiten und Befall prüfen",
  "Check plant": "Pflanze prüfen",
  "Please choose a plant.": "Bitte eine Pflanze auswählen.",
  "Plant not reachable": "Pflanze nicht erreichbar",
  "Watering saved. The countdown was recalculated.": "Gießen gespeichert. Der Countdown wurde neu berechnet.",
  "The entry could not be undone anymore.": "Der Eintrag konnte nicht mehr rückgängig gemacht werden.",
  "Test or wrong entry undone.": "Test oder Fehleingabe rückgängig gemacht.",
  "Please choose a plant in the card editor.": "Bitte im Karteneditor eine Pflanze auswählen.",
  "Loading plant …": "Pflanze wird geladen …",
  "{name}: watered now": "{name}: Jetzt gegossen",
  "Undo": "Rückgängig",
  "Plant": "Pflanze",
  "Compact card": "Kompakte Karte",
  "No room": "Raum offen",
  "Your plants at home": "Deine Pflanzen zu Hause",
  "Plants at a glance": "Pflanzen im Blick",
  "Plants": "Pflanzen",
  "Watering checks due": "Gießprüfungen fällig",
  "Next date:": "Nächster Termin:",
  "Search name, species or room …": "Name, Pflanzenart oder Raum suchen …",
  "Search plants": "Pflanzen suchen",
  "Room": "Raum",
  "All rooms": "Alle Räume",
  "Care status": "Pflegestatus",
  "All states": "Alle Zustände",
  "Care notes": "Pflegehinweise",
  "+ Add plant": "+ Pflanze hinzufügen",
  "Import / Export": "Import / Export",
  "No plants in this selection.": "Keine Pflanzen in dieser Auswahl.",
  "The countdown is a care reminder. Check the soil before watering. Without a soil moisture sensor the water reserve is estimated; room climate and season can change the next date.": "Der Countdown ist eine Pflegeerinnerung. Prüfe die Erde vor dem Gießen. Ohne Bodenfeuchtesensor ist der Wasservorrat geschätzt; Raumklima und Jahreszeit können den nächsten Termin verändern.",
  "Diseases and pests": "Krankheiten und Befall",
  "A current close-up photo can give hints about possible causes. A photo check does not replace a diagnosis.": "Ein aktuelles Detailfoto kann Hinweise auf mögliche Ursachen geben. Eine Fotoprüfung ersetzt keine Diagnose.",
  "Single card for the floor plan": "Einzelkarte für den Grundriss",
  "This card uses the existing watering status. Confirming here or on the floor plan updates the same plant.": "Diese Karte verwendet den vorhandenen Gießstatus. Eine Bestätigung hier oder im Grundriss aktualisiert dieselbe Pflanze.",
  "The saved photo could not be loaded.": "Das gespeicherte Foto konnte nicht geladen werden.",
  "The check is not available right now.": "Die Prüfung ist gerade nicht verfügbar.",
  "No usable match. This neither confirms nor rules out a disease or pests.": "Kein auswertbarer Treffer. Eine Krankheit oder ein Befall ist damit weder bestätigt noch ausgeschlossen.",
  "Similarity: {n} % · not a probability of disease": "Ähnlichkeitswert: {n} % · keine Erkrankungswahrscheinlichkeit",
  "No reliable match: the image similarities are low. For another check, take a sharp close-up of the affected spot.": "Keine belastbare Zuordnung: Die Bildähnlichkeiten sind niedrig. Für eine erneute Prüfung ein scharfes Detailfoto der auffälligen Stelle aufnehmen.",
  "Show weak suggestions": "Schwache Bildvorschläge anzeigen",
  "Compare the suggestions with what you can see. They do not confirm a disease.": "Die Vorschläge müssen mit den sichtbaren Merkmalen verglichen werden. Sie bestätigen keine Krankheit.",
  "Close photo check": "Fotoprüfung schließen",
  "Check {name}": "{name} prüfen",
  "Take a photo of affected leaves, leaf undersides or visible pests, as close and sharp as you can. The chosen photo is only sent to Pl@ntNet with “Check for free”, and is then saved with this plant.": "Fotografiere auffällige Blätter, Blattunterseiten oder sichtbare Schädlinge möglichst nah und scharf. Das ausgewählte Foto wird erst mit „Kostenlos prüfen“ an Pl@ntNet gesendet und anschließend bei dieser Pflanze gespeichert.",
  "Checking free access …": "Kostenlosen Zugang prüfen …",
  "Free access confirmed · {remaining} of {total} identifications left today. Plant and pest identification share this quota.": "Kostenloser Zugang bestätigt · {remaining} von {total} Erkennungen heute noch verfügbar. Pflanzen- und Befallerkennung teilen sich dieses Kontingent.",
  "Free access not confirmed yet.": "Kostenloser Zugang noch nicht bestätigt.",
  "Pl@ntNet only recognizes a limited selection of species and diseases so far. A result is a suggestion. No match does not mean the plant is healthy.": "Pl@ntNet erkennt bisher nur eine begrenzte Auswahl an Arten und Krankheiten. Ein Ergebnis ist ein Verdachtsvorschlag. Kein Treffer bedeutet nicht, dass die Pflanze gesund ist.",
  "Take photo": "Foto aufnehmen",
  "Choose photo": "Foto auswählen",
  "Use saved photo": "Gespeichertes Foto verwenden",
  "Chosen photo for the check": "Ausgewähltes Foto für die Prüfung",
  "Checking photo …": "Foto wird geprüft …",
  "Check for free": "Kostenlos prüfen",
  "Previous photo checks": "Bisherige Fotoprüfungen",
  "suggestions": "Verdachtsvorschläge",
  "No photo check saved yet.": "Noch keine Fotoprüfung gespeichert.",
  "Image-based identification by Pl@ntNet": "Bildbasierte Erkennung durch Pl@ntNet",
  "About the service": "Informationen zum Dienst",
};

let fixedLanguage = null; // the language set for this whole Home Assistant, if any
let settingLoad = null;
let LANG = 'en';
let LOCALE = 'en';

// The user's language from their Home Assistant profile ("de", "de-CH", ...), unless fixed.
export function languageOf(hass) {
  if(fixedLanguage) return fixedLanguage;
  return String(hass?.locale?.language || hass?.language || 'en').toLowerCase().split('-')[0] === 'de' ? 'de' : 'en';
}
export const localeOf = hass => fixedLanguage || hass?.locale?.language || hass?.language || 'en';
const syncLanguage = hass => { LANG = languageOf(hass); LOCALE = localeOf(hass); };
// Asked once per page; the setting changes rarely, and the option's text says to refresh.
export function loadLanguageSetting(hass) {
  settingLoad ??= hass.callWS({type:'plant_manager/language'})
    .then(r => { fixedLanguage = r.fixed || null; })
    .catch(() => { settingLoad = null; });
  return settingLoad.then(() => syncLanguage(hass));
}
export const gardenLanguage = () => LANG;
export const gt = (text, values = {}) => (LANG === 'de' ? GERMAN[text] ?? text : text).replace(/\{(\w+)\}/g, (match, key) => key in values ? String(values[key]) : match);
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
  if(!care) return gt('No date yet');
  if(care.needs_water) return gt('Check the soil now');
  const end = Date.parse(care.next_watering);
  if(!Number.isFinite(end)) return gt('No date yet');
  const mins = Math.max(0, Math.ceil((end-now)/60000));
  if(!mins) return gt('Check the soil now');
  const d=Math.floor(mins/1440), h=Math.floor(mins%1440/60), m=mins%60;
  return d ? gt(d===1?'{d} day · {h} h':'{d} days · {h} h',{d,h}) : h ? gt('{h} h · {m} min',{h,m}) : gt('{m} min',{m});
}
export const dateText = iso => {
  const d = new Date(iso);
  return iso && Number.isFinite(+d) ? new Intl.DateTimeFormat(LOCALE,{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}).format(d) : gt('Not recorded yet');
};
export const lightText = key => gt({low:'Low light',medium:'Medium light',bright_indirect:'Bright, no direct sun',direct:'Direct sun'}[key] || 'Light not recorded');
export function updateCountdowns(root) {
  root.querySelectorAll('[data-garden-until]').forEach(el=>{
    el.textContent=countdown({next_watering:el.dataset.gardenUntil,needs_water:el.dataset.due==='true'});
  });
}
export function plantTile(p, area='', compact=false, busy=false) {
  const e=escapeHTML, c=p.care || {}, reserve=Math.max(0,Math.min(100,Number(c.water_reserve)||0));
  const problems=(c.problems||[]).filter(x=>x!=='watering_overdue');
  return `<article class="g-plant ${compact?'g-compact':''} ${c.needs_water?'g-due':''}">
    <button class="g-picture" data-action="open-plant" data-id="${e(p.id)}" aria-label="${e(gt('{name}: open details',{name:plantName(p)}))}">${p.photos?.[0]?`<img src="${e(p.photos[0].url)}" alt="${e(plantName(p))}" loading="lazy">`:icon('leaf')}
      <span class="g-room">${icon('pin')}${e(area || gt('Room not set'))}</span>
    </button>
    <div class="g-body"><button class="g-name" data-action="open-plant" data-id="${e(p.id)}">${e(plantName(p))}</button><div class="g-species">${e(p.species)}</div>
      <div class="g-count"><span class="g-caption">${icon('clock')} ${gt(c.needs_water?'Watering check due':'Until the next watering check')}</span><strong data-garden-until="${e(c.next_watering || '')}" data-due="${!!c.needs_water}">${countdown(p.care)}</strong><span class="g-small">${c.needs_water?gt('Check the soil before watering'):gt('Expected {date}',{date:dateText(c.next_watering)})}</span></div>
      <div class="g-reserve" aria-label="${gt('Estimated water reserve {n} percent',{n:Math.round(reserve)})}"><span style="width:${reserve}%"></span></div>
      <div class="g-details"><span>${icon('drop')} ${c.moisture!=null?gt('Soil: {n} %',{n:e(c.moisture)}):gt('{n} % · estimated',{n:Math.round(reserve)})}</span><span>${icon('sun')}${e(lightText(p.light))}</span></div>
      <div class="g-last">${gt('Last watered: {date}',{date:dateText(p.last_watered)})}</div>
      ${problems.length?`<div class="g-warning">${gt(problems.length===1?'{n} care note · open details':'{n} care notes · open details',{n:problems.length})}</div>`:''}
      <div class="g-buttons"><button class="g-water" data-action="water" data-id="${e(p.id)}" ${busy?'disabled':''}>${icon('check')}${gt(busy?'Saving …':'Watered now')}</button><button class="g-health" data-action="health-open" data-id="${e(p.id)}" title="${gt('Check a photo for diseases and pests')}">${icon('bug')}${gt('Check plant')}</button></div>
    </div></article>`;
}
export const syncGardenLanguage = syncLanguage;
export const GARDEN_STYLES = `
 :host{--g-leaf:var(--primary-color);--g-button:var(--primary-color);--g-on-button:var(--text-primary-color);--g-soft:color-mix(in srgb,var(--primary-color) 12%,var(--g-paper));--g-due:var(--warning-color);--g-warning:color-mix(in srgb,var(--warning-color) 65%,var(--primary-text-color));--g-focus:var(--accent-color);--g-bar:var(--primary-color);--g-label-bg:color-mix(in srgb,var(--g-paper) 93%,transparent);--g-label:var(--primary-text-color);--g-overlay:var(--mdc-dialog-scrim-color,rgba(0,0,0,.4));--g-shadow:rgba(0,0,0,.13);--g-shadow-soft:rgba(0,0,0,.06);--g-paper:var(--ha-card-background,var(--card-background-color));--g-muted:var(--secondary-text-color);--g-line:var(--divider-color);color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,Roboto,Arial,sans-serif)}
 *{box-sizing:border-box}.g-icon{width:20px;height:20px;flex:none;vertical-align:middle}.g-heading{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:26px 0 24px}.g-kicker{color:var(--g-leaf);font-size:12px;letter-spacing:.14em;text-transform:uppercase;margin-bottom:9px}.g-heading h2{font-size:clamp(26px,3vw,38px);font-weight:500;letter-spacing:-.03em;margin:0 0 9px}.g-heading p{margin:0;color:var(--g-muted);font-size:14px;max-width:570px;line-height:1.6}.g-heading>.g-icon{width:76px;height:76px;padding:18px;color:var(--g-leaf);background:var(--g-soft);border-radius:50%}.g-summary{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:24px}.g-summary span{display:flex;gap:8px;align-items:center;background:var(--g-paper);border:1px solid var(--g-line);padding:10px 14px;border-radius:12px;font-size:13px}.g-summary b{font-size:17px;color:var(--g-leaf)}
 .g-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,265px),1fr));gap:22px}.g-plant{background:var(--g-paper);border:1px solid var(--g-line);border-radius:21px;overflow:hidden;box-shadow:0 5px 18px var(--g-shadow-soft);min-width:0}.g-due{border-color:var(--g-due)}.g-picture{position:relative;width:100%;height:204px;padding:0;display:flex;align-items:center;justify-content:center;border:0;background:var(--g-soft);cursor:pointer;color:var(--g-leaf)}.g-picture>.g-icon{width:72px;height:72px}.g-picture img{width:100%;height:100%;object-fit:cover}.g-room{position:absolute;left:12px;bottom:12px;display:flex;align-items:center;gap:5px;border-radius:20px;background:var(--g-label-bg);color:var(--g-label);padding:5px 9px;font-size:11px}.g-room .g-icon{width:14px;height:14px}.g-body{padding:17px}.g-name{background:none;border:0;color:inherit;font:inherit;font-size:19px;font-weight:500;padding:0;text-align:left;cursor:pointer;line-height:1.3}.g-species{font-size:12px;color:var(--g-muted);font-style:italic;margin-top:4px;min-height:16px}.g-count{display:flex;flex-direction:column;gap:7px;margin:19px 0 14px}.g-caption{font-size:11px;color:var(--g-muted);display:flex;align-items:center;gap:6px}.g-caption .g-icon{width:15px;height:15px}.g-count strong{font-size:25px;font-weight:500;letter-spacing:-.04em;line-height:1.2;font-variant-numeric:tabular-nums}.g-small{font-size:11px;color:var(--g-muted)}.g-reserve{height:5px;background:var(--g-soft);border-radius:3px;overflow:hidden}.g-reserve span{display:block;height:100%;background:var(--g-bar);border-radius:3px}.g-details{display:flex;flex-wrap:wrap;gap:7px 14px;margin:12px 0;color:var(--g-muted);font-size:11px}.g-details>span{display:flex;align-items:center;gap:5px}.g-details .g-icon{width:15px;height:15px}.g-last{font-size:11px;color:var(--g-muted);line-height:1.6}.g-buttons{display:grid;grid-template-columns:1fr;gap:8px;margin-top:16px}.g-buttons button,.g-button{display:flex;justify-content:center;align-items:center;gap:7px;min-height:42px;border:1px solid var(--g-line);border-radius:11px;font:inherit;font-size:13px;cursor:pointer;padding:9px 11px}.g-buttons .g-water,.g-button.primary{background:var(--g-button);color:var(--g-on-button);border-color:var(--g-button)}.g-health,.g-button{background:var(--g-paper);color:inherit}.g-buttons button:disabled,.g-button:disabled{opacity:.5;cursor:wait}button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid var(--g-focus);outline-offset:3px}.g-warning{font-size:12px;color:var(--g-warning);margin-top:9px;line-height:1.5}.g-footnote{font-size:12px;color:var(--g-muted);line-height:1.65;margin:23px 0}.g-empty{padding:45px 20px;text-align:center;color:var(--g-muted)}
 .g-compact .g-picture{height:110px}.g-compact .g-body{padding:12px}.g-compact .g-count{margin:12px 0}.g-compact .g-count strong{font-size:21px}.g-compact .g-details,.g-compact .g-last,.g-compact .g-small{display:none}.g-compact .g-name{font-size:16px}.g-compact .g-buttons{margin-top:12px}.g-compact .g-buttons button{font-size:12px;padding:7px;min-height:38px}
 .g-overlay{position:fixed;inset:0;z-index:25;background:var(--g-overlay);display:flex;align-items:flex-start;justify-content:center;padding:28px 14px;overflow:auto}.g-dialog{background:var(--g-paper);color:var(--primary-text-color);width:min(100%,760px);border-radius:22px;box-shadow:0 20px 80px var(--g-shadow);overflow:hidden}.g-dialog-head{display:flex;align-items:center;gap:14px;border-bottom:1px solid var(--g-line);padding:18px 22px}.g-dialog-head h2{font-size:20px;margin:0;font-weight:500}.g-dialog-body{padding:22px;line-height:1.6;font-size:14px}.g-dialog-body h3{font-size:15px;margin:24px 0 8px}.g-dialog-body p{margin:0 0 13px}.g-dialog-body .g-preview{max-height:240px;max-width:100%;border-radius:12px;display:block;margin:14px 0}.g-actions{display:flex;flex-wrap:wrap;gap:9px;margin:16px 0}.g-status{padding:12px 14px;background:var(--g-soft);color:var(--primary-text-color);border-radius:12px;font-size:13px}.g-result{border-top:1px solid var(--g-line);padding:14px 0}.g-result b{font-weight:500}.g-result a{color:var(--g-leaf)}.g-error{color:var(--error-color);font-size:13px}.g-dialog code{display:block;white-space:pre-wrap;padding:13px;background:var(--g-soft);border-radius:10px;font-size:12px}.g-dialog label.g-button{cursor:pointer}.g-dialog .g-checkbox{display:flex;gap:10px;font-size:13px;margin-top:12px;align-items:flex-start}.g-checkbox input{margin-top:5px}.g-notice{font-size:12px;color:var(--g-muted)}
 @media(max-width:600px){.g-grid{gap:14px}.g-heading{padding-top:12px;gap:10px}.g-heading>.g-icon{width:56px;height:56px;padding:13px}.g-summary{gap:6px;margin-bottom:16px}.g-summary span{padding:8px 10px;font-size:12px}.g-overlay{padding:10px}.g-dialog-body{padding:17px}.g-picture{height:210px}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
`;
