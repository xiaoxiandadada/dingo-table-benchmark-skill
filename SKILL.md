---
name: dingo-table-benchmark
description: 从 Dingo 表格问题记录构建可追溯单表数据集，通过可配置模型生成并复核 HTML/JSON 金标，接入任意提供可转换表格输出的 API 或本地 OCR 模型并制作错误定位和飞书图片对照。适用于表格识别评测，不用于整页文档解析排行榜。
---

# Dingo 单表 benchmark

先确认本次阶段：采集裁剪、金标、模型运行、评分或展示。复用已有合格产物，不因调用本 skill 自动启动全部 API 或发布数据。

## 工作顺序

1. 读取问题记录和已有 manifest；最终样本单位是具体表格而不是 PDF。以 PDF 哈希、页码、裁剪区域和图像哈希去重，关联全部问题 ID。无法定位、权限受限、文件缺失单列原因，不拿同篇其他表替代。
2. 按用户范围选择：困难集要求实际复杂结构；全量问题集不能擅自排除简单但确有错误的表。裁剪规则见 [采集与标注](references/dataset-and-gold.md)。
3. 原图生成后逐张检查完整性。使用 `scripts/crop_table.py` 固定分辨率渲染；不能用屏幕缩放后的截图冒充 300 DPI。
4. 用户指定且已授权的金标候选模型（可选 Astra）生成候选 HTML＋JSON，再对照原图检查首尾行、所有分段、空单元格、数字及合并关系。模型自我复查不是独立人工确认。冻结已复核版本后才评分。
5. 模型数量和名称均由配置决定，按 [适配器与全流程](references/adapters.md) 接入；历史六模型配置仅作 [运行参考](references/models-and-runs.md)，先 3 张、后全量；读取提交回执避免重复请求。本地内存受限时串行运行，输出上限或尺寸改变应成为独立配置。
6. 采用同一批冻结金标、同一规范化、同一分母评分。失败/截断计零，未完成与失败分开；参见 [指标和结果](references/evaluation-and-results.md)。
7. 原图、金标和预测分别渲染；用具体单元格索引标注错误，保留原模型文字。若需要飞书展示，按 [展示与发布](references/render-and-publish.md) 操作用户指定的现有表格。

## 可执行工具

依赖见 `requirements.txt`；用独立虚拟环境安装。

- `scripts/crop_table.py PDF PAGE X0 Y0 X1 Y1 OUTPUT.png`：页码从 1 开始，坐标为未旋转 PDF 点；输出 PNG 和可追溯 JSON。
- `scripts/render_table.py INPUT.html OUTPUT.png [--mark 0,4,8]`：HTML 原样单元格渲染，可用零基单元格索引加红框。检测空渲染并保留边界检查。
- `scripts/evaluate.py --gold GOLD.json --predictions RUN.json --teds-module /path/to/official/teds.py --output scores.json`：使用外部已核验的官方实现，不内置未经授权的第三方评分代码。

接口、路径和凭据由当前项目配置提供。不要复制历史会话中的密钥、私有地址、飞书 token、真实业务图像到 skill 或 Git 仓库。发布仓库和数据分别需要用户授权；已有运行授权不自动授权新付费平台。

## 完成判定

交付数量、成功数、失败数、待核对数必须可从文件清单复算。上传回执不是视觉验收：检查本地图片是否真有表格，并回读目标单元格核对样本和图片 token。清理可重建缓存，保留原始响应、配置、失败回执、金标版本和来源记录。

## 模型无关执行入口

先读 [适配器与全流程](references/adapters.md)。复制 `examples/project.json`，填入 manifest、任意数量模型及输出目录。`run_benchmark.py run --config project.json` 默认只跑三张；审核试跑后加 `--all`。再次执行会跳过已完成样本、轮询 pending 回执，不重发未知提交。`report` 阶段生成覆盖状态与图片对照，有冻结且已复核金标时可评分。

“任意模型”指可以通过兼容 Chat API 或自定义命令适配器接入；不承诺任意服务零配置可用。金标复核、问题定位和外部发布仍需执行相应步骤，不能将请求成功视为全流程已验收。

本次历史结果见 [结果快照](references/result-snapshot.json)；这是小规模业务困难集，不是官方榜单，也不能代表模型在所有表格上的平均能力。
