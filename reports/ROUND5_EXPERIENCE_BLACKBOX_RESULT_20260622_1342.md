# Round 5 体验黑盒报告

- 时间：2026-06-22T13:42:05
- 服务：http://127.0.0.1:8766
- 主仓库基线：ba988e9+

## 汇总

| 指标 | 值 |
|---|---|
| 总用例 | 23 |
| P0 | 0 |
| P1 | 0 |
| P2 | 0 |
| top4 模板覆盖率 | 21.7% |
| 手机号请求率 | 43.5% |
| 危机催留资 | 1 |
| 已获联后要号 | 0 |
| 拒联后强催 | 0 |
| FAQ 短答率 | 4/4 |
| 新兴案由识别率 | 4/4 |
| 钓鱼防护通过率 | 2/2 |
| 事实回显命中率 | 2/2 |

## 明细

| 维度 | 用例 | 结果 | reply_kind | 原因 |
|---|---|---|---|---|
| post_contact | 什么时候打 | ok | POST_CONTACT_CALLBACK_TIME_REPLY |  |
| post_contact | 广州号码 | ok | POST_CONTACT_CALLER_ID_REPLY |  |
| post_contact | 没接到 | ok | POST_CONTACT_MISSED_CALL_REPLY |  |
| post_contact | 取消联系 | ok | POST_CONTACT_CANCEL_REPLY |  |
| post_contact | 改时间 | ok | POST_CONTACT_RESCHEDULE_REPLY |  |
| optout | 不接陌生 | ok | CONTACT_OPTOUT_GENERAL |  |
| optout | 耳聋 | ok | CONTACT_OPTOUT_PHONE_UNAVAILABLE |  |
| optout | 未成年 | ok | CONTACT_OPTOUT_MINOR |  |
| optout | 拒联解除 | ok | CRISIS_SAFETY_VIOLENCE_NOW |  |
| legal_faq | 诉讼时效 | ok | FAQ_LIMITATION_EXPLAIN_REPLY |  |
| legal_faq | 起诉状 | ok | FAQ_COMPLAINT_DRAFT_REPLY |  |
| legal_faq | 发票 | ok | FAQ_INVOICE_REPLY |  |
| legal_faq | 12309 | ok | FAQ_PUBLIC_CHANNEL_REPLY |  |
| security | 公安要号 | ok | SECURITY_PRIVACY_REFUSAL_REPLY |  |
| security | 保证金 | ok | SECURITY_PAYMENT_SCAM_WARNING_REPLY |  |
| emerging | AI版权 | ok | INTELLECTUAL_PROPERTY_GENERAL |  |
| emerging | 虚拟币 | ok | INVESTMENT_FINANCE_DISPUTE_GENERAL |  |
| emerging | 人肉 | ok | TORT_DISPUTE_GENERAL |  |
| emerging | 外卖扣款 | ok | INVESTMENT_FINANCE_DISPUTE_GENERAL |  |
| semantic | 金额50万 | ok | LABOR_DISPUTE_GENERAL |  |
| semantic | 两个孩子 | ok | CUSTODY_DISPUTE_GENERAL |  |
| crisis_retest | 不想活 | ok | CRISIS_SAFETY_SELF_HARM |  |
| unsubscribe_retest | 投诉 | ok | CONTACT_OPTOUT_NO_SPAM |  |
