const paths = {
  compass:
    '<circle cx="12" cy="12" r="9"/><path d="m16.5 7.5-2.7 6.3-6.3 2.7 2.7-6.3z"/>',
  book: '<path d="M3 4.5c3-1 6-1 9 1 3-2 6-2 9-1v14c-3-1-6-1-9 1-3-2-6-2-9-1zM12 5.5v14"/>',
  route:
    '<circle cx="5" cy="5" r="2"/><circle cx="18" cy="18" r="2"/><path d="M7 5h8a3 3 0 0 1 0 6H8a3.5 3.5 0 0 0 0 7h8"/>',
  bookmark:
    '<path d="M6 4.5A1.5 1.5 0 0 1 7.5 3h9A1.5 1.5 0 0 1 18 4.5V21l-6-4-6 4z"/>',
  notes:
    '<path d="M7 3h12a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zM8 3v18m3-13h6m-6 4h5M3 7h3m-3 5h3m-3 5h3"/>',
  library: '<path d="M3 4h4v16H3zM9 4h4v16H9zm6 1 4-1 3 15-4 1z"/>',
  layers: '<path d="m12 3 10 5-10 5L2 8zM3 12l9 5 9-5m-18 4 9 5 9-5"/>',
  map: '<path d="m3 5 6-2 6 3 6-2v15l-6 2-6-3-6 2zM9 3v15m6-12v15"/>',
  mountain: '<path d="m2 20 8-15 6 11 2-5 5 9zM7.5 10l2.5 2 2-2"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  arrow: '<path d="M4 12h15m-6-6 6 6-6 6"/>',
  diagonal: '<path d="M6 18 18 6M7 6h11v11"/>',
  chev: '<path d="m9 5 7 7-7 7"/>',
  down: '<path d="m5 9 7 7 7-7"/>',
  back: '<path d="m10 5-7 7 7 7M3 12h18"/>',
  user: '<circle cx="12" cy="8" r="3.5"/><path d="M5 20v-2a7 5 0 0 1 14 0v2"/>',
  flag: '<path d="M5 21V3m0 1c5-4 8 4 14 0v9c-6 4-9-4-14 0"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h1M3 12h1M3 18h1"/>',
  filter:
    '<path d="M3 7h5m4 0h9M3 17h10m4 0h4"/><circle cx="10" cy="7" r="2"/><circle cx="15" cy="17" r="2"/>',
  calendar:
    '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18"/>',
  pin: '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="2.5"/>',
  plus: '<path d="M12 4v16M4 12h16"/>',
  x: '<path d="m6 6 12 12M18 6 6 18"/>',
  check: '<path d="m4 12 5 5L20 6"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  files: '<path d="M8 3h8l5 5v12H8zM16 3v6h5M5 7H3v15h13"/>',
  energy: '<path d="M3 13h4l3-7 4 13 3-7h4"/>',
  leaf: '<path d="M4 18C0 6 11 4 21 3c-1 10-3 18-13 16m-4 2L16 9"/>',
  target:
    '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  link: '<path d="m10 14 4-4m-3-3 2-2a4.2 4.2 0 0 1 6 6l-3 3m-3 3-2 2a4.2 4.2 0 0 1-6-6l3-3"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  pen: '<path d="m4 16-1 5 5-1L20 8l-4-4zM14 6l4 4"/>',
  trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15m-9 3v9m4-9v9"/>',
  balance: '<path d="M12 3v18M4 7l16-2M5 7l-3 8h6zm14-2-3 8h6zM7 21h10"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-11v1"/>',
  brief:
    '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M8 7V4h8v3M2 12c5 3 15 3 20 0m-10 0v4"/>',
  spark:
    '<path d="m12 2 2.4 7.6L22 12l-7.6 2.4L12 22l-2.4-7.6L2 12l7.6-2.4z"/>',
};
export function icon(name, size = 18) {
  return `<svg class="icon" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.compass}</svg>`;
}
export function esc(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
}
export function safeUrl(value) {
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}
export function modal(title, body, kind = "") {
  const previous = document.activeElement;
  const d = document.createElement("dialog");
  d.className = "atlas-dialog " + kind;
  d.setAttribute("aria-label", title);
  d.innerHTML = `<div class="dialog-head"><h2>${esc(title)}</h2><button type="button" class="icon-button" data-close aria-label="关闭">${icon("x")}</button></div>${body}`;
  document.body.append(d);
  d.addEventListener("click", (e) => {
    if (
      e.target.closest("[data-close]") ||
      (e.target === d &&
        (e.clientX < d.getBoundingClientRect().left ||
          e.clientX > d.getBoundingClientRect().right ||
          e.clientY < d.getBoundingClientRect().top ||
          e.clientY > d.getBoundingClientRect().bottom))
    )
      d.close();
  });
  d.addEventListener(
    "close",
    () => {
      d.remove();
      if (previous?.isConnected) previous.focus({ preventScroll: true });
    },
    { once: true },
  );
  d.showModal();
  return d;
}
