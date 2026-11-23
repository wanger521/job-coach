import { mkdir, cp } from "node:fs/promises";
const files = [
  "index.html",
  "style.css",
  "app.mjs",
  "ui.mjs",
  "collector-client.mjs",
  "profile.mjs",
  "profile.css",
  "data",
  "assets",
];
await mkdir("dist", { recursive: true });
for (const file of files) await cp(file, `dist/${file}`, { recursive: true });
console.log("Static site built in dist/");
