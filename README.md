# Model-agnostic Table Benchmark Skill

用同一套协议接入任意数量的表格解析模型，完成裁剪、候选金标与复核、批量推理、TEDS/S-TEDS、渲染、逐格错误标注和飞书对照。

- 内置 OpenAI-compatible Chat 视觉接口（同步、非流式）。
- 自定义命令适配器：可接本地模型、其他 HTTP API、异步上传/轮询服务。
- 按图像及配置指纹断点续跑；未知提交不自动重试，避免重复计费。
- 默认三张试跑；未完成任务不生成冒充最终结果的评分。

入口：[SKILL.md](SKILL.md)；完整运行方法：[适配器协议](references/adapters.md)；配置：[examples/project.json](examples/project.json)。适配器负责服务差异、输出格式转换；不是任意平台零配置部署器。

安装到 `~/.codex/skills/dingo-table-benchmark` 后用 `$dingo-table-benchmark` 调用。Python 依赖见 requirements.txt；渲染另需 Pango/字体。没有业务原图、凭据或权重。

历史六模型结果与局限保留在 [指标说明](references/evaluation-and-results.md) 和 [快照](references/result-snapshot.json)，不是新的通用模型排行榜。
