// Dessin d'un parcours GPS, sans bibliothèque : tuiles de carte en <img>
// (OpenStreetMap par défaut, réglé par le serveur) et tracé en SVG par-dessus.
// Sans fond de carte configuré, seul le tracé est dessiné.

"use strict";

const TILE = 256;

// Projection Web Mercator : degrés -> pixels du monde au niveau de zoom `z`.
function project(lat, lon, z) {
  const size = TILE * 2 ** z;
  const s = Math.sin((Math.max(-85, Math.min(85, lat)) * Math.PI) / 180);
  return [((lon + 180) / 360) * size, (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * size];
}

function fitZoom(points, width, height) {
  const lats = points.map((p) => p[0]);
  const lons = points.map((p) => p[1]);
  for (let z = 17; z > 1; z--) {
    const [x1, y1] = project(Math.max(...lats), Math.min(...lons), z);
    const [x2, y2] = project(Math.min(...lats), Math.max(...lons), z);
    if (x2 - x1 <= width * 0.85 && y2 - y1 <= height * 0.85) return z;
  }
  return 1;
}

function svgNode(tag, attrs) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

// Dessine `points` ([[lat, lon], ...]) dans `container`.
function drawRoute(container, points, tilesUrl) {
  container.replaceChildren();
  container.classList.add("map");
  if (!points.length) return;
  const width = container.clientWidth || 600;
  const height = container.clientHeight || 320;
  const z = fitZoom(points, width, height);
  const px = points.map((p) => project(p[0], p[1], z));
  const xs = px.map((p) => p[0]);
  const ys = px.map((p) => p[1]);
  const left = (Math.min(...xs) + Math.max(...xs)) / 2 - width / 2;
  const top = (Math.min(...ys) + Math.max(...ys)) / 2 - height / 2;

  if (tilesUrl) {
    const n = 2 ** z;
    for (let tx = Math.floor(left / TILE); tx <= Math.floor((left + width) / TILE); tx++) {
      for (let ty = Math.floor(top / TILE); ty <= Math.floor((top + height) / TILE); ty++) {
        if (ty < 0 || ty >= n) continue;
        const img = document.createElement("img");
        img.alt = "";
        img.referrerPolicy = "no-referrer";
        img.onerror = () => img.remove();
        img.src = tilesUrl.replace("{z}", z).replace("{x}", ((tx % n) + n) % n).replace("{y}", ty);
        img.style.left = tx * TILE - left + "px";
        img.style.top = ty * TILE - top + "px";
        container.append(img);
      }
    }
  }

  const svg = svgNode("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  const coords = px.map(([x, y]) => `${(x - left).toFixed(1)},${(y - top).toFixed(1)}`);
  svg.append(svgNode("polyline", { points: coords.join(" "), class: "route" }));
  const [sx, sy] = coords[0].split(",");
  const [ex, ey] = coords[coords.length - 1].split(",");
  svg.append(svgNode("circle", { cx: sx, cy: sy, r: 6, class: "route-start" }));
  svg.append(svgNode("circle", { cx: ex, cy: ey, r: 6, class: "route-end" }));
  container.append(svg);

  if (tilesUrl && tilesUrl.includes("openstreetmap.org")) {
    const credit = document.createElement("a");
    credit.className = "map-credit";
    credit.href = "https://www.openstreetmap.org/copyright";
    credit.target = "_blank";
    credit.rel = "noopener";
    credit.textContent = "© OpenStreetMap";
    container.append(credit);
  }
}

window.drawRoute = drawRoute;
