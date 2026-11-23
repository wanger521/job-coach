// UI order also gives multi-stage results a stable order independent of the notice wording.
export const stageOptions = Object.freeze([
  { id: 'preschool', label: '幼儿园／学前' },
  { id: 'primary', label: '小学' },
  { id: 'junior', label: '初中' },
  { id: 'senior', label: '高中' },
  { id: 'secondary-vocational', label: '中职' },
  { id: 'vocational', label: '职校（高职校）' },
  { id: 'university', label: '大学（含高职专科、职业本科）' },
  { id: 'unknown', label: '学段未明确' },
].map(Object.freeze));

const labels = new Map(stageOptions.map(({ id, label }) => [id, label]));
const markers = [
  ['unknown', /中小学校?|中学|附中/],
  ['preschool', /幼儿园|幼儿教师|幼教|幼师|学前/],
  ['primary', /小学|附小/],
  ['junior', /初级中学|初中/],
  ['senior', /高级中学|高中|普高|A[- ]?LEVEL|IBDP/i],
  ['secondary-vocational', /中等职业(?:技术)?学校|中等专业学校|中职|中专|技工学校|职业高(?:级中学|中)|职业中学|职业中专|职高/],
  ['vocational', /高等职业(?:技术)?学校|高职校/],
  ['university', /高职(?:专科|院校)|(?:高等)?职业(?:技术)?学院|高等专科学校|专科院校|职业(?:技术)?大学|职业本科|大学|高校|高等院校|本科院校|高等学校/],
];
const markerPattern = new RegExp(markers.map(([, pattern]) => `(${pattern.source})`).join('|'), 'gi');
const teachingRole = /(?:^|-)teacher$/;
const teachingTitle = /教师(?!资格|证|发展|培训|公寓|宿舍|教育学院|助理|管理平台)|老师|幼师(?!范)|讲师|教授(?!助理|课题组)|师资招聘|招聘师资|师资引进|教学(?:科研)?岗|准聘长聘岗/;
const computingSubject = /信息(?:科[技学]|技术|学|(?=教师|老师|学科|岗|课|$))|计算机|软件|人工智能|智能体|网络技术|编程/;
const otherSubject = /语文|数学|英语|物理|化学|生物|地理|历史|政治|体育|音乐|美术|道德与法治/;
const nonTeaching = /辅导员|宿管|(?:生活|常规管理|内勤|宿舍管理)老师|研发教师|教师发展中心|教师培训|教师资格证|教师助理|教授助理|教学管理|教学秘书|校医|电教员/;
const stageListSeparator = /^[\s、,，/和及与部学段()]*$/;
const qualification = /(?:任职|应聘|岗位|专业|学历)要求|报考条件|工作职责|资格条件|协助|配合|服务于|须取得|具有.{0,10}学历|任职资格|须(?:持|有|具备)|要求(?:持有|具备)|持有|优先考虑/;

function clean(value) {
  return typeof value === 'string' ? value.normalize('NFKC').trim() : '';
}

function assignmentText(text) {
  // Education majors describe the course or qualification, even when the employer is a university.
  return text.replace(/(?:学前教育|小学教育|幼儿教育)(?:专业|专任|学院|课程|系|学科)|幼(?:儿)?师范/g, '')
    .replace(/^(?:【|\[)(?:转发|转载|代发)[】\]]/, '').split(/转发|转载|代发/).at(-1).split(qualification)[0]
    .replace(/【[^】]*(?:就业|招聘网|宣讲)[^】]*】|[^，,：:；;|\s]*(?:就业网|就业指导中心|就业服务网|就业信息网)/g, '')
    .replace(/[(【][^(【)】]*(?:毕业|学历|资格证|经历|经验|优先|宣讲|大学站)[^(【)】]*[)】]/g, '')
    .replace(/^(?:【[^】]*大学[^】]*】|\[[^\]]*大学[^\]]*\])/, '')
    .replace(/(?:高职专科|职业本科)(?=及以上|学历|毕业|学位)/g, '')
    .replace(/(?:大学|高校)(?:全日制)?(?:本科|专科|(?:应届)?毕业生?|应届生|学历|生|任教经历|教学经验)|本科及以上/g, '')
    .replace(/初[、/和及与]?高中/g, '初中、高中');
}

// Keep each stage with its own subject(s). In “小学数学、初中信息技术教师”
// only the second stage supports a computing vacancy. Bare stage lists share a subject.
function assignmentStages(text, subject) {
  const hits = new Set();
  const subjectNames = text.match(new RegExp(`${otherSubject.source}|${computingSubject.source}`, 'g')) || [];
  const conflictingSubject = subject && subjectNames.some(name => !subject.test(name));
  for (const part of text.split(/(?:[;；。\n]|(?<=教师|老师|教学岗)[、,，和及与/])/)) {
    const matches = [...part.matchAll(markerPattern)];
    let pending = [];
    for (const [index, match] of matches.entries()) {
      const [token] = match;
      const [id] = markers[match.slice(1).findIndex(Boolean)];
      const rest = part.slice(match.index + token.length, matches[index + 1]?.index);
      // An affiliated school's parent university and a notice's campus venue can appear in the title.
      if (id === 'university' && /附属|附设|附校|就业|宣讲|专场|招聘会|工作经历|资格证/.test(part.slice(match.index + token.length))) continue;
      if (id === 'university' && index + 1 < matches.length && !stageListSeparator.test(rest) && !teachingTitle.test(rest)) continue;
      pending.push(id);
      if (stageListSeparator.test(rest) && index + 1 < matches.length) continue;
      if (!conflictingSubject || subject.test(rest)) {
        for (const stage of pending) hits.add(stage);
      }
      pending = [];
    }
  }
  return stageOptions.map(({ id }) => id).filter(id => hits.has(id));
}

// The feed stores the publishing institution in employer. Read only a named vacancy
// from its excerpt, which can also contain a school introduction or degree requirements.
function vacancyText(requirement) {
  const intro = /(?:招聘岗位|招聘学科|岗位名称|任教学段|岗位)\s*[:：]|(?:诚聘|招聘)\s*(?=(?:幼儿园|学前|幼师|小学|初中|高中|中小学|中职|高职|计算机|信息))|教师招聘岗位/;
  const start = intro.exec(requirement);
  if (!start) return '';
  const excerpt = requirement.slice(start.index + start[0].length).split(/[。；;\n]/)[0];
  // Flattened vacancy tables can begin with 学部 岗位 岗位要求 before the first data cell.
  return assignmentText(excerpt.replace(/^\s*学部\s*岗位\s*岗位要求/, '')).trim();
}

export function stagesFor(item) {
  if (!item || typeof item !== 'object') return [];
  const roles = Array.isArray(item.roleIds) ? item.roleIds : [];
  const taggedTeacher = roles.some(id => typeof id === 'string' && teachingRole.test(id));
  const title = assignmentText(clean(item.title));
  const vacancy = vacancyText(clean(item.requirement));
  if (!taggedTeacher && nonTeaching.test(title)) return [];
  const directVacancy = teachingTitle.test(vacancy) || (/(?:小学|初中|高中)部/.test(vacancy) && (otherSubject.test(vacancy) || computingSubject.test(vacancy)));
  if (!taggedTeacher && !teachingTitle.test(title) && !directVacancy) return [];

  const reviewed = clean(item.schoolStage);
  // Older reviewed rows use the broad label 职业学校. Resolve it from the actual school or post.
  if (reviewed && !/^(?:职业(?:技术)?学校|职校|高职)$/.test(reviewed)) {
    if (labels.has(reviewed)) return [reviewed];
    const ids = assignmentStages(reviewed, false);
    return ids.length ? ids : ['unknown'];
  }

  const computingOnly = roles.includes('computing-teacher') || (computingSubject.test(title) && !otherSubject.test(title));
  const fromTitle = assignmentStages(title, computingOnly && computingSubject);
  const specific = fromTitle.filter(id => id !== 'unknown');
  if (specific.length) return specific;
  const namedSubject = title.match(otherSubject)?.[0];
  const subject = computingOnly ? computingSubject : namedSubject && new RegExp(namedSubject);
  const fromVacancy = assignmentStages(vacancy, subject).filter(id => id !== 'unknown');
  if (fromVacancy.length) return fromVacancy;

  // A reviewed employer can establish a single school type. A feed publisher cannot.
  const isReview = !item.sourceId && !item.sourceName && item.recordType !== 'notice';
  if (isReview && !fromTitle.length && !(computingOnly && otherSubject.test(title))) {
    const employerStages = assignmentStages(assignmentText(clean(item.employer)), false);
    if (employerStages.length === 1) return employerStages;
  }
  return roles.includes('kindergarten-teacher') ? ['preschool'] : ['unknown'];
}

export function stageLabel(item) {
  return stagesFor(item).map(id => labels.get(id)).join('、');
}
