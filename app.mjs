import {
  careers,
  sources as allSources,
  groups,
  cities,
  cityKeys,
  careerPlate as asset,
  localRoleEvidence,
} from "./data/catalog.mjs";
import { occupationIndex, indexSource } from "./data/occupation-index.mjs";
import { icon as i, esc as e, safeUrl, modal } from "./ui.mjs";
import { openAssessment, matchCareer } from "./profile.mjs";
import { pathsPage, jobsPage, jobsUrl, updateJobs, refreshJobResults, jobDraft } from "./assets/features/explore.mjs";
import { collectSource } from "./collector-client.mjs";

const store = "career-atlas.workspace.v1";
const noteTypes = ["招聘样本", "从业者访谈", "试做体验", "资料摘录"];
const routes = {
  home: "探索工作台",
  city: "城市资料",
  paths: "专业与兴趣探索",
  jobs: "真实招聘",
  directory: "职业名称索引",
  library: "职业图鉴",
  fit: "适配测评",
  saved: "我的收藏",
  notes: "调研手记",
  sources: "资料来源",
};
const root = document.querySelector("#app");
let savedState = {};
try {
  savedState = JSON.parse(localStorage.getItem(store) || "{}") || {};
} catch {}
const state = {
  profile: savedState.profile || null,
  saved: Array.isArray(savedState.saved)
    ? savedState.saved.filter((id) => careers.some((c) => c.id === id))
    : [],
  notes: Array.isArray(savedState.notes) ? savedState.notes : [],
  answers:
    savedState.answers && typeof savedState.answers === "object"
      ? savedState.answers
      : {},
  view: savedState.view === "list" ? "list" : "grid",
};
let activeGroup = "全部方向",
  query = "",
  noteType = "全部记录",
  detailTab = "工作实景",
  toastTimer;
function routedIndexQuery() {
  try {
    return current().page === "directory"
      ? decodeURIComponent(current().id || "")
      : "";
  } catch {
    return "";
  }
}
let libraryCity = location.hash.startsWith("#library/")
    ? cityKeys[location.hash.split("/")[1]] || ""
    : "",
  detailCity = cities.find((city) => state.profile?.city?.includes(city)) || "",
  cityQuery = "",
  cityKind = "",
  indexQuery = "",
  indexGroup = "",
  indexLimit = 50,
  sourceCity = "";
const two = (n) => String(n).padStart(2, "0");
const getCareer = (id) => careers.find((c) => c.id === id);
function sourceFor(career, index) {
  const source = allSources[index];
  return career?.evidence.find((s) => s.url === source?.url) || source;
}
const current = () => {
  const [page, id] = location.hash.slice(1).split("/");
  return {
    page:
      page === "role" && getCareer(id) ? "role" : routes[page] ? page : "home",
    id,
  };
};
const today = () => new Date().toLocaleDateString("sv-SE");
function toast(text) {
  const el = document.querySelector("#message");
  el.textContent = text;
  el.classList.add("on");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("on"), 3000);
}
function persist() {
  try {
    localStorage.setItem(store, JSON.stringify(state));
    return true;
  } catch {
    toast("浏览器未能保存，请导出手记备份。");
    return false;
  }
}
function navigate(page) {
  if (location.hash === "#" + page) {
    render();
    window.scrollTo(0, 0);
  } else location.hash = page;
}
function openProfile() {
  openAssessment(state.profile, (profile) => {
    state.profile = profile;
    const stored = persist();
    navigate("fit");
    if (stored) toast("画像已保存，推荐方向已更新");
  });
}
function navItem(page, icon, label, count = "") {
  const active =
    current().page === page ||
    (page === "library" && ["role", "directory"].includes(current().page));
  return `<a href="#${page}" class="nav-item ${active ? "selected" : ""}" ${active ? 'aria-current="page"' : ""}>${i(icon, 19)}<span>${label}</span>${count === "" ? "" : `<small>${count}</small>`}</a>`;
}
function shell() {
  const { page, id } = current(),
    role = page === "role" && getCareer(id);
  const completed =
    Number(!!state.profile) +
    Number(!!state.saved.length) +
    Number(!!state.notes.length);
  const progress = Math.round((completed / 3) * 100);
  return `<div class="shell"><button class="nav-scrim" data-action="menu" aria-label="关闭导航"></button><aside class="sidebar" aria-label="工作空间导航">
    <a class="brand" href="#home" aria-label="职野 首页"><img src="./assets/compass.svg" width="42" height="42" alt=""><span><b>职野</b><em>Career Atlas</em></span></a>
    <nav><div class="nav-label">探索空间</div>${navItem("home", "compass", "探索工作台")}${navItem("library", "book", "职业图鉴")}${navItem("paths", "leaf", "专业与兴趣")}${navItem("jobs", "brief", "真实招聘")}${navItem("city", "map", "城市资料")}${navItem("fit", "route", "适配测评")}<div class="nav-label secondary">个人空间</div>${navItem("saved", "bookmark", "我的收藏", state.saved.length)}${navItem("notes", "notes", "调研手记")}${navItem("sources", "library", "资料来源")}</nav>
    <div class="side-end"><button class="progress-box" data-action="progress"><div class="progress-heading"><span>${i("flag", 15)} 探索进度</span><b>${completed}/3</b></div><div class="progress-track"><span style="width:${progress}%"></span></div><small>${["从一份职业画像开始", "继续收藏或记录你的发现", "再走一步，完成初次探索", "已完成初次探索"][completed]}</small></button>
    <button class="identity" data-action="account"><span class="avatar">${i("user", 20)}</span><span><b>本地探索者</b><small>个人工作空间</small></span>${i("down", 14)}</button></div></aside>
    <div class="workspace"><header class="topbar"><div class="crumb"><button class="mobile-toggle icon-button" data-action="menu" aria-label="打开导航">${i("menu")}</button><span class="crumb-label">我的空间</span><span class="crumb-sep">/</span><strong>${role ? `<a href="#library">职业图鉴</a><span class="crumb-sep">/</span>${e(role.name)}` : routes[page]}</strong></div>
    <div class="top-actions"><button class="search-trigger" data-action="search">${i("search", 16)}<span>搜索职业、技能…</span><kbd>Ctrl K</kbd></button><span class="local-indicator"><b></b> 本地工作区</span></div></header>
    <main id="content" tabindex="-1"></main><footer class="footer"><span><img src="./assets/compass.svg" alt="" width="17" height="17">职野 Career Atlas</span><a href="#sources">研究资料与使用说明 ${i("diagonal", 13)}</a></footer></div></div>`;
}
function hero() {
  return `<section class="hero"><div class="terrain"></div><div class="hero-content"><div class="guide-label"><span></span>职业探索指南<i></i>FIELD GUIDE</div><h1>找到你的职业坐标<span>。</span></h1><p>看见职业的真实日常，从你的兴趣、能力与生活偏好出发，<br class="wide-only">探索适合自己的下一站。</p><div class="hero-actions"><button class="btn primary" data-action="assessment">${i("compass", 17)}${state.profile ? "更新我的画像" : "开始适配测评"} ${i("arrow", 16)}</button><a class="hero-link" href="#library">浏览职业图鉴 ${i("chev", 13)}</a></div></div><span class="map-caption"><span></span>职业探索地形图</span></section>`;
}
function metric(page, ic, label, val, unit, cl) {
  return `<a href="#${page}" class="metric ${cl}"><span class="metric-icon">${i(ic, 23)}</span><span class="metric-text"><small>${label}</small><span><b>${two(val)}</b> ${unit}</span></span>${i("diagonal", 14)}</a>`;
}
const categoryClass = (g) =>
  ["sage", "peach", "blue", "ochre", "slate"][
    Math.max(0, groups.indexOf(g)) % 5
  ];
function card(c, showFit = false) {
  const saved = state.saved.includes(c.id);
  const matching =
    showFit && state.profile ? matchCareer(c, state.profile) : null;
  return `<article class="career-card ${categoryClass(c.category)}"><a href="#role/${c.id}" class="card-art" aria-label="查看${e(c.name)}职业档案"><img src="${asset(c)}" alt="" loading="lazy"><span class="cat-stamp"><b></b>${e(c.category)}</span></a><button class="save-button ${saved ? "is-saved" : ""}" aria-label="${saved ? "取消收藏" : "收藏"}${e(c.name)}" aria-pressed="${saved}" data-action="save" data-id="${c.id}">${i("bookmark", 16)}</button><div class="card-content"><div class="card-title"><a href="#role/${c.id}"><h3>${e(c.name)}</h3></a>${matching ? `<span class="fit-badge">${matching.score}% 匹配</span>` : ""}</div><div class="english">${e(c.english)}</div><p>${e(c.summary)}</p><div class="workload">${i("energy", 14)}<span>${e(c.load)}</span></div>${matching ? `<div class="reason">${i("target", 14)}${e(matching.reasons[0] || "查看画像与工作条件的重合情况")}</div>` : ""}<div class="card-foot"><span>${i("files", 14)} ${c.evidence.length} 条研究依据</span><a href="#role/${c.id}" aria-label="查看${e(c.name)}档案">查看档案 ${i("arrow", 14)}</a></div></div></article>`;
}
const groupCounts = new Map(groups.map((name) => [name, 0]));
for (const career of careers) {
  groupCounts.set(career.category, groupCounts.get(career.category) + 1);
}
function groupBar() {
  const entries = [["全部方向", careers.length], ...groupCounts];
  const buttons = entries.map(([name, count]) => {
    const selected = name === activeGroup;
    return `<button type="button" data-action="group" data-group="${e(name)}" aria-pressed="${selected}" aria-controls="career-results" aria-label="${e(name)}，${count} 份档案"><span>${e(name)}</span><small aria-hidden="true">${count}</small></button>`;
  });
  return `<div class="field-picker" role="group" aria-label="按职业领域筛选">${buttons.join("")}</div>`;
}
function galleryResultsHead(count) {
  const views = [["grid", "网格"], ["list", "列表"]];
  return `<div class="gallery-results-head"><p class="result-tally" role="status"><strong>${e(activeGroup)}</strong><span>${count} 份职业档案${state.profile ? " · 按适配度排序" : ""}</span></p>
    <div class="view-switch" role="group" aria-label="显示方式">${views.map(([key, label]) => `<button type="button" class="${state.view === key ? "active" : ""}" aria-label="${label}视图" aria-pressed="${state.view === key}" data-action="view" data-view="${key}">${i(key, 16)}</button>`).join("")}</div></div>`;
}
function filterCareers(q) {
  const words = q.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return careers.filter((c) =>
    words.every((w) =>
      [
        c.name,
        c.english,
        c.category,
        c.summary,
        ...c.tags,
        ...c.interests,
        ...c.conditions,
      ]
        .join(" ")
        .toLocaleLowerCase()
        .includes(w),
    ),
  );
}
function empty(ic, title, body, action = "", label = "") {
  return `<div class="empty"><div class="empty-icon">${i(ic, 28)}</div><h3>${e(title)}</h3><p>${e(body)}</p>${action ? `<button class="btn light" data-action="${action}">${e(label)} ${i("arrow", 15)}</button>` : ""}</div>`;
}
function grid(items, fit = false) {
  return `<div class="card-grid ${state.view === "list" ? "as-list" : ""}">${items.map((c) => card(c, fit)).join("")}</div>`;
}
function featured(home) {
  const items = filterCareers(home ? "" : query).filter(
    (c) =>
      (activeGroup === "全部方向" || c.category === activeGroup) &&
      (home || !libraryCity || localRoleEvidence(c, libraryCity).length),
  );
  if (home && state.profile)
    items.sort(
      (a, b) =>
        matchCareer(b, state.profile).score -
        matchCareer(a, state.profile).score,
    );
  return `${home ? groupBar() + galleryResultsHead(items.length) : `<div class="results-head"><span class="result-tally" role="status">${items.length} 份职业档案${libraryCity ? " · 含" + e(libraryCity) + "资料" : ""}</span><button class="btn light view-mode" data-action="view" data-view="${state.view === "grid" ? "list" : "grid"}">${i(state.view === "grid" ? "list" : "grid", 14)} ${state.view === "grid" ? "列表" : "网格"}视图</button></div>`}<div id="career-results">${items.length ? grid(items, home && !!state.profile) : empty("search", "没有找到对应职业", "可以换一个关键词，或查看全部方向。", "clearFilters", "重置筛选")}</div>`;
}
function pageHeading(title, desc, action = "") {
  return `<div class="page-heading"><div><h1>${title}</h1><p>${desc}</p></div>${action}</div>`;
}
function homePage() {
  return `${hero()}<div class="metrics">${metric("library", "book", "收录职业", careers.length, "份档案", "m-sage")}${metric("library", "layers", "探索领域", groups.length, "个方向", "m-ochre")}${metric("sources", "library", "研究资料", allSources.length, "个来源", "m-blue")}</div><div class="explore-entrance"><a class="text-link" href="#paths/learning">${i("leaf", 16)} 专业与兴趣探索 ${i("arrow", 14)}</a><span>从教育技术、短视频、穿搭或做饭开始</span></div><section class="gallery"><div class="section-head"><div><h2>${state.profile ? "为你推荐的职业" : "职业探索图鉴"}</h2><p>${state.profile ? "先看与你画像更匹配的职业，也可以按领域探索。" : "从真实的工作内容出发，了解每个职业的收获与代价。"}</p></div><a class="text-link directory-link" href="#directory">查职业名称索引 <span>${occupationIndex.length.toLocaleString("zh-CN")}</span> ${i("arrow", 15)}</a></div>${featured(true)}</section>`;
}
function libraryModes(directory = false) {
  return `<nav class="library-modes" aria-label="图鉴类型"><a href="#library" ${directory ? "" : 'aria-current="page"'}>${i("book", 16)} 深度职业档案 <b>${careers.length}</b></a><a href="#directory" ${directory ? 'aria-current="page"' : ""}>${i("library", 16)} 职业名称索引 <b>${occupationIndex.length.toLocaleString()}</b></a></nav>`;
}
function cityOptions(selected, label = "全部城市") {
  return `<option value="">${label}</option>${cities.map((city) => `<option value="${city}" ${city === selected ? "selected" : ""}>${city}</option>`).join("")}`;
}
function libraryFilters() {
  return `<div class="atlas-filters"><label>${i("layers", 15)} 领域<select id="library-group"><option value="全部方向">全部领域</option>${groups.map((g) => `<option ${g === activeGroup ? "selected" : ""}>${e(g)}</option>`).join("")}</select></label></div><div class="city-filter-row" aria-label="按城市资料筛选"><span>${i("pin", 15)} 城市资料</span>${["", ...cities].map((city) => `<button class="city-choice" data-action="library-city" data-city="${city}" aria-pressed="${libraryCity === city}">${city || "全部城市"}</button>`).join("")}</div>`;
}
function sourceMatches(s, q) {
  const related = (s.roles || []).map((id) => getCareer(id)?.name || "");
  return q
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .every((w) =>
      [s.label, s.region, s.city, s.kind, s.note, ...related]
        .join(" ")
        .toLowerCase()
        .includes(w),
    );
}
function evidenceResults(items, id = "") {
  return `<p class="result-tally" role="status">找到 ${items.length} 份资料</p>${items.length ? `<div class="evidence-list">${items.map((s) => evidenceCard(s, id)).join("")}</div>` : empty("search", "暂无符合条件的资料", "可以切换城市、资料类型或关键词。")}`;
}
function cityKey(city) {
  return (
    Object.keys(cityKeys).find((key) => cityKeys[key] === city) || "beijing"
  );
}
function cityPage() {
  const city = cityKeys[current().id] || cities[0];
  const records = allSources.filter((s) => s.city === city);
  const roles = careers.filter((c) => localRoleEvidence(c, city).length);
  const postings = records.filter((s) => s.kind === "岗位样本");
  return `${pageHeading("城市资料", "按工作城市核对招聘要求、具体任务和当地市场数据。")}<nav class="city-nav" aria-label="选择城市">${cities.map((item) => `<a href="#city/${cityKey(item)}" ${item === city ? 'aria-current="page"' : ""}>${item}</a>`).join("")}</nav><section class="city-summary"><div class="city-pin">${i("pin", 24)}</div><div><h2>${city}</h2><p>${records.length} 份本地原文 <span>·</span> ${postings.length} 份招聘样本 <span>·</span> 涉及 ${roles.length} 份职业档案</p></div><div class="city-actions"><a class="text-link" href="${jobsUrl([], city)}">查看${e(city)}招聘 ${i("arrow", 15)}</a><a class="text-link" href="#library/${cityKey(city)}">筛选当地职业 ${i("arrow", 15)}</a></div></section><div class="source-search-row"><label class="library-search">${i("search")}<input id="city-query" value="${e(cityQuery)}" placeholder="搜索机构、职业或资料内容" aria-label="搜索本城资料"></label><label class="compact-select">资料类型<select id="city-kind"><option value="">全部类型</option>${[...new Set(records.map((s) => s.kind).filter(Boolean))].map((t) => `<option ${t === cityKind ? "selected" : ""}>${e(t)}</option>`).join("")}</select></label></div><div id="city-results">${evidenceResults(records.filter((s) => (!cityKind || s.kind === cityKind) && sourceMatches(s, cityQuery)))}</div>`;
}
function localPanel(c) {
  const eligible = localRoleEvidence(c);
  const filtered = eligible.filter((s) => !detailCity || s.city === detailCity);
  return `<section class="detail-panel"><div class="local-filter-title"><div><h2>这份职业的城市资料</h2><p class="support-text">按招聘批次和工作地点比较，查看用人单位原文中的条件。</p></div><label class="compact-select">城市<select id="detail-city">${cityOptions(detailCity)}</select></label></div>${filtered.length ? evidenceResults(filtered, c.id) : `<div class="local-empty"><p>当前尚未收录${e(detailCity || "六座城市")}与${e(c.name)}直接相关的资料。</p><a class="text-link" href="#city/${cityKey(detailCity)}">浏览城市资料 ${i("arrow", 14)}</a></div>`}</section>`;
}
function directoryList() {
  const words = indexQuery.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const filtered = occupationIndex.filter(
    (item) =>
      (!indexGroup || indexGroup === item.group) &&
      words.every((w) =>
        [item.name, item.code, item.group].join(" ").toLowerCase().includes(w),
      ),
  );
  const visible = filtered.slice(0, indexLimit);
  return `<div class="directory-count" role="status">共 ${filtered.length.toLocaleString()} 项，显示 ${visible.length.toLocaleString()} 项</div>${
    visible.length
      ? `<div class="occupation-list">${visible
          .map((item) => {
            const role = careers.find((c) => c.name === item.name);
            return `<article><code>${e(item.code)}</code><div><b>${e(item.name)}</b><small>${e(item.group)}</small></div>${role ? `<a class="text-link" href="#role/${role.id}">读档案 ${i("arrow", 13)}</a>` : `<button class="inline-action" data-action="index-note" data-name="${e(item.name)}">做调研 ${i("pen", 13)}</button>`}</article>`;
          })
          .join("")}</div>`
      : empty(
          "search",
          "未找到匹配的职业条目",
          "换一个行业关键词，或用职业编码查找。",
        )
  }${visible.length < filtered.length ? `<button class="btn light more-index" data-action="more-index">再显示 ${Math.min(50, filtered.length - visible.length)} 项</button>` : ""}`;
}
function directoryPage() {
  return `${pageHeading("职业图鉴", "从职业名称与编码查方向，也可以直接阅读已整理的深度档案。")}${libraryModes(true)}<div class="index-method"><div>${i("library", 18)}<b>${e(indexSource.label)}</b></div><p>${e(indexSource.note)} <a href="${e(safeUrl(indexSource.url))}" target="_blank" rel="noopener noreferrer">查看原始名录 ${i("diagonal", 12)}</a></p></div><div class="source-search-row"><label class="library-search">${i("search")}<input id="index-query" value="${e(indexQuery)}" aria-label="搜索职业名称或编码" placeholder="搜索职业名称或编码"></label><label class="compact-select">职业大类<select id="index-group"><option value="">全部大类</option>${[...new Set(occupationIndex.map((x) => x.group))].map((g) => `<option ${g === indexGroup ? "selected" : ""}>${e(g)}</option>`).join("")}</select></label></div><div id="index-results">${directoryList()}</div>`;
}
function libraryPage() {
  return `${pageHeading("职业图鉴", "按领域、技能或城市资料找方向，进入档案查看工作实景与入行路径。")} ${libraryModes()}<div class="library-filter-panel"><label class="library-search">${i("search")}<input id="library-query" value="${e(query)}" placeholder="搜索职业名称、技能或工作偏好" aria-label="搜索职业名称、技能或工作偏好"></label>${libraryFilters()}</div><section id="library-body">${featured(false)}</section>`;
}
function fitPage() {
  const p = state.profile;
  if (!p)
    return `${pageHeading("适配测评", "用兴趣、技能和生活偏好缩小探索范围。")}${hero()}<div class="plain-panel"><h2>你的画像如何影响推荐</h2><p>先选择愿意反复做的事，再选择能接受的工作条件。完成后，每个推荐方向都会说明匹配依据，你还可以进入岗位情境，试一试自己的反应。</p></div>`;
  const sorted = careers
    .slice()
    .sort((a, b) => matchCareer(b, p).score - matchCareer(a, p).score);
  return `${pageHeading("我的职业画像", "从匹配理由开始探索，再用真实的岗位与访谈验证。", `<button class="btn light" data-action="assessment">${i("pen", 16)} 编辑画像</button>`)}<section class="profile-summary"><span class="round-symbol">${i("compass", 30)}</span><div><h2>${e(p.stage || "职业探索者")}${p.city ? `<small>${i("pin", 14)}${e(p.city)}</small>` : ""}</h2><div class="tag-row">${[...p.interests, ...p.conditions, ...(p.skills || [])].map((t) => `<span>${e(t)}</span>`).join("")}</div></div></section><div class="section-head"><div><h2>适合优先了解的方向</h2><p>匹配度表示画像偏好与岗位特征的重合程度。选择档案可查看依据。</p></div></div>${grid(sorted, true)}`;
}
function savedPage() {
  const jobs = state.saved.map(getCareer).filter(Boolean);
  return `${pageHeading("我的收藏", `已保存 ${jobs.length} 份职业档案，将感兴趣的方向放在一起比较。`, jobs.length >= 2 ? `<button class="btn primary" data-action="compare">${i("balance", 16)} 对比职业</button>` : "")}${jobs.length ? grid(jobs, !!state.profile) : empty("bookmark", "把想深入了解的职业留在这里", "在职业卡片上点击书签，收藏两个方向后可以并排比较。", "library", "浏览职业图鉴")}`;
}
function evidenceCard(s, careerId = "") {
  const idx = allSources.findIndex((item) => item.url === s.url);
  return `<article class="evidence-card"><div class="evidence-icon">${i("files", 20)}</div><div class="evidence-copy"><div class="source-meta">${s.kind ? `<b>${e(s.kind)}</b> ` : ""}${e(s.region)} <span>·</span> ${e(s.date)}</div><h3><a href="${e(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer">${e(s.label)} ${i("diagonal", 13)}</a></h3><p>${e(s.note)}</p>${
    !careerId && s.roles?.length
      ? `<div class="evidence-related">${s.roles
          .map(getCareer)
          .filter(Boolean)
          .map((c) => `<a href="#role/${c.id}">${e(c.name)}</a>`)
          .join("")}</div>`
      : ""
  }<div class="source-actions">${/\.pdf(?:$|[?#])/i.test(s.url) ? `<a class="pdf-source" href="${e(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer">${i("book", 14)} 阅读 PDF 报告</a>` : `<button data-action="capture" data-index="${idx}" data-id="${e(careerId)}">${i("download", 14)} 采集网页摘要</button>`}<button data-action="clip" data-index="${idx}" data-id="${e(careerId)}">${i("notes", 14)} 摘录到手记</button></div></div></article>`;
}
function sourcesPage() {
  return `${pageHeading("资料来源", "查看职业档案引用的原始资料，按地区核对口径，采集需要跟进的证据。")}<div class="source-notice">${i("info", 18)}<p>职业预测按来源地区展示。核实本地机会时，可将目标城市的招聘启事和访谈加入同一份调研手记。</p></div><label class="library-search">${i("search")}<input id="source-query" placeholder="搜索机构、地区或资料名称" aria-label="搜索资料来源"></label><label class="compact-select source-city-select">城市<select id="source-city">${cityOptions(sourceCity, "所有地区")}</select></label><div class="evidence-list" id="sources-list">${allSources.map((s) => evidenceCard(s)).join("")}</div>`;
}
function pointBlock(title, text, ic) {
  return `<div class="detail-block"><h3>${i(ic, 17)}${e(title)}</h3><p>${e(text)}</p></div>`;
}
function bullets(items) {
  return `<ul class="point-list">${items.map((item) => `<li>${e(item)}</li>`).join("")}</ul>`;
}
const tabs = [
  "工作实景",
  "城市资料",
  "市场与 AI",
  "成长路径",
  "情境测评",
  "调研依据",
];
function details(c) {
  const s = state.answers[c.id],
    scenario = c.scenario;
  if (detailTab === "城市资料") return localPanel(c);
  if (detailTab === "工作实景")
    return `<div class="detail-layout"><section class="detail-panel"><h2>日常在做什么</h2><p class="support-text">根据职业资料整理的典型工作情境。实际排班、任务分工和地点可在调研手记中核实。</p>${bullets(c.day)}<div class="tradeoffs"><div><h3>${i("leaf", 17)}工作中的收获</h3>${bullets(c.pros)}</div><div><h3>${i("energy", 17)}需要承担的代价</h3>${bullets(c.cons)}</div></div></section><aside class="detail-panel">${pointBlock("强度与疲惫来源", c.intensity, "energy")}${pointBlock("地点与生活体验", c.geography, "pin")}</aside></div>`;
  if (detailTab === "市场与 AI")
    return `<div class="detail-layout"><section class="detail-panel">${pointBlock("就业市场与入场竞争", c.market, "brief")}${pointBlock("AI 会改变哪些任务", c.ai, "layers")}</section><aside class="detail-panel"><h2>核实本地竞争</h2><p>在${e(state.profile?.city || "目标城市")}收集同口径的招聘样本。记录经验门槛、地点和发布日期，面试时再确认团队分工。</p>${localEvidence(c)}<button class="btn light" data-action="new-note" data-id="${c.id}">${i("plus", 15)} 添加招聘样本</button></aside></div>`;
  if (detailTab === "成长路径")
    return `<section class="detail-panel"><h2>可以怎样迈出第一步</h2><ol class="step-list">${c.steps.map((step, j) => `<li><b>${two(j + 1)}</b><p>${e(step)}</p></li>`).join("")}</ol><button class="btn light" data-action="experience" data-id="${c.id}">${i("notes", 15)} 记录试做体验</button></section>`;
  if (detailTab === "情境测评")
    return `<section class="detail-panel scenario"><div class="source-meta">岗位情境练习</div><h2>${e(scenario.question)}</h2><div class="option-list">${scenario.options.map((op, j) => `<button data-action="answer" data-id="${c.id}" data-index="${j}" aria-pressed="${s === j}" class="${s === j ? "chosen" : ""}"><span>${String.fromCharCode(65 + j)}</span>${e(op.label)}${s === j ? i("check", 16) : ""}</button>`).join("")}</div>${s != null && scenario.options[s] ? `<div class="feedback"><b>${["值得进一步验证", "可以继续尝试", "与这项任务较契合"][scenario.options[s].fit] || "你的选择"}</b><p>${e(scenario.options[s].feedback)}</p></div>` : '<p class="support-text">选择你最可能采取的做法，查看它与这项工作任务的关系。</p>'}</section>`;
  return `<section class="detail-panel"><h2>这份档案的研究依据</h2><p class="support-text">来源说明标明了每份资料能够支持的判断。</p><div class="evidence-list">${c.evidence.map((s) => evidenceCard(s, c.id)).join("")}</div><h3 class="subhead">我的岗位记录</h3>${
    state.notes.filter((n) => n.career === c.id).length
      ? state.notes
          .filter((n) => n.career === c.id)
          .map(noteCard)
          .join("")
      : '<p class="support-text">尚未添加本地招聘样本或访谈。</p>'
  }<button class="btn light" data-action="new-note" data-id="${c.id}">${i("plus", 15)} 新建调研记录</button></section>`;
}
function localEvidence(c) {
  const samples = state.notes.filter(
    (n) =>
      n.career === c.id &&
      n.type === "招聘样本" &&
      (!state.profile?.city || n.city === state.profile.city),
  );
  return `<div class="sample-count"><b>${samples.length}</b> 条${state.profile?.city ? e(state.profile.city) : "已记录"}招聘样本</div>`;
}
function rolePage(c) {
  const isSaved = state.saved.includes(c.id),
    fit = state.profile ? matchCareer(c, state.profile) : null;
  return `<a class="backlink" href="#library">${i("back", 15)} 返回职业图鉴</a><section class="role-banner ${categoryClass(c.category)}"><div class="role-intro"><div class="source-meta">${e(c.category)} <span>/</span> 职业档案</div><h1>${e(c.name)}</h1><div class="english">${e(c.english)}</div><p>${e(c.summary)}</p><div class="tag-row">${c.tags.map((t) => `<span>${e(t)}</span>`).join("")}</div></div><div class="role-plate"><img src="${asset(c)}" alt=""></div></section><div class="role-toolbar"><div class="role-fit">${i("target", 17)}${fit ? `画像适配度 <b>${fit.score}%</b>` : "建立画像后可查看个人适配度"} <button class="inline-action" data-action="${fit ? "whyMatch" : "assessment"}" data-id="${c.id}">${fit ? "查看理由" : "开始测评"} ${i("chev", 12)}</button></div><a class="text-link" href="${jobsUrl([c.id])}">${i("brief", 15)} 对应招聘</a><button class="btn light" data-action="save" data-id="${c.id}" aria-pressed="${isSaved}">${i("bookmark", 15)}${isSaved ? "已收藏" : "收藏职业"}</button></div><div class="detail-tabs" aria-label="档案内容">${tabs.map((t) => `<button data-action="tab" data-tab="${t}" class="${detailTab === t ? "active" : ""}" aria-pressed="${detailTab === t}">${t}</button>`).join("")}</div><div id="detail-body">${details(c)}</div>`;
}
function noteCard(n) {
  const c = getCareer(n.career);
  return `<article class="note-card"><div class="note-top"><span class="note-type">${e(n.type)}</span><small>${e(n.date)}${n.city ? " · " + e(n.city) : ""}</small></div><h3>${e(n.title)}</h3>${c ? `<a class="note-career" href="#role/${c.id}">${i("brief", 12)} ${e(c.name)}</a>` : ""}<p>${e(n.text)}</p>${n.pay || n.hours ? `<div class="note-meta">${n.pay ? "薪酬 " + e(n.pay) + "　" : ""}${n.hours ? "工时 " + e(n.hours) : ""}</div>` : ""}<div class="note-foot">${safeUrl(n.url) ? `<a href="${e(safeUrl(n.url))}" target="_blank" rel="noopener noreferrer">${i("link", 13)} 查看原文 ${i("diagonal", 12)}</a>` : "<span>个人调研记录</span>"}<div><button class="icon-button" data-action="edit-note" data-id="${e(n.id)}" aria-label="编辑手记">${i("pen", 14)}</button><button class="icon-button" data-action="delete-note" data-id="${e(n.id)}" aria-label="删除手记">${i("trash", 14)}</button></div></div></article>`;
}
function notesList(q = "") {
  const notes = state.notes.filter(
    (n) =>
      (noteType === "全部记录" || n.type === noteType) &&
      [n.title, n.text, n.city, getCareer(n.career)?.name]
        .join(" ")
        .includes(q.trim()),
  );
  return notes.length
    ? `<div class="note-grid">${notes.map(noteCard).join("")}</div>`
    : empty(
        "notes",
        state.notes.length ? "没有符合筛选的手记" : "记录你的第一条职业线索",
        state.notes.length
          ? "切换类型或换一个关键词。"
          : "保存一条招聘启事、一次从业者访谈，或你亲自试做后的感受。",
        "new-note",
        "写一条手记",
      );
}
function notesPage() {
  return `${pageHeading("调研手记", "把工作地点、实际工时和亲身感受，放回具体的岗位里。", `<div class="heading-actions">${state.notes.length ? `<button class="btn light" data-action="export">${i("download", 15)} 导出</button>` : ""}<button class="btn primary" data-action="new-note">${i("plus", 16)} 新建手记</button></div>`)}<label class="library-search">${i("search")}<input id="notes-query" placeholder="查找岗位、城市或笔记内容" aria-label="搜索手记"></label><div class="group-tabs note-filters">${["全部记录", ...noteTypes].map((t) => `<button class="chip ${t === noteType ? "active" : ""}" data-action="note-type" data-type="${t}">${t}</button>`).join("")}</div><div id="notes-body">${notesList()}</div>`;
}
function render() {
  const { page, id } = current();
  root.innerHTML = shell();
  const main = document.querySelector("main");
  const pages = {
    home: homePage,
    library: libraryPage,
    paths: () => pathsPage(id, state.profile),
    jobs: jobsPage,
    city: cityPage,
    directory: directoryPage,
    fit: fitPage,
    saved: savedPage,
    notes: notesPage,
    sources: sourcesPage,
    role: () => rolePage(getCareer(id)),
  };
  main.innerHTML = pages[page]();
  document.title = `${page === "role" ? getCareer(id).name : routes[page]} · 职野 Career Atlas`;
}
function searchDialog() {
  const d = modal(
    "搜索职业图鉴",
    `<div class="dialog-body"><label class="dialog-search">${i("search")}<input id="global-search" placeholder="试试：数据、沟通协作、现场工作" aria-label="职业搜索"></label><div class="result-list"></div></div>`,
  );
  const paint = (q) => {
    const jobs = filterCareers(q).slice(0, 12);
    d.querySelector(".result-list").innerHTML = jobs.length
      ? jobs
          .map(
            (c) =>
              `<a href="#role/${c.id}" class="result-link">${i("book", 20)}<span><strong>${e(c.name)}</strong><small>${e(c.category)} · ${e(c.tags.slice(0, 2).join("、"))}</small></span>${i("chev", 14)}</a>`,
          )
          .join("")
      : '<p class="empty-search">深度档案中暂无匹配，可继续查找职业名称索引。</p>';
    d.querySelector(".result-list").insertAdjacentHTML(
      "beforeend",
      `<a class="result-link" href="#directory/${encodeURIComponent(q.trim())}">${i("library", 18)}<span><strong>在职业名称索引中查找</strong><small>${occupationIndex.length.toLocaleString()} 个职业条目</small></span>${i("chev", 14)}</a>`,
    );
  };
  paint("");
  d.querySelector("input").focus();
  d.querySelector("input").oninput = (ev) => paint(ev.target.value);
  d.addEventListener("click", (ev) => {
    if (ev.target.closest("a")) d.close();
  });
}
function comparison() {
  const options = state.saved.map(getCareer).filter(Boolean);
  if (options.length < 2) return;
  const d = modal(
    "职业对比",
    `<div class="dialog-body"><p class="dialog-copy">选择两个方向，并排比较你需要承担的工作条件。</p><div class="compare-select">${[0, 1].map((x) => `<label>${x ? "第二个方向" : "第一个方向"}<select>${options.map((c, j) => `<option ${j === x ? "selected" : ""} value="${c.id}">${e(c.name)}</option>`).join("")}</select></label>`).join("")}</div><div class="compare-body"></div></div>`,
    "wide-dialog",
  );
  const paint = () => {
    const [a, b] = [...d.querySelectorAll("select")].map((s) =>
      getCareer(s.value),
    );
    d.querySelector(".compare-body").innerHTML =
      a.id === b.id
        ? '<p class="empty-search">选择两个不同的职业即可开始比较。</p>'
        : `<table class="compare-table"><thead><tr><th>观察维度</th><th>${e(a.name)}</th><th>${e(b.name)}</th></tr></thead><tbody>${[
            ["典型任务", "day"],
            ["工作强度", "intensity"],
            ["地理体验", "geography"],
            ["就业市场", "market"],
            ["AI 影响", "ai"],
            ["努力方向", "steps"],
          ]
            .map(
              ([label, key]) =>
                `<tr><th>${label}</th>${[a, b].map((c) => `<td>${e(Array.isArray(c[key]) ? c[key][0] : c[key])}</td>`).join("")}</tr>`,
            )
            .join("")}</tbody></table>`;
  };
  d.onchange = paint;
  paint();
}
function noteForm(n = {}) {
  const editing = !!n.id;
  const d = modal(
    editing ? "编辑调研手记" : "新建调研手记",
    `<form class="dialog-body note-form"><div class="form-grid"><label>记录类型<select name="type">${noteTypes.map((t) => `<option ${n.type === t ? "selected" : ""}>${t}</option>`).join("")}</select></label><label>关联职业<select name="career"><option value="">通用调研</option>${careers.map((c) => `<option value="${c.id}" ${n.career === c.id ? "selected" : ""}>${e(c.name)}</option>`).join("")}</select></label></div><label>标题<input name="title" maxlength="120" required placeholder="例如：某公司初级岗位的实际工作安排" value="${e(n.title)}"></label><div class="form-grid"><label>城市或地区<input name="city" maxlength="80" placeholder="例如：香港" value="${e(n.city ?? state.profile?.city ?? "")}"></label><label>记录日期<input type="date" name="date" required value="${e(n.date || today())}"></label></div><label>原文链接 <small>选填</small><input name="url" type="url" placeholder="https://…" value="${e(n.url)}"></label><div class="form-grid job-fields"><label>薪酬与币种 <small>选填</small><input name="pay" maxlength="100" placeholder="例如：港币 / 月" value="${e(n.pay)}"></label><label>工时或排班 <small>选填</small><input name="hours" maxlength="100" placeholder="记录原文或访谈所述工时" value="${e(n.hours)}"></label></div><label>观察与摘录<textarea name="text" maxlength="12000" rows="5" required>${e(n.text)}</textarea></label><p class="form-hint"></p><div class="dialog-actions"><button type="button" class="btn light" data-close>取消</button><button class="btn primary" type="submit">保存手记</button></div></form>`,
  );
  const f = d.querySelector("form");
  const hints = {
    招聘样本: "记下入行门槛、常见任务，以及尚未说明的工时和待遇。",
    从业者访谈: "可以问：最近一周最累的是哪一件事？哪些任务最有成就感？",
    试做体验: "记录试做任务、耗时、遇到的困难，以及你是否愿意再做一次。",
    资料摘录: "保留原文语境、统计范围和时间，写下与你的职业选择有关的发现。",
  };
  const sync = () => {
    f.querySelector(".job-fields").hidden =
      f.elements.type.value !== "招聘样本";
    f.querySelector(".form-hint").textContent = hints[f.elements.type.value];
  };
  sync();
  f.elements.type.onchange = sync;
  f.elements.url.oninput = () => f.elements.url.setCustomValidity("");
  f.elements.title.oninput = () => f.elements.title.setCustomValidity("");
  f.elements.text.oninput = () => f.elements.text.setCustomValidity("");
  f.onsubmit = (ev) => {
    ev.preventDefault();
    const vals = Object.fromEntries(
      [...new FormData(f)].map(([k, v]) => [k, v.trim()]),
    );
    if (vals.url && !safeUrl(vals.url)) {
      f.elements.url.setCustomValidity("请输入 http 或 https 网页地址");
      f.reportValidity();
      return;
    }
    for (const k of ["title", "text"])
      if (!vals[k]) {
        f.elements[k].setCustomValidity("请输入内容");
        f.reportValidity();
        return;
      }
    if (vals.type !== "招聘样本") {
      vals.hours = "";
      vals.pay = "";
    }
    const record = { ...vals, id: n.id || crypto.randomUUID() };
    if (editing)
      state.notes = state.notes.map((x) => (x.id === n.id ? record : x));
    else state.notes.unshift(record);
    const stored = persist();
    d.close();
    render();
    if (stored) toast("调研手记已保存");
  };
}
function exportNotes() {
  const data = JSON.stringify(
    { exportedAt: new Date().toISOString(), notes: state.notes },
    null,
    2,
  );
  const url = URL.createObjectURL(
    new Blob([data], { type: "application/json;charset=utf-8" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = `职野-调研手记-${today()}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function capture(source, careerId) {
  const d = modal(
    "采集网页摘要",
    `<div class="dialog-body"><h3>${e(source.label)}</h3><p class="dialog-copy capture-status" role="status">正在读取来源网页…</p><div class="capture-preview"></div><div class="dialog-actions"><button class="btn light" data-close>关闭</button><button class="btn primary capture-save" disabled>存入手记</button></div></div>`,
  );
  let draft;
  const btn = d.querySelector(".capture-save");
  const status = d.querySelector(".capture-status");
  const preview = d.querySelector(".capture-preview");
  (async () => {
    try {
      const data = await collectSource(source.url);
      draft = {
        type: "资料摘录",
        career: careerId,
        url: data.url || source.url,
        title: data.title || source.label,
        text:
          data.excerpt +
          "\n\n采集时间：" +
          new Date(data.retrievedAt).toLocaleString("zh-CN"),
      };
      status.textContent = "已读取网页，可检查摘要后存入手记。";
    } catch (err) {
      status.textContent =
        err.message || "暂时无法读取网页，你可以保存已整理的来源说明。";
      draft = {
        type: "资料摘录",
        career: careerId,
        url: source.url,
        title: source.label,
        text: source.note,
      };
      btn.textContent = "保存来源说明";
    }
    preview.textContent = draft.text;
    btn.disabled = false;
    btn.onclick = () => {
      d.close();
      noteForm({ ...draft, city: source.city || "" });
    };
  })();
}
function progressDialog() {
  const tasks = [
    ["建立职业画像", !!state.profile, "fit"],
    ["收藏一个方向", !!state.saved.length, "library"],
    ["写下调研记录", !!state.notes.length, "notes"],
  ];
  const d = modal(
    "我的探索进度",
    `<div class="dialog-body"><div class="result-list">${tasks.map(([label, done, route]) => `<a href="#${route}" class="result-link">${i(done ? "check" : "flag")}<strong>${label}</strong><small>${done ? "已完成" : "待探索"}</small>${i("chev", 14)}</a>`).join("")}</div></div>`,
  );
  d.onclick = (ev) => {
    if (ev.target.closest("a")) d.close();
  };
}
function accountDialog() {
  const d = modal(
    "个人工作空间",
    `<div class="dialog-body"><p class="dialog-copy">职业画像、收藏与手记保存在当前浏览器。已收藏 ${state.saved.length} 个职业，记录了 ${state.notes.length} 条手记。</p><div class="dialog-actions"><button class="btn light account-export" ${state.notes.length ? "" : "disabled"}>${i("download", 15)} 导出手记</button><button class="btn primary account-profile">${state.profile ? "编辑画像" : "建立画像"}</button></div></div>`,
  );
  d.querySelector(".account-export").onclick = exportNotes;
  d.querySelector(".account-profile").onclick = () => {
    d.close();
    openProfile();
  };
}
function saveCareer(id) {
  if (!getCareer(id)) return;
  const isSaved = state.saved.includes(id);
  state.saved = isSaved
    ? state.saved.filter((x) => x !== id)
    : [...state.saved, id];
  const stored = persist();
  render();
  document
    .querySelector(`[data-action="save"][data-id="${CSS.escape(id)}"]`)
    ?.focus({ preventScroll: true });
  if (stored) toast(isSaved ? "已移出收藏" : "已加入我的收藏");
}
function setGroup(g) {
  activeGroup = g;
  render();
  document
    .querySelector(`[data-action="group"][data-group="${CSS.escape(g)}"]`)
    ?.focus({ preventScroll: true });
}
root.addEventListener("click", (ev) => {
  const button = ev.target.closest("[data-action]");
  if (!button) return;
  const { action, id, index, group, tab, type, view } = button.dataset;
  const c = getCareer(id);
  switch (action) {
    case "library-city":
      libraryCity = button.dataset.city;
      render();
      document
        .querySelector(
          `[data-action="library-city"][data-city="${CSS.escape(libraryCity)}"]`,
        )
        ?.focus({ preventScroll: true });
      break;
    case "more-index":
      indexLimit += 50;
      document.querySelector("#index-results").innerHTML = directoryList();
      break;
    case "job-note": {
      const draft = jobDraft(button.dataset.job);
      if (draft) noteForm(draft);
      break;
    }
    case "index-note":
      noteForm({
        type: "资料摘录",
        title: button.dataset.name + " · 职业调研",
        url: indexSource.url,
        text: "职业名称：" + button.dataset.name + "\n想进一步了解的工作内容：",
      });
      break;
    case "menu":
      document.body.classList.toggle("menu-open");
      break;
    case "assessment":
      openProfile();
      break;
    case "search":
      searchDialog();
      break;
    case "library":
      activeGroup = "全部方向";
      query = "";
      navigate("library");
      break;
    case "save":
      saveCareer(id);
      break;
    case "group":
      setGroup(group);
      break;
    case "view":
      state.view = view;
      persist();
      render();
      document
        .querySelector(`[data-action="view"][data-view="${view}"]`)
        ?.focus({ preventScroll: true });
      break;
    case "clearFilters":
      libraryCity = "";
      query = "";
      setGroup("全部方向");
      break;
    case "tab":
      detailTab = tab;
      render();
      document
        .querySelector(`[data-tab="${tab}"]`)
        ?.focus({ preventScroll: true });
      break;
    case "answer":
      state.answers[id] = Number(index);
      persist();
      document.querySelector("#detail-body").innerHTML = details(c);
      document
        .querySelector(`[data-action="answer"][data-index="${index}"]`)
        ?.focus({ preventScroll: true });
      break;
    case "whyMatch": {
      const m = matchCareer(c, state.profile);
      modal(
        "适配依据",
        `<div class="dialog-body"><h3>${e(c.name)} · ${m.score}% 匹配</h3>${bullets(m.reasons)}<p class="support-text">评分用于比较偏好重合程度。可结合情境练习与本地调研记录，进一步验证选择。</p></div>`,
      );
      break;
    }
    case "compare":
      comparison();
      break;
    case "new-note":
      noteForm({ career: id || "", type: "招聘样本" });
      break;
    case "experience":
      noteForm({ career: id, type: "试做体验", title: `${c.name} · 任务试做` });
      break;
    case "edit-note": {
      const n = state.notes.find((item) => item.id === id);
      if (n) noteForm(n);
      break;
    }
    case "delete-note": {
      const n = state.notes.find((item) => item.id === id);
      if (!n) break;
      const d = modal(
        "删除这条手记？",
        `<div class="dialog-body"><p class="dialog-copy">「${e(n.title)}」将从本地手记中移除。</p><div class="dialog-actions"><button class="btn light" data-close>保留手记</button><button class="btn primary confirm-delete">删除手记</button></div></div>`,
      );
      d.querySelector(".confirm-delete").onclick = () => {
        state.notes = state.notes.filter((item) => item.id !== id);
        const stored = persist();
        d.close();
        render();
        if (stored) toast("手记已删除");
      };
      break;
    }
    case "note-type":
      noteType = type;
      render();
      break;
    case "clip": {
      const s = sourceFor(c, index);
      if (s)
        noteForm({
          type: "资料摘录",
          career: id || "",
          title: s.label,
          city: s.city || "",
          url: s.url,
          text: s.note + "\n\n资料范围：" + s.region + " · " + s.date,
        });
      break;
    }
    case "capture": {
      const s = sourceFor(c, index);
      if (s) capture(s, id || "");
      break;
    }
    case "export":
      exportNotes();
      break;
    case "account":
      accountDialog();
      break;
    case "progress":
      progressDialog();
      break;
  }
});
function updateCityResults() {
  const city = cityKeys[current().id] || cities[0];
  document.querySelector("#city-results").innerHTML = evidenceResults(
    allSources.filter(
      (s) =>
        s.city === city &&
        (!cityKind || s.kind === cityKind) &&
        sourceMatches(s, cityQuery),
    ),
  );
}
root.addEventListener("change", (ev) => {
  const el = ev.target;
  if (el.form?.id === "job-filters") {
    updateJobs(el.form);
    return;
  }
  if (el.id === "library-group") {
    activeGroup = el.value;
    document.querySelector("#library-body").innerHTML = featured(false);
  }
  if (el.id === "city-kind") {
    cityKind = el.value;
    updateCityResults();
  }
  if (el.id === "index-group") {
    indexGroup = el.value;
    indexLimit = 50;
    document.querySelector("#index-results").innerHTML = directoryList();
  }
  if (el.id === "detail-city") {
    detailCity = el.value;
    document.querySelector("#detail-body").innerHTML = details(
      getCareer(current().id),
    );
    document.querySelector("#detail-city")?.focus({ preventScroll: true });
  }
  if (el.id === "source-city") {
    sourceCity = el.value;
    document
      .querySelector("#source-query")
      .dispatchEvent(new Event("input", { bubbles: true }));
  }
});
root.addEventListener("input", (ev) => {
  const el = ev.target;
  if (el.id === "city-query") {
    cityQuery = el.value;
    updateCityResults();
  }
  if (el.id === "index-query") {
    indexQuery = el.value;
    indexLimit = 50;
    document.querySelector("#index-results").innerHTML = directoryList();
  }
  if (el.id === "library-query") {
    query = el.value;
    document.querySelector("#library-body").innerHTML = featured(false);
  }
  if (el.id === "source-query") {
    const q = el.value.toLowerCase().trim();
    const found = allSources.filter(
      (s) => (!sourceCity || s.city === sourceCity) && sourceMatches(s, q),
    );
    document.querySelector("#sources-list").innerHTML = found.length
      ? found.map((s) => evidenceCard(s)).join("")
      : empty("search", "未找到资料", "可尝试搜索地区或机构名称。");
  }
  if (el.id === "notes-query")
    document.querySelector("#notes-body").innerHTML = notesList(el.value);
});
root.addEventListener("click", (ev) => {
  if (ev.target.closest('a[href^="#role/"]') && current().page === "city")
    libraryCity = cityKeys[current().id] || "";
  if (ev.target.closest('a[href^="#"]'))
    document.body.classList.remove("menu-open");
});
window.addEventListener("hashchange", () => {
  document.body.classList.remove("menu-open");
  activeGroup = "全部方向";
  if (current().page === "library") libraryCity = cityKeys[current().id] || "";
  if (current().page === "directory") {
    indexQuery = routedIndexQuery();
    indexGroup = "";
    indexLimit = 50;
  }
  detailCity =
    libraryCity ||
    cities.find((city) => state.profile?.city?.includes(city)) ||
    "";
  cityQuery = "";
  cityKind = "";
  sourceCity = "";
  query = "";
  detailTab = "工作实景";
  render();
  window.scrollTo({ top: 0, behavior: "instant" });
});
document.addEventListener("keydown", (ev) => {
  if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "k") {
    ev.preventDefault();
    if (!document.querySelector("dialog[open]")) searchDialog();
  }
  if (ev.key === "Escape") document.body.classList.remove("menu-open");
});
indexQuery = routedIndexQuery();
render();

// Re-evaluate deadlines when returning from a school website or leaving this tab open.
window.addEventListener('pageshow', refreshJobResults);
document.addEventListener('visibilitychange', () => { if (!document.hidden) refreshJobResults(); });
window.setInterval(() => { if (!document.hidden) refreshJobResults(); }, 60000);
