import { teacherSeeds } from "./nanjing-teacher-seeds.mjs";
import { interestJobs } from "./interest-jobs.mjs";

const regionalJobs = [
  {
    "id": "bj-kitchen-producer",
    "title": "美食制作人（食品内容方向）",
    "employer": "下厨房",
    "city": "北京",
    "roleIds": [
      "food-content",
      "short-video-editor"
    ],
    "requirement": "制作美食教程或菜谱，撰写脚本，并配合剪辑、平面设计做成品。应聘者须有讲菜谱或处理美食图文、视频的经验，优先考虑能提供既往作品者。",
    "url": "https://www.xiachufang.com/job/",
    "published": "",
    "deadline": "",
    "closed": false,
    "checked": "2026-11-23"
  },
  {
    "id": "sh-fudan-learning",
    "title": "EE学习创新发展中心 在线课程开发专员",
    "employer": "复旦大学管理学院",
    "city": "上海",
    "roleIds": [
      "instructional-designer"
    ],
    "requirement": "教育技术学等相关专业本科及以上，要求两年以上相关经验。需和教师共同完成教学设计、脚本及素材，并根据学习反馈修改课程。",
    "url": "https://www.fdsm.fudan.edu.cn/aboutus/zp1393509194906.m",
    "published": "",
    "deadline": "",
    "closed": false,
    "checked": "2026-11-23"
  },
  {
    "id": "cd-ysl-qunguang",
    "title": "美容顾问（成都群光 YSL）",
    "employer": "欧莱雅",
    "city": "成都",
    "roleIds": [
      "beauty-advisor"
    ],
    "requirement": "成都群光门店全职。需了解护肤、彩妆和香水，能沟通需求并演示产品，也要完成销售目标、盘点和维护客情。",
    "url": "https://careers.loreal.com/en/job/chengdu/%E7%BE%8E%E5%AE%B9%E9%A1%BE%E9%97%AE-%E6%88%90%E9%83%BD%E7%BE%A4%E5%85%89-ysl/3456/46381785408",
    "published": "2026-10-27",
    "deadline": "",
    "closed": false,
    "checked": "2026-11-23"
  },
  {
    "id": "sh-tongji-media",
    "title": "继续教育学院新媒体运营岗",
    "employer": "同济大学继续教育学院",
    "city": "上海",
    "roleIds": [
      "short-video-editor"
    ],
    "requirement": "沪北校区，派遣岗。本科及以上，需 5 年以上行业经验，其中至少 2 年担任视频项目负责人。申请须交作品清单，说明本人职责。",
    "url": "https://rczx.tongji.edu.cn/info/1004/1792.htm",
    "published": "2026-11-20",
    "deadline": "2026-12-04",
    "closed": false,
    "checked": "2026-11-23"
  },
  {
    "id": "cd-tianfu-campus-media",
    "title": "招生办公室工作人员（视频制作）",
    "employer": "西南财经大学天府学院",
    "city": "成都",
    "roleIds": [
      "short-video-editor"
    ],
    "requirement": "成都校区，要求硕士及以上学历。需独立策划、拍摄和剪辑招生视频，并跟踪抖音及视频号的传播效果。",
    "url": "https://www.tfswufe.edu.cn/info/1361/154971.htm",
    "published": "2026-05-11",
    "deadline": "2026-07-10",
    "closed": true,
    "checked": "2026-11-23"
  },
  {
    "id": "nj-course-video-engineer",
    "title": "课程视频制作工程师",
    "employer": "南京航空航天大学信息化处",
    "city": "南京",
    "roleIds": [
      "learning-media"
    ],
    "requirement": "南京校区，劳务派遣。本科及以上，公告列影视摄影、数字媒体等相关专业。需能与教师对接脚本，完成拍摄、剪辑与动效。",
    "url": "https://xxhc.nuaa.edu.cn/_t2236/2026/1012/c17976a414623/page.htm",
    "published": "2026-10-13",
    "deadline": "2026-10-30",
    "closed": true,
    "checked": "2026-11-23"
  },
  {
    "id": "nj-jiangning-politics",
    "title": "高中政治教师",
    "schoolStage": "高中",
    "employer": "南京师范大学附属中学江宁分校",
    "city": "南京",
    "roleIds": [
      "secondary-school-teacher"
    ],
    "requirement": "岗位表列 1 个名额。所学专业、教师资格证学科与任教学科须一致，另有学历或教学经验条件。",
    "url": "https://career.ahnu.edu.cn/info/1008/33942.htm",
    "published": "2026-06-06",
    "deadline": "",
    "closed": false,
    "checked": "2026-11-23"
  },
  {
    "id": "cd-hospital-finance",
    "title": "财务部会计核算岗",
    "employer": "成都大学附属医院",
    "city": "成都",
    "roleIds": [
      "accountant"
    ],
    "requirement": "负责会计核算，要求会计学或财务管理专业、硕士研究生学历及硕士学位。",
    "url": "https://cdfy120.cdu.edu.cn/info/1174/13350.htm",
    "published": "2025-10-30",
    "deadline": "2025-11-06",
    "closed": true,
    "checked": "2026-11-23"
  },
  {
    "id": "cd-hospital-pharmacy",
    "title": "西药剂科调剂岗",
    "employer": "成都大学附属医院",
    "city": "成都",
    "roleIds": [
      "pharmacist"
    ],
    "requirement": "负责药品调剂和处方审核，要求药学相关专业本科及以上学历学位、药师及以上职称。",
    "url": "https://cdfy120.cdu.edu.cn/info/1174/13350.htm",
    "published": "2025-10-30",
    "deadline": "2025-11-06",
    "closed": true,
    "checked": "2026-11-23"
  },
  {
    "id": "gz-k11-ysl",
    "title": "美容顾问（广州 K11 · YSL）",
    "employer": "欧莱雅",
    "city": "广州",
    "roleIds": [
      "beauty-advisor"
    ],
    "requirement": "全职零售岗。工作包括产品试用讲解、销售、客户跟进和柜台盘点，需要熟悉门店数字工具，能与同事及商场配合。",
    "url": "https://careers.loreal.com/en/job/guangzhou/%E7%BE%8E%E5%AE%B9%E9%A1%BE%E9%97%AE-%E5%B9%BF%E5%B7%9Ek11-ysl/3456/44928077888",
    "published": "2026-10-23",
    "deadline": "",
    "closed": false,
    "checked": "2026-11-23"
  },
  {
    "id": "sz-maoye-lancome",
    "title": "美容顾问（深圳南山茂业 · 兰蔻）",
    "employer": "欧莱雅",
    "city": "深圳",
    "roleIds": [
      "beauty-advisor"
    ],
    "requirement": "全职门店岗。按顾客需求提供产品建议，维护客户关系，承担销售目标，并学习护肤、化妆和香水知识。",
    "url": "https://careers.loreal.com/en/job/shenzhen/%E7%BE%8E%E5%AE%B9%E9%A1%BE%E9%97%AE-%E6%B7%B1%E5%9C%B3%E5%8D%97%E5%B1%B1%E8%8C%82%E4%B8%9A-%E5%85%B0%E8%94%BB/3456/43562174464",
    "published": "2026-09-30",
    "deadline": "",
    "closed": false,
    "checked": "2026-11-23"
  }
];

export const jobPostings = [...teacherSeeds, ...interestJobs, ...regionalJobs];
