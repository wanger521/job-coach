import { careers, cities, cityKeys } from '../../data/catalog.mjs';
import { matchCareer } from '../../profile.mjs';
import { recruitmentFeed } from '../../data/recruitment-feed.mjs';
import { jobPostings } from '../../data/job-board.mjs';
import { stageOptions, stageLabel, stagesFor } from '../../data/teaching-stages.mjs';
import { applicationStatus, statusOptions } from '../../data/application-status.mjs';
import { esc as e, icon as i, safeUrl } from '../../ui.mjs';

const roles = new Map(careers.map(c => [c.id, c]));
const tracks = [
  { key: 'learning', name: '教育技术', icon: 'book', question: '你更想把知识讲清楚，还是把它拍得好懂？', task: '挑一道拿手菜，写出新手最容易做错的一步。做一页图解，再请一位没做过的人照着试。', picks: [['computing-teacher', '为学生设计信息科技实验，试讲前先核对本学段的专业目录和教师资格要求。'], ['instructional-designer', '访谈学习者，把知识拆成目标、练习和反馈。'], ['learning-media', '把讲解改成分镜，用画面、字幕和声音帮助理解。']] },
  { key: 'video', name: '短视频', icon: 'pen', question: '刷到喜欢的视频后，你愿意研究它怎么拍，再自己改一版吗？', task: '选一条喜欢的抖音视频，标出前三秒、转场和结尾。用自己的素材剪一个 30 秒版本，再按反馈重剪一次。', picks: [['short-video-editor', '选题、写脚本、协调拍摄，也要接受返工。'], ['photographer', '练习控光和构图，按客户需求拍出一组能交付的照片。'], ['learning-media', '把同一项技能分别剪成演示版和讲解版，比较哪版更好学。']] },
  { key: 'style', name: '穿搭与美妆', icon: 'user', question: '你享受给人提供建议，还是更喜欢自己琢磨搭配和摆放？', task: '用已有衣物为三个不同场合做搭配。请朋友任选一套，再问她为什么选，看看你更享受搭配还是沟通。', picks: [['visual-merchandiser', '按主题、动线与库存搭配商品，在线下反复调整陈列。'], ['beauty-advisor', '倾听顾客需求、演示产品，同时适应门店排班和销售目标。']] },
  { key: 'food', name: '做饭与美食', icon: 'leaf', question: '你最享受做好一顿饭，还是让别人也能跟着做成功？', task: '把家常菜写成一份标明用量的食谱，让朋友只看食谱试做。比较你对备菜、拍摄、写作和答疑的感受。', picks: [['food-content', '试做食谱、拍步骤、检查用量，把做法编辑成可复现的内容。'], ['chinese-cook', '在有限时间里备料、出菜和清洁，体验后厨协作与体力要求。'], ['short-video-editor', '把烹饪过程拍成短片，平衡步骤准确性与画面节奏。']] },
];
export function jobsUrl(roleIds = [], city = '', status = 'open', stage = '', season = '') {
  const params = new URLSearchParams();
  const cityId = Object.keys(cityKeys).find(key => cityKeys[key] === city);
  if (cityId) params.set('city', cityId);
  if (roleIds.length) params.set('roles', roleIds.join(','));
  if (stage) params.set('stage', stage);
  if (season) params.set('season', season);
  if (status !== 'open') params.set('status', status);
  return '#jobs' + (params.size ? '/' + params.toString() : '');
}
export function pathsPage(key, profile = null) {
  const track = tracks.find(t => t.key === key) || tracks[0];
  const score = id => matchCareer(roles.get(id), profile).score;
  const hasPreferences = [profile?.conditions, profile?.interests, profile?.skills].some(values => values?.length);
  const picks = hasPreferences ? [...track.picks].sort(([a], [b]) => score(b) - score(a)) : track.picks;
  return `<div class="page-heading"><div><h1>专业与兴趣探索</h1><p>从教育技术出发，把平时喜欢的事换成一项可以试做的工作。</p></div></div>
  <nav class="city-nav" aria-label="选择探索线索">${tracks.map(t => `<a href="#paths/${t.key}" ${t === track ? 'aria-current="page"' : ''}>${i(t.icon, 16)} ${t.name}</a>`).join('')}</nav>
  <section class="path-question"><h2>${track.question}</h2><div><strong>先试一次</strong><p>${track.task}</p></div></section>
  <div class="paths-profile"><span>${hasPreferences ? "按已填写的工作偏好排序" : "你更喜欢独立剪辑、与人交流，还是现场动手？"}</span><button class="inline-action" data-action="assessment">${hasPreferences ? "调整我的画像" : "填写我的工作偏好"} ${i('arrow', 14)}</button></div>
  <div class="path-roles">${picks.map(([id, why]) => { const c = roles.get(id); return `<article><div><a class="path-title" href="#role/${id}">${e(c.name)} ${i('chev', 15)}</a>${hasPreferences ? `<span class="path-fit">画像匹配 ${score(id)}%</span>` : ""}<p>${e(why)}</p></div><a class="text-link" href="${jobsUrl([id])}">查招聘 ${i('arrow', 14)}</a></article>`; }).join('')}</div>
  <a class="btn primary" href="${jobsUrl(track.picks.map(([id]) => id))}">${i('brief', 16)} 勾选这组职业查招聘</a>`;
}

function canFilterStage(roleIds) {
  return !roleIds.length || roleIds.some(id => id.endsWith('-teacher'));
}

function selectedJobs() {
  const params = new URLSearchParams(location.hash.split('/')[1] || '');
  const roleIds = [...new Set((params.get('roles') || '').split(','))].filter(id => roles.has(id));
  const status = statusOptions.find(s => s.id === params.get('status'))?.id || 'open';
  const stage = canFilterStage(roleIds) && stageOptions.some(s => s.id === params.get('stage')) ? params.get('stage') : '';
  const season = params.get('city') === 'nanjing' && canFilterStage(roleIds) && /^20\d{2}$/.test(params.get('season')) ? params.get('season') : '';
  return { roleIds, season, city: Object.hasOwn(cityKeys, params.get('city')) ? cityKeys[params.get('city')] : '', status, stage };
}

const watchedByUrl = new Map(recruitmentFeed.notices.map(item => [item.url, item]));
const sourceById = new Map(recruitmentFeed.sources.map(item => [item.id, item]));

function matchingRecords(selection, now = new Date()) {
  const inScope = item => (!selection.city || item.city === selection.city) &&
    (!selection.stage || stagesFor(item).includes(selection.stage));
  const roleMatches = item => !selection.roleIds.length || item.roleIds.some(id => selection.roleIds.includes(id));
  const jobs = jobPostings.filter(job => inScope(job) && roleMatches(job));
  const reviewedUrls = new Set(jobs.map(job => job.url));
  const records = jobs.map(item => ({ item, kind: 'job', status: applicationStatus(item, watchedByUrl.get(item.url), now) }));
  for (const item of recruitmentFeed.notices) {
    if (reviewedUrls.has(item.url) || !inScope(item)) continue;
    let kind = 'notice';
    if (!roleMatches(item)) {
      if (!selection.roleIds.includes('computing-teacher') || item.roleIds.length || !item.positionTables?.length || !/教师|师资/.test(item.title)) continue;
      kind = 'check-subject';
    }
    records.push({ item, kind, status: applicationStatus(item, null, now) });
  }
  return records;
}

function periodText(item, status) {
  if (item.recordType === 'notice' && !Object.hasOwn(item, 'windowVerified')) return '';
  const end = item.deadline ? `${item.deadline}${item.deadlineTime ? ' ' + item.deadlineTime : ''}` : '';
  if (status.id === 'closed' && item.applicationStart && end) return `当时报名 ${item.applicationStart}${item.applicationStartTime ? ' ' + item.applicationStartTime : ''} 至 ${end}`;
  if (status.id === 'upcoming') return `开始报名 ${item.applicationStart}${item.applicationStartTime ? ' ' + item.applicationStartTime : ''}${end ? '　·　截止 ' + end : ''}`;
  return end ? '报名截止 ' + end : '';
}

function statusBadge(status) {
  return `<small class="posting-status" data-state="${e(status.id)}">${e(status.label)}</small>`;
}

function jobRow({ item: job, status }) {
  const watched = watchedByUrl.get(job.url);
  const stage = stageLabel(job);
  const period = periodText(job, status);
  return `<article class="posting"><div class="posting-top"><span>${e(job.city)} · ${e(job.employer)}${stage ? ' · ' + e(stage) : ''}</span>${statusBadge(status)}</div>
  <h3>${e(job.title)}</h3>${period ? `<div class="job-period">${e(period)}</div>` : ''}<p>${e(job.requirement)}</p>
  <div class="job-role-links">${job.roleIds.map(id => `<a href="#role/${id}">${e(roles.get(id).name)} ${i('chev', 11)}</a>`).join('')}</div>
  <div class="posting-dates">${job.published ? `发布 ${e(job.published)} · ` : ''}岗位核对 ${e(job.checked)}${watched?.checked ? ` · 原文读取 ${e(watched.checked)}` : ''}</div>
  <div class="posting-actions"><a class="text-link" href="${e(safeUrl(job.url))}" target="_blank" rel="noopener noreferrer">招聘原文 ${i('diagonal', 14)}</a><button type="button" class="inline-action" data-action="job-note" data-job="${e(job.id)}">${i('notes', 15)} 记入手记</button></div></article>`;
}

function noticeRow({ item, status }) {
  const src = sourceById.get(item.sourceId);
  const stage = stageLabel(item);
  const period = periodText(item, status);
  const tables = (item.positionTables || []).filter(a => safeUrl(a.url));
  return `<article><div class="posting-top"><span>${e(item.city || '地点见原文')} · ${e(src?.name || item.employer)}${stage ? ' · ' + e(stage) : ''}</span>${statusBadge(status)}</div><h3><a href="${e(safeUrl(item.url))}" target="_blank" rel="noopener noreferrer">${e(item.title)} ${i('diagonal', 13)}</a></h3>${period ? `<div class="job-period">${e(period)}</div>` : ''}<p>${e(item.requirement)}</p>${tables.length ? `<div class="job-role-links">${tables.map(a => `<a href="${e(safeUrl(a.url))}" target="_blank" rel="noopener noreferrer">${e(a.title)} ${i('diagonal', 12)}</a>`).join('')}</div>` : ''}<div class="notice-meta">${item.published ? '发布 ' + e(item.published) + ' · ' : ''}原文读取 ${e(item.checked)}</div></article>`;
}

const sourceStates = { ok: '已检查', empty: '栏目未匹配到招聘标题', partial: '部分详情读取失败', failed: '检查失败' };
function feedSummary() {
  const stamp = recruitmentFeed.updatedAt;
  const time = stamp ? stamp.slice(0, 16).replace('T', ' ') : '等待首次检查';
  const sources = recruitmentFeed.sources;
  const problemCount = sources.filter(s => ['failed','partial'].includes(s.status)).length;
  return `<details class="feed-sources"><summary>采集来源与状态（${sources.length} 个栏目）<span>最近检查　${e(time)}${stamp ? '（北京时间）' : ''}${problemCount ? ' · ' + problemCount + ' 个栏目需复查' : ''}</span></summary><ul>${sources.map(s => `<li><a href="${e(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer">${e(s.name)} ${i('diagonal', 12)}</a><small>${e(s.kind)} · ${e(sourceStates[s.status] || '待核实')}${s.lastSuccess ? ' · 上次读到栏目 ' + e(s.lastSuccess.slice(0, 10)) : ''}</small></li>`).join('')}</ul></details>`;
}

function noticeList(records) {
  return `<div class="notice-list">${records.map(noticeRow).join('')}</div>`;
}

export function belongsToSeason(item, year) {
  if (item.recruitmentYear) return String(item.recruitmentYear) === String(year);
  const title = (item.title || '').normalize('NFKC');
  if (!/招聘|选聘|选调|引进|招考/.test(title)) return false;
  // Deadlines and degree conditions are not recruitment years.
  const heading = title.split(/[（(]?(?:报名)?截[至止]|(?:学历|年龄|毕业时间)要求/)[0];
  return [...heading.matchAll(/(20\d{2})\s*(?:年(?!\s*\d+月\d+日(?:前|毕业)|毕业)|届(?=.{0,10}(?:校招|校园招聘|毕业生.{0,6}教师招聘)))/g)].some(match => match[1] === String(year));
}

function nextRecruitYear() {
  const date = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit' }).format(new Date());
  const [year, month] = date.split('-').map(Number);
  return String(month >= 8 ? year + 1 : year);
}

function teacherSeason(selection) {
  const { season, roleIds, stage } = selection;
  const records = matchingRecords(selection);
  const isTeaching = r => stagesFor(r.item).length > 0 || r.item.roleIds.some(id => id.endsWith('-teacher'));
  const inSeason = records.filter(r => isTeaching(r) && belongsToSeason(r.item, season));
  const jobs = inSeason.filter(r => r.kind === 'job');
  const notices = inSeason.filter(r => r.kind === 'notice');
  const archives = records.filter(r => r.kind === 'job' && isTeaching(r) && r.status.id === 'closed' && !belongsToSeason(r.item, season) && (r.item.deadline || r.item.published || '9999').slice(0, 4) < season);
  const reviewedUrls = new Set([...jobs, ...notices].map(r => r.item.url));
  const departments = recruitmentFeed.notices.filter(item => !reviewedUrls.has(item.url) && item.city === '南京' && belongsToSeason(item, season) && /教师|师资|直属学校/.test(item.title) && item.roleIds.length === 0 && ['教育部门', '学校官网'].includes(sourceById.get(item.sourceId)?.kind) && (!stage || stagesFor(item).includes('unknown') || !stagesFor(item).length || stagesFor(item).includes(stage)));
  const columns = recruitmentFeed.sources.filter(s => s.city === '南京' && ['教育部门', '学校官网'].includes(s.kind));
  const currentHref = jobsUrl(roleIds, '南京', 'open', stage);
  return `<section class="teacher-season"><header><div><h2>${e(season)} 年南京教师招聘</h2><p>每日采集官网更新，按公告写明的招聘年度归集。</p></div><a class="text-link" href="${currentHref}">查看当前报名 ${i('arrow', 13)}</a></header>
    <h3>${e(season)} 招聘公告</h3>${jobs.length ? `<div class="posting-list">${jobs.map(jobRow).join('')}</div>` : ''}${notices.length ? noticeList(notices) : ''}${!jobs.length && !notices.length ? '<p class="season-empty" role="status">当前筛选下，暂未收录这一年度明确列出相关岗位的公告。</p>' : ''}
    ${departments.length ? `<details class="more-notices"><summary>${departments.length} 条统招公告待查岗位表</summary>${noticeList(departments.map(item => ({ item, status: applicationStatus(item) })))}</details>` : ''}
    <details class="more-notices"><summary>查看关注的教育局和学校来源</summary><ul class="season-sources">${columns.map(s => `<li><a class="text-link" href="${e(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer">${e(s.name)} ${i('diagonal', 12)}</a></li>`).join('')}</ul></details>
    <h3>往年岗位参考 <small>${archives.length} 个</small></h3>${archives.length ? `<p>先对照毕业证上的专业全称、师范要求和教师资格证，再看岗位表是否要求教学经历。</p><div class="posting-list">${archives.map(jobRow).join('')}</div>` : '<p>当前职业和学段暂未收录往年岗位，可切换到全部学段查看更多。</p>'}
    </section>`;
}

function results(selection) {
  if (selection.season) return teacherSeason(selection);
  const all = matchingRecords(selection);
  const visible = all.filter(r => r.status.id === selection.status);
  const jobs = visible.filter(r => r.kind === 'job').sort((a, b) => (a.item.deadline || '9999').localeCompare(b.item.deadline || '9999') * (selection.status === 'closed' ? -1 : 1));
  const notices = visible.filter(r => r.kind === 'notice');
  const tentative = visible.filter(r => r.kind === 'check-subject');
  const status = statusOptions.find(s => s.id === selection.status).label;
  const scope = [selection.city, stageOptions.find(s => s.id === selection.stage)?.label].filter(Boolean).map(e).join(' · ');
  const summary = `<p class="result-tally" role="status">${scope ? scope + ' · ' : ''}${e(status)} · ${jobs.length} 个已核对岗位，${notices.length} 条自动公告</p>`;
  let empty = '';
  if (!jobs.length && !notices.length) {
    const alternatives = statusOptions.filter(s => s.id !== selection.status && all.some(r => r.kind !== 'check-subject' && r.status.id === s.id));
    const links = alternatives.map(s => `<a class="text-link" href="${jobsUrl(selection.roleIds, selection.city, s.id, selection.stage)}">查看${s.id === 'closed' ? '已截止样本' : s.label + '信息'} ${i('arrow', 13)}</a>`).join('');
    empty = `<div class="job-empty"><h3>${selection.status === 'open' ? '这个筛选下，暂未找到可确认正在报名的岗位' : '这个筛选下暂无' + e(status) + '的记录'}</h3><p>${selection.status === 'open' ? '可以换个学段或城市，或等下一次来源更新。' : '可以调整职业、城市或学段后再查看。'}</p>${links ? `<div class="job-empty-links">${links}</div>` : ''}</div>`;
  }
  return summary + empty + (jobs.length ? `<div class="posting-list">${jobs.map(jobRow).join('')}</div>` : '') +
    (notices.length ? `<section class="auto-section"><h2>自动采集公告 <small>${notices.length} 条</small></h2>${noticeList(notices.slice(0, 3))}${notices.length > 3 ? `<details class="more-notices"><summary>查看其余 ${notices.length - 3} 条公告</summary>${noticeList(notices.slice(3))}</details>` : ''}</section>` : '') +
    (tentative.length ? `<details class="more-notices"><summary>另有 ${tentative.length} 条教师公告需查岗位表确认学科</summary>${noticeList(tentative)}</details>` : '');
}

function options(items, selected) {
  return items.map(({ id, label }) => `<option value="${e(id)}"${id === selected ? ' selected' : ''}>${e(label)}</option>`).join('');
}

function checkbox(id, selection) {
  return `<label class="job-check"><input type="checkbox" name="job-role" value="${e(id)}" ${selection.roleIds.includes(id) ? 'checked' : ''}><span>${e(roles.get(id).name)}</span></label>`;
}

let lastResultsHtml = '';

export function jobsPage() {
  const selection = selectedJobs();
  const featured = new Set([...tracks.flatMap(t => t.picks.map(([id]) => id)), ...selection.roleIds]);
  const remaining = careers.filter(c => !featured.has(c.id));
  const season = selection.season || nextRecruitYear();
  const watchRoles = selection.roleIds.filter(id => id.endsWith('-teacher'));
  const watchHref = jobsUrl(watchRoles.length ? watchRoles : ['computing-teacher'], '南京', 'open', selection.stage, season);
  lastResultsHtml = results(selection);
  return `<div class="page-heading"><div><h1>真实招聘</h1><p>查看官方公告的报名期限、用人单位和岗位要求。</p></div></div>
  <div class="teacher-shortcut"><a class="text-link" href="${jobsUrl(['computing-teacher'], '南京')}">${i('book', 16)} 南京计算机教师 ${i('arrow', 14)}</a><a class="text-link season-shortcut" href="${watchHref}">${i('bookmark', 15)} 关注 ${e(season)} 年南京教师招聘 ${i('arrow', 14)}</a>${feedSummary()}</div>
  <form class="job-filters" id="job-filters"><fieldset><legend>职业方向 <small>可多选，留空查看全部</small></legend><div class="job-checks">${[...featured].map(id => checkbox(id, selection)).join('')}</div>
  <details class="other-roles"><summary>更多职业方向</summary><div class="job-checks">${remaining.map(c => checkbox(c.id, selection)).join('')}</div></details></fieldset>
  <div class="job-filter-foot"><label class="compact-select">工作城市<select name="job-city">${options([{ id: '', label: '全部城市' }, ...cities.map(city => ({ id: city, label: city }))], selection.city)}</select></label>
  <label class="compact-select" id="job-stage-field"${canFilterStage(selection.roleIds) ? '' : ' hidden'}>任教学段<select name="job-stage">${options([{ id: '', label: '全部学段' }, ...stageOptions], selection.stage)}</select></label>
  <label class="compact-select" id="job-status-field"${selection.season ? ' hidden' : ''}>报名状态<select name="job-status">${options(statusOptions, selection.status)}</select></label><a class="text-link" href="#jobs">重置筛选</a></div></form>
  <section id="job-results" aria-label="匹配的招聘记录">${lastResultsHtml}</section>`;
}

export function updateJobs(form) {
  const values = new FormData(form);
  const roleIds = values.getAll('job-role');
  const stageVisible = canFilterStage(roleIds);
  const stageField = form.elements['job-stage'];
  form.querySelector('#job-stage-field').hidden = !stageVisible;
  if (!stageVisible) stageField.value = '';
  const city = values.get('job-city') || '', stage = stageField.value, status = values.get('job-status');
  const season = stageVisible && city === '南京' ? selectedJobs().season : '';
  form.querySelector('#job-status-field').hidden = Boolean(season);
  history.replaceState(null, '', jobsUrl(roleIds, city, status, stage, season));
  refreshJobResults();
}

export function refreshJobResults() {
  const target = document.getElementById('job-results');
  if (!target) return;
  const html = results(selectedJobs());
  if (html === lastResultsHtml) return;
  target.innerHTML = html;
  lastResultsHtml = html;
}


export function jobDraft(id) {
  const job = jobPostings.find(j => j.id === id);
  if (!job) return null;
  const career = job.roleIds.find(role => selectedJobs().roleIds.includes(role)) || job.roleIds[0];
  return {type:'招聘样本', title:job.employer + ' · ' + job.title, city:job.city, url:job.url, career, text:job.requirement + '\n核对日期 ' + job.checked + ' · ' + applicationStatus(job, watchedByUrl.get(job.url)).label};
}
