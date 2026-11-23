import assert from 'node:assert/strict';
import test from 'node:test';
import { applicationStatus } from '../data/application-status.mjs';
import { belongsToSeason, jobsPage, jobsUrl } from '../assets/features/explore.mjs';
import { stagesFor } from '../data/teaching-stages.mjs';

const job = { applicationStart: '2026-11-20', deadline: '2026-11-23', deadlineTime: '16:00', checked: '2026-11-23' };
const before = new Date('2026-11-23T15:59:00+08:00');
test('a Beijing closing minute and conditional vacancy are not interchangeable', () => {
  assert.equal(applicationStatus(job, null, before).id, 'open');
  assert.equal(applicationStatus(job, null, new Date('2026-11-23T08:00:00Z')).id, 'closed');
  assert.equal(applicationStatus({ ...job, conditionalVacancy:true }, null, before).id, 'pending');
  assert.equal(applicationStatus({ ...job, deadlineTime:'' }, null, before).id, 'pending');
  assert.equal(applicationStatus({ ...job, applicationStart:'2026-11-23', applicationStartTime:'16:00' }, null, before).id, 'upcoming');
  assert.equal(applicationStatus(job, { availability:'changed' }, before).id, 'pending');
  assert.equal(applicationStatus({ ...job, recordType:'notice' }, null, before).id, 'pending');
  assert.equal(applicationStatus({ ...job, recordType:'notice', windowVerified:true }, null, before).id, 'open');
});
test('annual view uses the stated batch, not the deadline or an applicant requirement', () => {
  assert.equal(belongsToSeason({title:'南京市2027年公开招聘教师公告'}, 2027), true);
  assert.equal(belongsToSeason({title:'2027届校园招聘教师公告'}, 2027), true);
  assert.equal(belongsToSeason({title:'2026年教师招聘公告（截至2027年1月）', deadline:'2027-01-27'}, 2027), false);
  assert.equal(belongsToSeason({title:'教师招聘（2027年毕业）'}, 2027), false);
});
test('stage filtering keeps repost sources and degree requirements out of the school stage', () => {
  const notice = {recordType:'notice', employer:'某大学就业网', roleIds:['computing-teacher'], title:'某中学计算机教师招聘', requirement:'须大学本科以上'};
  assert.deepEqual(stagesFor(notice), ['unknown']);
  assert.deepEqual(stagesFor({...notice, title:'小学数学、初中信息技术教师'}), ['junior']);
  assert.deepEqual(stagesFor({...notice, title:'初中、高中信息技术教师'}), ['junior','senior']);
});
test('the January Jiangning post is accessible as junior-school history and stays out of current applications', () => {
  const page = (status, stage, season) => {
    globalThis.location = {hash: jobsUrl(['computing-teacher'], '南京', status, stage, season)};
    return jobsPage().split('id="job-results"')[1];
  };
  assert.doesNotMatch(page('open','junior'), /南京市东山初级中学/);
  assert.match(page('closed','junior'), /南京市东山初级中学/);
  assert.match(page('open','junior','2027'), /往年岗位参考[\s\S]*南京市东山初级中学/);
  assert.doesNotMatch(page('open','primary','2027'), /南京市东山初级中学/);
});
