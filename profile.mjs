import { modal } from "./ui.mjs";

/**
 * Parent contract: load profile.css, then call openAssessment(profile, onComplete).
 * The parent owns persistence. Save calls onComplete once with a fresh object:
 * { interests: string[], conditions: string[], skills: string[], stage: string, city: string }.
 * Escape, Close, and dialog.close() discard the draft. A populated profile opens in review.
 * Uses the project's native modal() helper and returns the active HTMLDialogElement.
 * matchCareer is a pure function and may also be imported without a DOM.
 */
const interests = [
  ["分析推理", "从线索中找出规律"],
  ["创意表达", "把想法变成作品"],
  ["沟通协作", "和别人一起解决问题"],
  ["动手实践", "亲手制作、调试或修理"],
  ["帮助他人", "陪伴、指导或提供支持"],
  ["组织规划", "安排任务，把握进度"],
];
const conditions = [
  ["稳定节奏", "日常安排大致可预期"],
  ["独立专注", "有整块时间独立做事"],
  ["持续学习", "经常接触新知识"],
  ["现场工作", "在现场接触人或设备"],
  ["团队协作", "与同伴分工、交流"],
  ["灵活地点", "可以选择工作的地点"],
];
// These explicit terms are the entire skill vocabulary used for inference. Each hit
// carries the field and term that justified it, and counts at most once per skill.
const skillTerms = new Map([
  ["数据分析", ["统计分析", "数据可视化", "SQL"]],
  ["表格处理", ["电子表格", "Excel"]],
  ["文字写作", ["写作", "撰稿", "文案", "写稿"]],
  ["视觉设计", ["平面设计", "界面设计", "视觉传达"]],
  ["编程开发", ["编程", "软件开发", "程序开发", "Python", "JavaScript"]],
  ["用户研究", ["用户调研", "用户访谈", "可用性测试"]],
  ["沟通协调", ["跨部门沟通", "客户沟通", "团队协调"]],
  ["项目管理", ["项目统筹", "项目规划", "项目进度"]],
  ["教学辅导", ["教学", "授课", "课程辅导"]],
  ["设备操作", ["操作设备", "操作机床", "设备调试"]],
]);
const stages = [
  "在校探索",
  "准备实习",
  "初次求职",
  "在职发展",
  "考虑转行",
  "重返职场",
];
const contextNote =
  "阶段和城市会随画像保存，供后续规划参考。匹配分数只看兴趣、工作条件和技能。";
const steps = [
  {
    label: "活动兴趣",
    key: "interests",
    title: "哪些事让你愿意主动去做？",
    hint: "想想做起来容易投入的事。可以多选，也可以先跳过。",
    options: interests,
  },
  {
    label: "工作条件",
    key: "conditions",
    title: "怎样工作，你会更自在？",
    hint: "选出你希望在日常工作中遇到的条件。可以多选，也可以跳过。",
    options: conditions,
  },
  {
    label: "个人技能",
    key: "skills",
    title: "哪些技能你已经用过？",
    hint: "上课、做项目或工作中用过的都算。可以多选，也可以跳过。",
    options: Array.from(skillTerms.keys(), (name) => [name]),
  },
  {
    label: "阶段与城市",
    progressLabel: "探索计划",
    title: "你准备从哪里出发？",
    hint: contextNote,
  },
  {
    label: "核对画像",
    title: "看看你的职业画像",
    hint: "看看这些选择是否符合现在的你。保存前，每一项都可以修改。",
  },
];
const reviewStep = steps.length - 1;
const clean = (value) => (typeof value === "string" ? value.trim() : "");
const keyOf = (value) => clean(value).normalize("NFKC").toLowerCase();
function uniqueText(values) {
  const unique = new Map();
  for (const value of Array.isArray(values) ? values : [values]) {
    const key = keyOf(value);
    if (key && !unique.has(key)) unique.set(key, clean(value));
  }
  return [...unique.values()];
}
function copyProfile(profile) {
  return {
    interests: uniqueText(profile?.interests),
    conditions: uniqueText(profile?.conditions),
    skills: uniqueText(profile?.skills),
    stage: clean(profile?.stage),
    city: clean(profile?.city),
  };
}
const fields = {
  name: "职业名称",
  summary: "职业简介",
  tags: "标签",
  interests: "活动兴趣",
  conditions: "工作条件",
  category: "职业类别",
};
function containsTerm(text, term) {
  const needle = keyOf(term);
  // Match Latin tool names as tokens: SQL matches “用SQL查询”, but not “NoSQL”.
  const escaped = needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const prefix = /^[a-z0-9]/.test(needle) ? "(?:^|[^a-z0-9_])" : "";
  const suffix = /[a-z0-9]$/.test(needle) ? "(?=$|[^a-z0-9_])" : "";
  return new RegExp(prefix + escaped + suffix, "u").test(text);
}
/** Equal weight per distinct selection within each dimension. Missing evidence earns
 * zero. Reasons describe coverage of the supplied record, including unmatched items. */
export function matchCareer(career, profile) {
  const draft = copyProfile(profile);
  const total =
    draft.interests.length + draft.conditions.length + draft.skills.length;
  if (!total)
    return {
      score: 0,
      reasons: [
        "还没有可计分的选择。选一项兴趣、工作条件或技能，就能查看匹配依据。",
      ],
    };

  const data = Object.fromEntries(
    Object.keys(fields).map((key) => [
      key,
      uniqueText(career?.[key]).map(keyOf),
    ]),
  );
  const hits = [],
    misses = [];
  for (const { key, label } of steps.filter((step) => step.options)) {
    for (const choice of draft[key]) {
      let evidence;
      if (key === "skills") {
        const terms = [choice, ...(skillTerms.get(choice) || [])];
        for (const field of [
          "tags",
          "name",
          "summary",
          "category",
          "interests",
          "conditions",
        ]) {
          const term = terms.find((word) =>
            data[field].some((text) => containsTerm(text, word)),
          );
          if (term) {
            evidence = `${fields[field]}中有“${term}”`;
            break;
          }
        }
      } else {
        const field = [key, "tags"].find((field) =>
          data[field].includes(keyOf(choice)),
        );
        if (field) evidence = `职业${fields[field]}列出了这一项`;
      }
      if (evidence) hits.push(`${label}“${choice}”有依据，${evidence}。`);
      else misses.push(choice);
    }
  }
  const score = Math.round((100 * hits.length) / total);
  const reasons = [
    ...hits,
    `所选 ${total} 项中，职业资料支持 ${hits.length} 项，等权换算为 ${score} 分。`,
  ];
  if (misses.length)
    reasons.push(
      `资料中暂未找到依据的选择有${misses.map((item) => `“${item}”`).join("、")}。`,
    );
  return { score, reasons };
}

let activeDialog = null;
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = `jcp-${className}`;
  if (text !== undefined) node.textContent = text;
  return node;
}
function button(className, text, action) {
  const node = element("button", className, text);
  node.type = "button";
  node.addEventListener("click", action);
  return node;
}
function renderChoices(step, draft, count) {
  const group = element("fieldset", "choices");
  group.append(element("legend", "sr", `${step.label}，可多选`));
  const grid = element("div", "grid");
  const names = uniqueText([
    ...step.options.map(([name]) => name),
    ...draft[step.key],
  ]);
  const descriptions = new Map(step.options);
  const selected = () => draft[step.key].map(keyOf);
  const updateCount = () => {
    count.textContent = `已选 ${draft[step.key].length} 项`;
  };
  for (const name of names) {
    const label = element("label", "choice");
    const input = element("input");
    input.type = "checkbox";
    input.value = name;
    input.checked = selected().includes(keyOf(name));
    input.addEventListener("change", () => {
      draft[step.key] = draft[step.key].filter(
        (value) => keyOf(value) !== keyOf(name),
      );
      if (input.checked) draft[step.key].push(name);
      updateCount();
    });
    const copy = element("span", "choice-copy");
    copy.append(element("span", "choice-name", name));
    if (descriptions.get(name))
      copy.append(element("span", "choice-hint", descriptions.get(name)));
    label.append(input, copy);
    grid.append(label);
  }
  group.append(grid);
  updateCount();
  return group;
}
function renderContext(draft) {
  const form = element("div", "fields");
  const stageLabel = element("label", "field", "当前阶段（选填）");
  const select = element("select");
  for (const name of ["", ...uniqueText([...stages, draft.stage])]) {
    const option = element("option", "", name || "暂不填写");
    option.value = name;
    select.append(option);
  }
  select.value = draft.stage;
  select.addEventListener("change", () => {
    draft.stage = select.value;
  });
  stageLabel.append(select);
  const cityLabel = element("label", "field", "目标城市（选填）");
  const city = element("input");
  city.type = "text";
  city.placeholder = "例如：杭州";
  city.value = draft.city;
  city.addEventListener("input", () => {
    draft.city = city.value;
  });
  cityLabel.append(city);
  form.append(stageLabel, cityLabel);
  return form;
}
function renderReview(draft, startEdit) {
  const list = element("dl", "review");
  steps.slice(0, reviewStep).forEach(({ key, label }, index) => {
    const row = element("div", "review-row");
    const value = key
      ? draft[key].join("、")
      : `阶段：${draft.stage || "未填写"}　城市：${clean(draft.city) || "未填写"}`;
    const description = element("dd", "review-value");
    description.append(
      element("span", value ? "" : "empty", value || "暂未选择"),
    );
    const edit = button("edit", "修改", () => startEdit(index));
    edit.setAttribute("aria-label", `修改${label}`);
    edit.dataset.jcpEdit = String(index);
    description.append(edit);
    row.append(element("dt", "", label), description);
    list.append(row);
  });
  const details = element("details", "method");
  details.append(
    element("summary", "", "匹配分数怎么算？"),
    element(
      "p",
      "",
      "每项选择权重相同。兴趣和工作条件核对职业条目和标签；技能核对职业资料里的技能名称或相关关键词。分数等于有依据的项数除以所选项数，再换算成百分制并四舍五入。没有可计分的选择时显示 0 分。",
    ),
    element("p", "", contextNote),
  );
  const fragment = document.createDocumentFragment();
  fragment.append(list, details);
  return fragment;
}

/** Open or focus the current assessment. See the parent contract above. */
export function openAssessment(currentProfile, onComplete) {
  if (typeof onComplete !== "function")
    throw new TypeError("openAssessment requires an onComplete callback");
  if (activeDialog?.open) {
    activeDialog.querySelector(".jcp-question")?.focus();
    return activeDialog;
  }
  const draft = copyProfile(currentProfile);
  const hasProfile =
    draft.interests.length + draft.conditions.length + draft.skills.length >
      0 || Boolean(draft.stage || draft.city);
  let index = hasProfile ? reviewStep : 0;
  let editing = false;
  const dialog = modal(
    "职业画像",
    '<div class="jcp-sheet"></div>',
    "jcp-dialog",
  );
  dialog.lang = "zh-CN";
  const shell = dialog.querySelector(".jcp-sheet");
  const header = dialog.querySelector(".dialog-head");
  header.className = "jcp-header";
  header.querySelector("h2").className = "jcp-title";
  const close = header.querySelector("[data-close]");
  close.className = "jcp-close";
  close.setAttribute("aria-label", "关闭，放弃本次修改");
  const progress = element("ol", "progress");
  progress.setAttribute("aria-label", "评估进度");
  const markers = steps.map((step) =>
    element("li", "marker", step.progressLabel || step.label),
  );
  progress.append(...markers);
  const body = element("div", "body");
  const footer = element("footer", "footer");
  shell.append(header, progress, body, footer);

  function showStep(focusEdit = null) {
    const step = steps[index];
    progress.setAttribute(
      "aria-label",
      `评估进度，第 ${index + 1} 步，共 ${steps.length} 步`,
    );
    markers.forEach((marker, i) => {
      marker.classList.toggle("jcp-done", i < index);
      if (i === index) marker.setAttribute("aria-current", "step");
      else marker.removeAttribute("aria-current");
    });
    const heading = element("h3", "question");
    heading.tabIndex = -1;
    heading.append(
      element("span", "sr", `第 ${index + 1} 步，共 ${steps.length} 步。`),
      step.title,
    );
    const hint = element("p", "hint", step.hint);
    const count = element("span", "count");
    count.setAttribute("role", "status");
    body.replaceChildren(heading, hint);
    if (step.options) body.append(renderChoices(step, draft, count));
    else if (index < reviewStep) body.append(renderContext(draft));
    else
      body.append(
        renderReview(draft, (i) => {
          index = i;
          editing = true;
          showStep();
        }),
      );

    footer.replaceChildren();
    if (index > 0 && !editing)
      footer.append(
        button("back", "上一步", () => {
          index--;
          showStep();
        }),
      );
    if (step.options) footer.append(count);
    const next = button(
      "next",
      editing ? "返回核对" : index === reviewStep ? "保存画像" : "下一步",
      () => {
        if (editing) {
          const edited = index;
          editing = false;
          index = reviewStep;
          showStep(edited);
        } else if (index === reviewStep) {
          saved = copyProfile(draft);
          dialog.close();
        } else {
          index++;
          showStep();
        }
      },
    );
    if (
      index === reviewStep &&
      !draft.interests.length &&
      !draft.conditions.length &&
      !draft.skills.length
    ) {
      next.disabled = true;
      const hint = element(
        "p",
        "hint",
        "请先选择至少一项兴趣、工作条件或技能，再保存画像查看匹配结果。",
      );
      body.append(hint);
    }
    footer.append(next);
    body.scrollTop = 0;
    if (dialog.open)
      (focusEdit === null
        ? heading
        : body.querySelector(`[data-jcp-edit="${focusEdit}"]`)
      ).focus();
  }
  function trapTab(event) {
    if (event.key !== "Tab" || event.defaultPrevented) return;
    const stops = [
      ...shell.querySelectorAll("button,input,select,summary"),
    ].filter((node) => !node.disabled && node.getClientRects().length);
    const first = stops[0],
      last = stops[stops.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
  // modal() owns native Escape, close/backdrop dismissal, removal and opener focus.
  // Its close listener runs first, so the parent can safely redraw or open another view.
  let saved = null;
  dialog.addEventListener("keydown", trapTab);
  dialog.addEventListener(
    "close",
    () => {
      dialog.removeEventListener("keydown", trapTab);
      if (activeDialog === dialog) activeDialog = null;
      if (saved) onComplete(saved);
    },
    { once: true },
  );
  activeDialog = dialog;
  showStep();
  return dialog;
}
