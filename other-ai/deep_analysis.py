#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深度分析测试结果，找出隐藏的短板"""

import json
from collections import Counter, defaultdict

with open(r"C:\Users\wupei\Desktop\测试622\test_report_20260622_092303.jsonl", "r", encoding="utf-8") as f:
    lines = [json.loads(l) for l in f if l.strip()]

valid = [r for r in lines if r["assistant_reply"] and not r["assistant_reply"].startswith("ERROR")]

print("=" * 70)
print("深度分析：KST自动回复短板")
print("=" * 70)

# 1. 回复多样性分析
print("\n--- 1. 回复多样性分析 ---")
replies = [r["assistant_reply"] for r in valid]
unique = set(replies)
print(f"  总回复: {len(replies)}, 唯一: {len(unique)} ({len(unique)/len(replies)*100:.1f}%)")

# 2. 前20字前缀分析
prefixes = Counter()
for r in valid:
    pref = r["assistant_reply"][:25]
    prefixes[pref] += 1
print("\n  高频回复前缀 Top 10:")
for pref, cnt in prefixes.most_common(10):
    print(f"    [{cnt}x] {pref}...")

# 3. 要手机号分析
print("\n--- 2. 要手机号分析 ---")
phone_phrases = ["手机号", "联系方式", "留个电话", "留电话", "加您"]
for phrase in phone_phrases:
    cnt = sum(1 for r in valid if phrase in r["assistant_reply"])
    print(f"  包含'{phrase}': {cnt}/{len(valid)} ({cnt/len(valid)*100:.1f}%)")

# 4. 按类别分析要手机号情况
print("\n--- 3. 各类别要手机号比例 ---")
cat_phone = defaultdict(lambda: {"total": 0, "phone": 0})
for r in valid:
    cat = r["category"]
    cat_phone[cat]["total"] += 1
    if any(p in r["assistant_reply"] for p in phone_phrases):
        cat_phone[cat]["phone"] += 1

for cat, stats in sorted(cat_phone.items(), key=lambda x: x[1]["phone"]/max(x[1]["total"],1), reverse=True):
    pct = stats["phone"]/max(stats["total"],1)*100
    bar = "█" * int(pct/5) + "░" * (20-int(pct/5))
    print(f"  {cat:<20} [{bar}] {pct:.0f}% ({stats['phone']}/{stats['total']})")

# 5. 分析拒绝留电话场景 - 用户说了"不方便留电话"后还要电话
print("\n--- 4. 拒绝留电话场景深度分析 ---")
refuse_replies = [r for r in valid if r["category"] == "拒绝留电话"]
for r in refuse_replies:
    has_phone = any(p in r["assistant_reply"] for p in phone_phrases)
    print(f"  访客: {r['visitor_text'][:30]:<30} | 要电话: {has_phone} | 回复: {r['assistant_reply'][:80]}")

# 6. 辱骂退订场景分析
print("\n--- 5. 辱骂退订场景深度分析 ---")
abuse_replies = [r for r in valid if r["category"] == "辱骂退订"]
for r in abuse_replies:
    has_phone = any(p in r["assistant_reply"] for p in phone_phrases)
    print(f"  访客: {r['visitor_text'][:30]:<30} | 要电话: {has_phone} | 回复: {r['assistant_reply'][:80]}")

# 7. 短句追问是否千篇一律
print("\n--- 6. 短句追问多轮回复一致性 ---")
short_replies = [r for r in valid if r["category"] == "短句追问"]
for r in short_replies:
    print(f"  [{r['visitor_text'][:20]:<20}] {r['assistant_reply'][:100]}")

# 8. 已留联系方式后是否还引导新问题
print("\n--- 7. 已留联系方式后追问分析 ---")
contact_replies = [r for r in valid if r["category"] == "已留联系方式"]
for r in contact_replies:
    print(f"  [{r['visitor_text'][:30]:<30}] {r['assistant_reply'][:100]}")

# 9. 留电后追问分析
print("\n--- 8. 留电后追问分析 ---")
post_replies = [r for r in valid if r["category"] == "留电后追问"]
for r in post_replies:
    print(f"  [{r['visitor_text'][:30]:<30}] {r['assistant_reply'][:100]}")

# 10. 非法律咨询分析
print("\n--- 9. 非法律咨询回复分析 ---")
nonlegal = [r for r in valid if r["category"] == "非法律咨询"]
for r in nonlegal:
    has_phone = any(p in r["assistant_reply"] for p in phone_phrases)
    print(f"  访客: {r['visitor_text'][:25]:<25} | 要电话: {has_phone} | {r['assistant_reply'][:80]}")

# 11. 恶意输入回复分析
print("\n--- 10. 恶意输入回复分析 ---")
malicious = [r for r in valid if r["category"] == "恶意输入"]
for r in malicious:
    print(f"  访客: {r['visitor_text'][:40]:<40} | {r['assistant_reply'][:100]}")

# 12. 情绪状态回复分析
print("\n--- 11. 情绪状态回复分析 ---")
emotional = [r for r in valid if r["category"] == "情绪状态"]
for r in emotional:
    print(f"  访客: {r['visitor_text'][:40]:<40} | {r['assistant_reply'][:100]}")

# 13. 回复长度差异
print("\n--- 12. 回复长度分析 ---")
lengths = [len(r["assistant_reply"]) for r in valid]
print(f"  平均: {sum(lengths)/len(lengths):.0f}字, 最短: {min(lengths)}字, 最长: {max(lengths)}字")
print(f"  中位数: {sorted(lengths)[len(lengths)//2]}字")

# 14. 回复中是否包含实质性建议
print("\n--- 13. 实质性建议 vs 模板化回复 ---")
substantive = sum(1 for r in valid if any(kw in r["assistant_reply"] for kw in 
    ["证据", "材料", "时效", "赔偿", "起诉", "法院", "仲裁", "合同", "认定", "流程", "程序"]))
template_only = sum(1 for r in valid if "手机号" in r["assistant_reply"] and not any(
    kw in r["assistant_reply"] for kw in ["证据", "材料", "时效", "赔偿", "起诉", "法院", "仲裁", "合同", "认定", "流程", "程序"]))
print(f"  包含实质性建议: {substantive}/{len(valid)} ({substantive/len(valid)*100:.1f}%)")
print(f"  纯模板话术(仅要电话): {template_only}/{len(valid)} ({template_only/len(valid)*100:.1f}%)")

# 15. 检查"方向偏XX"判定准确性
print("\n--- 14. 案由分类准确性抽查 ---")
case_replies = [r for r in valid if r["category"] == "案由明确"]
for r in case_replies:
    reply = r["assistant_reply"]
    text = r["visitor_text"]
    # 提取回复中的方向描述
    direction = ""
    if "方向偏" in reply:
        start = reply.index("方向偏")
        end = reply.index("。", start) if "。" in reply[start:] else start+20
        direction = reply[start:end]
    print(f"  输入: {text[:40]:<40} | 方向: {direction}")

print("\n" + "=" * 70)
print("分析完成")
print("=" * 70)