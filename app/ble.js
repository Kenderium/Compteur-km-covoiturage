// Liaison Bluetooth (Web Bluetooth) avec le boîtier CarpoX.
// Le boîtier expose le service « Nordic UART » : on écrit des lignes de texte
// sur RX et on reçoit des lignes JSON par notifications sur TX.
// Fonctionne dans Chrome/Edge (Android, Windows, macOS, Linux), pas sur iPhone.

const NUS_SERVICE = "6e400001-b5a3-f393-e0a9-e50e24dcca9e";
const NUS_RX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"; // app -> boîtier
const NUS_TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"; // boîtier -> app

class BoxLink {
  constructor() {
    this.device = null;
    this.rx = null;
    this.buffer = "";
    this.waiters = []; // réponses attendues, dans l'ordre
    this.queue = Promise.resolve();
    this.onDisconnect = null;
  }

  static supported() {
    return !!(navigator.bluetooth && window.isSecureContext);
  }

  async connect() {
    this.device = await navigator.bluetooth.requestDevice({ filters: [{ services: [NUS_SERVICE] }] });
    this.device.addEventListener("gattserverdisconnected", () => {
      this.rx = null;
      this.waiters.splice(0).forEach((w) => w.reject(new Error("Boîtier déconnecté")));
      if (this.onDisconnect) this.onDisconnect();
    });
    const server = await this.device.gatt.connect();
    const service = await server.getPrimaryService(NUS_SERVICE);
    this.rx = await service.getCharacteristic(NUS_RX);
    const tx = await service.getCharacteristic(NUS_TX);
    tx.addEventListener("characteristicvaluechanged", (e) => this._onData(e.target.value));
    await tx.startNotifications();
    return this.device.name || "CarpoX";
  }

  connected() {
    return !!(this.device && this.device.gatt.connected && this.rx);
  }

  disconnect() {
    if (this.device && this.device.gatt.connected) this.device.gatt.disconnect();
  }

  _onData(dataView) {
    this.buffer += new TextDecoder().decode(dataView);
    let idx;
    while ((idx = this.buffer.indexOf("\n")) >= 0) {
      const line = this.buffer.slice(0, idx).trim();
      this.buffer = this.buffer.slice(idx + 1);
      if (!line) continue;
      let msg;
      try { msg = JSON.parse(line); } catch { continue; }
      const waiter = this.waiters[0];
      if (!waiter) continue;
      waiter.lines.push(msg);
      // Une commande multi-lignes (EVENTS) se termine par {"end": true}.
      if (!waiter.multi || msg.end || msg.ok === false) {
        this.waiters.shift();
        clearTimeout(waiter.timer);
        waiter.resolve(waiter.multi ? waiter.lines : msg);
      }
    }
  }

  // Envoie une commande et attend sa réponse. Les commandes passent une par une.
  command(line, { multi = false, timeoutMs = 15000 } = {}) {
    const run = async () => {
      if (!this.connected()) throw new Error("Boîtier non connecté");
      const done = new Promise((resolve, reject) => {
        const waiter = { lines: [], multi, resolve, reject };
        waiter.timer = setTimeout(() => {
          this.waiters.splice(this.waiters.indexOf(waiter), 1);
          reject(new Error("Le boîtier ne répond pas"));
        }, timeoutMs);
        this.waiters.push(waiter);
      });
      const bytes = new TextEncoder().encode(line + "\n");
      for (let i = 0; i < bytes.length; i += 20) {
        await this.rx.writeValue(bytes.slice(i, i + 20));
      }
      return done;
    };
    const result = this.queue.then(run, run);
    this.queue = result.catch(() => {});
    return result;
  }
}

window.BoxLink = BoxLink;
