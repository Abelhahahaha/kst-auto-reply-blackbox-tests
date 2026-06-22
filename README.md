# KST 自动回复黑盒测试归档

本仓库汇总 **两位 AI 测试工程师** 对 KST 虚拟访客自动回复系统的黑盒测试结果与对话记录，供 ChatGPT / 其他工具继续分析。

**被测项目**：`最终版5.3 - 可用`（虚拟入口 `tools/virtual_chat_server.py`，黑盒 API `http://127.0.0.1:8765`）

**测试模式**：主要为 `--no-llm` 规则模式；Round 3 含 LLM 对比（8766 端口）

---

## 给 ChatGPT 的阅读顺序

1. [`docs/CONSOLIDATED_SUMMARY.md`](docs/CONSOLIDATED_SUMMARY.md) — **先看**：两轮 AI 合并结论、P0 短板、累计数据
2. [`chat-logs/cursor-agent-transcript.jsonl`](chat-logs/cursor-agent-transcript.jsonl) — Cursor Auto 完整对话（含 Round 1–3 用户指令与报告）
3. [`chat-logs/CURSOR_CHAT_EXPORT.md`](chat-logs/CURSOR_CHAT_EXPORT.md) — 上述对话的可读 Markdown 摘要
4. 测试结果 JSONL（见下方目录表）— 逐条 visitor / reply / verdict 原始数据

---

## 目录结构

### Cursor Auto（本会话 AI）

| 文件 | 说明 |
|------|------|
| `cursor-auto/blackbox_auto_reply_test.py` | Round 1：19 persona，57 轮 |
| `cursor-auto/blackbox_test_results.jsonl` | Round 1 结果 |
| `cursor-auto/blackbox_auto_reply_test_round2.py` | Round 2：112 persona，251 轮 |
| `cursor-auto/blackbox_test_round2_results.jsonl` | Round 2 结果 |
| `cursor-auto/analyze_round2.py` | Round 2 统计分析脚本 |
| `cursor-auto/blackbox_auto_reply_test_round3.py` | Round 3：8 套件，291 轮 |
| `cursor-auto/blackbox_test_round3_results.jsonl` | Round 3 结果 |
| `cursor-auto/blackbox_test_round3_summary.json` | Round 3 汇总 |

### 另一位 AI（同目录早期测试）

| 文件 | 说明 |
|------|------|
| `other-ai/comprehensive_test.py` | 全面黑盒脚本（约 248 条用例） |
| `other-ai/test_report_20260622_092303.jsonl` | 该 AI 测试原始结果 |
| `other-ai/deep_analysis.py` | 回复多样性 / 前缀频率等深度分析 |

### 对话记录

| 文件 | 说明 |
|------|------|
| `chat-logs/cursor-agent-transcript.jsonl` | Cursor 会话原始 JSONL |
| `chat-logs/CURSOR_CHAT_EXPORT.md` | 可读版对话与报告摘要 |

---

## 累计规模（Cursor 三轮）

| 轮次 | Persona/套件 | 轮次 | 通过率 |
|------|-------------|------|--------|
| R1 | 19 | 57 | 50.9% |
| R2 | 112 | 251 | 66.5% |
| R3 | 8 套件 | 291 | 83.8% |
| **合计** | ~243 | **599** | — |

另一位 AI：`comprehensive_test.py` 约 **248** 条独立用例。

---

## 复现

```powershell
Set-Location "C:\Users\wupei\Desktop\最终版5.3 - 可用"
python tools\virtual_chat_server.py --host 127.0.0.1 --port 8765 --no-llm

python cursor-auto\blackbox_auto_reply_test.py
python cursor-auto\blackbox_auto_reply_test_round2.py
python cursor-auto\blackbox_auto_reply_test_round3.py
python other-ai\comprehensive_test.py
```

---

## 核心结论（摘要）

- **P0**：多轮模板复读；危机/自伤/家暴未识别；换话题不跟随
- **P1**：程序性问题（时效/执行/管辖）无答案；拒留电话仍催留资
- **已验证 OK**：50 路并发稳定、API 健壮、跨 session 隔离、首轮常见案由识别

详见 `docs/CONSOLIDATED_SUMMARY.md`。
