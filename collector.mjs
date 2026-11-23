import https from 'node:https';
import { lookup } from 'node:dns';
import { BlockList, isIP } from 'node:net';

const MAX_BODY = 8 * 1024;
const MAX_HTML = 2 * 1024 * 1024;
const FETCH_MS = 12_000;
const cache = new Map();
const pending = new Map();

class CollectionError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}
const problem = (status, code, message) => new CollectionError(status, code, message);

// Keep the exact submitted spelling separate from the document URL used by HTTP.
// Fragments can identify curated evidence but are never sent to the publisher.
function parseUrl(raw, base) {
  try { return new URL(raw, base); } catch { return null; }
}
function documentUrl(raw) {
  if (typeof raw !== 'string' || !raw.startsWith('https://') || /[\s\\\x00-\x1f\x7f]/u.test(raw)) return null;
  const url = parseUrl(raw);
  if (!url || url.username || url.password || url.port || !url.hostname.includes('.') ||
      isIP(url.hostname) || !/^[a-z\d.-]+\.[a-z\d-]+$/i.test(url.hostname) ||
      /\.(?:localhost|local|internal|test|invalid|onion|home\.arpa)$/i.test(url.hostname)) return null;
  url.hash = '';
  return url;
}

async function curatedUrls() {
  const catalog = await import('./data/catalog.mjs');
  const entries = new Map();
  const documents = new Set();
  function add(entry) {
    const raw = typeof entry === 'string' ? entry : entry?.url;
    const url = documentUrl(raw);
    if (url) {
      entries.set(raw, url);
      documents.add(url.href);
    }
  }
  catalog.sources.forEach(add);
  return { entries, documents };
}

// The TLS connection uses the very address checked here (no second DNS lookup).
const reserved = new BlockList();
for (const [ip, bits] of [
  ['0.0.0.0', 8], ['10.0.0.0', 8], ['100.64.0.0', 10], ['127.0.0.0', 8], ['169.254.0.0', 16],
  ['172.16.0.0', 12], ['192.0.0.0', 24], ['192.0.2.0', 24], ['192.88.99.0', 24], ['192.168.0.0', 16],
  ['198.18.0.0', 15], ['198.51.100.0', 24], ['203.0.113.0', 24], ['224.0.0.0', 3],
]) reserved.addSubnet(ip, bits, 'ipv4');
for (const [ip, bits] of [['2001::', 23], ['2001:db8::', 32], ['2002::', 16], ['3fff::', 20]]) {
  reserved.addSubnet(ip, bits, 'ipv6');
}
function publicLookup(hostname, options, done) {
  lookup(hostname, { all: true, verbatim: false }, (err, addresses) => {
    if (err) return done(err);
    const usable = addresses.filter(({ address, family }) => family === 4
      ? !reserved.check(address, 'ipv4')
      : /^[23]/.test(address) && !reserved.check(address, 'ipv6'));
    if (!usable.length) return done(problem(403, 'unsafe_address', '此来源的网络地址不适合公开采集。'));
    if (options.all) return done(null, usable);
    done(null, usable[0].address, usable[0].family);
  });
}

function getPage(url, signal) {
  return new Promise((resolve, reject) => {
    https.get(url, {
      agent: false, lookup: publicLookup, signal, maxHeaderSize: 32 * 1024,
      headers: { Accept: 'text/html, application/xhtml+xml', 'Accept-Encoding': 'identity', 'User-Agent': 'CareerAtlas/1.0 (study notebook source reader)' },
    }, resolve).once('error', reject);
  });
}

function decodeHtml(bytes, type) {
  const head = bytes.subarray(0, 4096).toString('latin1');
  const charset = /charset\s*=\s*["']?([\w.-]+)/i.exec(type)?.[1] ??
    /<meta\s[^>]*?charset\s*=\s*["']?([\w.-]+)/i.exec(head)?.[1] ?? 'utf-8';
  try { return new TextDecoder(charset).decode(bytes); }
  catch { throw problem(422, 'unreadable_page', '来源页面的文字编码暂不支持。'); }
}

const names = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', ndash: '–', mdash: '—', hellip: '…', lsquo: '‘', rsquo: '’', ldquo: '“', rdquo: '”', middot: '·', copy: '©', reg: '®' };
function plain(text = '') {
  return text.replace(/&(#x[\da-f]+|#\d+|[a-z]+);/gi, (all, entity) => {
    if (entity[0] !== '#') return Object.hasOwn(names, entity) ? names[entity] : all;
    const n = /^#x/i.test(entity) ? parseInt(entity.slice(2), 16) : Number(entity.slice(1));
    return n > 0 && n <= 0x10ffff && !(n >= 0xd800 && n <= 0xdfff) ? String.fromCodePoint(n) : '�';
  }).replace(/[\s\u0000-\u001f\u007f]+/gu, ' ').trim();
}
function attributes(tag) {
  const result = Object.create(null);
  for (const m of tag.matchAll(/([^\s=<>/]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g)) {
    result[m[1].toLowerCase()] = m[2] ?? m[3] ?? m[4];
  }
  return result;
}
const innerText = html => plain(html.replace(/<br\b[^>]*>/gi, ' ').replace(/<[^>]*>/g, ''));
const firstText = (html, re) => innerText(re.exec(html)?.[1] ?? '');
const blockedTitle = /^(?:just a moment|access denied|forbidden|robot check|error\b|404\b|403\b|sign in\b|log in\b|安全验证|访问受限|页面不存在)|captcha|verify (?:you are|you're) human|人机验证/i;
const boilerplate = /enable javascript|requires? javascript|javascript (?:is )?(?:disabled|required)|请启用\s*javascript|cookie (?:policy|settings|preferences)|accept (?:all )?cookies|使用.{0,5}cookie|verify (?:that )?you are human/i;
const useful = text => text.length >= 18 && !boilerplate.test(text);
const clip = (text, length) => text.length > length ? text.slice(0, length - 1).trimEnd() + '…' : text;

function extractPage(html) {
  const readable = html.replace(/<!--[\s\S]*?(?:-->|$)/g, '').replace(/<(script|style|template|noscript|svg)\b[^>]*>[\s\S]*?(?:<\/\1\s*>|$)/gi, ' ');
  const meta = new Map();
  for (const m of readable.matchAll(/<meta\b(?:[^>"']|"[^"]*"|'[^']*')*>/gi)) {
    const a = attributes(m[0]);
    const key = (a.property || a.name || a.itemprop || '').toLowerCase();
    if (key && a.content && !meta.has(key)) meta.set(key, plain(a.content));
  }
  const docTitle = firstText(readable, /<title\b[^>]*>([\s\S]*?)<\/title\s*>/i);
  const body = readable.replace(/<(head|header|nav|footer|aside|form)\b[^>]*>[\s\S]*?<\/\1\s*>/gi, ' ');
  const main = /<(main|article)\b[^>]*>([\s\S]*?)<\/\1\s*>/i.exec(body)?.[2] ?? body;
  const heading = firstText(main, /<h1\b[^>]*>([\s\S]*?)<\/h1\s*>/i);
  const title = meta.get('og:title') || docTitle || heading;
  if (!title || [title, docTitle, heading].some(s => blockedTitle.test(s))) {
    throw problem(422, 'unreadable_page', '来源页面缺少可核实的标题，或需要登录、验证。');
  }
  // A publisher may reuse the same meta description for every occupation. Prefer
  // a substantive paragraph in the article (or following the page heading).
  const article = main.split(/<\/h1\s*>/i, 2).at(-1);
  let excerpt;
  for (const match of article.matchAll(/<p\b([^>]*)>([\s\S]*?)(?:<\/p\s*>|(?=<p\b)|$)/gi)) {
    if (/(?:\shidden\b|aria-hidden\s*=\s*["']?true|visually-hidden|sr-only)/i.test(match[1])) continue;
    const text = innerText(match[2]);
    if (useful(text) && text !== title) { excerpt = text; break; }
  }
  if (!excerpt) {
    const visible = innerText(main);
    if (boilerplate.test(visible) || (!useful(visible) && /<noscript\b|\bid\s*=\s*["'](?:app|root|__next)["']/i.test(html))) {
      throw problem(422, 'unreadable_page', '来源页面需要浏览器加载或验证，未能取得正文。');
    }
    excerpt = [meta.get('og:description'), meta.get('description'), meta.get('twitter:description')]
      .find(text => text && useful(text) && text !== title);
  }
  if (!excerpt) throw problem(422, 'unreadable_page', '未取得可核实的摘要，页面可能需要浏览器加载。');
  // Only keep dates explicitly identified by the publisher. A copyright year or
  // the HTTP Date header is not the publication date of this document.
  const published = ['article:published_time', 'datepublished', 'citation_publication_date', 'dcterms.issued'].map(key => meta.get(key));
  const updated = ['article:modified_time', 'datemodified', 'dcterms.modified'].map(key => meta.get(key));
  for (const m of readable.matchAll(/<time\b[^>]*>/gi)) {
    const a = attributes(m[0]);
    if (a.itemprop?.toLowerCase() === 'datepublished' || /\spubdate(?:[\s=>])/i.test(m[0])) published.push(a.datetime);
    if (a.itemprop?.toLowerCase() === 'datemodified') updated.push(a.datetime);
  }
  for (const m of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)) {
    if (attributes(m[1]).type?.toLowerCase() !== 'application/ld+json' || m[2].length > 128_000) continue;
    let schema;
    try { schema = JSON.parse(m[2]); } catch { continue; }
    for (const item of [schema].flat().flatMap(node => node?.['@graph'] ?? node)) {
      if (!item || ![item['@type']].flat().some(t => /^(?:(?:News|Tech|Scholarly)?Article|BlogPosting|WebPage|ProfilePage)$/i.test(t))) continue;
      published.push(item.datePublished);
      updated.push(item.dateModified);
    }
  }
  const date = values => values.find(v => typeof v === 'string' && /^\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[T ][\d:.+\-Z ]+)?$/i.test(v)) ?? null;
  return { title: clip(title, 240), excerpt: clip(excerpt, 480), publishedAt: date(published), updatedAt: date(updated) };
}

async function fetchSource(start, documents) {
  const signal = AbortSignal.timeout(FETCH_MS);
  let url = start;
  const visited = new Set();
  try {
    while (true) {
      visited.add(url.href);
      const response = await getPage(url, signal);
      try {
        const status = response.statusCode;
        if ([301, 302, 303, 307, 308].includes(status)) {
          const location = response.headers.location;
          const target = location && parseUrl(location, url);
          const next = target && documentUrl(target.href);
          if (!next || !documents.has(next.href) || visited.has(next.href) || visited.size > 3) {
            throw problem(422, 'redirect_rejected', '来源跳转到了未经收录的页面，或跳转次数过多。');
          }
          url = next;
          continue;
        }
        if (status !== 200) throw problem(502, 'upstream_status', `来源网站返回 HTTP ${status}，本次未能采集。`);
        const type = response.headers['content-type'] ?? '';
        if (!/^(?:text\/html|application\/xhtml\+xml)(?:\s*;|$)/i.test(type) ||
            (response.headers['content-encoding'] || 'identity').toLowerCase() !== 'identity') {
          throw problem(422, 'unsupported_page', '来源未返回可读取的 HTML 页面。');
        }
        const tooLarge = () => problem(422, 'page_too_large', '来源页面超过采集大小限制。');
        if (Number(response.headers['content-length']) > MAX_HTML) throw tooLarge();
        const chunks = [];
        let size = 0;
        for await (const chunk of response) {
          size += chunk.length;
          if (size > MAX_HTML) throw tooLarge();
          chunks.push(chunk);
        }
        const fields = extractPage(decodeHtml(Buffer.concat(chunks, size), type));
        return { ...fields, url: url.href, retrievedAt: new Date().toISOString() };
      } finally { response.destroy(); }
    }
  } catch (err) {
    if (signal.aborted) throw problem(504, 'timeout', '读取来源页面超时。');
    if (err instanceof CollectionError) throw err;
    throw problem(502, 'unavailable', '暂时无法连接来源网站或读取完整页面。');
  }
}

async function collect(raw) {
  const { entries, documents } = await curatedUrls();
  if (!entries.size) throw problem(503, 'catalog_unavailable', '暂时无法加载已收录的来源目录。');
  const start = entries.get(raw);
  if (!start) throw problem(403, 'not_curated', '只支持采集目录中完整匹配的来源链接。');
  const key = start.href;
  const hit = cache.get(key);
  if (hit?.until > Date.now()) {
    if (hit.error) throw hit.error;
    return hit.page;
  }
  if (pending.has(key)) return pending.get(key);
  if (pending.size >= 6) throw problem(503, 'busy', '采集服务正忙，请稍后重试。');
  function remember(entry) {
    cache.delete(key);
    if (cache.size >= 128) cache.delete(cache.keys().next().value);
    cache.set(key, entry);
  }
  const task = fetchSource(start, documents).then(page => {
    remember({ page, until: Date.now() + 15 * 60_000 });
    return page;
  }, error => {
    remember({ error, until: Date.now() + 30_000 });
    throw error;
  }).finally(() => pending.delete(key));
  pending.set(key, task);
  return task;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    const timer = setTimeout(() => finish(problem(408, 'request_timeout', '提交链接超时。')), 5000);
    function finish(error) {
      clearTimeout(timer);
      req.off('data', onData).off('end', onEnd).off('error', finish);
      if (error) { req.resume(); reject(error); }
      else resolve(Buffer.concat(chunks).toString('utf8'));
    }
    function onData(chunk) {
      size += chunk.length;
      if (size > MAX_BODY) finish(problem(413, 'request_too_large', '提交内容超过大小限制。'));
      else chunks.push(chunk);
    }
    const onEnd = () => finish();
    req.on('data', onData).once('end', onEnd).once('error', finish);
  });
}

/** Dispatch the exact /api/collect route here. This handler always owns the response. */
export async function handleCollection(req, res) {
  let status = 200;
  let result;
  try {
    if (req.method !== 'POST') {
      res.setHeader('Allow', 'POST');
      throw problem(405, 'method_not_allowed', '请使用 POST 提交链接。');
    }
    if (!/^application\/json(?:\s*;|$)/i.test(req.headers['content-type'] ?? '')) {
      throw problem(415, 'expected_json', '请以 JSON 格式提交链接。');
    }
    const body = await readBody(req);
    let data;
    try { data = JSON.parse(body); } catch { /* handled below */ }
    if (!data || typeof data.url !== 'string' || !data.url || Object.keys(data).length !== 1) {
      throw problem(400, 'invalid_request', '请提交一个包含来源链接的 JSON 对象。');
    }
    result = { ...await collect(data.url), sourceUrl: data.url };
  } catch (err) {
    const error = err instanceof CollectionError ? err : problem(500, 'collection_error', '采集服务暂时不可用。');
    status = error.status;
    result = { error: { code: error.code, message: `${error.message}仍可手动保存此来源。` } };
    if (status === 413 || status === 408) res.setHeader('Connection', 'close');
  }
  if (res.destroyed) return;
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
  res.end(JSON.stringify(result));
}
