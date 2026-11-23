"""Refresh the occupation directory from the public OSTA classification system.

Run `python tools/import_occupation_index.py` with Python 3.10+ and requests.
The checks use the same category totals displayed in the portal navigation.
"""

from collections import Counter
from datetime import date
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

import requests


PORTAL = "https://www.osta.org.cn/career"
API = "https://www.osta.org.cn/api/client/"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "occupation-index.mjs"
OCCUPATION_CODE = re.compile(r"[1-8](?:-[0-9]{2}){3}")
# The classification puts L (green) and S (digital) markers after the name.
MARKER = re.compile(r"\s*(?:L/S|L|S)$")


def fetch(session, endpoint, **params):
    response = session.get(API + endpoint, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 200 or not isinstance(data.get("body"), list):
        raise ValueError(f"Unexpected response from {endpoint}")
    return data["body"]


def collect(session):
    tree = fetch(session, "get/tree")
    groups = {g["careerCode"]: g["careerName"] for g in tree}
    if set(groups) != set("12345678") or len(tree) != len(groups):
        raise ValueError("Review the major categories before refreshing")

    small_versions = {}
    expected = {}
    for major in tree:
        key = major["careerCode"]
        children = fetch(session, "subordinate/data", careerCode=key, versionId=major["versionId"])
        middle_codes = {m["careerCode"] for m in major["children"]}
        if middle_codes != {c["careerCode"] for c in children} or len(children) != len(middle_codes):
            raise ValueError(f"Category listings disagree for {key}")
        for child in children:
            expected[child["careerCode"]] = child["careerNum"]
        for middle in major["children"]:
            for small in middle["children"]:
                small_versions[small["careerCode"]] = small["versionId"]

    names = {}
    # The portal searches substrings. Every full occupation code contains a hyphen.
    for row in fetch(session, "career/query", careerCodeAndName="-"):
        code = row["careerCode"]
        if not OCCUPATION_CODE.fullmatch(code) or small_versions.get(code.rsplit("-", 1)[0]) != row["versionId"]:
            raise ValueError(f"Invalid or unclassified occupation code {code!r}")
        name = MARKER.sub("", row["name"].strip())
        if not name or "\ufffd" in name or not name.isprintable():
            raise ValueError(f"Unreadable occupation name for {code}")
        if names.setdefault(code, name) != name:
            raise ValueError(f"Conflicting occupation names for {code}")

    counts = Counter(code[:4] for code in names)
    if counts != Counter(expected):
        raise ValueError("Unique occupation counts disagree with the portal's middle-category totals")
    return groups, names, len(expected)


def render(groups, names, middle_count):
    source = {
        "label": "技能人才评价工作网 · 职业分类系统",
        "url": PORTAL,
        "region": "中国内地",
        "date": date.today().isoformat(),
        "note": (
            f"在线目录核对快照，共 {len(names)} 个职业细类，覆盖 {len(groups)} 个大类、{middle_count} 个中类。"
            "保留官方职业编码，按所属大类分组。名称已去除绿色（L）和数字（S）标记。"
            "收录范围随平台更新，工种和职业描述不在本索引内。"
        ),
    }
    lines = [
        "// Generated from the official portal by tools/import_occupation_index.py.",
        "// indexSource.date is the retrieval date of this online snapshot.",
        "export const indexSource = " + json.dumps(source, ensure_ascii=False, indent=2) + ";",
        "",
        "const majorGroups = " + json.dumps(groups, ensure_ascii=False, indent=2, sort_keys=True) + ";",
        "",
        "export const occupationIndex = [",
    ]
    for code, name in sorted(names.items()):
        lines.append("  " + json.dumps([code, name], ensure_ascii=False) + ",")
    lines.append("].map(([code, name]) => ({ code, name, group: majorGroups[code[0]] }));")
    return "\n".join(lines) + "\n"


def main():
    with requests.Session() as session:
        groups, names, middle_count = collect(session)
    contents = render(groups, names, middle_count)
    with NamedTemporaryFile(dir=OUTPUT.parent, mode="w", encoding="utf-8", newline="\n", delete=False) as tmp:
        tmp.write(contents)
    Path(tmp.name).replace(OUTPUT)
    print(f"Verified {len(names)} occupations across {middle_count} categories and {len(groups)} major groups.")


if __name__ == "__main__":
    main()
