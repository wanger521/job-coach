// Dates and times in recruitment notices use the mainland China calendar.
const beijingClock = new Intl.DateTimeFormat('sv-SE', {
  timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});
const day = /^\d{4}-\d{2}-\d{2}$/;
const minute = /^(?:[01]\d|2[0-3]):[0-5]\d$/;
export const statusOptions = [
  { id: 'open', label: '报名中' }, { id: 'upcoming', label: '即将报名' },
  { id: 'pending', label: '待核实' }, { id: 'closed', label: '已截止' },
];
const pending = label => ({ id: 'pending', label });

export function applicationStatus(item, watched, now = new Date()) {
  const stamp = beijingClock.format(now);
  const today = stamp.slice(0, 10);
  const isNotice = item.recordType === 'notice';
  const verified = isNotice ? item.windowVerified === true : item.windowVerified !== false;
  const end = day.test(item.deadline) ? item.deadline : '';
  const start = day.test(item.applicationStart) ? item.applicationStart : '';
  const boundKnown = !isNotice || typeof item.windowVerified === 'boolean';
  if ((item.closed && boundKnown) || (watched?.applicationStatus === 'closed' && !watched.availability) || (boundKnown && end && (end < today ||
      (end === today && minute.test(item.deadlineTime) && stamp >= end + ' ' + item.deadlineTime)))) {
    return { id: 'closed', label: '已截止' };
  }
  const availability = watched?.availability || item.availability;
  if (availability === 'unavailable') return pending('原文已失效');
  if (availability === 'changed') return pending('原文已变更');
  if (availability) return pending('原文需复核');
  if (watched?.windowVerified && (watched.deadline !== end ||
      (start && watched.applicationStart && watched.applicationStart !== start) ||
      (item.deadlineTime && watched.deadlineTime && watched.deadlineTime !== item.deadlineTime))) return pending('报名期有变，需复核');
  if (start && end && start > end) return pending('报名期限待核实');
  if (item.published && item.published > today) return pending('公告日期待核实');
  // A successful HTTP read alone cannot renew an old manual verification.
  const checked = watched?.windowVerified && watched.checked > item.checked ? watched.checked : item.checked;
  const ageDays = (Date.parse(today) - Date.parse(checked)) / 86400000;
  if (!(ageDays >= 0 && ageDays <= 7)) return pending('报名信息待复核');
  if (boundKnown && start && (start > today || (start === today && minute.test(item.applicationStartTime) && stamp < start + ' ' + item.applicationStartTime))) {
    return { id: 'upcoming', label: '即将报名' };
  }
  if (item.conditionalVacancy || watched?.conditionalVacancy || /(?:招满|额满|聘满)(?:即止|为止)|录满为止/.test(item.requirement || '')) return pending('招满即止，余缺待核实');
  if (!end || !verified) return pending('报名期限待核实');
  if (end === today && !minute.test(item.deadlineTime)) return pending('今日截止，时刻待核实');
  if (!start && item.windowVerified !== true) return pending('报名开始时间待核实');
  return { id: 'open', label: '公告报名中' };
}
