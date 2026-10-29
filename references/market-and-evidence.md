# 为什么选择这些场景？

桌面研究更新于 **2026-10-30**。这是公开资料支持下的产品取舍，不是用户访谈、临床验证或市场适配结论。下面把资料中的现象与本项目的设计推断分开。

| 资料与可支持的事实 | PetLife 的设计选择（本项目推断） | 适用边界 |
| --- | --- | --- |
| [毕马威：2025年中国宠物行业市场报告](https://kpmg.com/cn/zh/insights/2025/06/2025-china-pet-industry-market-report.html)；[同机构宠物消费分析](https://kpmg.com/cn/zh/media/press-releases/2025/11/pet-economy-and-hospitality-industry.html)描述陪伴价值、精细消费与对透明信息的关注 | 用实付单价、包装规格和明确标签整理账本；生活月报既可读也有数字来源 | 不做品牌健康排行榜。综合宠物经济、城镇犬猫消费和预测数据口径不同，本项目不拼接成增长图 |
| [艾媒咨询：2026年中国宠物行业发展趋势与消费者洞察报告](https://www.iimedia.cn/c1086/117998.html)列出寄养照顾、服务兑现和收费透明相关问题 | 把“承诺怎么照顾”和“照顾者报告做了什么”分开；交接单、任务、报告人和冲突保留来源 | 可读取的公开摘要未充分呈现抽样细节；不把调查百分比推广为所有养宠人的比例，也不据此声称能保证托管质量 |
| [FDA：Proper Storage of Pet Food & Treats](https://www.fda.gov/animal-veterinary/animal-health-literacy/proper-storage-pet-food-treats)强调保存包装/批号/日期，储存状况也很重要 | 记录批号、开封信息、标签日期；在同一产品内提供日期约束下的用量规划，并显示排除原因 | 日期没过不等于安全；没有自动查询召回，不凭开封日推算统一保存天数 |
| [AAHA：Evaluating the Healthy Senior Pet](https://www.aaha.org/resources/2023-aaha-senior-care-guidelines-for-dogs-and-cats/evaluating-the-healthy-senior-pet/)强调病史、日常行为及当前治疗信息对评估的作用 | 整理观察时间线、现有食物和治疗说明，保留缺失与待确认内容 | 来源为老年犬猫照顾指南；用于支持记录整理思路，不外推成所有年龄宠物的诊断流程 |
| [AAFCO：Reading Labels](https://aafco.org/consumers/understanding-pet-food/reading-labels/)和 [WSAVA：Global Nutrition Guidelines](https://wsava.org/global-guidelines/global-nutrition-guidelines/)区分标签事实与个体化营养评估 | 用明确单位做算术，使用主人已有用量进行库存与打包计算 | 单位热量价格不表示营养适合程度，不据体重自行开食谱或调整治疗饮食 |

## 为什么适合做成 Agent Skill

这些任务经常重复，而且横跨图片、短句、日期、数量和不同照顾者。宿主 Agent 处理语言/图片和任务判断；Skill 提供按需加载的工作方法、稳定记录格式与可执行工具。下次调用能读取同一本本地记录，而不必由主人重新口述全部信息。

普通聊天也能在用户明确要求、允许使用本地文件和工具的情况下做这些。安装的价值是把规则、记录与工具预先封装，不是给宿主增加一个新模型，也不是证明它“更聪明”。相同 ID 的小票重放、陈旧文件拒写、批次日期缺口与打卡冲突可通过仓库示例复现；没有宣称识图正确率、节省时长或真实留存提升。

## 本轮主动不做的事

没有数据支持的个性化“健康分”、自动诊断/剂量、无来源的喂养建议、把消费高低当作爱宠程度、云端提醒和自动采购都不是当前能力。后续改进优先收集脱敏真实任务中的失败例子，验证字段负担和输出可用性，再决定是否扩展。
