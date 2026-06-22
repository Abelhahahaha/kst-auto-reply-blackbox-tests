import json
from collections import Counter, defaultdict

path = r"C:/Users/wupei/Desktop/测试622/blackbox_test_round2_results.jsonl"
rows = [json.loads(l) for l in open(path, encoding="utf-8")]
issues = [r for r in rows if r["verdict"] != "ok"]
by_p = defaultdict(list)
for r in issues:
    by_p[r["persona"]].append(r)
print("=== 问题最多的 persona ===")
for name, items in sorted(by_p.items(), key=lambda x: -len(x[1]))[:15]:
    print(f"{len(items)} | {items[0]['category']} | {name}")
cat_total = Counter()
cat_rep = Counter()
cat_all_issues = Counter()
for r in rows:
    cat_total[r["category"]] += 1
    if r["verdict"] == "repetitive":
        cat_rep[r["category"]] += 1
    if r["verdict"] != "ok":
        cat_all_issues[r["category"]] += 1
print("\n=== 各类别 repetitive 率 ===")
for c in sorted(cat_total):
    t = cat_total[c]
    rep = cat_rep[c]
    print(f"{c}: {rep}/{t} = {rep/t*100:.0f}%  总问题={cat_all_issues[c]}")
print("\n=== 各类别首轮 ok 样例 ===")
seen = set()
for r in rows:
    if r["turn_index"] == 1 and r["verdict"] == "ok" and r["category"] not in seen:
        seen.add(r["category"])
        print(f"[{r['category']}] {r['persona']}")
        print(f"  访客: {r['visitor_text'][:50]}")
        print(f"  回复: {r['assistant_reply'][:80]}")
