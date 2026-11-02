const {escapeHTML:e,icon,plantName,plantTile,countdown,GARDEN_STYLES,updateCountdowns,applyGardenTheme}=await import(`./garden-common.js${new URL(import.meta.url).search}`);

class PlantEinzelkarte extends HTMLElement {
 constructor(){super();this.attachShadow({mode:'open'});this.shadowRoot.addEventListener('click',ev=>this._click(ev));}
 static getStubConfig(){return {plant_id:'',compact:false};}
 static getConfigElement(){return document.createElement('plant-einzelkarte-editor');}
 setConfig(config){if(!config)throw Error('Bitte eine Pflanze auswählen.');this._config={compact:false,...config};if(this._hass)this._load();this._render();}
 set hass(h){this._hass=h;applyGardenTheme(this,h);if(this._config&&this.isConnected)this._start();}
 getCardSize(){return this._config?.compact?3:6;}
 getGridOptions(){return {columns:this._config?.compact?6:12,rows:'auto',min_columns:4};}
 connectedCallback(){if(this._hass)this._start();this._clock??=setInterval(()=>updateCountdowns(this.shadowRoot),30000);}
 disconnectedCallback(){this._unsub?.then(f=>f()).catch(()=>{});this._unsub=null;clearInterval(this._clock);this._clock=null;clearTimeout(this._toastTimer);}
 async _start(){if(!this._config||this._starting||this._unsub)return;this._starting=true;try{await this._load();if(!this.isConnected)return;this._unsub=this._hass.connection.subscribeMessage(msg=>{if(msg.type==='updated')this._load();},{type:'plant_manager/subscribe'});this._unsub.catch(()=>{this._unsub=null;});}finally{this._starting=false;}}
 async _load(){if(!this._hass||!this._config?.plant_id){this._render();return;}const id=this._config.plant_id;try{const p=await this._hass.callWS({type:'plant_manager/plants/get',plant_id:id,language:'de'});if(this._config.plant_id!==id)return;this._plant=p;this._error=null;}catch(err){this._error=err.message||'Pflanze nicht erreichbar';}this._render();}
 _open(check=false){const p=this._config?.plant_id;if(!p)return;history.pushState(null,'',`/plant-manager/plants?plant=${encodeURIComponent(p)}${check?'&check=1':''}`);window.dispatchEvent(new CustomEvent('location-changed',{detail:{replace:false}}));}
 async _click(ev){const el=ev.target.closest('[data-action]');if(!el)return;const a=el.dataset.action;if(a==='open-plant'){this._open();return;}if(a==='health-open'){this._open(true);return;}if(a==='water'||a==='undo'){
   if(this._busy)return;this._busy=true;this._render();try{
    if(a==='water'){const r=await this._hass.callWS({type:'plant_manager/plants/water',plant_id:this._config.plant_id,language:'de'});this._undoId=r.undo_id;this._notice='Gießen gespeichert. Der Countdown wurde neu berechnet.';clearTimeout(this._toastTimer);this._toastTimer=setTimeout(()=>{this._undoId=null;this._notice='';this._render();},10000);}
    else{const r=await this._hass.callWS({type:'plant_manager/undo',undo_id:this._undoId,language:'de'});if(!r.undone)throw Error('Der Eintrag konnte nicht mehr rückgängig gemacht werden.');this._undoId=null;this._notice='Test oder Fehleingabe rückgängig gemacht.';}
    await this._load();
   }catch(err){this._error=err.message;}finally{this._busy=false;this._render();}
 }}
 _render(){if(!this._config||!this.shadowRoot)return;const p=this._plant,area=this._hass?.areas?.[p?.area_id]?.name||'';let body=this._error?`<p class="g-error">${e(this._error)}</p>`:!this._config.plant_id?'<div class="g-empty">Bitte im Karteneditor eine Pflanze auswählen.</div>':!p?'<div class="g-empty">Pflanze wird geladen …</div>':plantTile(p,area,this._config.compact,this._busy);
  if(this._config.marker&&p){body=`<div class="g-marker ${p.care?.needs_water?'g-marker-due':''}"><button data-action="open-plant" aria-label="${e(plantName(p))}: Details öffnen">${icon('leaf')}<span><b>${e(plantName(p))}</b><small data-garden-until="${e(p.care?.next_watering||'')}" data-due="${!!p.care?.needs_water}">${countdown(p.care)}</small></span></button><button data-action="water" title="Jetzt gegossen" aria-label="${e(plantName(p))}: Jetzt gegossen" ${this._busy?'disabled':''}>${icon('drop')}</button></div>`;}
  this.shadowRoot.innerHTML=`<style>${GARDEN_STYLES}:host{display:block}ha-card{background:transparent;box-shadow:none;border:0}.g-note{font-size:12px;padding:10px;color:var(--g-muted);line-height:1.5}.g-note button{background:none;border:0;text-decoration:underline;color:inherit;cursor:pointer;font:inherit}.g-marker{display:flex;align-items:stretch;background:var(--g-paper);color:var(--primary-text-color);border:1px solid var(--g-line);box-shadow:0 3px 15px var(--g-shadow);border-radius:13px;overflow:hidden}.g-marker-due{border-color:var(--g-due)}.g-marker button{display:flex;align-items:center;gap:8px;padding:9px;background:none;color:inherit;border:0;cursor:pointer;font:inherit}.g-marker button:first-child{flex:1;text-align:left}.g-marker button:last-child{background:var(--g-soft);min-width:39px;justify-content:center}.g-marker span{min-width:0}.g-marker b{font-size:12px;display:block;font-weight:500}.g-marker small{font-size:11px;color:var(--g-muted);display:block;margin-top:3px}.g-marker .g-icon{width:18px;height:18px}</style><ha-card>${body}${this._notice?`<div class="g-note" role="status">${e(this._notice)} ${this._undoId?'<button data-action="undo">Rückgängig</button>':''}</div>`:''}</ha-card>`;
 }
}

class PlantEinzelkarteEditor extends HTMLElement {
 setConfig(c){this._config=c;this._render();}
 set hass(h){this._hass=h;if(!this._requested){this._requested=true;h.callWS({type:'plant_manager/plants/list',language:'de'}).then(p=>{this._plants=p;this._render();}).catch(()=>{this._plants=[];this._render();});}this._render();}
 _render(){if(!this._hass||!this._config)return;if(!this._form){this._form=document.createElement('ha-form');this._form.computeLabel=s=>({plant_id:'Pflanze',compact:'Kompakte Karte'}[s.name]||s.name);this._form.addEventListener('value-changed',ev=>{this._config={...this._config,...ev.detail.value};this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this._config},bubbles:true,composed:true}));});this.append(this._form);}this._form.hass=this._hass;this._form.schema=[{name:'plant_id',required:true,selector:{select:{options:(this._plants||[]).map(p=>({value:p.id,label:plantName(p)+' · '+(this._hass.areas?.[p.area_id]?.name||'Raum offen')})),mode:'dropdown'}}},{name:'compact',selector:{boolean:{}}}];this._form.data=this._config;}
}
class PlantGrundrisspunkt extends PlantEinzelkarte {setConfig(c){super.setConfig({...c,marker:true,compact:true});}}

export function registerGardenCards(){
 if(!customElements.get('plant-einzelkarte'))customElements.define('plant-einzelkarte',PlantEinzelkarte);
 if(!customElements.get('plant-einzelkarte-editor'))customElements.define('plant-einzelkarte-editor',PlantEinzelkarteEditor);
 if(!customElements.get('plant-grundrisspunkt'))customElements.define('plant-grundrisspunkt',PlantGrundrisspunkt);
 window.customCards=window.customCards||[];
 if(!window.customCards.some(c=>c.type==='plant-einzelkarte'))window.customCards.push({type:'plant-einzelkarte',name:'Pflanze · Einzelkarte',description:'Foto, Countdown, Gießbestätigung und Fotoprüfung einer Pflanze.',preview:true});
}
