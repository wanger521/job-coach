import assert from 'node:assert/strict';
import {access} from 'node:fs/promises';
import {careers,sources,cities,groups,careerPlate,localRoleEvidence} from '../data/catalog.mjs';
import {occupationIndex} from '../data/occupation-index.mjs';
import {matchCareer} from '../profile.mjs';
import {jobPostings} from '../data/job-board.mjs';
const ids=new Set(careers.map(c=>c.id));
assert.equal(ids.size,careers.length,'duplicate career id');
assert.equal(new Set(sources.map(s=>s.url)).size,sources.length,'duplicate source URL');
assert.equal(new Set(occupationIndex.map(item=>item.code)).size,occupationIndex.length,'duplicate occupation code');
for(const c of careers){
  for(const key of ['id','name','english','category','summary','load','intensity','geography','market','ai']) assert.equal(typeof c[key],'string',c.id+' '+key);
  for(const key of ['day','pros','cons','steps','interests','conditions','evidence']) assert(c[key]?.length,c.id+' '+key);
  assert.equal(c.scenario.options.length,3,c.id+' scenario');
  assert(matchCareer(c,{interests:c.interests,conditions:c.conditions}).score===100,c.id+' matching');
  await access(new URL('../'+careerPlate(c),import.meta.url));
}
for(const s of sources){
  assert(s.date && s.region && s.note && s.label && /^https?:\/\//.test(s.url),s.label);
  for(const id of s.roles) assert(ids.has(id),'unmapped source id '+id+' in '+s.label);
}
console.log(careers.length+' profiles, '+groups.length+' fields, '+sources.length+' research sources, '+occupationIndex.length+' index entries');
console.table(cities.map(city=>({city,sources:sources.filter(s=>s.city===city).length,careers:careers.filter(c=>localRoleEvidence(c,city).length).length})));

assert.equal(new Set(jobPostings.map(job => job.id)).size,jobPostings.length,'duplicate job id');
for (const job of jobPostings) {
  assert(cities.includes(job.city) && job.roleIds.length && job.roleIds.every(id=>ids.has(id)), 'unmapped job ' + job.id);
  for (const key of ['title','employer','requirement','checked']) assert(job[key], job.id + ' ' + key);
  for (const date of [job.checked,job.published,job.deadline].filter(Boolean)) assert(/^\d{4}-\d{2}-\d{2}$/.test(date), job.id + ' invalid date ' + date);
  assert(sources.some(s=>s.url===job.url),'unregistered job source ' + job.id);
}
console.log(jobPostings.length+' verified job records');
