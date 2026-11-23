"""Fetch public recruitment notices and publish an atomic snapshot for the website."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from email.message import Message
from html.parser import HTMLParser
from http.client import HTTPException
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sys
import tempfile
import threading
import time
from urllib import error, parse, request, robotparser

if __package__:
    from .recruit_extract import application_status, parse_listing, parse_notice
else:
    from recruit_extract import application_status, parse_listing, parse_notice

EXTRACTOR_VERSION = hashlib.sha256(Path(__file__).with_name('recruit_extract.py').read_bytes()).hexdigest()[:12]

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
CACHE = ROOT / '.cache' / 'recruitment'
OUTPUT = DATA / 'recruitment-feed.mjs'
EXPORT = 'export const recruitmentFeed = '
AGENT = 'CareerAtlasDaily/1.0'
LIMIT = 2 * 1024 * 1024
LOCAL = timezone(timedelta(hours=8))


def atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temp = Path(f.name)
        f.write(content)
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def exclusive_run():
    CACHE.mkdir(parents=True, exist_ok=True)
    with (CACHE / 'run.lock').open('a+b') as lock:
        lock.seek(0)
        if os.name == 'nt':
            import msvcrt
            if not lock.read(1):
                lock.write(b'0')
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def previous_feed():
    if not OUTPUT.exists():
        return {'sources': [], 'notices': []}
    text = OUTPUT.read_text(encoding='utf-8').strip()
    return json.loads(text.removeprefix(EXPORT).removesuffix(';'))


def http_url(url):
    parts = parse.urlsplit(url)
    if parts.scheme not in ('https', 'http') or not parts.hostname or parts.username or parts.password:
        raise ValueError('不支持的网页地址')
    return parse.urlunsplit((parts.scheme, parts.netloc, parse.quote(parts.path, safe="/%:@!$&'()*+,;=-._~"), parse.quote(parts.query, safe="%=&+;:,/?@!$()*-._~"), ''))


def host(url):
    return (parse.urlsplit(url).hostname or '').lower()


class SiteRedirect(request.HTTPRedirectHandler):
    def __init__(self, allowed):
        self.allowed = allowed

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        newurl = http_url(newurl)
        if host(newurl) not in self.allowed:
            raise ValueError('跳转到来源配置以外的站点')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


next_request = {}
rate_lock = threading.Lock()


def throttle(domain, delay=1.1):
    with rate_lock:
        now = time.monotonic()
        start = max(now, next_request.get(domain, 0))
        next_request[domain] = start + delay
    time.sleep(max(0, start - now))


def decode_html(body, content_type):
    meta = re.search(rb'charset\s*=\s*[\'"\s]*([\w-]+)', body[:8192], re.I)
    header = Message()
    header['Content-Type'] = content_type
    for encoding in ('utf-8-sig', header.get_content_charset(), meta and meta[1].decode('ascii'), 'gb18030'):
        if encoding:
            try:
                return body.decode(encoding)
            except (UnicodeError, LookupError):
                pass
    raise ValueError('无法解码网页')


class SiteClient:
    def __init__(self, source):
        self.source = source
        self.allowed = {host(source['url']), *source.get('allowedHosts', [])}
        self.opener = request.build_opener(SiteRedirect(self.allowed))
        self.policies = {}
        self.paused = False

    def fetch(self, url, headers=None, delay=1.1):
        if self.paused:
            raise ValueError('站点限流，留待下次检查')
        url = http_url(url)
        if host(url) not in self.allowed:
            raise ValueError('不在采集来源范围内')
        throttle(host(url), delay)
        req = request.Request(url, headers={'User-Agent': AGENT, 'Accept': 'text/html,text/plain,*/*;q=0.2', **(headers or {})})
        try:
            with self.opener.open(req, timeout=9) as resp:
                body = resp.read(LIMIT + 1)
                if len(body) > LIMIT:
                    raise ValueError('页面超过大小限制')
                return resp.geturl(), resp.headers, body
        except error.HTTPError as exc:
            if exc.code == 429:
                self.paused = True
            raise

    def policy(self, url):
        origin = parse.urlsplit(url)._replace(path='', query='', fragment='').geturl()
        if origin not in self.policies:
            rules = robotparser.RobotFileParser()
            try:
                _, _, raw = self.fetch(origin + '/robots.txt')
                rules.parse(raw.decode('utf-8-sig', errors='replace').splitlines())
            except error.HTTPError as exc:
                if exc.code in (404, 410):
                    rules.allow_all = True
                elif exc.code in (401, 403):
                    rules.disallow_all = True
                else:
                    raise
            self.policies[origin] = rules
        return self.policies[origin]

    def html(self, url):
        rules = self.policy(url)
        if not rules.can_fetch(AGENT, url):
            raise ValueError('站点 robots.txt 限制访问')
        key = hashlib.sha256(url.encode()).hexdigest()
        storage = CACHE / 'pages' / (key + '.gz')
        cached = {}
        if storage.exists():
            try:
                cached = json.loads(gzip.decompress(storage.read_bytes()))
            except (ValueError, OSError):
                pass
        condition = {h:cached[k] for h,k in [('If-None-Match','etag'), ('If-Modified-Since','modified')] if cached.get(k)}
        try:
            final, headers, raw = self.fetch(url, condition, max(1.1, rules.crawl_delay(AGENT) or 0))
        except error.HTTPError as exc:
            if exc.code == 304 and 'text' in cached:
                return cached['text'], cached['url']
            raise
        if 'html' not in headers.get('Content-Type','').lower() and b'<html' not in raw[:3000].lower():
            raise ValueError('返回内容不是 HTML')
        text = decode_html(raw, headers.get('Content-Type',''))
        if not text.strip() or re.search(r'<title[^>]*>\s*(安全验证|访问验证|验证码|Just a moment|Access Denied|404)', text, re.I):
            raise ValueError('返回验证页或错误页')
        data = dict(text=text, url=final, etag=headers.get('ETag'), modified=headers.get('Last-Modified'))
        atomic(storage, gzip.compress(json.dumps(data,ensure_ascii=False).encode(), compresslevel=3))
        return text, final


class PositionTables(HTMLParser):
    def __init__(self, base, allowed):
        super().__init__(convert_charrefs=True)
        self.base, self.allowed = base, allowed
        self.active = ''
        self.label = []
        self.tables = []

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag == 'a':
            self.active = parse.urljoin(self.base, attr.get('href') or '')
            self.label = [attr.get('title') or '']

    def handle_data(self, data):
        if self.active:
            self.label.append(data)

    def handle_endtag(self, tag):
        if tag != 'a' or not self.active:
            return
        link = self.active
        self.active = ''
        parts = parse.urlsplit(link)
        if parts.scheme not in ('https','http') or host(link) not in self.allowed:
            return
        label = ' '.join(''.join(self.label).split())
        if re.search(r'岗位(?:信息|计划|需求|情况|简介|一览|汇总|目录|表)|招聘(?:计划|职位|岗位)表', label) and len(self.tables) < 4:
            self.tables.append({'title': label[:100], 'url': link})


def error_text(exc):
    if isinstance(exc, error.HTTPError):
        return 'HTTP ' + str(exc.code)
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return '连接超时'
    return str(exc)[:170]


def invalidate_window(record, availability):
    # Leave checked at the last successful detail read. Erase old bounds as
    # older consumers use deadline itself to classify a vacancy.
    record.update(applicationStart='', deadline='', windowVerified=False,
                  applicationStatus='unknown', closed=False, availability=availability)
    for key in ('applicationStartTime', 'deadlineTime'):
        record.pop(key, None)


def mark_stale(record):
    previous = record.get('availability')
    invalidate_window(record, previous if previous in ('unavailable', 'changed') else 'stale')


def check_site(source, existing, last, limit, stamp):
    client = SiteClient(source)
    # Revisit false positives and temporary detail failures after a short cooldown.
    # This lets the next daily batch reach older links on a busy listing.
    queue_path = CACHE / 'queue' / (hashlib.sha256(source['id'].encode()).hexdigest() + '.json')
    recent = {}
    if queue_path.exists():
        saved_queue = json.loads(queue_path.read_text(encoding='utf-8'))
        if saved_queue.get('rules') == EXTRACTOR_VERSION:
            recent = saved_queue.get('skipped', {})
    since = (datetime.fromisoformat(stamp) - timedelta(days=5)).date().isoformat()
    recent = {url:day for url,day in recent.items() if day > since}
    records = {n['url']:dict(n) for n in existing}
    today = datetime.fromisoformat(stamp).astimezone(LOCAL).date().isoformat()
    for record in records.values():
        if ('windowVerified' not in record or record.get('checked') != today or record.get('availability')):
            mark_stale(record)
        elif not record.get('closed'):
            record['applicationStatus'] = application_status(record, stamp)
            record['closed'] = record['applicationStatus'] == 'closed'

    status = {k:source[k] for k in ('id','name','city','kind','url')}
    status.update(status='failed', lastAttempt=stamp, lastSuccess=last.get('lastSuccess',''), discovered=0, verified=0, added=0, errors=[])
    try:
        text, url = client.html(source['url'])
        listing = ([{'url': url, 'title': source['watchTitle']}] if source.get('watchTitle')
                   else parse_listing(text, url, source))
        # New links on the current list first. Reserve capacity to revisit previously seen notices.
        links = {item['url']: item for item in listing}
        status['discovered'] = len(links)
        unseen = [item for key,item in links.items() if key not in records and (source.get('watchTitle') or key not in recent)]
        old = sorted(records.values(), key=lambda item:(item.get('lastAttempt',''),item['url']))
        known = [links.get(item['url'], {'url':item['url'],'title':item['title'],'published':item.get('published','')}) for item in old]
        reserve = min(len(known), max(1,limit//3)) if limit>1 else 0
        batch = unseen[:limit-reserve]
        batch += known[:limit-len(batch)]
        for index, item in enumerate(batch):
            key = item['url']
            try:
                page, final = (text, url) if source.get('watchTitle') and key == url else client.html(key)
                notice = parse_notice(page, final, item, source, stamp)
                if notice:
                    tables = PositionTables(final, client.allowed)
                    tables.feed(page)
                    if tables.tables:
                        notice['positionTables'] = tables.tables
                    notice['lastAttempt'] = stamp
                    if key != notice['url']:
                        recent[key] = stamp[:10]
                        records.pop(key, None)
                    records[notice['url']] = notice
                    status['verified'] += 1
                    status['added'] += int(key not in {r['url'] for r in existing})
                elif key in records:
                    invalidate_window(records[key], 'changed')
                    records[key]['lastAttempt'] = stamp
                else:
                    recent[key] = stamp[:10]
            except (OSError, ValueError, HTTPException) as exc:
                status['errors'].append(error_text(exc) + ' · ' + key)
                if key not in records and isinstance(exc, error.HTTPError) and exc.code in (404,410):
                    recent[key] = stamp[:10]
                if key in records:
                    records[key]['lastAttempt'] = stamp
                    if isinstance(exc, error.HTTPError) and exc.code in (404,410):
                        invalidate_window(records[key], 'unavailable')
                    else:
                        mark_stale(records[key])
                if client.paused:
                    for remaining in batch[index + 1:]:
                        if remaining['url'] in records:
                            mark_stale(records[remaining['url']])
                    break
        status['status'] = 'partial' if status['errors'] else 'ok' if links else 'empty'
        if status['status'] != 'partial' or status['verified']:
            status['lastSuccess'] = stamp
    except (OSError, ValueError, HTTPException) as exc:
        status['errors'].append(error_text(exc))
        for record in records.values():
            mark_stale(record)
            if source.get('watchTitle') and record['url'] == source['url']:
                record['lastAttempt'] = stamp
                if isinstance(exc, error.HTTPError) and exc.code in (404, 410):
                    invalidate_window(record, 'unavailable')
    atomic(queue_path, json.dumps({'rules':EXTRACTOR_VERSION, 'skipped':recent}).encode())
    return list(records.values()), status


def run(limit):
    stamp = datetime.now(LOCAL).isoformat(timespec='seconds')
    previous = previous_feed()
    sources = []
    for filename in ('nanjing-recruit-sources.json','general-recruit-sources.json','teacher-recruit-pages.json'):
        sources.extend(json.loads((DATA / filename).read_text(encoding='utf-8-sig')))
    ids = [source['id'] for source in sources]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('采集源为空或 ID 重复')
    old_status = {s['id']:s for s in previous['sources']}
    output = {'updatedAt':stamp,'sources':[], 'notices':[]}
    with ThreadPoolExecutor(max_workers=5) as pool:
        pending = {}
        for source in sources:
            existing = [r for r in previous['notices'] if r['sourceId'] == source['id']]
            future = pool.submit(check_site, source, existing, old_status.get(source['id'],{}), limit, stamp)
            pending[future] = source['name']
        for future in as_completed(pending):
            records, status = future.result()
            output['notices'].extend(records)
            output['sources'].append(status)
            print(status['name'], status['status'], status['verified'], flush=True)
    output['sources'].sort(key=lambda s:ids.index(s['id']))
    output['notices'].sort(key=lambda n:(n.get('published') or '',n['url']), reverse=True)
    # Overlapping sources can reread the same URL with different outcomes.
    # Prefer a successful current read, then the most recent attempt.
    unique = {}
    def priority(n):
        return (not n.get('availability'), n.get('lastAttempt', ''), n['sourceId'])

    for record in output['notices']:
        key = record['url']
        if key not in unique or priority(record) > priority(unique[key]):
            unique[key] = record
    output['notices'] = list(unique.values())
    content = (EXPORT + json.dumps(output,ensure_ascii=False,indent=2)+';\n').encode()
    atomic(OUTPUT, content)
    if (ROOT/'dist'/'index.html').exists():
        atomic(ROOT/'dist'/'data'/OUTPUT.name, content)
    print(f"{stamp} | {len(sources)} sources | {len(output['notices'])} notices", flush=True)
    return 1 if all(s['status'] == 'failed' for s in output['sources']) else 0


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--scheduled', action='store_true', help='将定时运行的日志保存在本机')
    cli.add_argument('--limit',type=int,choices=range(1,41),default=10,metavar='1..40',help='每个来源每次检查的详情页上限')
    args = cli.parse_args()
    if args.scheduled:
        CACHE.mkdir(parents=True, exist_ok=True)
        sys.stdout = sys.stderr = (CACHE / 'last-run.log').open('w', encoding='utf-8', buffering=1)
    try:
        with exclusive_run():
            sys.exit(run(args.limit))
    except (OSError,ValueError) as exc:
        sys.exit('Recruitment update failed: ' + error_text(exc))
