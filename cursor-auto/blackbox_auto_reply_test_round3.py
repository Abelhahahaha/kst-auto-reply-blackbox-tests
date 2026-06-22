# -*- coding: utf-8 -*-
"""Round 3 全方向黑盒测试：夜间/回访/并发/LLM对比/API健壮性/深度场景"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

import requests

BASE_NO_LLM = "http://127.0.0.1:8765"
BASE_LLM = "http://127.0.0.1:8766"
TIMEOUT = 45
OUT = "C:/Users/wupei/Desktop/测试622/blackbox_test_round3_results.jsonl"
OUT_SUMMARY = "C:/Users/wupei/Desktop/测试622/blackbox_test_round3_summary.json"


@dataclass
class TurnResult:
    suite: str
    category: str
    persona: str
    session_id: str
    turn_id: str
    turn_index: int
    visitor_text: str
    assistant_reply: str
    verdict: str
    reason: str
    expected_behavior: str
    extra: dict = field(default_factory=dict)


def sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip(), b.strip()).ratio()


def post(base: str, path: str, body: dict) -> tuple[int, dict | str]:
    try:
        r = requests.post(f"{base}{path}", json=body, timeout=TIMEOUT)
        try:
            data = r.json()
        except Exception:
            data = r.text
        return r.status_code, data
    except Exception as e:
        return 0, str(e)


def get(base: str, path: str) -> tuple[int, dict | str]:
    try:
        r = requests.get(f"{base}{path}", timeout=TIMEOUT)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text
    except Exception as e:
        return 0, str(e)


def chat(base: str, session_id: str, message: str, visitor_id: str = "") -> dict:
    body = {"session_id": session_id, "message": message, "source": "round3-blackbox"}
    if visitor_id:
        body["visitor_id"] = visitor_id
    code, data = post(base, "/api/v1/chat", body)
    if code != 200 or not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError(f"chat failed {code}: {data}")
    return data


def new_session(base: str, visitor_id: str, tags: list[str]) -> dict:
    code, data = post(
        base,
        "/api/v1/sessions",
        {"visitor_id": visitor_id, "source": "round3-blackbox", "tags": tags},
    )
    if code != 200 or not isinstance(data, dict):
        raise RuntimeError(f"session failed {code}: {data}")
    return data


def evaluate_generic(
    suite: str,
    category: str,
    persona: str,
    turn_idx: int,
    visitor: str,
    reply: str,
    prev: list[str],
    rules: dict | None = None,
) -> tuple[str, str, str]:
    rules = rules or {}
    exp = rules.get("expected", "应有针对性回复")
    v, r = visitor.strip(), reply.strip()
    if not r:
        return "mismatch", "回复为空", exp
    for p in prev:
        if sim(p, r) >= 0.82:
            return "repetitive", f"与上轮高度相似({sim(p,r):.0%})", "多轮应差异化"

    must_have = rules.get("must_have", [])
    if must_have and not any(x in r for x in must_have):
        return "mismatch", f"缺少期望关键词: {must_have}", exp

    must_not = rules.get("must_not", [])
    if must_not and any(x in r for x in must_not):
        return "unsafe", f"出现不应有表述: {must_not}", exp

    if rules.get("no_phone_ask") and re.search(r"手机|电话|联系方式|留个.*号", r):
        return "missed_contact", "不应再催留资", exp

    if rules.get("should_ask_phone") and not re.search(r"手机|电话|联系方式|微信", r):
        return "missed_contact", "应引导留资", exp

    if rules.get("no_repetitive_template") and "重点要补充时间、金额、材料和目前处理进展" in r and turn_idx >= 2:
        return "repetitive", "追问仍套通用材料模板", exp

    return "ok", "未发现明显问题", exp


# ── Suite 1: 夜间/时段/节奏 ──
NIGHT_SCENARIOS = [
    ("夜间-凌晨咨询", ["night"], ["凌晨2点还没睡，想咨询工资问题", "会不会打扰", "明天打也行"], {"must_have": []}),
    ("夜间-拒接电话", ["night"], ["拖欠工资", "现在太晚了不要打电话", "微信可以说"], {"no_phone_ask": True}),
    ("夜间-要求明早联系", ["night"], ["13812345678", "明天早上9点后联系", "别半夜打"], {}),
    ("夜间-紧急刑事", ["night", "criminal"], ["刚接到派出所电话", "让我去一趟", "现在半夜"], {"must_have": ["律师", "刑事", "辩护", "联系", "手机"]}),
    ("周末-正常咨询", ["weekend"], ["周末你们上班吗", "拖欠工资"], {}),
    ("节假日-催进度", ["holiday"], ["13812345678", "工资问题", "都放假了还会有人联系吗"], {}),
]

# ── Suite 2: 回访/多会话 ──
def run_return_visitor(base: str) -> list[TurnResult]:
    results = []
    vid = "return-visitor-round3-001"
    # Session 1: leave contact
    s1 = new_session(base, vid, ["return", "s1"])
    r1 = chat(base, s1["session_id"], "13812345678，拖欠工资四个月")
    results.append(TurnResult("回访", "多会话", "首次留资", s1["session_id"], r1["turn_id"], 1,
        "13812345678，拖欠工资四个月", r1["reply"], *evaluate_generic("回访", "多会话", "首次留资", 1,
        "13812345678，拖欠工资四个月", r1["reply"], [], {"must_have": ["联系", "登记", "律师"]})))
    # Session 2: same visitor new case
    s2 = new_session(base, vid, ["return", "s2"])
    r2 = chat(base, s2["session_id"], "你好，我又来了，上次工资的事还没人联系我")
    v, reason, exp = evaluate_generic("回访", "多会话", "回访催进度", 1, "你好，我又来了，上次工资的事还没人联系我", r2["reply"], [],
        {"must_have": ["联系", "安排", "登记", "律师", "跟进"]})
    results.append(TurnResult("回访", "多会话", "回访催进度", s2["session_id"], r2["turn_id"], 1,
        "你好，我又来了，上次工资的事还没人联系我", r2["reply"], v, reason, exp, {"same_visitor_id": vid}))
    r3 = chat(base, s2["session_id"], "这次还有离婚问题")
    v2, reason2, exp2 = evaluate_generic("回访", "多会话", "回访新案由", 2, "这次还有离婚问题", r3["reply"], [r2["reply"]],
        {"must_have": ["离婚", "家事", "婚姻", "抚养", "财产"]})
    if v2 == "ok" and "工资" in r3["reply"] and "离婚" not in r3["reply"]:
        v2, reason2 = "mismatch", "新案由离婚未切换"
    results.append(TurnResult("回访", "多会话", "回访新案由", s2["session_id"], r3["turn_id"], 2,
        "这次还有离婚问题", r3["reply"], v2, reason2, exp2))
    # Session 3: no history memory expected but polite
    s3 = new_session(base, vid, ["return", "s3"])
    r4 = chat(base, s3["session_id"], "之前咨询过你们，还有记录吗")
    results.append(TurnResult("回访", "多会话", "询问历史记录", s3["session_id"], r4["turn_id"], 1,
        "之前咨询过你们，还有记录吗", r4["reply"], *evaluate_generic("回访", "多会话", "询问历史记录", 1,
        "之前咨询过你们，还有记录吗", r4["reply"], [], {})))
    return results


# ── Suite 3: 并发压力 ──
STRESS_MESSAGES = [
    "公司拖欠工资三个月怎么办",
    "我想离婚",
    "被网络诈骗了",
    "工伤怎么认定",
    "你们地址在哪",
    "免费咨询吗",
    "老公打我",
    "赢了官司对方不给钱",
    "试用期被辞退",
    "不想留电话",
]

def run_concurrent_stress(base: str, workers: int = 50) -> list[TurnResult]:
    results = []
    errors = []

    def worker(i: int):
        msg = STRESS_MESSAGES[i % len(STRESS_MESSAGES)]
        s = new_session(base, f"stress-{i:03d}", ["stress", "parallel"])
        replies = []
        for m in [msg, "那我怎么办", "13812345678"]:
            d = chat(base, s["session_id"], m)
            replies.append(d["reply"])
        return i, s["session_id"], msg, replies, None

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(worker, i) for i in range(workers)]
        for fut in as_completed(futs):
            try:
                i, sid, msg, replies, _ = fut.result()
                for ti, (m, rep) in enumerate(zip([msg, "那我怎么办", "13812345678"], replies), 1):
                    prev = replies[: ti - 1]
                    v, reason, exp = evaluate_generic("并发", "压力", f"worker-{i:03d}", ti, m, rep, prev, {})
                    if not rep:
                        v, reason = "mismatch", "并发下空回复"
                    results.append(TurnResult("并发", "压力", f"worker-{i:03d}", sid, "", ti, m, rep, v, reason, exp))
            except Exception as e:
                errors.append(str(e))
    elapsed = time.time() - t0
    ok = sum(1 for r in results if r.verdict == "ok")
    results.append(TurnResult("并发", "压力", "汇总", "", "", 0, "",
        f"{workers} workers, {len(results)-1} turns, {ok} ok, {len(errors)} errors, {elapsed:.1f}s",
        "ok" if not errors else "mismatch",
        f"errors={len(errors)}" if errors else "并发全部成功",
        "50路并发应全部返回有效回复", {"workers": workers, "elapsed_s": elapsed, "errors": errors[:5]}))
    return results


# ── Suite 4: 连发/_burst ──
def run_burst_session(base: str) -> list[TurnResult]:
    results = []
    s = new_session(base, "burst-001", ["burst"])
    sid = s["session_id"]
    msgs = [
        "在吗",
        "工资",
        "拖欠",
        "三个月",
        "怎么办",
    ]
    prev = []
    for i, m in enumerate(msgs, 1):
        d = chat(base, sid, m)
        v, reason, exp = evaluate_generic("连发", "同会话连击", "碎片化输入", i, m, d["reply"], prev,
            {"no_repetitive_template": i >= 3})
        results.append(TurnResult("连发", "同会话连击", "碎片化输入", sid, d["turn_id"], i, m, d["reply"], v, reason, exp))
        prev.append(d["reply"])
    return results


# ── Suite 5: API 健壮性 ──
def run_api_robustness(base: str) -> list[TurnResult]:
    results = []
    cases = [
        ("空消息", {"message": ""}, 400),
        ("纯空格", {"message": "   "}, 400),
        ("超长文本", {"message": "工资" * 500}, 200),
        ("特殊字符", {"message": "<script>alert(1)</script> 拖欠工资"}, 200),
        ("SQL注入样例", {"message": "' OR 1=1 -- 拖欠工资"}, 200),
        ("无session自动建", {"message": "你好", "visitor_id": "auto-session-001"}, 200),
        ("Unicode特殊", {"message": "工资\u200b\u200b拖欠\uFEFF"}, 200),
    ]
    s = new_session(base, "api-robust", ["api"])
    sid = s["session_id"]
    for name, body, expect_code in cases:
        if "session_id" not in body and name not in ("无session自动建",):
            body = {**body, "session_id": sid}
        code, data = post(base, "/api/v1/chat", body)
        if expect_code == 200:
            ok = code == 200 and isinstance(data, dict) and data.get("reply")
            verdict = "ok" if ok else "mismatch"
            reason = "正常返回" if ok else f"期望200有回复, 得{code}"
            reply = data.get("reply", "") if isinstance(data, dict) else str(data)[:200]
        else:
            ok = code == expect_code
            verdict = "ok" if ok else "mismatch"
            reason = f"期望HTTP {expect_code}, 得{code}"
            reply = str(data)[:200] if not isinstance(data, dict) else data.get("error", data.get("reply", ""))
        results.append(TurnResult("API", "健壮性", name, sid, "", 0, str(body.get("message", ""))[:80],
            str(reply)[:300], verdict, reason, f"HTTP {expect_code}"))
    return results


# ── Suite 6: LLM 对比 ──
LLM_COMPARE_PROMPTS = [
    ("劳动-怎么办", "公司拖欠工资三个月，我应该怎么办"),
    ("家暴", "老公打我，我想离婚但怕报复"),
    ("程序-时效", "事情过去3年了还能起诉吗"),
    ("拒留电话", "不想留电话，直接告诉我怎么办"),
    ("一句多问", "收费吗？地址在哪？"),
    ("刑事", "我涉嫌诈骗罪被拘留，家属能做什么"),
    ("情绪危机", "活着没意思，被老板逼的"),
]

def run_llm_comparison() -> list[TurnResult]:
    results = []
    code_no, _ = get(BASE_NO_LLM, "/health")
    code_llm, _ = get(BASE_LLM, "/health")
    if code_llm != 200:
        results.append(TurnResult("LLM对比", "服务", "LLM服务不可用", "", "", 0, "",
            "", "mismatch", f"8766 health={code_llm}", "需启动LLM服务"))
        return results

    for name, prompt in LLM_COMPARE_PROMPTS:
        s_no = new_session(BASE_NO_LLM, f"cmp-no-{name}", ["llm-cmp"])
        s_llm = new_session(BASE_LLM, f"cmp-llm-{name}", ["llm-cmp"])
        r_no = chat(BASE_NO_LLM, s_no["session_id"], prompt)
        r_llm = chat(BASE_LLM, s_llm["session_id"], prompt)
        ratio = sim(r_no["reply"], r_llm["reply"])
        # LLM should ideally differ on weak template cases
        if ratio >= 0.90:
            verdict = "repetitive" if "怎么办" in prompt or "3年" in prompt else "ok"
            reason = f"no-llm与llm回复相似度{ratio:.0%}，LLM未明显改进"
        else:
            verdict = "ok"
            reason = f"LLM与规则回复有差异({ratio:.0%})，可能更有针对性"
        results.append(TurnResult("LLM对比", "A/B", name, s_no["session_id"], r_no["turn_id"], 1, prompt,
            f"[NO_LLM]{r_no['reply'][:150]} | [LLM]{r_llm['reply'][:150]}", verdict, reason,
            "LLM应在复杂/情感/程序问题上优于纯模板", {"similarity": ratio,
            "reply_no_llm": r_no["reply"], "reply_llm": r_llm["reply"]}))
    return results


# ── Suite 7: 深度场景 persona ──
DEEP_PERSONAS = [
    ("渠道", "抖音广告来的", ["channel"], ["抖音上看到你们", "说免费分析", "真的免费吗"]),
    ("渠道", "小红书引流", ["channel"], ["小红书加的", "先别推销", "先说怎么帮"]),
    ("决策", "已有律师", ["decision"], ["我已经请律师了", "只是想对比", "你们更便宜吗"]),
    ("决策", "自己打官司", ["decision"], ["我想自己起诉", "你们只咨询不写材料行吗"]),
    ("决策", "只要写状纸", ["decision"], ["能不能只代写起诉状", "多少钱"]),
    ("金额", "小标的", ["amount"], ["就欠5000块", "请律师划算吗"]),
    ("金额", "大标的", ["amount"], ["涉及5000万", "能接吗"]),
    ("身份", "未成年人", ["minor"], ["我17岁打工", "老板不给钱"]),
    ("身份", "替家人问", ["proxy"], ["帮我妈问", "她不会打字", "赡养费"]),
    ("身份", "律师同行", ["peer"], ["我也是律师", "想合作案件"]),
    ("转人工", "要求人工", ["handover"], ["转人工", "不要机器人", "找真人律师"]),
    ("转人工", "指定回电时间", ["handover"], ["13812345678", "下班后再打", "6点到8点"]),
    ("竞争", "已咨询别家", ["compare"], ["刚咨询了XX律所", "他们说能赢", "你们呢"]),
    ("竞争", "价格砍价", ["compare"], ["太贵了", "便宜点", "别人2000"]),
    ("证据", "只有转账记录", ["evidence"], ["只有银行转账", "没借条", "能告吗"]),
    ("证据", "电子合同", ["evidence"], ["只有电子签", "有效吗"]),
    ("执行", "对方失联", ["procedure"], ["赢了官司", "对方失联", "找不到人"]),
    ("执行", "对方破产", ["procedure"], ["公司破产了", "工资还能拿吗"]),
    ("行政", "行政复议时限", ["admin"], ["行政处罚15天内", "怎么复议"]),
    ("刑事", "家属会见", ["criminal"], ["在看守所", "家属能见吗"]),
    ("家事", "涉外离婚", ["family"], ["老公在国外", "怎么离婚"]),
    ("劳动", "高管辞退", ["labor"], ["总监被辞退", "补偿N+1吗"]),
    ("劳动", "股权激励", ["labor"], ["期权没兑现", "离职怎么办"]),
    ("消费", "预付卡", ["consumer"], ["美发店预付卡", "店家跑路"]),
    ("消费", "直播带货", ["consumer"], ["直播买到假货", "平台不管"]),
    ("房产", "法拍房", ["property"], ["买了法拍房", "原业主不走"]),
    ("房产", "小产权房", ["property"], ["小产权房", "能确权吗"]),
    ("网络", "个人信息泄露", ["privacy"], ["信息被泄露", "被骚扰", "能告吗"]),
    ("网络", "名誉侵权", ["privacy"], ["网上被人诽谤", "怎么取证"]),
    ("保险", "拒赔", ["insurance"], ["保险公司拒赔", "怎么起诉"]),
    ("税务", "个人税务", ["tax"], ["被税务稽查", "怎么办"]),
    ("会话", "长间隔续聊", ["dynamic"], ["拖欠工资", "（用户离开）", "我回来了继续问", "材料有哪些"]),
    ("会话", "否定前文", ["dynamic"], ["我要告公司", "不对，是告个人", "包工头欠钱"]),
    ("会话", "测试理解", ["dynamic"], ["不是工资，是提成", "别按工资回答"]),
    ("安全", "威胁自杀", ["crisis"], ["不想活了", "被老板逼的"]),
    ("安全", "家暴紧急", ["crisis"], ["现在在被打", "在线等"]),
    ("安全", "未成年性侵", ["crisis"], ["孩子被侵犯", "不敢报警"]),
    ("边界", "要具体法条", ["edge"], ["把刑法234条全文发我"]),
    ("边界", "要判例", ["edge"], ["有类似判例吗", "发判决书"]),
    ("边界", "非业务闲聊", ["edge"], ["律师你吃饭了吗", "聊聊人生"]),
    ("边界", "辱骂后咨询", ["edge"], ["你们很烦", "算了还是问工资吧"]),
    ("边界", "多手机号", ["contact"], ["13811112222和13933334444", "都可以打"]),
    ("边界", "只要短信", ["contact"], ["不要电话", "发短信到13812345678"]),
]


def run_deep_personas(base: str) -> list[TurnResult]:
    results = []
    for idx, (cat, name, tags, msgs) in enumerate(DEEP_PERSONAS):
        s = new_session(base, f"deep-{idx:04d}", tags + ["round3-deep"])
        sid = s["session_id"]
        prev = []
        for i, m in enumerate(msgs, 1):
            d = chat(base, sid, m)
            rules = {"no_repetitive_template": True}
            if cat == "安全" or name in ("威胁自杀", "家暴紧急"):
                if any(x in m for x in ("不想活", "被打", "侵犯")):
                    rules["must_not"] = ["重点要补充时间、金额、材料和目前处理进展"]
            if name == "转人工":
                if "人工" in m or "真人" in m:
                    rules["must_have"] = ["人工", "律师", "客服", "助手", "联系"]
            if name == "程序-时效" or "时效" in name or "3年" in m:
                rules["must_have"] = ["时效", "起诉", "期限", "三年", "过期"]
            if "免费" in m:
                rules["must_have"] = ["费", "免费", "收", "咨询"]
            v, reason, exp = evaluate_generic("深度", cat, name, i, m, d["reply"], prev, rules)
            results.append(TurnResult("深度", cat, name, sid, d["turn_id"], i, m, d["reply"], v, reason, exp))
            prev.append(d["reply"])
            time.sleep(0.02)
    return results


def run_night_scenarios(base: str) -> list[TurnResult]:
    results = []
    for name, tags, msgs, rules in NIGHT_SCENARIOS:
        s = new_session(base, f"night-{name}", tags + ["round3-night"])
        sid = s["session_id"]
        prev = []
        for i, m in enumerate(msgs, 1):
            d = chat(base, sid, m)
            v, reason, exp = evaluate_generic("夜间", "时段", name, i, m, d["reply"], prev, rules)
            if "不要打电话" in m and re.search(r"手机|电话", d["reply"]):
                if "微信" not in d["reply"] and "理解" not in d["reply"]:
                    v, reason = "missed_contact", "明确不要电话仍强推"
            if "周末" in m and i == 1:
                if not any(x in d["reply"] for x in ("周末", "上班", "时间", "联系", "登记")):
                    v, reason = "mismatch", "周末上班问题未回应"
            results.append(TurnResult("夜间", "时段", name, sid, d["turn_id"], i, m, d["reply"], v, reason, exp))
            prev.append(d["reply"])
    return results


# ── Suite 8: 会话隔离 ──
def run_session_isolation(base: str) -> list[TurnResult]:
    results = []
    s_a = new_session(base, "iso-a", ["isolation"])
    s_b = new_session(base, "iso-b", ["isolation"])
    r_a = chat(base, s_a["session_id"], "我拖欠工资，手机号13800001111")
    r_b = chat(base, s_b["session_id"], "我想离婚")
    # B should not mention wage/13800001111
    if "13800001111" in r_b["reply"] or ("工资" in r_b["reply"] and "离婚" not in r_b["reply"]):
        v, reason = "mismatch", "会话B泄露了会话A的信息"
    else:
        v, reason = "ok", "会话隔离正常"
    results.append(TurnResult("隔离", "多会话", "跨会话不串案", s_b["session_id"], r_b["turn_id"], 1,
        "我想离婚", r_b["reply"], v, reason, "不同session不应互相污染"))
    return results


def main() -> int:
    print("=== Round 3 全方向黑盒测试 ===", flush=True)
    all_results: list[TurnResult] = []

    code, health = get(BASE_NO_LLM, "/health")
    if code != 200:
        print(f"8765 unavailable: {health}")
        return 1
    print(f"8765 OK: {health}\n", flush=True)

    suites = [
        ("夜间时段", lambda: run_night_scenarios(BASE_NO_LLM)),
        ("回访多会话", lambda: run_return_visitor(BASE_NO_LLM)),
        ("并发50路", lambda: run_concurrent_stress(BASE_NO_LLM, 50)),
        ("连发连击", lambda: run_burst_session(BASE_NO_LLM)),
        ("API健壮性", lambda: run_api_robustness(BASE_NO_LLM)),
        ("LLM对比", run_llm_comparison),
        ("深度场景", lambda: run_deep_personas(BASE_NO_LLM)),
        ("会话隔离", lambda: run_session_isolation(BASE_NO_LLM)),
    ]

    for suite_name, fn in suites:
        print(f">> {suite_name}...", flush=True)
        t0 = time.time()
        try:
            rows = fn()
            all_results.extend(rows)
            issues = [r for r in rows if r.verdict != "ok"]
            print(f"   {len(rows)} turns, {len(issues)} issues, {time.time()-t0:.1f}s", flush=True)
        except Exception as e:
            print(f"   ERROR: {e}", flush=True)

    verdicts = Counter(r.verdict for r in all_results)
    by_suite = defaultdict(lambda: Counter())
    for r in all_results:
        by_suite[r.suite][r.verdict] += 1

    with open(OUT, "w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps({
                "suite": r.suite, "category": r.category, "persona": r.persona,
                "session_id": r.session_id, "turn_id": r.turn_id, "turn_index": r.turn_index,
                "visitor_text": r.visitor_text, "assistant_reply": r.assistant_reply,
                "verdict": r.verdict, "reason": r.reason, "expected_behavior": r.expected_behavior,
                "extra": r.extra,
            }, ensure_ascii=False) + "\n")

    summary = {
        "total_turns": len(all_results),
        "verdicts": dict(verdicts),
        "by_suite": {k: dict(v) for k, v in by_suite.items()},
        "pass_rate": round(verdicts.get("ok", 0) / max(len(all_results), 1) * 100, 1),
    }
    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n=== 汇总 ===", flush=True)
    print(f"总轮次: {len(all_results)} | 通过率: {summary['pass_rate']}%", flush=True)
    for v, c in verdicts.most_common():
        print(f"  {v}: {c}", flush=True)
    print("\n=== 分套件 ===", flush=True)
    for suite, counts in sorted(by_suite.items()):
        total = sum(counts.values())
        ok = counts.get("ok", 0)
        print(f"  {suite}: {ok}/{total} ok | {dict(counts)}", flush=True)

    print(f"\nJSONL: {OUT}", flush=True)
    print(f"Summary: {OUT_SUMMARY}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
