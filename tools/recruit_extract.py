"""Offline extraction of candidate recruitment notices from decoded HTML.

parse_listing returns unique {url, title, published?} links in document order.
parse_notice takes the final URL, its listing item, and an ISO check date or timestamp. It
returns a JSON-ready notice or None. Empty strings/role lists mean unknown.
applicationStart/deadline are ISO dates or empty; corresponding Time fields
are optional Beijing HH:mm. windowVerified requires both bounds of one window.
applicationStatus is unknown, upcoming, open or closed as of the check.
closed mirrors the closed state. An end date alone cannot establish open.

source: {id, name, url, city, kind, include?, allowedHosts?, detailPattern?}.
Nonempty include supplies literal alternatives to the default keywords.
detailPattern is a regex on the absolute URL or path with query. It can admit
application/position titles for inspection. Detail text must still qualify.
allowedHosts adds exact hostnames on default HTTP(S) ports to the source origin.
No I/O, external dependencies, cache, or system clock.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta, timezone
from unicodedata import normalize
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from xml.etree.ElementTree import TreeBuilder

__all__ = ['parse_listing', 'parse_notice', 'application_status']

_VOID = set('area base br col embed hr img input link meta param source track wbr'.split())
_BLOCK = set('address article aside blockquote br caption dd div dl dt h1 h2 h3 h4 h5 h6 hr '
             'li main ol p section table td th tr ul'.split())
_NOISE = re.compile(r'(?:^|[\W_])(?:nav(?:igation|bar)?|menus?|footer|copyright|breadcrumb[s]?|'
                    r'crumbs?|sidebar|sidenav|related|share|pagination|prev[-_]?next|'
                    r'(?:article|post|news)[-_]?(?:neighbors|siblings|navigation)|友情链接)(?:$|[\W_])', re.I)
_LIST = re.compile(r'(?:news|notice|article|recommend|latest|related)[-_ ]?list|公告列表|相关新闻|(?:^|\s)(?:list|listbox|list[-_]?(?:box|news|article|notice))(?=\s|$)', re.I)
_CONTENT = re.compile(r'(?:^|[\s_-])(?:v_news_content|wp_articlecontent|trs_editor|vsb_content(?:_\d+)?|'
                      r'article[-_]?(?:body|content|text)|news[-_]?(?:body|content|text)|'
                      r'detail[-_]?content|正文|zoom)(?:$|[\s_-])', re.I)


class _Document(HTMLParser):
    """Build a small HTML tree, including fragments and optional list/table ends."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tree = TreeBuilder()
        self.root = self.tree.start('document', {})
        self.tags = []
        self.feed(html)
        self.close()
        while self.tags:
            self.tree.end(self.tags.pop())
        self.tree.end('document')
        self.tree.close()

    def handle_starttag(self, tag, attrs):
        peers = {'td', 'th'} if tag in {'td', 'th'} else {tag}
        if tag in {'li', 'p', 'tr', 'td', 'th', 'a'} and self.tags and self.tags[-1] in peers:
            self.tree.end(self.tags.pop())
        self.tree.start(tag, {k: v or '' for k, v in attrs})
        if tag in _VOID:
            self.tree.end(tag)
        else:
            self.tags.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in self.tags:
            while self.tags:
                last = self.tags.pop()
                self.tree.end(last)
                if last == tag:
                    break

    def handle_data(self, text):
        self.tree.data(text)


def _marks(node):
    return ' '.join(node.get(key, '') for key in ('class', 'id', 'role', 'itemprop'))


def _document(html, *, listing=False):
    root = _Document(html).root
    # WebPlus uses list markers on both detail-page layout wrappers and actual
    # neighbouring lists. Preserve the path to the article, but prune its siblings.
    article_path = set()
    if not listing:
        for node in reversed(list(root.iter())):
            if (node.tag in {'html', 'body', 'main', 'article'} or _CONTENT.search(_marks(node))
                    or any(child in article_path for child in node)):
                article_path.add(node)
    stack = [(root, False)]
    while stack:
        parent, in_article = stack.pop()
        for node in list(parent):
            marks = _marks(node)
            article = in_article or node.tag == 'article' or bool(_CONTENT.search(marks))
            if (node.tag in {'script', 'style', 'noscript', 'template', 'svg', 'iframe', 'aside',
                             'nav', 'footer', 'form', 'button', 'select'}
                    or (node.tag == 'header' and not article)
                    or 'hidden' in node.attrib or node.get('aria-hidden', '').lower() == 'true'
                    or re.search(r'display\s*:\s*none|visibility\s*:\s*hidden', node.get('style', ''), re.I)
                    or _NOISE.search(marks) or (not listing and node not in article_path and _LIST.search(marks))):
                # Keep any prose after an inline removed node, with a word boundary.
                tail = node.tail
                node.clear()
                node.tag, node.tail = 'br', tail
            else:
                stack.append((node, article))
    return root


def _clean(text):
    return ' '.join((text or '').split())


def _lines(root, skip=frozenset()):
    """Block boundaries protect dates and job labels in separate paragraphs/cells."""
    parts = []
    pending = [root]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            parts.append(item)
            continue
        if item.tag in skip:
            parts.append('\n')
            continue
        if item.tag in _BLOCK:
            parts.append('\n')
            pending.append('\n')
        for child in reversed(item):
            if child.tail:
                pending.append(re.sub(r'\s+', ' ', child.tail))
            pending.append(child)
        if item.text:
            parts.append(re.sub(r'\s+', ' ', item.text))
    return [line for s in ''.join(parts).splitlines() if (line := _clean(s))]


_FILE = re.compile(r'\.(?:pdf|docx?|xlsx?|pptx?|od[st]|csv|txt|rtf|zip|rar|7z|gz|tar|'
                   r'jpe?g|gif|png|webp|svg|mp[34]|exe|js|css)(?:$|[/;&?#])', re.I)
_DOWNLOAD = re.compile(r'(?:^|/)(?:attachments?|uploads?|_upload|download(?:file)?|filedownload)'
                       r'(?:[/._;?]|$)', re.I)


def _absolute(raw, base=''):
    if not isinstance(raw, str):
        return ''
    raw = raw.strip()
    if not raw or raw.startswith('#') or re.search(r'[\x00-\x20\x7f\\]', raw):
        return ''
    try:
        parsed = urlsplit(urljoin(base, raw))
        host, port = parsed.hostname, parsed.port
        if (parsed.scheme not in ('http', 'https') or not host or '@' in parsed.netloc
                or not re.fullmatch(r'[a-z0-9.-]+', host, re.I)):
            return ''
        default = 443 if parsed.scheme == 'https' else 80
        netloc = host if port is None or port == default else f'{host}:{port}'
        return urlunsplit((parsed.scheme, netloc, parsed.path or '/', parsed.query, ''))
    except ValueError:
        return ''


class _Scope:
    def __init__(self, source):
        self.origin = urlsplit(_absolute(source['url']))
        self.hosts = {h.lower() for h in source.get('allowedHosts', [])}
        self.pattern = re.compile(source['detailPattern']) if source.get('detailPattern') else None

    def resolve(self, raw, base='', *, detail=False):
        url = _absolute(raw, base)
        if not url or not self.origin.hostname:
            return ''
        target = urlsplit(url)
        if ((target.scheme, target.netloc) != (self.origin.scheme, self.origin.netloc)
                and not (target.netloc in self.hosts and target.port is None)):
            return ''
        if detail:
            resource = target.path + ('?' + target.query if target.query else '')
            decoded = unquote(resource)
            if _FILE.search(decoded) or _DOWNLOAD.search(decoded):
                return ''
            if self.pattern and not (self.pattern.search(url) or self.pattern.search(resource)):
                return ''
        return url


_YEAR = r'(?:\d{4}|[零〇○一二三四五六七八九]{4})'
_MD = r'(?:\d{1,2}|[零〇一二三四五六七八九十]{1,3})'
_DATE = re.compile(rf'(?<!\d)({_YEAR})\s*[-年./]\s*({_MD})\s*[-月./]\s*({_MD})(?!\d)\s*[日号]?')
_DIGITS = str.maketrans('零〇○一二三四五六七八九', '000123456789')


def _number(part):
    part = part.translate(_DIGITS)
    if '十' in part:
        tens, units = part.split('十')
        return int(tens or '1') * 10 + int(units or '0')
    return int(part)


def _iso(match):
    if match:
        try:
            return date(*map(_number, match.groups())).isoformat()
        except ValueError:
            pass
    return ''


_PUBLICATION = re.compile(r'(?:发布(?:时间|日期|日)|刊登日期|公告日期|发[布表]于|发稿时间)\s*[:：]?\s*为?\s*')
_EXCLUDE = re.compile(r'公示|成绩|体检|拟(?:录用|聘用|聘任|聘|录取|录)|更正|勘误|招标|中标|采购公告|'
                      r'入围|递补|补正|中选公告|成交公告|面试(?:人员|考生)?(?:名单|通知|安排|公告)|资格复审(?:通知|公告|名单)|'
                      r'笔试(?:安排|通知|公告)|录用名单|考察名单|招聘(?:结果|工作总结)|活动回顾|'
                      r'(?:岗位|招聘计划)\s*(?:予以)?(?:取消|核减)|(?:取消|核减)(?:部分)?(?:招聘计划|招聘岗位|岗位)')
_POSITIVE = re.compile(r'招聘|校招|招考教师|诚聘|招募(?:实习生|毕业生)|人才引进|引进(?:人才|教师)|选聘|招教|招录')
_MENU_TITLE = re.compile(r'^(?:首页|更多|下一页|上一页|通知公告|新闻动态|公告列表|人才招聘|招聘信息|招聘动态|招贤纳士)(?:\s*[>»…]+)?$')
# A detail route is often shared by the whole school's announcements column.
# A neutral application or vacancy label can still be verified in the body.
_INSPECT_TITLE = re.compile(r'岗位|职位|用人需求|人员需求|应聘|选调生|(?:申请|报名)(?:事项|须知|事宜|说明)|'
                            r'毕业生(?:双选|洽谈)会')
_SECTION_TITLE = re.compile(r'(?:公开|校园|社会|人才)?招聘(?:公告|启事|通知|信息|专栏|网站)?|'
                            r'人事(?:工作|信息|动态)|(?:通知|新闻|最新|站内)公告|公告详情|正文')
_ARTICLE_TITLE = re.compile(r'(?:^|[\s_-])(?:arti(?:cle)?[-_]?title|news[-_]?title|headline)(?=$|[\s_-])', re.I)
_ATTACHMENT_TITLE = re.compile(r'^附件|附件下载|点击下载|下载附件')


def _matches(text, source):
    terms = [s.strip() for s in source.get('include', []) if s.strip()]
    return any(s in text for s in terms) if terms else bool(_POSITIVE.search(text))


_CARD_FIELD = re.compile(r'\s*[\[【]\s*(日期|访问(?:量)?)\s*[\]】]\s*[:：]?\s*')


def _listing_label(anchor):
    visible = _clean(' '.join(anchor.itertext()))
    tip = _clean(anchor.get('title'))
    # Some schools wrap title, summary, publication date and visit count in a
    # single link. Read labelled metadata only from that link, before its row.
    published = ''
    for text in (visible, tip):
        for field in _CARD_FIELD.finditer(text):
            if field[1] == '日期' and (value := _iso(_DATE.match(text, field.end()))):
                published = value
                break
        if published:
            break
    heading = next((n for n in anchor.iter() if 'list-content-title' in n.get('class', '').split()), None)
    visible = _clean(''.join((heading if heading is not None else anchor).itertext()))
    visible, tip = (_CARD_FIELD.split(s, maxsplit=1)[0].strip() for s in (visible, tip))
    title = tip if tip and (not visible or visible.rstrip('.…') in tip) else visible
    return title, published


def _row_date(row, anchor):
    if row is None or any(a is not anchor for a in row.iter('a')):
        return ''
    # Only isolated row dates and publication labels are publish evidence.
    # Never borrow an application date printed in the title or a neighbouring row.
    lines = _lines(row, {'a'})
    values = set()
    for text in lines:
        text = _PUBLICATION.sub('', text, count=1).strip(' []【】()（）')
        if value := _iso(_DATE.fullmatch(text)):
            values.add(value)
    for node in row.iter('time'):
        if node.get('itemprop', '').lower() in ('', 'datepublished'):
            if value := _iso(_DATE.match(node.get('datetime', ''))):
                values.add(value)
    return values.pop() if len(values) == 1 else ''


def parse_listing(html: str, base_url: str, source: dict) -> list[dict]:
    """Extract candidate links. base_url is the listing's final response URL."""
    scope = _Scope(source)
    base = scope.resolve(base_url)
    if not base:
        return []
    root = _document(html, listing=True)
    parents = {child: parent for parent in root.iter() for child in parent}
    results = {}
    for anchor in root.iter('a'):
        url = scope.resolve(anchor.get('href'), base, detail=True)
        if not url or url == base or 'download' in anchor.attrib:
            continue
        title, card_date = _listing_label(anchor)
        if (not title or _EXCLUDE.search(title) or _ATTACHMENT_TITLE.search(title)
                or _MENU_TITLE.fullmatch(title)
                or not (_matches(title, source) or scope.pattern and _INSPECT_TITLE.search(title))):
            continue
        row = parents.get(anchor)
        while row is not None and row.tag not in {'li', 'tr', 'dd', 'p', 'div', 'section', 'body', 'document'}:
            row = parents.get(row)
        item = results.setdefault(url, {'url': url, 'title': title})
        if 'published' not in item:
            published = card_date
            if not published and row is not None and row.tag not in {'body', 'document'}:
                published = _row_date(row, anchor)
            if published:
                item['published'] = published
    return list(results.values())


# Only match an application label at a clause boundary. An unqualified
# “截止时间” also occurs for fees, exams, qualification checks and appeals.
_APPLICATION = r'(?:简历(?:接收|投递)|(?:网上|网络|线上|现场)?(?:报名|网申|申请|应聘|投递))'
_START_LABEL = r'(?:开始|起始|启动)(?:时间|日期|日)?'
_END_LABEL = r'(?:截止(?:时间|日期|日)?|截至|结束(?:时间|日期))'
_LABEL = re.compile(rf'^(?:[（(]?[一二三四五六七八九十0-9]+[)）.、]\s*)?(?:本次(?:招聘)?|本岗位)?'
                    rf'{_APPLICATION}(?:的)?(?P<kind>{_START_LABEL}|{_END_LABEL}|'
                    rf'(?:时间|日期|期限|期间)(?:{_START_LABEL}|{_END_LABEL})?|(?=自|从|至|于))'
                    r'\s*[:：]?\s*(?:为|是)?\s*')
_RANGE = re.compile(r'\s*(?:开始|起)?\s*(?:至|到|[~～—–-]+)\s*')
_SHORT_END = re.compile(rf'(?:({_MD})月\s*)?({_MD})[日号]')
_CLOCK = re.compile(r'\s*(?:[（(]北京时间[)）]\s*)?(上午|下午|晚上|中午|凌晨)?\s*'
                    r'(\d{1,2})(?::(\d{2})|[时点](?:(\d{1,2})分)?)')
_UNCERTAIN = re.compile(r'招满(?:即|为)止|额满(?:即|为)止|随时截止|分批(?:次)?报名|分阶段报名|'
                        r'各(?:岗位|批次)报名时间|(?:报名|申请)时间(?:以.*?为准|另行通知)|'
                        r'工作日|节假日除外|每天|每日')
_FOREIGN_ZONE = re.compile(r'当地时间|(?:美国|伦敦|纽约|香港以外|东京|欧洲|美东|美西)时间|'
                           r'(?<![A-Za-z])(?:UTC|GMT|EST|EDT|PST|PDT|CET|BST)\b', re.I)
_CLOSED = re.compile(r'^(?:本次|此次|本岗位)?(?:招聘)?(?:报名|招聘|投递|应聘)(?:通道|工作|申请)?'
                     r'(?:已|已经)(?:结束|关闭|截止)[了。！!]?$|^职位已下线[。！!]?$')
_BEIJING = timezone(timedelta(hours=8))


def _published(root, lines, fallback):
    for node in root.iter():
        key = (node.get('property') or node.get('name') or node.get('itemprop') or '').lower()
        if (node.tag == 'meta' and key in {'article:published_time', 'datepublished', 'pubdate',
                                           'publishdate', 'citation_publication_date', 'dcterms.issued'}
                or node.tag == 'time' and (key == 'datepublished' or 'pubdate' in node.attrib)):
            if value := _iso(_DATE.match(node.get('content') or node.get('datetime', ''))):
                return value
    for line in lines:
        for label in _PUBLICATION.finditer(line):
            if value := _iso(_DATE.match(line, label.end())):
                return value
    return _iso(_DATE.fullmatch(fallback or ''))


def _endpoint(text, pos=0, start=''):
    """Read one calendar date and its immediately attached clock."""
    match = _DATE.match(text, pos)
    if match:
        day = _iso(match)
    elif start and (match := _SHORT_END.match(text, pos)):
        first = date.fromisoformat(start)
        try:
            day = first.replace(month=_number(match[1]) if match[1] else first.month,
                                day=_number(match[2])).isoformat()
        except ValueError:
            return None
    else:
        return None
    if not day:
        return None
    return _clock_on(day, text, match.end())


def _clock_on(day, text, pos):
    time = _CLOCK.match(text, pos)
    if not time:
        return day, '', pos
    period, hour, colon_minutes, cn_minutes = time.groups()
    hour, minute = int(hour), int(colon_minutes or cn_minutes or 0)
    if hour > 23 or minute > 59 or (period and not 1 <= hour <= 12):
        return None
    if period in ('下午', '晚上') and hour < 12:
        hour += 12
    elif (period == '中午' and hour != 12) or (period in ('上午', '凌晨') and hour == 12):
        return None  # Ambiguous colloquial clock.
    return day, f'{hour:02d}:{minute:02d}', time.end()


def _boundaries(clause, label):
    value = clause[label.end():].strip()
    kind = label['kind']
    start_label = re.search(_START_LABEL + '$', kind) or value.startswith(('自', '从'))
    end_label = re.search(_END_LABEL + '$', kind) or value.startswith('至')
    value = re.sub(r'^(?:自|从|至|于|到)\s*', '', value)
    # “即日起” has no absolute start date. Its labelled end can stand alone.
    relative = re.match(r'(?:即日|即刻|公告发布之日|本公告发布之日)起?\s*(?:至|到)\s*', value)
    if relative:
        value, end_label = value[relative.end():], True
    first = _endpoint(value)
    if not first:
        return None
    day, clock, pos = first
    if join := _RANGE.match(value, pos):
        last = _endpoint(value, join.end(), day)
        if not last and clock and _CLOCK.match(value, join.end()):
            # A range with two clocks on one explicitly named day.
            last = _clock_on(day, value, join.end())
        if not last or end_label:
            return None
        result = [('applicationStart', day, clock), ('deadline', *last[:2])]
        pos = last[2]
    elif end_label or re.fullmatch(r'\s*(?:截止|结束)\s*', value[pos:]):
        result = [('deadline', day, clock)]
    elif start_label or re.match(r'\s*(?:起|开始)', value[pos:]):
        result = [('applicationStart', day, clock)]
    else:
        return None
    # Reject unparsed extra dates, malformed clocks, exceptions and alternatives.
    if not re.fullmatch(r'\s*(?:前|止|截止|结束|开始|起)?\s*(?:[（(]北京时间[)）])?\s*', value[pos:]):
        return None
    return result


def _window_lines(article):
    # Keep inline <time> and two-column label/value rows. Never combine dates
    # across sibling rows, headings, attachment links or unrelated paragraphs.
    skip = {'head', 'h1', 'title', 'a'}
    # Many institutional sites use layout tables containing full paragraphs.
    # Read their text normally and additionally join explicit label/value cells.
    lines = [s for s in _lines(article, skip) if not _LABEL.fullmatch(normalize('NFKC', s))]
    for row in article.iter('tr'):
        cells = [c for c in row if c.tag in {'td', 'th'}]
        if len(cells) == 2:
            label, value = (' '.join(_lines(c, skip)) for c in cells)
            if _LABEL.fullmatch(normalize('NFKC', label)):
                lines.append(label + ' ' + value)
    return [s for s in lines if not _ATTACHMENT_TITLE.search(s) and not _FILE.search(s)
            and not _BOILERPLATE.search(s)]


def _uncertain_scope(text):
    phases = set(re.findall(r'第([一二三四五六七八九十0-9]+)(?:批(?:次)?|阶段|轮)', text))
    return len(phases) > 1 or bool(re.search(
        r'延长报名|延期报名|补报名|原报名|原定报名|重新报名|分批(?:次)?报名|'
        r'(?:另行|单独)报名|(?:招满|额满)(?:即|为)止|(?:甲|乙|[AB]|其他|部分|不同)(?:类)?岗(?:位)?.{0,10}(?:报名|申请)|'
        r'(?:报名|申请)(?:时间|日期)(?:以[^。；\n]+为准|另行通知)|(?:原定|原计划|原公告).{0,15}(?:报名|申请)', text))


def _application_window(text):
    blank = {'applicationStart': '', 'deadline': '', 'windowVerified': False}
    values = {}
    if _uncertain_scope(text) or _FOREIGN_ZONE.search(text):
        return blank
    for line in text.splitlines():
        application_clause = False
        for clause in re.split(r'[。；;，,！!]', line):
            clause = clause.strip()
            if not (label := _LABEL.match(clause)):
                # A second bare range after a comma/line break can be an
                # alternative window. An explicitly labelled exam/fee date is separate.
                if (application_clause and re.match(r'(?:或|以及|另)?\s*(?:\d{4}[-./年]|\d{1,2}月|\d{1,2}:)', clause)
                        and re.search(r'至|到|~|—|:|\s-\s', clause)):
                    return blank
                continue
            application_clause = True
            if _UNCERTAIN.search(line):
                return blank
            endpoints = _boundaries(clause, label)
            if not endpoints:
                return blank
            for key, day, clock in endpoints:
                if key in values:
                    old_day, old_clock = values[key]
                    if day != old_day or (clock and old_clock and clock != old_clock):
                        return blank
                    clock = clock or old_clock
                values[key] = day, clock
    result = blank.copy()
    for key, (day, clock) in values.items():
        result[key] = day
        if clock:
            result[key + 'Time'] = clock
    if len(values) == 2:
        start, end = values['applicationStart'], values['deadline']
        if start[0] > end[0] or (start[0] == end[0] and all((start[1], end[1])) and start[1] >= end[1]):
            return blank
        result['windowVerified'] = True
    return result


def _beijing_check(checked):
    if len(checked) == 10:
        return date.fromisoformat(checked).isoformat(), ''
    instant = datetime.fromisoformat(checked)
    local = instant.astimezone(_BEIJING) if instant.tzinfo else instant
    return local.date().isoformat(), local.strftime('%H:%M')


def application_status(window, checked):
    """Classify saved evidence at an ISO date/instant, in Beijing time."""
    today, now = _beijing_check(checked)
    start, end = window.get('applicationStart'), window.get('deadline')
    opens, closes = window.get('applicationStartTime'), window.get('deadlineTime')
    if end and (today > end or (today == end and closes and now and now >= closes)):
        return 'closed'
    if start and (today < start or (today == start and opens and now and now < opens)):
        return 'upcoming'
    if not window.get('windowVerified') or (not now and (today == start and opens or today == end and closes)):
        return 'unknown'
    return 'open'


# Match position names. A major, certification, past job or attachment label is
# insufficient. A punctuation/cell boundary can never join subject and position.
_SUBJECT = r'(?:信息科技|信息技术|计算机)'
_TEACHING = r'(?:(?:学科|课程|专业课)?(?:专任|专职)?教师|(?:学科)?教学岗)'
_COMPUTING = rf'(?:{_SUBJECT}\s*{_TEACHING}|{_TEACHING}\s*[（(]\s*{_SUBJECT}\s*[)）])'
_ROLE_PATTERNS = {key: re.compile(pattern) for key, pattern in (
    ('computing-teacher', _COMPUTING),
    ('secondary-school-teacher', r'(?:高中|初中|中学)(?:语文|数学|英语|物理|化学|生物|历史|地理|政治|体育|音乐|美术)教师'),
    ('instructional-designer', r'(?:教学|数字课程|在线课程)设计师'),
    ('learning-media', r'课程视频制作工程师'),
    ('short-video-editor', r'短视频(?:剪辑师|编导)'),
    ('visual-merchandiser', r'(?:视觉|商品)陈列师'),
    ('beauty-advisor', r'美容顾问'),
    ('software-test-engineer', r'软件测试工程师'),
    ('embedded-software-engineer', r'嵌入式软件(?:开发)?工程师'),
    ('data-analyst', r'数据分析师'),
    ('product-manager', r'产品经理'),
)}
_QUALIFICATION = re.compile(r'资格证|教师资格|教师证|工作经验|任教经验|工作经历|专业要求|所学专业|任职资格|'
                            r'持有|须持|曾任|优先考虑|协助|配合|服务于|教师培训|信息中心.{0,8}技术岗|不招聘|不设|不含|不招|无需|不涉及')
_POSITION = re.compile(r'招聘|招收|招募|诚聘|拟聘请|选聘|岗位|职位|职务')


def _position_lines(article):
    # Role names in a qualifications column, even standalone, describe the
    # applicant. Keep cells separate and use the position column when labelled.
    for line in _lines(article, _SKIP_TEXT | {'table'}):
        if not (_BOILERPLATE.search(line) or _METADATA.search(line) or _FILE.search(line)):
            yield line
    for table in article.iter('table'):
        columns = None
        for row in table.findall('./tr') + table.findall('./thead/tr') + table.findall('./tbody/tr'):
            cells = [c for c in row if c.tag in {'th', 'td'}]
            labels = [' '.join(_lines(c, _SKIP_TEXT)) for c in cells]
            header = [i for i, text in enumerate(labels) if re.fullmatch(
                r'(?:招聘|招考|需求)?(?:岗位|职位|职务)(?:名称)?', text)]
            if header or any(c.tag == 'th' for c in cells):
                columns = header
                continue
            if labels and re.fullmatch(r'(?:所学专业|专业要求|任职条件|学历要求)', labels[0]):
                continue
            for i, text in enumerate(labels):
                if (columns is None or i in columns) and not _FILE.search(text):
                    yield text


def _roles(title, lines):
    found = set()
    for line in [title, *lines]:
        if _ATTACHMENT_TITLE.search(line):
            continue
        for phrase in re.split(r'[，,。；;！!？?]', line):
            if _QUALIFICATION.search(phrase):
                continue
            for key, pattern in _ROLE_PATTERNS.items():
                match = pattern.search(phrase)
                if not match:
                    continue
                # Accept a title, a labelled vacancy or a standalone role/table cell.
                if (line == title or _POSITION.search(phrase[:match.start()]) or
                        re.fullmatch(r'[（(]?(?:(?:小学|初中|高中|中小学|中职|中学|职校)\s*)?', phrase[:match.start()].strip())
                        and re.match(r'\s*(?:$|岗|[（(、：:]|\d+\s*[名人])', phrase[match.end():])):
                    found.add(key)
    return [key for key in _ROLE_PATTERNS if key in found]


_CITIES = {'北京', '上海', '广州', '深圳', '南京', '成都'}
_BATCH = re.compile(r'多[所校地]|跨[省市区]|各[地校]|各高校|所属学校|直属学校|部分学校|所属中小学|全省|'
                    r'联合招聘|学校汇总|岗位汇总|学校名单|省(?:教育厅)?直属|[两三四五六七八九十数多\d]+所(?:中小学|学校)|'
                    r'multi[-_ ]?school|多校|全国各地|多城市|省属(?:中小学|学校|高校|事业单位)', re.I)
_PLATFORM = re.compile(r'就业(?:网|信息|指导|服务)|公共招聘|人才网|教育局|教育厅|人社局|多校|联合招聘|multi[-_ ]?school|career[-_]?board|aggregator', re.I)
_LOCATION = re.compile(r'(?:工作(?:城市|地点|地区|地)|任教地点|岗位地点|任职地点)\s*[:：为]\s*([^。；;\n]+)')
_EMPLOYER = re.compile(r'(?:^|[；;])\s*(?:招聘单位|用人单位|雇主)\s*[:：]\s*([^。；;，,]{2,70})')


def _location(title, lines, source):
    configured = source.get('city', '').strip().removesuffix('市')
    cities = _CITIES | ({configured} if 1 < len(configured) < 12 and
                        not re.search(r'全国|多地|[、,，/与和]', configured) else set())
    locs = [m[1] for text in [title, *lines] for m in _LOCATION.finditer(text)]
    if locs:
        identified = set()
        for loc in locs:
            # Require a single named location. A mixed list, even with a city
            # outside the catalog, cannot support a single-city filter.
            if re.search(r'[、,/，或及和]|全国|多地|待定|另行|未定', loc):
                return ''
            hits = {c for c in cities if c in loc}
            if len(hits) != 1:
                return ''
            identified.update(hits)
        return identified.pop() if len(identified) == 1 else ''
    batch = _BATCH.search('\n'.join([source['name'], source['kind'], title, *lines]))
    platform = _PLATFORM.search(source['name'] + ' ' + source['kind'])
    # A city education authority's named municipal batch is local even if
    # individual schools/subjects are only listed in a separate attachment.
    jurisdictions = {c for c in cities if re.search(re.escape(c) + r'市(?:教育局|所属|直属|属学校|各区|[\u4e00-\u9fff]{2,5}区(?:教育局|所属|直属))', title)}
    if len(jurisdictions) == 1 and sum(c in title for c in cities) == 1:
        return jurisdictions.pop()
    if batch or platform or any(c != configured and c in title for c in cities):
        return ''
    return configured if configured in cities else ''


_SKIP_TEXT = {'head', 'a', 'h1', 'time', 'title'}
_BOILERPLATE = re.compile(r'^(?:当前位置|上一篇|下一篇|上一条|下一条|公告列表$|通知公告$|新闻列表$|相关(?:新闻|链接|公告)|友情链接|'
                          r'版权所有|Copyright\b|打印(?:本页|文章)|关闭窗口|浏览次数|点击次数)', re.I)
_METADATA = re.compile(r'^(?:发布(?:时间|日期)|来源|作者|编辑|日期|浏览量|点击量|更新时间)\s*[:：]')
_RESULT_TEXT = re.compile(r'(?:现将|现予|现对)[^。；，！？]{0,35}(?:名单(?:予以|进行)?公示|成绩(?:予以)?公布|体检名单)|'
                          r'(?:本公告|本文)为.{0,12}(?:更正|成绩|拟聘用|招标)(?:公告|通知|公示)')


def _article(root):
    for node in root.iter():
        if _CONTENT.search(_marks(node)):
            return node
    for tag in ('article', 'main', 'body'):
        if (node := next(root.iter(tag), None)) is not None:
            return node
    return root


def _heading(root, article, listed, source):
    # WebPlus puts the masthead before the article and its labelled heading
    # outside wp_articlecontent. Linked headings belong to other stories.
    nodes = [n for n in root.iter() if _ARTICLE_TITLE.search(_marks(n))]
    nodes.extend(article.iter('h1'))
    nodes.extend(root.iter('h1'))
    nodes.extend(root.iter('title'))
    candidates = []
    generic = ''
    specific_listing = (listed and _matches(listed, source)
                        and not (_SECTION_TITLE.fullmatch(listed) or _MENU_TITLE.fullmatch(listed)))
    truncated = listed.endswith(('…', '...'))
    for node in dict.fromkeys(nodes):
        if node.tag == 'a' or node.find('.//a') is not None:
            continue
        text = _clean(''.join(node.itertext()))
        if node.tag == 'title':
            text = re.split(r'\s+[-–—]\s+|-{2,}|\s*[|｜]\s*', text, maxsplit=1)[0]
        if not text:
            continue
        if _SECTION_TITLE.fullmatch(text) or _MENU_TITLE.fullmatch(text):
            generic = generic or text
            continue
        if _EXCLUDE.search(text):
            return text  # A result/correction supersedes a stale listing title.
        if truncated and text.startswith(listed.rstrip('….').strip()):
            return text
        if _matches(text, source) and (not specific_listing or text == listed):
            return text
        candidates.append(text)
    return listed or generic or next(iter(candidates), '')


def parse_notice(html: str, url: str, link: dict, source: dict, checked: str) -> dict | None:
    """Return a candidate with a short body excerpt and its canonical source URL."""
    scope = _Scope(source)
    final = scope.resolve(url, detail=True)
    if not final or (link.get('url') and not scope.resolve(link['url'], source['url'], detail=True)):
        return None
    root = _document(html)
    article = _article(root)
    # A rolling careers page can stay online after a specific year's vacancy disappears.
    if source.get('requiredText'):
        body = _clean(' '.join(root.itertext())).casefold()
        if any(_clean(term).casefold() not in body for term in source['requiredText']):
            return None
    listed = _CARD_FIELD.split(_clean(link.get('title')), maxsplit=1)[0].strip()
    title = _heading(root, article, listed, source)
    if not title or _EXCLUDE.search(title) or _EXCLUDE.search(link.get('title', '')):
        return None
    lines = [s for s in _lines(article, _SKIP_TEXT) if s != title and not _BOILERPLATE.search(s)]
    prose = [s for s in lines if not _METADATA.search(s) and not _DATE.fullmatch(s)]
    evidence = [s for s in prose if not _ATTACHMENT_TITLE.search(s) and not _FILE.search(s)]
    if not prose or all(s.rstrip('：:') == '附件' for s in prose):
        # An attachment link may be the only visible content under a valid
        # vacancy title. Keep its visible label as the excerpt, never as a role.
        labels = [_clean(''.join(a.itertext())) for a in article.iter('a')
                  if _FILE.search(unquote(a.get('href', ''))) or 'download' in a.attrib]
        attachments = [s for s in labels if s]
        if attachments:
            prose = [(prose[0] if prose else '') + attachments[0]]
    # A WebPlus PDF player can be the entire article. Validate its in-scope
    # PDF reference as evidence of an attachment, without reading the file.
    embedded_pdf = not prose and any(
        urlsplit(scope.resolve(node.get('pdfsrc'), final)).path.lower().endswith('.pdf')
        for node in article.iter() if 'wp_pdf_player' in node.get('class', '').split())
    if (not (prose or embedded_pdf) or not any(_matches(text, source) for text in [title, *evidence])
            or any(_RESULT_TEXT.search(s) for s in evidence)):
        return None
    excerpt = ' '.join(evidence or prose)
    schedule = normalize('NFKC', '\n'.join([title, *_window_lines(article)]))
    window = _application_window(schedule)
    published = _published(root, _lines(root, {'head', 'a', 'title'}), link.get('published'))
    check_date, _ = _beijing_check(checked)
    status = application_status(window, checked)
    if not _uncertain_scope(schedule) and any(
            _CLOSED.fullmatch(part.strip()) for line in evidence for part in re.split('[。；;！!]', line)):
        status = 'closed'
        window = {'applicationStart': '', 'deadline': '', 'windowVerified': False}
    company = next((m[1].strip() for text in prose if (m := _EMPLOYER.search(text))), '')
    if not company and not _PLATFORM.search(source['name'] + ' ' + source['kind']):
        company = source['name'].split(' · ', 1)[0]
    identity = hashlib.sha256((source['id'] + '\0' + final).encode('utf-8')).hexdigest()[:20]
    return {
        'id': 'notice-' + identity, 'title': title, 'employer': company,
        'city': _location(title, evidence, source), 'roleIds': _roles(title, _position_lines(article)),
        'requirement': excerpt if len(excerpt) <= 240 else excerpt[:239].rstrip() + '…',
        'url': final, 'published': published, **window,
        **({'conditionalVacancy': True} if re.search(r'(?:招满|额满|聘满|录满|满额)(?:即止|为止)', schedule) else {}),
        'applicationStatus': status, 'closed': status == 'closed',
        'checked': check_date, 'sourceId': source['id'], 'recordType': 'notice',
    }
