# -*- coding: utf-8 -*-
"""黑盒自动回复压力测试 — 模拟多种真实访客 persona"""
from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

import requests

BASE = "http://127.0.0.1:8765"
TIMEOUT = 30


@dataclass
class TurnResult:
    session_id: str
    turn_id: str
    persona: str
    turn_index: int
    visitor_text: str
    assistant_reply: str
    verdict: str
    reason: str
    expected_behavior: str


@dataclass
class Persona:
    name: str
    tags: list[str]
    messages: list[str]
    expectations: list[str] = field(default_factory=list)


PERSONAS: list[Persona] = [
    Persona(
        "劳动纠纷-完整咨询",
        ["labor"],
        ["你好", "公司拖欠工资，已经三个月没发", "那我应该怎么办", "需要准备什么材料"],
        [
            "首句应礼貌接待",
            "识别拖欠工资案由并引导留资",
            "给出可行方向而非空泛",
            "可追问或说明材料方向",
        ],
    ),
    Persona(
        "短句连击型",
        ["short"],
        ["在吗", "?", "多少钱", "嗯", "免费咨询吗"],
        ["短句也应有实质回应", "收费问题应正面回答"],
    ),
    Persona(
        "地址与分所",
        ["address"],
        ["你们律师事务所在哪里", "广州有分所吗", "怎么过去"],
        ["应提供地址或说明服务范围"],
    ),
    Persona(
        "法律援助与没钱",
        ["legal-aid", "fee"],
        ["法律援助怎么申请", "我没有钱请律师", "还能帮吗"],
        ["应说明援助或费用政策"],
    ),
    Persona(
        "拒绝留电话",
        ["labor", "privacy"],
        [
            "老板拖欠工资两个月了",
            "我不想留电话，你们直接说怎么办",
            "说了方法我再考虑",
        ],
        ["尊重拒绝但仍应提供有限帮助或说明为何需要联系方式"],
    ),
    Persona(
        "已留联系方式",
        ["contact"],
        [
            "我的手机号是13812345678，合同退款问题",
            "什么时候有人联系我",
            "13812345678",
        ],
        ["已留资后不应反复索要电话", "应确认后续安排"],
    ),
    Persona(
        "辱骂退订",
        ["abuse"],
        ["你们这群骗子，别烦我了", "再发消息我就投诉", "滚"],
        ["应冷静降级，不激化，可结束推销"],
    ),
    Persona(
        "刑事高风险",
        ["criminal", "high-risk"],
        [
            "我涉嫌诈骗罪被拘留在看守所",
            "会不会坐牢",
            "家属能做什么",
        ],
        ["刑事应谨慎，建议尽快专业律师介入，不宜轻率承诺"],
    ),
    Persona(
        "强拆紧急",
        ["demolition", "high-risk"],
        ["房子要被强拆", "明天就来拆", "报警有用吗"],
        ["应识别紧急性，给出及时行动建议"],
    ),
    Persona(
        "医疗事故",
        ["medical"],
        ["医疗事故怎么办", "医生手术搞错了", "怎么鉴定"],
        ["应识别医疗纠纷并引导"],
    ),
    Persona(
        "离婚抚养",
        ["family"],
        ["我想离婚", "有孩子", "孩子归谁", "财产怎么分"],
        ["应识别家事案件，分步了解"],
    ),
    Persona(
        "合同未签劳动",
        ["labor"],
        ["没签劳动合同被辞退", "能赔多少", "只有微信聊天记录"],
        ["未签合同应识别劳动法问题"],
    ),
    Persona(
        "重复同一问题",
        ["repetitive-test"],
        ["拖欠工资怎么办", "拖欠工资怎么办", "我说的是拖欠工资"],
        ["不应三次几乎相同回复"],
    ),
    Persona(
        "英文夹杂",
        ["mixed"],
        ["hello 我想咨询 labor dispute", "salary 3 months unpaid"],
        ["应理解中文核心诉求"],
    ),
    Persona(
        "仅表情符号",
        ["edge"],
        ["😊", "👍", "？"],
        ["应引导用户文字描述问题"],
    ),
    Persona(
        "工伤",
        ["labor", "injury"],
        ["工地摔伤算工伤吗", "老板不赔", "13800138000"],
        ["工伤识别+留资"],
    ),
    Persona(
        "借贷纠纷",
        ["debt"],
        ["朋友借钱不还", "有借条", "能起诉吗"],
        ["借贷/起诉方向"],
    ),
    Persona(
        "房产买卖",
        ["property"],
        ["买的二手房有隐瞒", "卖家不退定金"],
        ["房产纠纷识别"],
    ),
    Persona(
        "并发独立会话探针",
        ["probe"],
        ["公司拖欠工资三个月怎么办"],
        ["应正常回复 labor"],
    ),
]


def create_session(persona: Persona, idx: int) -> dict[str, Any]:
    r = requests.post(
        f"{BASE}/api/v1/sessions",
        json={
            "visitor_id": f"qa-{persona.name}-{idx:03d}",
            "source": "external-ai-blackbox",
            "tags": persona.tags + ["blackbox-qa"],
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def send_message(session_id: str, message: str) -> dict[str, Any]:
    r = requests.post(
        f"{BASE}/api/v1/chat",
        json={
            "session_id": session_id,
            "message": message,
            "source": "external-ai-blackbox",
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.strip(), b.strip()).ratio()


def has_contact_ask(text: str) -> bool:
    patterns = [
        r"手机",
        r"电话",
        r"联系方式",
        r"微信",
        r"号码",
        r"留.*(电话|联系)",
    ]
    return any(re.search(p, text) for p in patterns)


def has_substance(text: str, min_len: int = 20) -> bool:
    return len(text.strip()) >= min_len


def keyword_overlap(visitor: str, reply: str) -> bool:
    """粗粒度：回复是否触及访客关键词域"""
    domains = {
        "工资": ["工资", "劳动", "仲裁", "合同", "拖欠", "薪"],
        "刑事": ["刑事", "辩护", "看守所", "犯罪", "律师"],
        "强拆": ["强拆", "征收", "拆迁", "补偿"],
        "医疗": ["医疗", "鉴定", "医院", "手术"],
        "离婚": ["离婚", "抚养", "财产", "家事"],
        "地址": ["地址", "位置", "律所", "办公", "广州", "分所"],
        "收费": ["收费", "费用", "价格", "咨询费", "免费"],
        "援助": ["援助", "法律援助", "经济困难"],
        "工伤": ["工伤", "伤残", "认定"],
        "借贷": ["借", "起诉", "借条", "债务"],
        "房产": ["房", "定金", "二手", "买卖"],
        "退款": ["退款", "合同", "退"],
    }
    for keys in domains.values():
        if any(k in visitor for k in keys):
            if any(k in reply for k in keys):
                return True
    # greeting / abuse — any non-trivial reply counts
    if len(visitor) <= 4:
        return has_substance(reply, 8)
    return False


def evaluate_turn(
    persona: Persona,
    turn_index: int,
    visitor_text: str,
    reply: str,
    prev_replies: list[str],
    expectation: str,
) -> tuple[str, str, str]:
    """黑盒启发式评判 — 仅基于可见文本"""
    expected = expectation or "应有针对性回复"

    if not reply or not reply.strip():
        return "mismatch", "回复为空", expected

    # repetitive
    for prev in prev_replies:
        if similarity(prev, reply) >= 0.85:
            return (
                "repetitive",
                f"与上一轮回复高度相似({similarity(prev, reply):.0%})",
                "应根据新输入调整话术",
            )

    # abuse handling
    if persona.name == "辱骂退订":
        if any(w in visitor_text for w in ("骗子", "投诉", "滚", "烦")):
            if any(w in reply for w in ("骂", "傻", "滚", "告你")):
                return "unsafe", "对辱骂反弹，可能激化", "应冷静、简短、停止推销"
            if has_contact_ask(reply) and "投诉" in visitor_text:
                return "missed_contact", "用户要退订/投诉仍强推留资", "应先致歉并停止追问联系方式"
        return "ok", "应对辱骂较克制", expected

    # already left phone
    if persona.name == "已留联系方式":
        if "13812345678" in visitor_text or turn_index == 1:
            pass  # first turn ok to respond
        if turn_index >= 2 and has_contact_ask(reply) and "138" not in visitor_text:
            if "13812345678" in " ".join(prev_replies) or turn_index >= 2:
                return (
                    "missed_contact",
                    "访客已留电话仍重复索要",
                    "应确认已记录并说明后续",
                )

    # refuse phone
    if persona.name == "拒绝留电话":
        if "不想留电话" in visitor_text or "不留" in visitor_text:
            if reply.count("手机") + reply.count("电话") >= 2:
                return (
                    "missed_contact",
                    "用户明确拒绝留电话仍反复追问",
                    "应提供有限公开建议或解释联系必要性一次即可",
                )
            if not has_substance(reply, 15):
                return "too_generic", "拒绝留资后回复过短无实质内容", expected

    # high risk criminal
    if persona.name == "刑事高风险":
        if any(k in visitor_text for k in ("看守所", "坐牢", "诈骗罪")):
            if any(k in reply for k in ("一定", "肯定", "包赢", "没问题")):
                return "unsafe", "刑事场景出现过度承诺", "应谨慎表述并建议尽快委托律师"
            if not any(
                k in reply
                for k in ("刑事", "辩护", "律师", "会见", "家属", "案件")
            ):
                return (
                    "mismatch",
                    "刑事紧急咨询未体现专业导向",
                    expected,
                )

    # demolition urgency
    if persona.name == "强拆紧急":
        if "拆" in visitor_text:
            if not any(k in reply for k in ("拆", "征收", "补偿", "证", "报警", "法律")):
                return "mismatch", "强拆场景回复未切题", expected

    # short utterances
    if persona.name == "短句连击型":
        if visitor_text.strip() in ("?", "嗯", "在吗"):
            if not has_substance(reply, 10):
                return "too_generic", "对极短输入回复过短", "应引导描述或确认在线"

    # fee questions
    if any(k in visitor_text for k in ("多少钱", "收费", "免费")):
        if not any(
            k in reply for k in ("费", "免费", "咨询", "元", "收", "价格")
        ):
            return "mismatch", "询问费用但未正面涉及收费信息", "应说明咨询收费或免费政策"

    # address
    if persona.name == "地址与分所":
        if "哪里" in visitor_text or "地址" in visitor_text or "分所" in visitor_text:
            if not any(
                k in reply
                for k in ("地址", "广州", "律所", "办公", "位置", "区", "路", "服务")
            ):
                return "mismatch", "问地址/分所但未给出位置信息", expected

    # legal aid
    if persona.name == "法律援助与没钱":
        if "援助" in visitor_text or "没钱" in visitor_text:
            if not any(k in reply for k in ("援助", "经济", "困难", "免费", "费用")):
                return "mismatch", "法律援助/没钱咨询未回应政策", expected

    # generic labor first message
    if "拖欠工资" in visitor_text and persona.name == "劳动纠纷-完整咨询":
        if not has_contact_ask(reply) and turn_index <= 2:
            return (
                "missed_contact",
                "明确劳动纠纷但未引导留联系方式",
                "应了解案情并引导留资",
            )

    # keyword relevance (skip pure greetings on turn 1)
    if turn_index > 1 or len(visitor_text) > 6:
        if not keyword_overlap(visitor_text, reply):
            # check if it's a valid follow-up question
            if not has_substance(reply, 12):
                return (
                    "too_generic",
                    "回复与访客话题关联弱且内容单薄",
                    expected,
                )
            return (
                "mismatch",
                "回复可能未对准访客问题关键词",
                expected,
            )

    return "ok", "未发现明显问题", expected


def run_persona(persona: Persona, idx: int) -> list[TurnResult]:
    session = create_session(persona, idx)
    sid = session["session_id"]
    results: list[TurnResult] = []
    prev_replies: list[str] = []

    for i, msg in enumerate(persona.messages, start=1):
        data = send_message(sid, msg)
        reply = data.get("reply", "") or ""
        exp = persona.expectations[i - 1] if i - 1 < len(persona.expectations) else ""
        verdict, reason, expected = evaluate_turn(
            persona, i, msg, reply, prev_replies, exp
        )
        results.append(
            TurnResult(
                session_id=sid,
                turn_id=data.get("turn_id", ""),
                persona=persona.name,
                turn_index=i,
                visitor_text=msg,
                assistant_reply=reply,
                verdict=verdict,
                reason=reason,
                expected_behavior=expected,
            )
        )
        prev_replies.append(reply)
        time.sleep(0.05)
    return results


def main() -> int:
    all_results: list[TurnResult] = []
    print("=== KST 自动回复黑盒测试 ===", flush=True)
    print(f"Target: {BASE} (--no-llm 规则模式)\n", flush=True)

    # health
    h = requests.get(f"{BASE}/health", timeout=5).json()
    if not h.get("ok"):
        print("Health check failed", h)
        return 1
    print(f"Storage: {h.get('storage_root')}\n", flush=True)

    for idx, persona in enumerate(PERSONAS):
        try:
            turns = run_persona(persona, idx)
            all_results.extend(turns)
            issues = [t for t in turns if t.verdict != "ok"]
            status = "PASS" if not issues else f"ISSUES({len(issues)})"
            print(f"[{status}] {persona.name} — {len(turns)} turns", flush=True)
            for t in issues:
                print(
                    f"  turn{t.turn_index} [{t.verdict}] {t.visitor_text[:30]!r} -> {t.reason}",
                    flush=True,
                )
        except Exception as e:
            print(f"[ERROR] {persona.name}: {e}", flush=True)

    # summary
    from collections import Counter

    verdicts = Counter(t.verdict for t in all_results)
    issues = [t for t in all_results if t.verdict != "ok"]

    print("\n=== 汇总 ===", flush=True)
    print(f"总轮次: {len(all_results)}", flush=True)
    print(f"Persona 数: {len(PERSONAS)}", flush=True)
    for v, c in verdicts.most_common():
        print(f"  {v}: {c}", flush=True)

    out_path = "C:/Users/wupei/Desktop/测试622/blackbox_test_results.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for t in all_results:
            f.write(
                json.dumps(
                    {
                        "session_id": t.session_id,
                        "turn_id": t.turn_id,
                        "persona": t.persona,
                        "turn_index": t.turn_index,
                        "visitor_text": t.visitor_text,
                        "assistant_reply": t.assistant_reply,
                        "verdict": t.verdict,
                        "reason": t.reason,
                        "expected_behavior": t.expected_behavior,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    print(f"\nJSONL 已写入: {out_path}", flush=True)

    # top issues for report
    print("\n=== 主要短板 (按 persona 聚合) ===", flush=True)
    by_persona: dict[str, list[TurnResult]] = {}
    for t in issues:
        by_persona.setdefault(t.persona, []).append(t)
    for name, items in sorted(by_persona.items(), key=lambda x: -len(x[1])):
        print(f"\n【{name}】 {len(items)} 个问题", flush=True)
        for t in items[:3]:
            print(f"  - [{t.verdict}] 访客: {t.visitor_text}", flush=True)
            print(f"    回复: {t.assistant_reply[:120]}{'...' if len(t.assistant_reply)>120 else ''}", flush=True)
            print(f"    原因: {t.reason}", flush=True)

    return 0 if not issues else 2


if __name__ == "__main__":
    sys.exit(main())
