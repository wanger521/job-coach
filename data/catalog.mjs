import { careers as coreCareers } from "./careers.mjs";
import { sources as coreSources } from "./sources.mjs";
import * as beijing from "./beijing.mjs";
import * as shanghai from "./shanghai.mjs";
import * as guangzhou from "./guangzhou.mjs";
import * as shenzhen from "./shenzhen.mjs";
import { sources as regionalEvidence } from "./regional-evidence.mjs";
import { careers as interestCareers } from "./interest-careers.mjs";
import { careers as additionalCareers } from "./additional-fields.mjs";
import { computingTeacher } from "./computing-teacher.mjs";
import { jobPostings } from "./job-board.mjs";
import { indexSource } from "./occupation-index.mjs";

export const cities = ["北京", "上海", "广州", "深圳", "南京", "成都"];
export const cityKeys = {
  beijing: "北京",
  shanghai: "上海",
  guangzhou: "广州",
  shenzhen: "深圳",
  nanjing: "南京",
  chengdu: "成都",
};
const localCatalogs = [beijing, shanghai, guangzhou, shenzhen];
const profiles = [
  ...coreCareers,
  ...localCatalogs.flatMap((catalog) => catalog.careers || []),
  ...interestCareers,
  computingTeacher,
  ...additionalCareers,
];
const originalSources = [
  ...localCatalogs.flatMap((catalog) => catalog.sources),
  ...regionalEvidence,
];
const roleAlias = {
  护士: "nurse",
  药师: "pharmacist",
  电气工程师: "electrical-engineer",
  质量工程师: "quality-engineer",
  产品经理: "product-manager",
};
// A notice may advertise several positions. Register its source once and retain every role.
const jobSources = new Map();
for (const job of jobPostings) {
  const entry = jobSources.get(job.url) || {
    url: job.url, label: job.employer + " · 招聘公告", kind: "岗位样本",
    city: job.city, region: "中国内地 · " + job.city,
    date: job.published || (job.checked + " 核对"), roles: [], note: "",
  };
  entry.roles.push(...job.roleIds);
  entry.note += (entry.note ? " " : "") + job.title + "：" + job.requirement;
  jobSources.set(job.url, entry);
}
const registered = new Map();
function register(source) {
  const previous = registered.get(source.url);
  const roles = new Set([...(previous?.roles || []), ...(source.roles || [])]);
  for (const name of source.roleNames || []) {
    const profile = profiles.find(
      (c) => c.name === name || c.id === roleAlias[name],
    );
    if (profile) roles.add(profile.id);
  }
  registered.set(source.url, { ...previous, ...source, roles: [...roles] });
}
for (const source of [
  ...jobSources.values(),
  ...coreSources,
  ...profiles.flatMap((c) => c.evidence),
  indexSource,
  ...originalSources,
])
  register(source);
export const sources = [...registered.values()];
export const careers = profiles.map((c) => {
  const evidence = new Map(
    c.evidence.map((s) => [s.url, { ...registered.get(s.url), ...s }]),
  );
  for (const s of sources)
    if (s.roles.includes(c.id) && !evidence.has(s.url)) evidence.set(s.url, s);
  return { ...c, evidence: [...evidence.values()] };
});
export const groups = [...new Set(careers.map((c) => c.category))];
export function localRoleEvidence(c, city = "") {
  return c.evidence.filter(
    (s) =>
      cities.includes(s.city) &&
      s.kind !== "调研入口" &&
      (!city || s.city === city) &&
      (s.roles.includes(c.id) || s.roleNames?.includes(c.name)),
  );
}
const fields = {
  农业与食品: "environment",
  旅游与会展: "hospitality",
  体育与健身: "people",
  风格与创作: "culture",
  技术与数据: "software",
  设计与创意: "culture",
  健康与服务: "medicine",
  商业与运营: "trade",
  工程与制造: "engineering",
  财务与审计: "finance",
  法律与合规: "law",
  教育与研究: "education",
  公共与文化: "culture",
  医疗与护理: "medicine",
  生物医药: "medicine",
  产品与运营: "software",
  电商与贸易: "trade",
  交通与物流: "trade",
  餐饮与酒店: "hospitality",
  技能与维修: "maintenance",
  环境与能源: "environment",
  养老与社区: "people",
  人力与行政: "people",
};
const originalPlates = new Map(
  coreCareers.map((c, index) => [c.id, `role-${index}`]),
);
export function careerPlate(c) {
  return `./assets/${originalPlates.get(c.id) || "field-" + (fields[c.category] || "education")}.webp`;
}
