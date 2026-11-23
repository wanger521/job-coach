import http from "node:http";
import { handleCollection } from "./collector.mjs";
import { readFile, stat } from "node:fs/promises";
import { resolve, extname, sep } from "node:path";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL(".", import.meta.url));
const arg = (key) => {
  const i = process.argv.indexOf(key);
  return i >= 0 ? process.argv[i + 1] : undefined;
};
const port = Number(arg("--port") || process.env.PORT || 5173);
const hostArg = arg("--host");
const host = hostArg && !hostArg.startsWith("-") ? hostArg : "127.0.0.1";
const types = {
  ".html": "text/html",
  ".mjs": "text/javascript",
  ".js": "text/javascript",
  ".css": "text/css",
  ".webp": "image/webp",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};
http
  .createServer(async (req, res) => {
    try {
      const pathname = decodeURIComponent(
        new URL(req.url, "http://localhost").pathname,
      );
      if (pathname === "/api/collect") return await handleCollection(req, res);
      if (!["GET", "HEAD"].includes(req.method)) {
        res.writeHead(405, { Allow: "GET, HEAD" });
        res.end();
        return;
      }
      const name = pathname === "/" ? "index.html" : pathname.slice(1);
      if (
        !/^(index\.html|app\.mjs|collector-client\.mjs|ui\.mjs|profile\.mjs|style\.css|profile\.css|data\/[\w-]+\.mjs|assets\/[\w./-]+)$/.test(
          name,
        )
      )
        throw Error();
      const file = resolve(root, name);
      if (
        !file.startsWith(resolve(root) + sep) ||
        !types[extname(file)] ||
        !(await stat(file)).isFile()
      )
        throw Error();
      const bytes = await readFile(file);
      res.writeHead(200, {
        "Content-Type":
          types[extname(file)] +
          ([".html", ".mjs", ".js", ".css"].includes(extname(file))
            ? "; charset=utf-8"
            : ""),
        "Cache-Control": "no-cache",
        "X-Content-Type-Options": "nosniff",
      });
      res.end(bytes);
    } catch {
      res.writeHead(404);
      res.end("Not found");
    }
  })
  .listen(port, host, () =>
    console.log(`Career Atlas: http://${host}:${port}`),
  );
