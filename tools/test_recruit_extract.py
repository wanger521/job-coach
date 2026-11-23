"""Offline regression fixtures. Run with python -B -m unittest tools.test_recruit_extract."""

import unittest
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError

if __package__:
    from . import update_recruitment as updater
    from .recruit_extract import parse_listing, parse_notice
else:
    import update_recruitment as updater
    from recruit_extract import parse_listing, parse_notice


BASE = 'https://school.example/list/index.htm'
URL = 'https://school.example/info/123.htm'
SOURCE = {'id': 'nj-school', 'name': '星河中学', 'url': BASE, 'city': '南京', 'kind': '学校官网'}
TITLE = '星河中学公开招聘教师公告'
CHECKED = '2026-11-23'


def notice(body, *, title=TITLE, source=SOURCE, link=None, url=URL, checked=CHECKED):
    html = f'<article><header><h1>{title}</h1></header>{body}</article>'
    return parse_notice(html, url, link or {'url': URL, 'title': title}, source, checked)


class ListingTests(unittest.TestCase):
    def test_order_title_entities_optional_end_tags_and_date_enrichment(self):
        html = '''<base href="https://wrong.example/"><ul>
          <li><a href="../info/123.htm#first" title="星河中学公开招聘教师公告">星河中学公开…</a>
          <li><a href="/info/456.htm?id=1&amp;b=2">校园招聘 · <b>研发岗位</b></a> 2026年11月8日
          <li><a href="https://SCHOOL.example:443/info/123.htm#copy">教师招聘</a> 二〇二六年十一月三日
          <li><a href="/info/456.htm?id=2&amp;b=2">校园招聘第二批</a></ul>'''
        self.assertEqual(parse_listing(html, BASE, SOURCE), [
            {'url': URL, 'title': TITLE, 'published': '2026-11-03'},
            {'url': URL.replace('123.htm', '456.htm?id=1&b=2'), 'title': '校园招聘 · 研发岗位', 'published': '2026-11-08'},
            {'url': URL.replace('123.htm', '456.htm?id=2&b=2'), 'title': '校园招聘第二批'},
        ])

    def test_jiangning_card_with_date_and_views_inside_anchor(self):
        html = '''<div class="list-imgs-wrap"><a href="/info/123.htm" title="高中政治短期代课教师招聘公告">
          <div class="list-img"><img src="/uploads/images/cover.png"></div>
          <div class="list-imgs-content"><div class="list-content-title">高中政治短期代课教师招聘公告</div>
          <div class="list-content-short">本批次安排见正文</div>
          <div class="list-content-remark">[日期]：2026年11月18日      [访问]：638</div></div></a></div>
        <a href="/info/124.htm">星河校招 [日期]：2026年11月5日 [访问]：88</a>'''
        first, second = parse_listing(html, BASE, SOURCE)
        self.assertEqual(first, {'url': URL, 'title':'高中政治短期代课教师招聘公告', 'published':'2026-11-18'})
        self.assertEqual(second['title'], '星河校招')
        self.assertEqual(second['published'], '2026-11-05')
        self.assertEqual(notice('<p>具体安排见正文。</p>', link=first)['published'], '2026-11-18')

    def test_one_date_belongs_to_one_row(self):
        html = '''<table><tr><td><a href="a">研发岗校招</a></td><td>2024/2/29</td></tr>
        <tr><td><a href="b">2026年10月9日前报名：教师招聘</a></td><td>报名截止：2026年10月9日</td></tr>
        <tr><td><a href="c">校招第三批</a></td><td><time datetime="2025-02-29"></time></td></tr></table>
        <div><a href="d">校招第四批</a><a href="e">校招第五批</a>2026-12-12</div>'''
        self.assertEqual([r.get('published') for r in parse_listing(html, BASE, SOURCE)],
                         ['2024-02-29', None, None, None, None])

    def test_fixed_origins_attachments_and_detail_regex(self):
        config = dict(SOURCE, detailPattern=r'^/info/\d+\.htm(?:\?|$)', allowedHosts=['news.example'])
        urls = [URL, '//news.example/info/555.htm', 'http://school.example/info/7.htm',
                'https://evil.school.example/info/8.htm', '//news.example.evil.example/info/9.htm',
                '//news.example:8443/info/10.htm', 'https://school.example@evil.example/info/11.htm',
                'https://evil.example@school.example/info/12.htm', 'javascript:alert(1)', 'mailto:x@y',
                '//school.example\\@evil.example/info/14.htm', '/manual/15.htm', '../info/file.pdf',
                '/info/123.htm?file=岗位%2EXLSX', '/download/16.htm', '#top', '', 'https://[bad']
        html = ''.join(f'<a href="{escape(h)}">招聘简章</a>' for h in urls)
        html += '<a href="/info/2.htm" download>校园招聘</a><a href="/info/3.htm">附件下载：招聘简章</a>'
        self.assertEqual([r['url'] for r in parse_listing(html, BASE, config)],
                         [URL, 'https://news.example/info/555.htm'])
        self.assertEqual(parse_listing(html, 'https://evil.example/list', config), [])
        self.assertIsNone(notice('招聘信息见正文。', url='https://evil.example/detail', source=config))
        self.assertIsNone(notice('招聘信息见正文。', url='https://news.example/wrong', source=config))

    def test_attachment_routes_without_pattern(self):
        for link in ['a.ZIP#page', 'files/%E5%B2%97%2Epdf', 'fileDownload.jsp?id=6',
                     'download/file?id=1', '附件.docx?v=1']:
            with self.subTest(link=link):
                self.assertEqual(parse_listing(f'<a href="{link}">招聘简章</a>', BASE, SOURCE), [])

    def test_exclusions_override_include_and_url_pattern(self):
        for reason in ['拟聘用人员公示', '笔试成绩', '体检通知', '拟录名单', '更正公告', '招标公告', '入围名单']:
            with self.subTest(reason=reason):
                title = TITLE + reason
                config = dict(SOURCE, include=['招聘'], detailPattern='/info/')
                self.assertEqual(parse_listing(f'<a href="{URL}">{title}</a>', BASE, config), [])
                self.assertIsNone(notice('现招聘教师。', title=title, source=config))
                self.assertIsNone(notice('现招聘教师。', title=title, link={'title': TITLE}, source=config))

    def test_general_notice_list_filters_neighbours_sharing_detail_urls(self):
        source = dict(SOURCE, detailPattern=r'/info/\d+\.htm$', include=['招聘', '选聘'])
        titles = ['食堂2026年11月23日至27日菜单', '2026-2027学年AP考试报名通知',
                  '初中招生简章', '中学生英才计划校级选拔通知', '第一期学生课题的招募计划书',
                  '学校运动会新闻', '2026年11月20日就业信息汇总', '关于本年度申请事项的说明',
                  '南京外国语学校机房实验员招聘启事', '招生办公室工作人员招聘公告']
        html = ''.join(f'<li><a href="/info/{i}.htm">{t}</a></li>' for i, t in enumerate(titles))
        self.assertEqual([r['title'] for r in parse_listing(html, BASE, source)], titles[-3:])

    def test_menu_and_page_furniture(self):
        anchor = f'<a href="{URL}">{TITLE}</a>'
        html = f'<nav>{anchor}</nav><footer>{anchor}</footer><div class="menu">{anchor}</div><script>{anchor}</script>'
        self.assertEqual(parse_listing(html, BASE, SOURCE), [])


class NoticeTests(unittest.TestCase):
    def test_contract_for_company_and_stable_id(self):
        source = dict(SOURCE, id='tech', name='星河科技', kind='企业招聘')
        row = {'url': URL + '#top', 'title': '星河科技秋季校园招聘'}
        body = '<p>招聘岗位：嵌入式软件工程师、软件测试工程师。</p><p>面向应届毕业生。</p>'
        item = notice(body, title=row['title'], link=row, source=source, url=URL + '#first')
        self.assertEqual(set(item), set('id title employer city roleIds requirement url published applicationStart deadline windowVerified applicationStatus closed checked sourceId recordType'.split()))
        self.assertEqual({**item, 'id': 'stable'}, {
            'id': 'stable', 'title': row['title'], 'employer': '星河科技', 'city': '南京',
            'roleIds': ['software-test-engineer', 'embedded-software-engineer'],
            'requirement': '招聘岗位：嵌入式软件工程师、软件测试工程师。 面向应届毕业生。',
            'url': URL, 'published': '', 'applicationStart': '', 'deadline': '', 'closed': False,
            'windowVerified': False, 'applicationStatus': 'unknown',
            'checked': CHECKED, 'sourceId': 'tech', 'recordType': 'notice',
        })
        self.assertEqual(item['id'], notice(body, title='更新标题：秋季校园招聘', source=source,
                                            checked='2026-11-24')['id'])
        self.assertNotEqual(item['id'], notice(body, url=URL + '?id=2', source=source)['id'])

    def test_njupt_masthead_and_full_article_heading(self):
        full = '南京邮电大学2026年面向社会公开招聘工作人员（人事代理）公告（第七批）'
        html = f'''<head><title>{full}</title></head><div><h1>教师工作部、人事处</h1></div>
        <div><h1 class="arti_title">{full}</h1><h2 class="arti_title"></h2>
        <div class="wp_articlecontent"><p>应聘者请按要求提交材料。</p></div></div>'''
        for listed in [full, full[:21] + '…', '教师工作部、人事处', '']:
            with self.subTest(listed=listed):
                item = parse_notice(html, URL, {'title': listed}, SOURCE, CHECKED)
                self.assertEqual(item['title'], full)
                self.assertEqual(item['requirement'], '应聘者请按要求提交材料。')

    def test_specific_listing_title_survives_section_headings(self):
        for heading in ['教师工作部、人事处', '人才招聘', '校园招聘', '公开招聘公告', '教学科研部']:
            with self.subTest(heading=heading):
                html = f'<h1>{heading}</h1><main><h2>通知公告</h2><p>请提交个人简历。</p></main>'
                self.assertEqual(parse_notice(html, URL, {'title': TITLE}, SOURCE, CHECKED)['title'], TITLE)

    def test_detail_result_heading_vetoes_stale_positive_list_title(self):
        html = f'''<title>{TITLE}</title><h1>通知公告</h1><h2 class="arti_title">招聘成绩公示</h2>
        <div class="wp_articlecontent"><p>本次招聘工作现已完成。</p></div>'''
        self.assertIsNone(parse_notice(html, URL, {'title': TITLE}, SOURCE, CHECKED))

    def test_neighbor_widget_cannot_supply_title_or_body_evidence(self):
        html = '''<main><h1>关于本年度申请事项的说明</h1><p>本次申请仅针对校内社团。</p>
        <div class="wp entry article-neighbors"><h2 class="arti_title">信息技术教师招聘公告</h2>
        <p>招聘岗位：信息技术教师。</p><p>报名截止：2026年11月15日。</p></div></main>'''
        self.assertIsNone(parse_notice(html, URL, {}, SOURCE, CHECKED))
        real = html.replace('本次申请仅针对校内社团。', '本次公开招聘工作人员。')
        item = parse_notice(real, URL, {}, SOURCE, CHECKED)
        self.assertEqual((item['title'], item['requirement'], item['roleIds'], item['deadline']),
                         ('关于本年度申请事项的说明', '本次公开招聘工作人员。', [], ''))

    def test_webplus_list_layout_with_recruitment_procedure(self):
        html = f'''<body class="list pagelist"><div class="col_news_list listcon">
        <div class="article"><h1 class="arti_title">{TITLE}</h1><div class="wp_articlecontent">
        <p>请提交个人简历。未达到开考比例时，部分岗位取消、核减招聘计划。</p>
        <p>拟聘用人员将公示。现将流程说明如下：入围名单将在网站公示。</p>
        <div class="news-list">其他岗位招聘已结束。</div></div></div></div></body>'''
        item = parse_notice(html, URL, {'title': TITLE}, SOURCE, CHECKED)
        self.assertIn('请提交个人简历', item['requirement'])
        self.assertNotIn('其他岗位', item['requirement'])
        self.assertFalse(item['closed'])

    def test_embedded_pdf_is_article_evidence_without_inventing_excerpt(self):
        for href, allowed in [('/_upload/article/notice.pdf', True), ('https://other.example/job.pdf', False),
                              ('javascript:void(0)', False), ('/images/logo.png', False)]:
            with self.subTest(href=href):
                html = f'''<body class="list"><h1 class="arti_title">{TITLE}</h1><div class="wp_articlecontent">
                <div class="wp_pdf_player" pdfsrc="{href}"></div></div></body>'''
                row = parse_notice(html, URL, {'title': TITLE}, SOURCE, CHECKED)
                if allowed:
                    self.assertEqual((row['url'], row['requirement'], row['roleIds'], row['deadline']), (URL, '', [], ''))
                    self.assertIsNone(parse_notice(html.replace(TITLE, '拟聘用人员公示'), URL, {'title': TITLE}, SOURCE, CHECKED))
                else:
                    self.assertIsNone(row)

    def test_cancellation_and_results_override_positive_listing(self):
        for title in ['关于部分岗位取消、核减招聘计划的公告', '教师招聘岗位取消/核减公告',
                      '教师招聘部分岗位核减公告', '2025年招聘工作人员进入面试考生名单']:
            with self.subTest(title=title):
                config = dict(SOURCE, detailPattern='/info/')
                self.assertEqual(parse_listing(f'<a href="{URL}">{title}</a>', BASE, config), [])
                self.assertIsNone(notice('<p>请查阅原招聘公告。</p>', title=title, link={'title': TITLE}))
        self.assertIsNone(notice('<p>现将本批招聘拟聘用人员名单公示如下。</p>'))

    def test_detail_keywords_and_literal_include(self):
        source = dict(SOURCE, detailPattern='/info/', include=['青苗计划+'])
        html = f'<li><a href="{URL}">关于本年度申请事项的说明</a></li>'
        row, = parse_listing(html, BASE, source)
        self.assertIsNone(notice('<p>请关注青苗计划。</p>', title=row['title'], link=row, source=source))
        self.assertIsNotNone(notice('<p>青苗计划+即日起接受申请。</p>', title=row['title'], link=row, source=source))
        self.assertIsNotNone(notice('<p>本公司面向应届生公开招聘。</p>', title='关于申请事项的说明'))
        self.assertIsNone(notice('<p>本次为校园开放日。</p>', title='关于申请事项的说明'))

    def test_clean_excerpt_and_role_evidence(self):
        html = '''<head><title>网页标题</title></head><nav>招聘信息技术教师</nav>
        <main><h1>招聘启事</h1><div class="wp_articlecontent"><p>招聘岗位：数据分析师。</p>
        <div id="news-list"><h3>更多招聘公告</h3><p>招聘岗位：计算机教师。</p></div>
        <script>报名已经截止</script><style>菜单</style><p hidden>计算机教学岗</p>
        <a href="other.htm">信息科技教师招聘</a><p>按通知提交材料，后续将组织体检、公示。</p></div></main>
        <footer>友情链接 工作地点：北京</footer>'''
        item = parse_notice(html, URL, {}, SOURCE, CHECKED)
        self.assertEqual(item['requirement'], '招聘岗位：数据分析师。 按通知提交材料，后续将组织体检、公示。')
        self.assertEqual(item['roleIds'], ['data-analyst'])
        self.assertFalse(item['closed'])
        self.assertIsNone(parse_notice('<nav>校园招聘</nav><p>学校运动会简讯。</p>', URL, {'title':'学校简讯'}, SOURCE, CHECKED))
        self.assertIsNone(notice('<ul><li><a href="other.htm">招聘信息科技教师</a></li></ul>'))
        self.assertLessEqual(len(notice('<p>' + '任职说明。' * 100 + '</p>')['requirement']), 240)

    def test_publication_and_application_windows(self):
        body = '<p>发布时间：二〇二六年十月三十一日</p><p>报名时间：2026年11月1日9:00起至2026年11月23日17:00。</p>'
        item = notice(body, link={'title': TITLE, 'published':'2025-01-02'})
        self.assertEqual((item['published'], item['deadline'], item['closed']), ('2026-10-31', CHECKED, False))
        self.assertTrue(notice(body, checked='2026-11-24')['closed'])
        self.assertEqual(notice('<p>报名截止时间为２０２６年１２月８日。</p>')['deadline'], '2026-12-08')
        self.assertTrue(notice('<p>本次报名已结束。</p>')['closed'])

    def test_metadata_and_row_date(self):
        html = '''<head><meta property="article:modified_time" content="2026-11-22">
        <meta name="datePublished" content="2026-11-01T12:00:00+08:00"></head>
        <article><h1>企业校园招聘简章</h1><p>本次招聘对象为应届生。</p></article>'''
        self.assertEqual(parse_notice(html, URL, {}, SOURCE, CHECKED)['published'], '2026-11-01')
        self.assertEqual(notice('<p>招收应届生。</p>', link={'title': TITLE, 'published':'2024-02-29'})['published'], '2024-02-29')

    def test_no_dates_from_incidental_invalid_or_partial_references(self):
        for content in ['更新日期：2026-11-22；考试时间：2026年12月1日。',
                        '报名自2026年11月1日起；截止时间另行通知。',
                        '报名时间：2026年12月1日至1月30日。', '面试材料截止时间：2026年12月1日。',
                        '发布时间：2025年2月29日；报名截止：2026年13月3日。',
                        '宣讲会定于2026年12月1日，招满即止。']:
            with self.subTest(content=content):
                item = notice(f'<p>{content}</p><p>应聘者请查看岗位说明。</p>')
                self.assertEqual((item['published'], item['deadline'], item['closed']), ('', '', False))
        self.assertEqual(notice('<p>甲岗报名截止：2026-10-01。</p><p>乙岗报名截止：2026-12-01。</p>')['deadline'], '')

    def test_teaching_subject_is_attached_to_position(self):
        for label in ['高中信息科技教师', '信息技术教学岗', '计算机专任教师', '教师（信息技术）',
                      '<span>信息科技</span><b>教师</b>', '计算机教学岗位']:
            with self.subTest(label=label):
                self.assertEqual(notice(f'<p>招聘岗位：{label}1名。</p>')['roleIds'], ['computing-teacher'])
        self.assertEqual(notice('<table><tr><td>高中信息科技教师</td><td>须持证</td></tr></table>')['roleIds'], ['computing-teacher'])

    def test_technical_staff_qualifications_and_missing_subject(self):
        for content in ['信息中心技术岗，所学专业为计算机，负责协助教师开展教学。',
                        '招聘岗位：数学教师；专业要求：信息技术或计算机。',
                        '岗位：信息中心技术岗（协助信息技术教师授课）。',
                        '优先考虑持有信息技术教师资格证的人员。',
                        '须有计算机教师工作经验。', '本校招聘教师，各学科岗位详见附件。',
                        '附件：信息科技教师岗位表.xlsx',
                        '<table><tr><td>计算机</td><td>教师</td></tr></table>',
                        '本次不招聘计算机教师。', '信息技术支持以及面向教师的教务工作。']:
            with self.subTest(content=content):
                self.assertEqual(notice(f'<div>{content}</div>')['roleIds'], [])

    def test_attachment_only_notice_produces_excerpt_without_a_subject(self):
        row = notice('<p>附件：<a href="/files/jobs.xlsx">信息科技教师岗位表.xlsx</a></p>')
        self.assertEqual(row['requirement'], '附件：信息科技教师岗位表.xlsx')
        self.assertEqual(row['roleIds'], [])
        self.assertEqual(row['url'], URL)

    def test_qualifications_column_cannot_assign_a_role(self):
        header = '<tr><th>招聘岗位</th><th>专业要求</th></tr>'
        for vacancy, major, expected in [('信息中心技术岗', '计算机教师', []),
                                         ('高中信息科技教师', '计算机', ['computing-teacher'])]:
            with self.subTest(vacancy=vacancy):
                body = f'<table><thead>{header}</thead><tbody><tr><td>{vacancy}</td><td>{major}</td></tr></tbody></table>'
                self.assertEqual(notice(body)['roleIds'], expected)

    def test_city_evidence_for_joint_batches(self):
        source = dict(SOURCE, name='省教育厅就业网', kind='多校批次')
        for title, body, expected in [
                ('省内多所学校公开招聘教师', '报名地址：南京市。', ''),
                ('南京市教育局直属学校公开招聘教师', '各校岗位见附件。', '南京'),
                ('省内多所学校公开招聘教师', '工作地点：南京市江宁区。', '南京'),
                ('省内多所学校公开招聘教师', '工作地点：南京、苏州。', ''),
                ('公开招聘公告', '工作地点：广州。工作地点：深圳。', ''),
                ('省内多所学校公开招聘教师', '宣讲地点：成都。', '')]:
            with self.subTest(title=title, body=body):
                self.assertEqual(notice(f'<p>{body}</p>', title=title, source=source)['city'], expected)
        self.assertEqual(notice('<p>工作地点：上海。</p><p>报名地址：南京市。</p>')['city'], '上海')
        self.assertEqual(notice('<p>招聘单位：星河科技。</p>', source=source)['employer'], '星河科技')


class ApplicationWindowTests(unittest.TestCase):
    def test_beijing_boundaries_to_the_minute(self):
        body = '<p>报名时间：2026年11月23日上午9时至23日下午5时30分（北京时间）。</p>'
        for checked, state in [('2026-11-23T00:59:59Z', 'upcoming'),
                               ('2026-11-23T01:00:00Z', 'open'),
                               ('2026-11-23T17:29:59+08:00', 'open'),
                               ('2026-11-23T17:30:00+08:00', 'closed'),
                               ('2026-11-23', 'unknown')]:
            with self.subTest(checked=checked):
                r = notice(body, checked=checked)
                self.assertTrue(r['windowVerified'])
                self.assertEqual((r['applicationStart'], r['deadline']), (CHECKED, CHECKED))
                self.assertEqual((r['applicationStartTime'], r['deadlineTime']), ('09:00', '17:30'))
                self.assertEqual((r['applicationStatus'], r['closed']), (state, state == 'closed'))

    def test_date_only_inclusive_and_mixed_precision(self):
        body = '<p>网上报名时间：2026年11月1日至11月23日。</p>'
        last_day = notice(body, checked='2026-11-23T15:59:59Z')
        self.assertEqual(last_day['applicationStatus'], 'open')
        self.assertNotIn('deadlineTime', last_day)
        self.assertEqual(notice(body, checked='2026-11-23T16:00:00Z')['applicationStatus'], 'closed')
        table = ('<table><tr><th>网申开始时间</th><td><time>2026/11/20</time></td></tr>'
                 '<tr><th>网申截止时间</th><td>2026/11/30 １３：０５</td></tr></table>')
        r = notice(table)
        self.assertEqual((r['windowVerified'], r['applicationStart'], r['deadlineTime']),
                         (True, '2026-11-20', '13:05'))
        self.assertNotIn('applicationStartTime', r)

    def test_one_sided_evidence_and_explicit_closure(self):
        for text, start, end, state in [
            ('报名开始时间：2026年11月24日。', '2026-11-24', '', 'upcoming'),
            ('报名自2026年11月22日起。', '2026-11-22', '', 'unknown'),
            ('报名截止时间为2026年11月26日。', '', '2026-11-26', 'unknown'),
            ('简历投递时间：即日起至2026年11月22日。', '', '2026-11-22', 'closed'),
            ('本次报名已结束。', '', '', 'closed'),
            ('如果报名已结束，请关注下次招聘。', '', '', 'unknown')]:
            with self.subTest(text=text):
                r = notice(f'<p>{text}</p>')
                self.assertEqual((r['applicationStart'], r['deadline'], r['applicationStatus'], r['windowVerified']),
                                 (start, end, state, False))

    def test_repeated_window_and_one_day_clock_range(self):
        body = ('<p>报名时间：2026年11月23日9:00至17:00。</p>'
                '<p>报名截止时间：2026年11月23日。</p>')
        r = notice(body, checked='2026-11-23T12:00:00+08:00')
        self.assertEqual((r['windowVerified'], r['applicationStartTime'], r['deadlineTime'],
                          r['applicationStatus']), (True, '09:00', '17:00', 'open'))
        r = notice('<p>报名于2026年11月22日截止。</p>')
        self.assertEqual((r['applicationStart'], r['deadline'], r['closed']), ('', '2026-11-22', True))

    def test_unrelated_dates_cannot_create_or_override_a_window(self):
        noise = ('<p>笔试报名时间：2026年1月1日至1月3日。截止时间：2026年1月2日。</p>'
                 '<p>报名费缴纳截止时间：2026-11-01。面试申请截止：2026-11-03。</p>'
                 '<p>附件：报名时间：2026年7月1日至9月1日。</p>'
                 '<a href="/old.pdf">报名截止：2026年8月1日。</a>')
        self.assertFalse(notice(noise)['closed'])
        self.assertEqual(notice(noise)['deadline'], '')
        r = notice(noise + '<p>申请时间：2026年11月1日至2026年12月1日。</p>')
        self.assertEqual((r['deadline'], r['windowVerified']), ('2026-12-01', True))

    def test_conflicts_irregular_hours_and_multiple_windows(self):
        for text in [
            '报名时间：2026年11月1日至11月30日；报名时间：2026年12月1日至12月10日。',
            '报名截止：2026-11-23 16:30。报名截止：2026-11-23 17:30。',
            '第一批：报名时间另行通知。第二批：报名时间：2026年11月1日至11月30日。',
            '报名时间：2026年11月1日至11月30日。招满即止。',
            '报名时间：2026年11月1日至11月30日。其他岗位报名时间另行通知。',
            '报名时间：2026年11月1日至11月30日，12月3日至12月6日。',
            '第一批报名时间已过。</p><p>报名已经截止。</p><p>第二批报名时间另行通知。',
            '报名时间：2026年11月1日至11月30日，每日9:00至17:00。',
            '报名时间：2026年11月25日至11月23日。',
            '报名时间：2026年11月1日25:20至11月30日。',
            '报名时间：2026年11月1日至11月30日 15:75。',
            '报名时间：2026年2月29日至11月30日。',
            '报名截止：2026年11月30日17:00（纽约时间）。']:
            with self.subTest(text=text):
                r = notice(f'<p>{text}</p>')
                self.assertEqual((r['applicationStart'], r['deadline'], r['applicationStatus'], r['windowVerified']),
                                 ('', '', 'unknown', False))


class RereadTests(unittest.TestCase):
    body = '<article><h1>' + TITLE + '</h1><p>报名时间：2026年11月1日9:00至11月23日17:00。</p></article>'
    stamp = CHECKED + 'T17:05:00+08:00'

    def check(self, replies, existing, source=SOURCE, limit=1):
        with TemporaryDirectory() as tmp, patch.object(updater, 'CACHE', Path(tmp)), \
                patch.object(updater.SiteClient, 'html', side_effect=replies):
            return updater.check_site(source, existing, {}, limit, self.stamp)

    def test_failed_detail_then_success_restores_timed_evidence(self):
        listing = (f'<a href="{URL}">{TITLE}</a>', BASE)
        known = notice(self.body, checked=CHECKED + 'T10:00:00+08:00')
        for error, availability in [(TimeoutError('timeout'), 'stale'),
                                    (ValueError('unexpected HTML'), 'stale'),
                                    (HTTPError(URL, 410, 'gone', {}, None), 'unavailable'),
                                    (('<article><h1>拟聘用人员公示</h1></article>', URL), 'changed')]:
            with self.subTest(availability=availability):
                (r,), status = self.check([listing, error], [known])
                self.assertEqual((r['availability'], r['checked'], r['lastAttempt']),
                                 (availability, CHECKED, self.stamp))
                self.assertEqual((r['windowVerified'], r['applicationStatus'], r['closed'], r['deadline'], r['applicationStart']),
                                 (False, 'unknown', False, '', ''))
                self.assertNotIn('deadlineTime', r)
                self.assertNotIn('applicationStartTime', r)
                self.assertEqual(status['verified'], 0)
                (restored,), status = self.check([listing, (self.body, URL)], [r])
                self.assertNotIn('availability', restored)
                self.assertTrue(restored['windowVerified'])
                self.assertEqual((restored['applicationStatus'], status['verified']), ('closed', 1))

    def test_failed_listing_and_watched_detail_have_different_scope(self):
        known = notice(self.body, checked='2026-11-22')
        gone = HTTPError(BASE, 404, 'missing', {}, None)
        (r,), status = self.check([gone], [known])
        self.assertEqual((r['availability'], r['checked'], r['deadline'], status['status']),
                         ('stale', '2026-11-22', '', 'failed'))
        (r,), _ = self.check([gone], [known], dict(SOURCE, url=URL, watchTitle=TITLE))
        self.assertEqual((r['availability'], r['lastAttempt']), ('unavailable', self.stamp))

    def test_budget_skips_legacy_or_previous_day_record(self):
        fresh = URL + '?new'
        listing = (f'<a href="{fresh}">{TITLE}</a>', BASE)
        for known in [dict(notice(self.body), checked='2026-11-22'),
                      {'url': URL, 'title': TITLE, 'deadline': '2026-10-01', 'closed': True, 'checked': CHECKED}]:
            rows, _ = self.check([listing, (self.body, fresh)], [known])
            old = next(r for r in rows if r['url'] == URL)
            self.assertEqual((old['applicationStatus'], old['availability'], old['closed'], old['deadline']),
                             ('unknown', 'stale', False, ''))


if __name__ == '__main__':
    unittest.main()
