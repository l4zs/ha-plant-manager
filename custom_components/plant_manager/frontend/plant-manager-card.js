// Loaded under this file's own ?v=<version>, so that a new release is never mixed with cached files.
const MODULE_QUERY = new URL(import.meta.url).search;
const {registerGardenCards} = await import(`./garden-cards.js${MODULE_QUERY}`);
const {languageOf, localeOf, loadLanguageSetting} = await import(`./garden-common.js${MODULE_QUERY}`);
// Plant Manager Lovelace card: plants that need water, with a quick "watered" button.

const CARD_DOMAIN = "plant_manager";

// Texts are written in English and looked up here, with {placeholders}.
const CARD_GERMAN = {
  Plants: "Pflanzen",
  "Overdue by {n} day": "Seit {n} Tag überfällig",
  "Overdue by {n} days": "Seit {n} Tagen überfällig",
  "Needs water": "Braucht Wasser",
  Fertilize: "Düngen",
  "Water {when}": "Gießen {when}",
  "Plant Manager is not available: {error}": "Plant Manager ist nicht verfügbar: {error}",
  "Loading…": "Lädt…",
  Watered: "Jetzt gegossen",
  "🌿 All plants are happy.": "Aktuell keine Gießprüfung fällig.",
  "Need water": "Brauchen Wasser",
  Problems: "Probleme",
  Title: "Titel",
  "Show counts (plants, need water, problems)": "Zahlen anzeigen (Pflanzen, brauchen Wasser, Probleme)",
};
const CARD_TRANSLATIONS = { de: CARD_GERMAN };

// The user's language from their Home Assistant profile ("de", "de-CH", ...).
const cardLanguage = (hass) => languageOf(hass);

const cardT = (hass, text, values = {}) =>
  (CARD_TRANSLATIONS[cardLanguage(hass)]?.[text] ?? text).replace(/\{(\w+)\}/g, (match, key) =>
    key in values ? String(values[key]) : match
  );

const cardEsc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );

function cardDue(hass, care) {
  if (!care) return "";
  if (care.needs_water) {
    const late = Math.round((care.dryness - 1) * care.interval_days);
    if (late >= 1) return cardT(hass, late === 1 ? "Overdue by {n} day" : "Overdue by {n} days", { n: late });
    return cardT(hass, "Needs water");
  }
  if (care.fertilize_due && care.status === "ok") return cardT(hass, "Fertilize");
  const days = Math.round(
    (new Date(care.next_watering).setHours(0, 0, 0, 0) - new Date().setHours(0, 0, 0, 0)) / 86400000
  );
  const when = new Intl.RelativeTimeFormat(localeOf(hass), { numeric: "auto" }).format(days, "day");
  return cardT(hass, "Water {when}", { when });
}

class PlantManagerCard extends HTMLElement {
  static getStubConfig() {
    return { show_counts: true };
  }

  static getConfigElement() {
    return document.createElement("plant-manager-card-editor");
  }

  setConfig(config) {
    // Without a title of its own the card is called "Plants" in the user's language.
    this._config = { show_counts: true, ...config };
    this._render();
  }

  set hass(hass) {
    const first = !this._hass;
    const changed = cardLanguage(hass) !== cardLanguage(this._hass);
    this._hass = hass;
    if (first) this._start();
    else if (changed) this._render();
  }

  getCardSize() {
    return 3;
  }

  connectedCallback() {
    if (this._hass && !this._unsub) this._start();
  }

  disconnectedCallback() {
    if (this._unsub) this._unsub.then((unsub) => unsub()).catch(() => {});
    this._unsub = null;
  }

  async _start() {
    if (!this.isConnected) return;
    await loadLanguageSetting(this._hass);
    await this._load();
    this._unsub = this._hass.connection.subscribeMessage(
      (message) => {
        if (message.type !== "updated") return;
        clearTimeout(this._timer);
        this._timer = setTimeout(() => this._load(), 300);
      },
      { type: `${CARD_DOMAIN}/subscribe` }
    );
    this._unsub.catch(() => {
      this._unsub = null;
    });
  }

  async _load() {
    try {
      this._summary = await this._hass.callWS({ type: `${CARD_DOMAIN}/summary`, language: cardLanguage(this._hass) });
      this._error = null;
    } catch (err) {
      this._error = err.message || String(err);
    }
    this._render();
  }

  _open(path) {
    history.pushState(null, "", path);
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
  }

  async _water(plantId) {
    try {
      await this._hass.callWS({ type: `${CARD_DOMAIN}/plants/water`, plant_id: plantId });
    } catch (err) {
      this._error = err.message || String(err);
      this._render();
    }
  }

  _render() {
    if (!this._config) return;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (ev) => {
        const water = ev.target.closest("[data-water]");
        if (water) {
          this._water(water.dataset.water);
          return;
        }
        const el = ev.target.closest("[data-open]");
        if (el) this._open(el.dataset.open);
      });
    }
    const summary = this._summary;
    let body;
    if (this._error) {
      body = `<div class="empty">${cardEsc(cardT(this._hass, "Plant Manager is not available: {error}", { error: this._error }))}</div>`;
    } else if (!summary) {
      body = `<div class="empty">${cardT(this._hass, "Loading…")}</div>`;
    } else {
      const list = summary.attention.length
        ? `<div class="list">${summary.attention
            .map((plant) => {
              const photo = plant.photos?.[0];
              const care = plant.care;
              return `
                <div class="row">
                  <div class="thumb" data-open="/plant-manager/plants">${photo ? `<img src="${cardEsc(photo.url)}" alt="">` : "🪴"}</div>
                  <div class="grow">
                    <div class="name">${cardEsc(plant.display_name || plant.name)}</div>
                    <div class="meta ${care.needs_water ? "late" : ""}">${cardEsc(cardDue(this._hass, care))}</div>
                  </div>
                  ${care.needs_water || care.status === "water_soon" ? `<button class="water" data-water="${plant.id}" title="${cardT(this._hass, "Watered")}">💧</button>` : ""}
                </div>`;
            })
            .join("")}</div>`
        : `<div class="empty">${cardT(this._hass, "🌿 All plants are happy.")}</div>`;
      const counts = this._config.show_counts
        ? `<div class="counts">
            <button data-open="/plant-manager/plants"><span>${summary.total}</span>${cardT(this._hass, "Plants")}</button>
            <button data-open="/plant-manager/today" class="${summary.needs_water ? "warn" : ""}"><span>${summary.needs_water}</span>${cardT(this._hass, "Need water")}</button>
            <button data-open="/plant-manager/today" class="${summary.problems ? "warn" : ""}"><span>${summary.problems}</span>${cardT(this._hass, "Problems")}</button>
          </div>`
        : "";
      body = list + counts;
    }
    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 16px; }
        .title { font-size: 20px; margin-bottom: 12px; cursor: pointer; }
        .list { display: flex; flex-direction: column; gap: 8px; }
        .row { display: flex; align-items: center; gap: 12px; }
        .thumb { width: 44px; height: 44px; border-radius: 8px; overflow: hidden; flex: none; cursor: pointer;
          display: flex; align-items: center; justify-content: center; font-size: 22px;
          background: color-mix(in srgb, var(--primary-color) 15%, transparent); }
        .thumb img { width: 100%; height: 100%; object-fit: cover; }
        .grow { flex: 1; min-width: 0; }
        .name { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .meta { font-size: 13px; color: var(--secondary-text-color); }
        .meta.late { color: var(--error-color); }
        .water { border: none; border-radius: 50%; width: 40px; height: 40px; cursor: pointer; font-size: 18px;
          background: var(--primary-color); color: var(--text-primary-color); }
        .empty { color: var(--secondary-text-color); padding: 8px 0; }
        .counts { display: flex; gap: 8px; margin-top: 16px; }
        .counts button { flex: 1; background: var(--secondary-background-color); border: none; border-radius: 8px;
          padding: 8px 4px; cursor: pointer; color: var(--primary-text-color); font: inherit; font-size: 12px;
          display: flex; flex-direction: column; align-items: center; }
        .counts span { font-size: 20px; font-weight: 500; }
        .counts .warn span { color: var(--error-color); }
      </style>
      <ha-card>
        <div class="title" data-open="/plant-manager/today">${cardEsc(this._config.title || cardT(this._hass, "Plants"))}</div>
        ${body}
      </ha-card>`;
  }
}

// Visual editor in the dashboard, built on Home Assistant's own form component.
const EDITOR_SCHEMA = [
  { name: "title", selector: { text: {} } },
  { name: "show_counts", selector: { boolean: {} } },
];
const EDITOR_LABELS = {
  title: "Title",
  show_counts: "Show counts (plants, need water, problems)",
};

class PlantManagerCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    const changed = this._form && cardLanguage(hass) !== cardLanguage(this._hass);
    if (!this._hass) loadLanguageSetting(hass).then(() => this._render());
    this._hass = hass;
    if (this._form) this._form.hass = hass;
    if (changed) this._render();
  }

  _render() {
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) =>
        EDITOR_LABELS[schema.name] ? cardT(this._hass, EDITOR_LABELS[schema.name]) : schema.name;
      this._form.addEventListener("value-changed", (ev) => {
        this._config = ev.detail.value;
        this.dispatchEvent(
          new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = EDITOR_SCHEMA;
    this._form.data = { show_counts: true, ...this._config };
  }
}

customElements.define("plant-manager-card", PlantManagerCard);
customElements.define("plant-manager-card-editor", PlantManagerCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "plant-manager-card",
  name: "Plant Manager",
  description: "Plants that need water, with a quick watered button.",
  preview: true,
});

registerGardenCards();
