# KST 自动回复黑盒测试 — 合并分析报告

> 供 ChatGPT 分析。数据来自 Cursor Auto（Round 1–3）+ 另一位 AI（`comprehensive_test.py`）。  
> 评判均为黑盒：仅依据访客可见 `reply` 文本。

---

## 1. 测试来源

| 来源 | 脚本 | 结果文件 | 规模 |
|------|------|----------|------|
| Cursor Auto R1 | `blackbox_auto_reply_test.py` | `blackbox_test_results.jsonl` | 57 轮 |
| Cursor Auto R2 | `blackbox_auto_reply_test_round2.py` | `blackbox_test_round2_results.jsonl` | 251 轮 |
| Cursor Auto R3 | `blackbox_auto_reply_test_round3.py` | `blackbox_test_round3_results.jsonl` | 291 轮 |
| 另一位 AI | `comprehensive_test.py` | `test_report_20260622_092303.jsonl` | ~248 条 |

**Cursor 合计**：599 轮，约 243 persona / 套件。  
**另一位 AI**：独立用例集，侧重案由分类、留资、辱骂、并发等（见其 JSONL 的 `category` 字段）。

---

## 2. 跨来源一致结论（高置信）

### 2.1 多轮模板复读（最严重，P0）

两套测试均发现：追问时大量复用骨架：

> 「可以，这个问题我先补充到前面的记录里 → 重点在…阶段 → 重点要补充时间、金额、材料和目前处理进展 → 留个手机号」

- Cursor R1：11/57 repetitive；R2：65/251；R3：41/291（深度场景 34% 失败）
- 另一位 AI `deep_analysis.py`：回复唯一率偏低，高频前缀如「收到，这个情况我先帮您记一下」

**影响**：访客感觉「只会催电话」，多轮无实质帮助。

### 2.2 上下文丢失 / 案由漂移（P0）

| 访客输入 | 系统表现 |
|----------|----------|
| 拖欠工资 → 换成离婚 | 仍走工资/商事模板 |
| 广州有分所吗 / 怎么过去 | 跑题到「时间、金额、材料」 |
| 我想离婚 / 有孩子 | 过度使用「房产来源、出资、还贷」 |
| 二手房隐瞒 | 误用「继承关系」模板 |
| 没签劳动合同 | 当成「公司商事」而非劳动法 |

### 2.3 危机 / 安全场景（P0，合规风险）

| 场景 | 问题 |
|------|------|
| 不想活了 / 活着没意思 | 仍套材料模板 + 催留资 |
| 老公打我 / 孩子被侵犯 | 无安全指引，催留资 |
| 现在在被打 | 未识别紧急性 |

Round 3 明确标为 **unsafe**。

### 2.4 专项 FAQ 缺失（P1）

- **收费**：「多少钱」常不答；「免费咨询吗」反而较好
- **地址**： rarely 给具体地址/区域
- **程序**：诉讼时效、强制执行、管辖 — 几乎不触及关键词
- **刑事追问**：「会不会坐牢」「家属能做什么」— 无实质法律要点

### 2.5 留资策略失衡（P1）

- 「不想留电话」「太晚了不要打」「别推销」→ 口头理解后仍要联系方式
- 已留电话后部分场景仍重复索要
- 「滚」类辱骂 — 收尾降级较好（少数通过）

### 2.6 LLM 未解决核心问题（R3）

8765（no-llm）vs 8766（LLM）对比 7 组：

- 「收费+地址」：**100% 相同**
- 诉讼时效、情绪危机、家暴：**两者均未实质改进**
- 刑事：LLM 略多「先别着急」，仍催留资

### 2.7 已验证能力（OK）

- **50 路并发**：151 轮，0 错误，~50s（R3）
- **API 健壮性**：空消息 400、XSS/SQL 样例不崩溃、超长文本 OK
- **会话隔离**：不同 session 不串案
- **首轮识别**：常见劳动/刑事/消费案由大体可用
- **留资确认**：首次手机号登记确认话术可用

---

## 3. Cursor 三轮 verdict 分布

| 轮次 | ok | repetitive | mismatch | missed_contact | unsafe | too_generic |
|------|-----|------------|----------|----------------|--------|-------------|
| R1 | 29 | 11 | 15 | 2 | 0 | 0 |
| R2 | 167 | 65 | 14 | 3 | 0 | 2 |
| R3 | 244 | 41 | 1 | 3 | 2 | 0 |

---

## 4. 另一位 AI 测试特点

`comprehensive_test.py` 覆盖：

- 案由明确（labor/criminal/family/…）
- 短句追问、地址收费、法律援助
- 辱骂退订、高风险刑事/强拆/医疗
- 拒绝留电话、已留联系方式
- 并发探针

`deep_analysis.py` 额外发现：

- 回复前缀高度集中（模板化严重）
- 按 category 统计 mismatch 分布
- 留资率与案由识别交叉分析

（具体数字请直接解析 `other-ai/test_report_20260622_092303.jsonl`）

---

## 5. 修复优先级（合并建议）

| 优先级 | 动作 |
|--------|------|
| **P0** | crisis intent：自伤/家暴/性侵 → 暂停留资 + 安全/热线指引 |
| **P0** | 多轮相似度 guard（>82% 强制换子模板） |
| **P0** | topic reset：识别「换成/算了说/另外」切换案由 |
| **P1** | 程序 FAQ：时效、执行、管辖、鉴定 |
| **P1** | opt-out 留资：拒电话/拒推销/夜间不要打 |
| **P1** | 过滤「是否报警」在劳动/家事/医疗中的滥用 |
| **P2** | burst 合并：5 秒内多条碎片消息合并理解 |
| **P2** | LLM 仅用于 crisis/程序/复杂追问 |

---

## 6. JSONL 字段说明

```json
{
  "visitor_text": "访客原文",
  "assistant_reply": "助手可见回复",
  "verdict": "ok | mismatch | repetitive | unsafe | missed_contact | too_generic",
  "reason": "评判原因",
  "expected_behavior": "期望行为"
}
```

Round 2/3 另有 `category`、`persona`、`suite` 等字段。

---

## 7. 建议 ChatGPT 分析任务

1. 对全部 JSONL 做 verdict 聚合，找出 **跨 Round 重复失败** 的 persona
2. 对 `assistant_reply` 做聚类，列出 **Top 10 模板骨架**
3. 比较 Cursor vs 另一位 AI 的 **失败用例交集**
4. 输出 **可执行的 regression test list**（JSON）供开发回归
5. 按业务风险排序：**unsafe > missed_contact > mismatch > repetitive**
