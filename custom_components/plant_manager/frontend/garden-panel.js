const {escapeHTML:e, icon, plantName, plantTile, countdown, dateText, GARDEN_STYLES, updateCountdowns} = await import(`./garden-common.js${new URL(import.meta.url).search}`);

const PANEL_STYLES = `
 :host{--pm-leaf:var(--g-button);--pm-accent:var(--g-button);--pm-water:var(--g-button);--pm-radius:18px;background:var(--primary-background-color,#f5f7f2)}
 main{max-width:1360px;padding:12px 28px 35px}.toolbar{background:var(--g-paper);color:var(--primary-text-color);border-bottom:1px solid var(--g-line);padding:12px 24px;gap:18px}.toolbar h1{font-weight:500;font-size:18px}.tab{font-size:13px;padding:9px 12px}.tab.active{background:var(--g-soft);color:var(--g-leaf);border-radius:10px;box-shadow:none}.filters{gap:9px;margin-bottom:22px}.filters input,.filters select{border-radius:11px;font-size:13px;padding:11px 12px}.filters .btn{font-size:12px;border-radius:11px;min-height:41px}.filters .primary{background:var(--g-button);color:white}.section{border-radius:17px}.dialog{border-radius:20px}.dialog-head{background:var(--g-paper)}.btn{min-height:38px}.facts .fact{padding:12px;border-radius:12px;background:var(--g-soft)}.g-detail-count{padding:17px;background:var(--g-soft);border-radius:14px;margin-bottom:15px}.g-detail-count strong{display:block;font-size:30px;line-height:1.4;font-weight:500}.g-plan-code{white-space:pre-wrap;font-size:11px;line-height:1.7;padding:12px;background:var(--g-soft);border-radius:10px}.narrow .g-grid{grid-template-columns:1fr}.narrow main{padding:12px 15px}.g-input-row{display:flex;gap:10px;align-items:center}
`;

function healthSuggestions(check) {
 const rows=check.candidates || [];
 if(!rows.length)return '<p>Kein auswertbarer Treffer. Eine Krankheit oder ein Befall ist damit weder bestätigt noch ausgeschlossen.</p>';
 const list=rows.map(c=>`<p>${e(c.label)}<br><span class="g-notice">Ähnlichkeitswert: ${Math.round(c.score*100)} % · keine Erkrankungswahrscheinlichkeit</span></p>`).join('');
 if(rows[0].score<0.5)return `<p>Keine belastbare Zuordnung: Die Bildähnlichkeiten sind niedrig. Für eine erneute Prüfung ein scharfes Detailfoto der auffälligen Stelle aufnehmen.</p><details><summary>Schwache Bildvorschläge anzeigen</summary>${list}</details>`;
 return `<p class="g-notice">Die Vorschläge müssen mit den sichtbaren Merkmalen verglichen werden. Sie bestätigen keine Krankheit.</p>${list}`;
}

export function installGardenPanel(Panel) {
 const proto=Panel.prototype;
 const shell=proto._renderShell, main=proto._renderMain, status=proto._editorStatus;
 const oldClick=proto._onClick, oldChange=proto._onChange, oldDisconnect=proto.disconnectedCallback, closeEditor=proto._closeEditor;
 proto._renderShell=function(){shell.call(this);const st=document.createElement('style');st.textContent=GARDEN_STYLES+PANEL_STYLES;this.shadowRoot.append(st);const mount=document.createElement('div');mount.id='garden-health';this.shadowRoot.append(mount);this._gardenOpenFromLocation();this._gardenClockStart();if(this._gardenHealth)this._renderHealth();};
 proto._renderMain=function(){main.call(this);updateCountdowns(this.shadowRoot);};
 proto._gardenClockStart=function(){if(!this._gardenClock)this._gardenClock=setInterval(()=>updateCountdowns(this.shadowRoot),30000);};
 const oldConnect=proto.connectedCallback;
 proto.connectedCallback=function(){oldConnect.call(this);this._gardenClockStart();};
 proto.disconnectedCallback=function(){oldDisconnect.call(this);clearInterval(this._gardenClock);this._gardenClock=null;this._gardenReleasePhoto();};
 proto._gardenOpenFromLocation=function(){const q=new URLSearchParams(location.search),id=q.get('plant'),key=id+':'+q.get('check');if(id && this._plantsById?.[id] && this._gardenRouteId!==key){this._gardenRouteId=key;if(q.get('check')==='1')this._openHealth(id);else this._openEditor(id);}};
 proto._closeEditor=function(){closeEditor.call(this);this._gardenRouteId=null;};
 proto._renderPlants=function(){
  const plants=this._filteredPlants(),areas=this._areas(),f=this._filter;
  const needs=this._plants.filter(p=>p.care?.needs_water).length;
  const next=this._plants.filter(p=>p.care?.next_watering).sort((a,b)=>a.care.next_watering.localeCompare(b.care.next_watering))[0];
  return `<header class="g-heading"><div><div class="g-kicker">Deine Pflanzen zu Hause</div><h2>Pflanzen im Blick</h2><p>Wann wurde gegossen, wann ist die nächste Prüfung fällig? Hier bleibt die Pflege jeder Pflanze nachvollziehbar.</p></div>${icon('leaf')}</header>
   <div class="g-summary"><span>${icon('leaf')}<b>${this._plants.length}</b> Pflanzen</span><span>${icon('drop')}<b>${needs}</b> Gießprüfungen fällig</span>${next?`<span>${icon('clock')}Nächster Termin: <b>${dateText(next.care.next_watering)}</b></span>`:''}</div>
   <div class="filters"><input type="search" placeholder="Name, Pflanzenart oder Raum suchen …" aria-label="Pflanzen suchen" value="${e(f.q)}" data-filter="q"><select data-filter="area" aria-label="Raum">${this._options(areas.map(a=>a.area_id),f.area,{empty:'Alle Räume',label:id=>this._areaName(id)})}</select><select data-filter="status" aria-label="Pflegestatus"><option value="" ${!f.status?'selected':''}>Alle Zustände</option><option value="attention" ${f.status==='attention'?'selected':''}>Pflegehinweise</option>${this._options(this._config.statuses,f.status)}</select><button class="btn primary" data-action="new-plant">+ Pflanze hinzufügen</button><button class="btn" data-action="toggle-data" aria-expanded="${this._showData}">Import / Export</button></div>
   ${this._showData?this._dataSection():''}<div class="g-grid">${plants.map(p=>plantTile(p,this._areaName(p.area_id),false,this._gardenBusy?.has(p.id))).join('')}</div>${!plants.length?'<div class="g-empty">Keine Pflanzen in dieser Auswahl.</div>':''}
   <p class="g-footnote">Der Countdown ist eine Pflegeerinnerung. Prüfe die Erde vor dem Gießen. Ohne Bodenfeuchtesensor ist der Wasservorrat geschätzt; Raumklima und Jahreszeit können den nächsten Termin verändern.</p>`;
 };
 proto._editorStatus=function(){
  const p=this._editor?.plant;if(!p?.care)return status.call(this);
  return `<div class="g-detail-count"><span class="g-caption">${icon('clock')} Bis zur nächsten Gießprüfung</span><strong data-garden-until="${e(p.care.next_watering)}" data-due="${!!p.care.needs_water}">${countdown(p.care)}</strong><span class="g-small">Voraussichtlich ${dateText(p.care.next_watering)}</span></div>`+status.call(this)+
   `<div class="section"><h2>${icon('bug')} Krankheiten und Befall</h2><p class="hint">Ein aktuelles Detailfoto kann Hinweise auf mögliche Ursachen geben. Eine Fotoprüfung ersetzt keine Diagnose.</p><button class="btn" data-action="health-open" data-id="${e(p.id)}">${icon('search')} Pflanze prüfen</button></div>
    <details class="section"><summary>Einzelkarte für den Grundriss</summary><p class="hint">Diese Karte verwendet den vorhandenen Gießstatus. Eine Bestätigung hier oder im Grundriss aktualisiert dieselbe Pflanze.</p><pre class="g-plan-code">type: custom:plant-einzelkarte\nplant_id: ${e(p.id)}\ncompact: true</pre></details>`;
 };
 proto._onClick=async function(ev){
  const el=ev.target.closest('[data-action]');if(!el)return oldClick.call(this,ev);
  const a=el.dataset.action;
  if(a==='health-open'){this._openHealth(el.dataset.id);return;}
  if(a==='health-close'){this._closeHealth();return;}
  if(a==='health-cover'){
   const h=this._gardenHealth,photo=this._plantsById?.[h?.id]?.photos?.[0];if(!h||!photo||h.busy)return;
   try{const r=await this._hass.fetchWithAuth(photo.url);if(!r.ok)throw Error('Das gespeicherte Foto konnte nicht geladen werden.');this._gardenReleasePhoto();h.file=await this._prepare(await r.blob());h.preview=URL.createObjectURL(h.file);h.error='';}catch(err){h.error=err.message;}this._renderHealth();return;
  }
  if(a==='health-run'){await this._runHealth();return;}
  if(a==='water'){
   this._gardenBusy??=new Set();if(this._gardenBusy.has(el.dataset.id))return;
   this._gardenBusy.add(el.dataset.id);el.disabled=true;
   try{await oldClick.call(this,ev);}finally{this._gardenBusy.delete(el.dataset.id);if(el.isConnected)el.disabled=false;}
   return;
  }
  return oldClick.call(this,ev);
 };
 proto._onChange=async function(ev){
  if(ev.target.matches('[data-health-file]')){
   const f=ev.target.files?.[0],h=this._gardenHealth;if(!f||!h)return;
   this._gardenReleasePhoto();h.file=await this._prepare(f);h.preview=URL.createObjectURL(h.file);h.error='';this._renderHealth();return;
  }
  return oldChange.call(this,ev);
 };
 proto._gardenReleasePhoto=function(){if(this._gardenHealth?.preview)URL.revokeObjectURL(this._gardenHealth.preview);};
 proto._closeHealth=function(){if(this._gardenHealth?.busy)return;this._gardenReleasePhoto();this._gardenHealth=null;this._gardenRouteId=null;this.shadowRoot.getElementById('garden-health')?.replaceChildren();};
 proto._openHealth=async function(id){
  this._gardenReleasePhoto();const h=this._gardenHealth={id,loading:true,file:null,checks:[]};this._renderHealth();
  try{const r=await this._hass.fetchWithAuth(`/api/plant_manager/health/${encodeURIComponent(id)}`);const d=await r.json();if(this._gardenHealth!==h)return;if(!r.ok)throw Error(d.message||'Die Prüfung ist gerade nicht verfügbar.');Object.assign(h,d);}catch(err){h.error=err.message;}finally{h.loading=false;if(this._gardenHealth===h)this._renderHealth();}
 };
 proto._runHealth=async function(){
  const h=this._gardenHealth;if(!h?.file||!h.ready||h.busy)return;
  h.busy=true;h.error='';this._renderHealth();
  try{const r=await this._post(`/api/plant_manager/health/${encodeURIComponent(h.id)}`,h.file);if(this._gardenHealth!==h)return;h.checks=[r,...h.checks];if(h.quota)h.quota.remaining=r.remaining;h.file=null;this._gardenReleasePhoto();h.preview=null;await this._load();this._renderMain();if(this._editor?.id===h.id)await this._refreshEditorPlant();}catch(err){h.error=err.message;}finally{h.busy=false;if(this._gardenHealth===h)this._renderHealth();}
 };
 proto._renderHealth=function(){
  const root=this.shadowRoot.getElementById('garden-health'),h=this._gardenHealth;if(!root||!h)return;
  const p=this._plantsById?.[h.id]||{name:'Pflanze'};
  root.innerHTML=`<div class="g-overlay"><section class="g-dialog" role="dialog" aria-modal="true" aria-labelledby="garden-health-title"><div class="g-dialog-head"><button class="g-button" data-action="health-close" aria-label="Fotoprüfung schließen" ${h.busy?'disabled':''}>✕</button><h2 id="garden-health-title">${icon('bug')} ${e(plantName(p))} prüfen</h2></div><div class="g-dialog-body">
   <p>Fotografiere auffällige Blätter, Blattunterseiten oder sichtbare Schädlinge möglichst nah und scharf. Das ausgewählte Foto wird erst mit „Kostenlos prüfen“ an Pl@ntNet gesendet und anschließend bei dieser Pflanze gespeichert.</p>
   <div class="g-status">${h.loading?'Kostenlosen Zugang prüfen …':h.ready?`Kostenloser Zugang bestätigt · ${e(h.quota.remaining)} von ${e(h.quota.total)} Erkennungen heute noch verfügbar. Pflanzen- und Befallerkennung teilen sich dieses Kontingent.`:e(h.message||h.error||'Kostenloser Zugang noch nicht bestätigt.')}</div>
   <p class="g-notice" style="margin-top:12px">Pl@ntNet erkennt bisher nur eine begrenzte Auswahl an Arten und Krankheiten. Ein Ergebnis ist ein Verdachtsvorschlag. Kein Treffer bedeutet nicht, dass die Pflanze gesund ist.</p>
   <div class="g-actions"><label class="g-button">${icon('photo')}Foto aufnehmen<input type="file" accept="image/*" capture="environment" data-health-file hidden ${h.busy?'disabled':''}></label><label class="g-button">Foto auswählen<input type="file" accept="image/*" data-health-file hidden ${h.busy?'disabled':''}></label>${p.photos?.[0]?`<button class="g-button" data-action="health-cover" ${h.busy?'disabled':''}>Gespeichertes Foto verwenden</button>`:''}</div>
   ${h.preview?`<img class="g-preview" src="${e(h.preview)}" alt="Ausgewähltes Foto für die Prüfung">`:''}
   <button class="g-button primary" data-action="health-run" ${!h.ready||!h.file||h.busy?'disabled':''}>${icon('search')}${h.busy?'Foto wird geprüft …':'Kostenlos prüfen'}</button>${h.error?`<p class="g-error" role="alert">${e(h.error)}</p>`:''}
   <h3>Bisherige Fotoprüfungen</h3>${h.checks.length?h.checks.map(check=>`<div class="g-result"><b>${dateText(check.checked_at)}</b><span class="g-notice"> · Pl@ntNet · Verdachtsvorschläge</span>${healthSuggestions(check)}</div>`).join(''):'<p class="g-notice">Noch keine Fotoprüfung gespeichert.</p>'}
   <p class="g-notice">Bildbasierte Erkennung durch Pl@ntNet · <a href="https://my.plantnet.org/" target="_blank" rel="noopener">Informationen zum Dienst</a></p></div></section></div>`;
 };
}
