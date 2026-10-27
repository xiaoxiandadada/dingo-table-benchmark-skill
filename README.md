# Dingo Table Benchmark Skill

从问题表定位、固定分辨率裁剪、Astra 候选金标与复核，到六模型评测、逐格错误标注和飞书图片对照。

入口：[SKILL.md](SKILL.md)。本仓库是可复用流程和工具包，不包含业务原图、密钥、模型权重，也不是六平台一键运行服务。

将本仓库克隆至 `~/.codex/skills/dingo-table-benchmark` 后，可使用 `$dingo-table-benchmark`。如该目录已存在，先检查已有版本，勿直接覆盖。Python 工具依赖见 `requirements.txt`；WeasyPrint 另需系统 Pango/字体环境。

历史结果见 [指标说明](references/evaluation-and-results.md) 和 [结果快照](references/result-snapshot.json)。快照来自 30 张业务困难表的固定基线；不是官方榜单，计时口径不同，金标仍有待核对项。
