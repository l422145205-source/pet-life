# 一户两猫，四件连续的小事

所有宠物、照顾者、商品、消费和观察均为合成资料。Markdown/JSON 为真实 Python 工具输出，未调用模型，不是 Agent 实测成绩。

从 [完整合成输入](../../assets/everyday.example.json) 出发：

1. **准备下周口粮**：[批次报告](stock.md) / [JSON](stock.json)。总量为7天的罐头，受到所录批次日期约束后出现1罐规划差额；不通过增加喂食消化临期库存。
2. **交给朋友照顾**：[交接打卡](care.md) / [JSON](care.json)。当天1个时段有相互冲突的报告，1个时段没有记录；两者分别处理。未来3天共12个时段只列计划。
3. **就诊前翻记录**：[观察摘要](visit.md) / [JSON](visit.json)。有3条已确认观察、1条待确认转述；中间空白日不补成连续症状。
4. **下一次记小票**：[跨调用重放](replay.md) / [JSON](replay.json)。209 → 221 → 221，第二次提交同一小票不增加支出。

狗狗版另见 [豆豆的散步/换水交接](dog/care.md)，输入为 [合成狗狗安排](../../assets/dog-walk.example.json)。给主人已有任务留打卡和协助请求，不自动制定遛弯时长。

仓库根目录运行 `python tools/reproduce.py --out work/demo` 可重新生成全部结果。打包量和原始记账流程见 [基础示例](../agent-example.md)。
