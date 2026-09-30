// App web CarpoX : comptes, voitures, soldes, saisie des pleins et liaison
// Bluetooth avec le boîtier. Pas de framework ni d'étape de compilation.

"use strict";

const view = document.getElementById("view");
const state = { token: null, me: null, config: null, link: new BoxLink(), linkDevice: null };

try { state.token = localStorage.getItem("carpox_token"); } catch { /* stockage indisponible */ }

// --- utilitaires -------------------------------------------------------------

// Construit un élément sans jamais interpréter de HTML (pas d'injection possible).
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (key === "class") node.className = value;
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

function render(...nodes) {
  // Même règles que el() : listes aplaties, valeurs vides ignorées.
  view.replaceChildren(...nodes.flat(Infinity).filter((n) => n !== null && n !== undefined && n !== false));
}

function toast(message) {
  const t = document.getElementById("toast");
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, 4000);
}

function euros(cents) {
  return (cents / 100).toLocaleString("fr-BE", { style: "currency", currency: "EUR" });
}

function parseEuros(text) {
  const value = Number(String(text).replace(/\s/g, "").replace(",", "."));
  if (!Number.isFinite(value) || value <= 0) throw new Error("Montant invalide");
  return Math.round(value * 100);
}

function number(text) {
  if (text === undefined || text === null || String(text).trim() === "") return null;
  const value = Number(String(text).replace(/\s/g, "").replace(",", "."));
  if (!Number.isFinite(value)) throw new Error("Nombre invalide : " + text);
  return value;
}

function dateTime(unix) {
  return unix ? new Date(unix * 1000).toLocaleString("fr-BE", { dateStyle: "short", timeStyle: "short" }) : "?";
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

async function api(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers.Authorization = "Bearer " + state.token;
  const res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  if (res.status === 401 && state.token && !path.startsWith("/api/auth/")) {
    setToken(null);
    location.hash = "#login";
    throw new Error("Session expirée, reconnectez-vous.");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let detail = data.detail;
    if (Array.isArray(detail)) detail = "Données invalides : " + detail.map((d) => d.loc.slice(-1)[0]).join(", ");
    throw new Error(detail || "Erreur " + res.status);
  }
  return data;
}

function setToken(token) {
  state.token = token;
  state.me = null;
  try {
    if (token) localStorage.setItem("carpox_token", token);
    else localStorage.removeItem("carpox_token");
  } catch { /* ignoré */ }
}

// Exécute une action de formulaire en affichant l'erreur éventuelle.
function guarded(fn) {
  return async (event) => {
    if (event) event.preventDefault();
    const button = event && event.submitter;
    if (button) button.disabled = true;
    try { await fn(event); } catch (err) { toast(err.message); } finally { if (button) button.disabled = false; }
  };
}

// --- routage ------------------------------------------------------------------

async function route() {
  const [page, id, tab, sub] = location.hash.slice(1).split("/");
  document.getElementById("nav").hidden = !state.token;
  if (!state.token) return viewLogin();
  try {
    if (!state.me) state.me = await api("GET", "/api/me");
    if (!state.config) state.config = await api("GET", "/api/config");
    if (page === "car" && id) return await viewCar(id, tab || "soldes", sub);
    if (page === "account") return await viewAccount();
    return await viewCars();
  } catch (err) {
    render(el("p", {}, err.message));
  }
}

window.addEventListener("hashchange", route);
route();

// --- connexion ----------------------------------------------------------------

function viewLogin() {
  let mode = "login";
  const draw = () => {
    const isRegister = mode === "register";
    render(
      el("h1", {}, isRegister ? "Créer un compte" : "Connexion"),
      el("form", { class: "card", onsubmit: guarded(submit) },
        isRegister && [el("label", { for: "display_name" }, "Prénom affiché"),
          el("input", { id: "display_name", name: "display_name", required: true, maxlength: 32, autocomplete: "nickname" })],
        el("label", { for: "username" }, "Nom d'utilisateur"),
        el("input", { id: "username", name: "username", required: true, autocomplete: "username", autocapitalize: "none" }),
        el("label", { for: "password" }, "Mot de passe"),
        el("input", { id: "password", name: "password", type: "password", required: true,
          minlength: isRegister ? 10 : null, autocomplete: isRegister ? "new-password" : "current-password" }),
        isRegister && el("p", { class: "muted" }, "Au moins 10 caractères. Une phrase de passe est idéale."),
        isRegister && [el("label", { for: "invite_code" }, "Code d'invitation (si le serveur en demande un)"),
          el("input", { id: "invite_code", name: "invite_code", autocomplete: "off" })],
        el("button", { type: "submit" }, isRegister ? "Créer le compte" : "Se connecter")),
      el("button", { class: "secondary", onclick: () => { mode = isRegister ? "login" : "register"; draw(); } },
        isRegister ? "J'ai déjà un compte" : "Créer un compte"));
  };
  const submit = async (event) => {
    const data = formData(event.target);
    if (!data.invite_code) delete data.invite_code;
    const res = await api("POST", mode === "register" ? "/api/auth/register" : "/api/auth/login", data);
    setToken(res.token);
    location.hash = "#cars";
    route();
  };
  draw();
}

async function viewAccount() {
  const tokens = await api("GET", "/api/me/tokens");
  const newToken = el("div");
  render(
    el("h1", {}, "Mon compte"),
    el("div", { class: "card" }, el("p", {}, state.me.display_name, " ", el("span", { class: "muted" }, "(" + state.me.username + ")"))),
    el("form", { class: "card", onsubmit: guarded(async (e) => {
      const data = formData(e.target);
      await api("POST", "/api/me/password", data);
      e.target.reset();
      toast("Mot de passe changé. Vos autres appareils ont été déconnectés.");
    }) },
      el("h2", {}, "Changer de mot de passe"),
      el("label", { for: "old" }, "Mot de passe actuel"),
      el("input", { id: "old", name: "old_password", type: "password", required: true, autocomplete: "current-password" }),
      el("label", { for: "new" }, "Nouveau mot de passe"),
      el("input", { id: "new", name: "new_password", type: "password", required: true, minlength: 10, autocomplete: "new-password" }),
      el("button", { type: "submit" }, "Changer")),
    el("div", { class: "card" },
      el("h2", {}, "Home Assistant et autres applications"),
      el("p", { class: "muted" }, "Un jeton personnel permet à Home Assistant de lire vos voitures, vos km et vos soldes. Il ne peut rien modifier. Il n'expire pas : révoquez-le quand il ne sert plus."),
      tokens.length === 0 && el("p", { class: "muted" }, "Aucun jeton pour l'instant."),
      tokens.map((t) => el("div", { class: "row" },
        el("span", {}, t.name, el("br"), el("span", { class: "muted" },
          "créé le " + dateTime(t.created_at) + " · " + (t.last_used_at ? "utilisé le " + dateTime(t.last_used_at) : "jamais utilisé"))),
        el("button", { class: "small secondary", onclick: guarded(async () => {
          if (!confirm(`Révoquer « ${t.name} » ? Ce qui l'utilise cessera de fonctionner.`)) return;
          await api("DELETE", `/api/me/tokens/${t.id}`);
          route();
        }) }, "Révoquer"))),
      el("form", { onsubmit: guarded(async (e) => {
        const t = await api("POST", "/api/me/tokens", formData(e.target));
        e.target.reset();
        newToken.replaceChildren(
          el("p", {}, el("strong", {}, "Copiez ce jeton maintenant : il ne sera plus affiché."),
            " Dans Home Assistant : Paramètres > Appareils et services > Ajouter une intégration > CarpoX, avec l'adresse ", el("strong", {}, location.origin), "."),
          el("pre", { class: "secret" }, t.token),
          el("button", { onclick: () => navigator.clipboard.writeText(t.token).then(() => toast("Copié")) }, "Copier"),
          el("button", { class: "secondary", onclick: () => route() }, "C'est noté"));
      }) },
        el("label", { for: "t-name" }, "Nom du jeton"),
        el("input", { id: "t-name", name: "name", required: true, maxlength: 40, placeholder: "Home Assistant maison" }),
        el("button", { type: "submit" }, "Créer un jeton")),
      newToken),
    el("button", { class: "secondary", onclick: guarded(async () => {
      await api("POST", "/api/auth/logout").catch(() => {});
      setToken(null);
      location.hash = "#login";
      route();
    }) }, "Se déconnecter"));
}

// --- voitures -----------------------------------------------------------------

async function viewCars() {
  const devices = await api("GET", "/api/devices");
  render(
    el("h1", {}, "Mes voitures"),
    devices.length === 0 && el("p", { class: "muted" }, "Aucune voiture. Ajoutez votre boîtier ci-dessous, ou demandez au propriétaire de vous inviter avec votre nom d'utilisateur : " + state.me.username),
    devices.map((d) => el("a", { class: "card row", href: "#car/" + d.id },
      el("strong", {}, d.name),
      el("span", { class: "muted" }, d.last_sync_at ? "synchro " + new Date(d.last_sync_at * 1000).toLocaleString("fr-BE") : "jamais synchronisé"))),
    el("form", { class: "card", onsubmit: guarded(async (e) => {
      const d = await api("POST", "/api/devices", formData(e.target));
      viewNewDevice(d);
    }) },
      el("h2", {}, "Ajouter une voiture (boîtier)"),
      el("label", { for: "name" }, "Nom de la voiture"),
      el("input", { id: "name", name: "name", required: true, maxlength: 40, placeholder: "Golf de Loïc" }),
      el("button", { type: "submit" }, "Ajouter")));
}

function viewNewDevice(d) {
  const origin = location.origin;
  const snippet = [
    `DEVICE_ID = "${d.id}"`,
    `DEVICE_TOKEN = "${d.device_token}"`,
    `BLE_PIN = "${d.ble_pin}"`,
    `SERVER_URL = "${origin}"`,
  ].join("\n");
  render(
    el("h1", {}, d.name + " ajoutée"),
    el("div", { class: "card" },
      el("p", {}, "Copiez ces lignes dans firmware/config.py avant d'installer le firmware sur le Pico W."),
      el("p", {}, el("strong", {}, "Le jeton n'est affiché qu'une seule fois."), " Si vous le perdez, générez-en un nouveau depuis la page de la voiture."),
      el("pre", { class: "secret" }, snippet),
      el("button", { onclick: () => navigator.clipboard.writeText(snippet).then(() => toast("Copié")) }, "Copier")),
    el("a", { class: "button", href: "#car/" + d.id }, "Ouvrir la voiture"));
}

const TABS = [["soldes", "Soldes"], ["trajets", "Trajets"], ["ajouter", "Ajouter"], ["journal", "Journal"],
  ["boitier", "Boîtier"], ["membres", "Membres"], ["voiture", "Voiture"]];

async function viewCar(id, tab, sub) {
  const device = await api("GET", "/api/devices/" + id);
  const header = [
    el("h1", {}, device.name),
    el("div", { class: "tabs" }, TABS.map(([key, label]) =>
      el("a", { href: `#car/${id}/${key}`, class: key === tab ? "active" : null }, label))),
  ];
  const tabs = { soldes: tabBalances, trajets: tabTrips, ajouter: tabAdd, journal: tabJournal, boitier: tabBox,
    membres: tabMembers, voiture: tabSettings };
  const body = await (tabs[tab] || tabBalances)(device, sub);
  render(...header, ...[body].flat());
}

function fuelCard(f, device) {
  if (f.remaining_l === null) {
    return el("p", { class: "muted" }, f.last_fill === null ? "L'estimation du réservoir commence au prochain plein."
      : (device.is_owner ? "Indiquez la taille du réservoir et la consommation dans l'onglet Voiture pour estimer le carburant restant."
        : "Le propriétaire n'a pas encore indiqué la taille du réservoir."));
  }
  const bar = el("div");
  bar.style.width = f.remaining_pct + "%";
  return [
    el("div", { class: "row" }, el("span", {}, "Carburant estimé"), el("strong", {}, `${f.remaining_l} L (${f.remaining_pct} %)`)),
    el("div", { class: "gauge" }, bar),
    el("div", { class: "row" }, el("span", {}, "Autonomie estimée"), el("span", {}, f.range_km + " km")),
    el("div", { class: "row" }, el("span", {}, "Consommation"),
      el("span", {}, f.consumption_l_100km + " L/100 km ", el("span", { class: "muted" }, f.consumption_source === "measured" ? "(mesurée)" : "(réglée)"))),
  ];
}

async function tabBalances(device) {
  const s = await api("GET", `/api/devices/${device.id}/summary`);
  return [
    el("div", { class: "card" },
      el("h2", {}, "Qui doit combien"),
      s.settlements.length === 0 ? el("p", { class: "muted" }, "Tout le monde est quitte.") :
        s.settlements.map((t) => el("div", { class: "row" },
          el("span", {}, t.from.name, " → ", t.to.name), el("strong", {}, euros(t.amount_cents))))),
    el("div", { class: "card" },
      el("h2", {}, "Soldes"),
      s.balances.length === 0 ? el("p", { class: "muted" }, "Aucun solde.") :
        s.balances.map((b) => el("div", { class: "row" },
          el("span", {}, b.name), el("span", { class: b.cents >= 0 ? "pos" : "neg" }, (b.cents > 0 ? "+" : "") + euros(b.cents))))),
    el("div", { class: "card" },
      el("h2", {}, "Depuis le dernier plein"),
      el("p", {}, el("span", { class: "big" }, s.km.since_fill + " km"), " ",
        el("span", { class: "muted" }, `dont ${s.pending_km} km sur ${s.pending_trips} trajet(s) badgé(s), payés au prochain plein`)),
      s.pending_untracked_km > 0 && el("p", { class: "muted" },
        `${s.pending_untracked_km} km roulés sans badge : ils seront à la charge de celui qui paie le prochain plein.`),
      fuelCard(s.fuel, device)),
    el("div", { class: "card" },
      el("h2", {}, "Km parcourus"),
      s.km_by_person.map((p) => el("div", { class: "row" }, el("span", {}, p.name), el("span", {}, p.km + " km")))),
  ];
}

function personSelect(name, people, selected) {
  return el("select", { name, id: name, required: true },
    people.map((p) => el("option", { value: p.key, selected: p.key === selected }, p.name)));
}

async function tabAdd(device) {
  const people = device.people;
  const me = state.me.person;
  if (people.length === 0) return el("p", {}, "Ajoutez d'abord des membres ou des badges.");
  const submit = (build) => guarded(async (e) => {
    await api("POST", `/api/devices/${device.id}/entries`, build(formData(e.target), e.target));
    toast("Enregistré");
    location.hash = `#car/${device.id}/soldes`;
  });
  return [
    el("form", { class: "card", onsubmit: submit((d) => ({
      type: "fuel", amount_cents: parseEuros(d.amount), payer: d.payer,
      distance_km: number(d.distance_km) ?? undefined, litres: number(d.litres) ?? undefined, note: d.note || undefined,
    })) },
      el("h2", {}, "Plein d'essence"),
      el("p", { class: "muted" }, "Le plein est réparti sur les trajets faits depuis le plein précédent. Synchronisez le boîtier avant, pour que tous les trajets soient comptés."),
      el("label", { for: "amount" }, "Prix payé (€)"),
      el("input", { id: "amount", name: "amount", inputmode: "decimal", required: true, placeholder: "84,18" }),
      el("label", { for: "litres" }, "Litres mis"),
      el("input", { id: "litres", name: "litres", inputmode: "decimal", placeholder: "42,5" }),
      el("p", { class: "muted" }, "Facultatif mais conseillé : avec les litres, CarpoX mesure la consommation réelle. Faites le plein complet."),
      el("label", { for: "payer" }, "Payé par"), personSelect("payer", people, me),
      el("label", { for: "distance_km" }, "Km au compteur journalier (facultatif)"),
      el("input", { id: "distance_km", name: "distance_km", inputmode: "decimal", placeholder: "750" }),
      el("p", { class: "muted" }, "Si le compteur dépasse les km enregistrés, la différence est à la charge de celui qui a payé."),
      el("button", { type: "submit" }, "Enregistrer le plein")),
    el("form", { class: "card", onsubmit: submit((d, form) => ({
      type: "expense", amount_cents: parseEuros(d.amount), payer: d.payer, note: d.note || undefined,
      shared_with: [...form.querySelectorAll("input[name=shared]:checked")].map((i) => i.value),
    })) },
      el("h2", {}, "Autre frais partagé"),
      el("label", { for: "e-amount" }, "Montant (€)"),
      el("input", { id: "e-amount", name: "amount", inputmode: "decimal", required: true, placeholder: "12,50" }),
      el("label", { for: "e-note" }, "Pour quoi"),
      el("input", { id: "e-note", name: "note", maxlength: 80, placeholder: "Péage, parking..." }),
      el("label", { for: "e-payer" }, "Payé par"), personSelect("payer", people, me),
      el("label", {}, "Partagé entre"),
      people.map((p) => el("label", { class: "check" }, el("input", { type: "checkbox", name: "shared", value: p.key, checked: true }), p.name)),
      el("button", { type: "submit" }, "Enregistrer le frais")),
    el("form", { class: "card", onsubmit: submit((d) => ({
      type: "payment", amount_cents: parseEuros(d.amount), from: d.from, to: d.to,
    })) },
      el("h2", {}, "Remboursement effectué"),
      el("label", { for: "from" }, "De"), personSelect("from", people, me),
      el("label", { for: "to" }, "À"), personSelect("to", people),
      el("label", { for: "p-amount" }, "Montant (€)"),
      el("input", { id: "p-amount", name: "amount", inputmode: "decimal", required: true }),
      el("button", { type: "submit" }, "Enregistrer le remboursement")),
  ];
}

const EVENT_LABELS = { trip: "Trajet", drive: "Km sans badge", fuel: "Plein", expense: "Frais", payment: "Remboursement" };

async function tabJournal(device) {
  const events = await api("GET", `/api/devices/${device.id}/events?limit=200`);
  if (events.length === 0) return el("p", { class: "muted" }, "Rien pour l'instant. Les trajets arrivent quand le boîtier se synchronise.");
  return el("div", { class: "card" }, events.map((e) => {
    const d = e.data;
    const isKm = e.type === "trip" || e.type === "drive";
    const what = isKm ? `${d.km.toFixed(1)} km` : euros(d.amount_cents) + (d.litres ? ` · ${d.litres} L` : "");
    const who = e.type === "trip" ? e.people.join(", ") : e.label + (d.note ? " · " + d.note : "");
    const when = d.end || d.start || e.created_at;
    return el("div", { class: "row" },
      el("span", {}, el("strong", {}, EVENT_LABELS[e.type] + " · " + what), el("br"),
        el("span", { class: "muted" }, who + " · " + new Date(when * 1000).toLocaleDateString("fr-BE"))),
      e.source === "app" && el("button", { class: "small secondary", onclick: guarded(async () => {
        if (!confirm("Supprimer cette entrée ?")) return;
        await api("DELETE", `/api/devices/${device.id}/entries/${e.id}`);
        route();
      }) }, "Supprimer"));
  }));
}

// --- historique des trajets ------------------------------------------------------

async function tabTrips(device, tripId) {
  if (tripId) return await tripDetail(device, tripId);
  const trips = await api("GET", `/api/devices/${device.id}/trips?limit=100`);
  if (trips.length === 0) return el("p", { class: "muted" }, "Aucun trajet pour l'instant. Ils arrivent quand le boîtier se synchronise.");
  return el("div", { class: "card" }, trips.map((t) => el("a", { class: "row", href: `#car/${device.id}/trajets/${t.id}` },
    el("span", {}, el("strong", {}, `${t.km.toFixed(1)} km`), " · ", t.type === "drive" ? "sans badge" : t.people.join(", "), el("br"),
      el("span", { class: "muted" }, dateTime(t.start || t.end || t.received_at))),
    el("span", { class: "muted" }, t.track_points && t.track_visible ? "parcours ›" : ""))));
}

async function tripDetail(device, tripId) {
  const t = await api("GET", `/api/devices/${device.id}/trips/${encodeURIComponent(tripId)}`);
  const map = el("div");
  const card = el("div", { class: "card" },
    el("h2", {}, t.type === "drive" ? "Km roulés sans badge" : "Trajet"),
    el("div", { class: "row" }, el("span", {}, "Distance"), el("strong", {}, t.km.toFixed(1) + " km")),
    el("div", { class: "row" }, el("span", {}, "Départ"), el("span", {}, dateTime(t.start))),
    el("div", { class: "row" }, el("span", {}, "Arrivée"), el("span", {}, dateTime(t.end))),
    t.type === "trip" && el("div", { class: "row" }, el("span", {}, "À bord"), el("span", {}, t.people.join(", "))),
    t.track.length ? map : el("p", { class: "muted" }, !t.track_visible
      ? "Le parcours n'est visible que par le propriétaire de la voiture et les personnes à bord."
      : "Pas de parcours GPS pour ce trajet."));
  if (t.track.length) requestAnimationFrame(() => drawRoute(map, t.track, state.config.map_tiles));
  return [card, el("a", { class: "button", href: `#car/${device.id}/trajets` }, "Tous les trajets")];
}

// --- réglages de la voiture ------------------------------------------------------

function tabSettings(device) {
  const s = device.settings;
  const field = (id, label, value, hint) => [
    el("label", { for: id }, label),
    el("input", { id, name: id, inputmode: "decimal", value: value ?? "", disabled: !device.is_owner }),
    hint && el("p", { class: "muted" }, hint)];
  return el("form", { class: "card", onsubmit: guarded(async (e) => {
    const d = formData(e.target);
    await api("PATCH", `/api/devices/${device.id}`, {
      name: d.name, tank_l: number(d.tank_l), consumption_l_100km: number(d.consumption_l_100km),
      odometer_start_km: number(d.odometer_start_km),
    });
    toast("Réglages enregistrés");
    route();
  }) },
    el("h2", {}, "Réglages de la voiture"),
    !device.is_owner && el("p", { class: "muted" }, "Seul le propriétaire peut modifier ces réglages."),
    el("label", { for: "name" }, "Nom"),
    el("input", { id: "name", name: "name", required: true, maxlength: 40, value: device.name, disabled: !device.is_owner }),
    field("tank_l", "Capacité du réservoir (L)", s.tank_l),
    field("consumption_l_100km", "Consommation moyenne (L/100 km)", s.consumption_l_100km,
      "Sert tant que les pleins n'indiquent pas les litres. Ensuite, la consommation mesurée prend le relais."),
    field("odometer_start_km", "Compteur de la voiture à l'installation du boîtier (km)", s.odometer_start_km,
      "Facultatif : permet d'estimer le kilométrage total de la voiture."),
    device.is_owner && el("button", { type: "submit" }, "Enregistrer"));
}

// --- Bluetooth ----------------------------------------------------------------

async function syncViaPhone(device, log) {
  const link = state.link;
  let total = 0;
  for (let round = 0; round < 20; round++) {
    const status = await link.command("STATUS");
    if (status.device_id !== device.id) throw new Error("Ce boîtier n'est pas " + device.name);
    const lines = await link.command("EVENTS " + status.synced_seq, { multi: true });
    const events = lines.filter((l) => l.event).map((l) => l.event);
    const response = await api("POST", `/api/devices/${device.id}/relay`, { device_id: device.id, events });
    const applied = await link.command("APPLY " + JSON.stringify(response));
    total += applied.acked || 0;
    if (!events.length || !applied.acked) break;
  }
  log(total ? `${total} trajet(s) envoyé(s) au serveur.` : "Le boîtier était déjà à jour.");
}

function tabBox(device) {
  const out = el("div", { class: "card" });
  const log = (msg) => out.append(el("p", {}, msg));
  const connected = state.link.connected() && state.linkDevice === device.id;

  if (!BoxLink.supported()) {
    return el("div", { class: "card" },
      el("p", {}, "Ce navigateur ne gère pas le Bluetooth web. Utilisez Chrome ou Edge sur Android, Windows, macOS ou Linux (pas disponible sur iPhone)."),
      el("p", { class: "muted" }, "Le boîtier se synchronise aussi tout seul dès qu'il capte un WiFi connu."));
  }

  const connect = guarded(async () => {
    const name = await state.link.connect();
    const auth = await state.link.command("AUTH " + device.ble_pin);
    if (!auth.ok) { state.link.disconnect(); throw new Error(auth.error); }
    if (auth.device_id !== device.id) { state.link.disconnect(); throw new Error("Ce boîtier appartient à une autre voiture."); }
    state.linkDevice = device.id;
    state.link.onDisconnect = () => { state.linkDevice = null; toast("Boîtier déconnecté"); };
    toast("Connecté à " + name);
    route();
  });

  if (!connected) {
    return [el("div", { class: "card" },
      el("p", {}, "Allumez le boîtier et restez à côté. Le code Bluetooth de cette voiture est ", el("strong", {}, device.ble_pin), "."),
      el("button", { onclick: connect }, "Connecter le boîtier")), out];
  }

  const status = el("div", { class: "card" }, el("p", { class: "muted" }, "Lecture de l'état..."));
  state.link.command("STATUS").then((s) => {
    status.replaceChildren(...[
      el("div", { class: "row" }, el("span", {}, "Trajets enregistrés"), el("strong", {}, s.last_seq)),
      el("div", { class: "row" }, el("span", {}, "Pas encore envoyés"), el("strong", {}, s.pending)),
      s.trip && el("div", { class: "row" }, el("span", {}, s.trip.active ? "Trajet en cours" : "Trajet en préparation"), el("strong", {}, s.trip.km + " km")),
      s.drive_km ? el("div", { class: "row" }, el("span", {}, "Km sans badge (en cours)"), el("strong", {}, s.drive_km + " km")) : null,
    ].filter(Boolean));
  }).catch((err) => status.replaceChildren(el("p", {}, err.message)));

  const badgeForm = el("form", { class: "card", onsubmit: guarded(async (e) => {
    const d = formData(e.target);
    await api("PUT", `/api/devices/${device.id}/badges/${encodeURIComponent(d.uid)}`,
      { label: d.label, username: d.username || null });
    await state.link.command(`BADGE ${d.uid} ${d.label}`);
    toast("Badge enregistré");
    e.target.reset();
  }) },
    el("h2", {}, "Associer un badge"),
    el("p", { class: "muted" }, "Sur le boîtier, ouvrez « Scanner badge » et présentez le badge, puis appuyez sur Lire."),
    el("label", { for: "uid" }, "Numéro du badge"),
    el("input", { id: "uid", name: "uid", required: true, pattern: "[0-9A-Za-z]{1,24}" }),
    el("button", { type: "button", class: "secondary", onclick: guarded(async () => {
      const r = await state.link.command("LASTSCAN");
      if (!r.uid) throw new Error("Aucun badge lu pour l'instant.");
      badgeForm.querySelector("#uid").value = r.uid;
    }) }, "Lire le dernier badge"),
    el("label", { for: "label" }, "Nom affiché sur le boîtier"),
    el("input", { id: "label", name: "label", required: true, maxlength: 16 }),
    el("label", { for: "b-user" }, "Compte lié (facultatif)"),
    el("select", { id: "b-user", name: "username" }, el("option", { value: "" }, "Invité sans compte"),
      device.members.map((m) => el("option", { value: m.username }, m.display_name))),
    el("button", { type: "submit" }, "Enregistrer le badge"));

  return [
    status,
    el("div", { class: "card" },
      el("h2", {}, "Synchroniser via le téléphone"),
      el("p", { class: "muted" }, "Envoie au serveur les trajets du boîtier, sans attendre le WiFi."),
      el("button", { onclick: guarded(() => syncViaPhone(device, log)) }, "Synchroniser"),
      el("button", { class: "secondary", onclick: () => { state.link.disconnect(); route(); } }, "Déconnecter")),
    out,
    badgeForm,
  ];
}

// --- membres et badges ---------------------------------------------------------

function tabMembers(device) {
  const reload = () => route();
  return [
    el("div", { class: "card" },
      el("h2", {}, "Membres"),
      device.members.map((m) => el("div", { class: "row" },
        el("span", {}, m.display_name, " ", el("span", { class: "muted" }, m.username)),
        device.is_owner && m.id !== state.me.id && el("button", { class: "small secondary", onclick: guarded(async () => {
          await api("DELETE", `/api/devices/${device.id}/members/${m.id}`);
          reload();
        }) }, "Retirer"))),
      device.is_owner && el("form", { onsubmit: guarded(async (e) => {
        await api("POST", `/api/devices/${device.id}/members`, formData(e.target));
        reload();
      }) },
        el("label", { for: "m-user" }, "Inviter (nom d'utilisateur)"),
        el("input", { id: "m-user", name: "username", required: true, autocapitalize: "none" }),
        el("button", { type: "submit" }, "Inviter"))),
    el("div", { class: "card" },
      el("h2", {}, "Badges"),
      device.badges.length === 0 && el("p", { class: "muted" }, "Associez les badges depuis l'onglet Boîtier."),
      device.badges.map((b) => el("div", { class: "row" },
        el("span", {}, b.label, " ", el("span", { class: "muted" }, "#" + b.uid + (b.username ? " · " + b.username : " · invité"))),
        el("button", { class: "small secondary", onclick: guarded(async () => {
          await api("DELETE", `/api/devices/${device.id}/badges/${encodeURIComponent(b.uid)}`);
          reload();
        }) }, "Oublier")))),
    device.is_owner && el("div", { class: "card" },
      el("h2", {}, "Jeton du boîtier"),
      el("p", { class: "muted" }, "À régénérer si le boîtier est perdu. Il faudra mettre à jour config.py."),
      el("button", { class: "secondary", onclick: guarded(async () => {
        if (!confirm("L'ancien jeton cessera de fonctionner. Continuer ?")) return;
        const r = await api("POST", `/api/devices/${device.id}/token`);
        viewNewDevice({ ...device, device_token: r.device_token });
      }) }, "Nouveau jeton")),
  ];
}
