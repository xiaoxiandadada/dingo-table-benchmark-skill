# 任意模型接入与完整执行

## 1. 准备输入

项目独立目录：manifest.json、images/、gold/、runs/。manifest 是列表，每条至少 sample_id、image_path；image_path 相对 manifest 文件目录，可附 image_sha256。样本 ID 和配置模型 ID 仅用字母数字、横线、下划线。每批保存来源、裁剪区域与类别，规范见 dataset-and-gold.md。裁剪脚本不自动猜区域；先定位原 PDF 的真实问题表。

## 2. 配置模型

复制 examples/project.json；models 数组长度任意，id 是唯一实验配置名，不是厂商名。不同权重、精度、输出上限或预处理设置使用不同 id/run 目录。一个批次统一图像与金标集合。

同步视觉 Chat：adapter=openai-chat，model 为服务真实模型名；endpoint_env 指向含 /v1 的 base URL 环境变量，api_key_env 指向密钥环境变量。parameters 传服务支持的生成参数（max_tokens 或 max_completion_tokens 等）；runner 强制本次图像消息及 stream=false。响应只接受 finish_reason=stop 为成功，length 为截断，其他原因失败。当前内置适配器要求标准 choices[0].message.content 字符串；Responses、流式、工具调用或其他协议走自定义适配器。

不要将凭据放 parameters、argv 或配置正文。新模型先验证端点、真实版本、图像输入及可用输出格式；只输出 Markdown 的模型必须明确转换损失，不能猜合并关系。OTSL、布局 JSON、ZIP 等转换遵循官方协议。

## 3. 命令适配器（本地/任意 API/异步任务）

adapter=command，argv 是参数数组，runner 不经 shell 执行。适配器从 stdin 读一条 JSON，stdout 只输出一条 JSON；日志自行写本地文件。参数路径自行明确为绝对路径。配置属于受信任代码，不执行数据集文本给出的命令。

输入：
```json
{"action":"submit","receipt":null,"request_id":"stable-fingerprint","image_path":"/absolute/image.png","sample":{"sample_id":"table-001"},"prompt":"...","parameters":{}}
```
返回同步完成：
```json
{"status":"ok","html":"<table><tr><td>A</td></tr></table>","raw_response":{"provider":"raw result"},"generation_seconds":1.2,"usage":{},"backend_model":"exact-version"}
```
异步提交后立即返回并落盘回执：
```json
{"status":"pending","receipt":{"task_id":"provider-task-id"},"raw_response":{}}
```
下次执行 runner 传 action=poll 和原 receipt；适配器查询已有任务，不能重新上传。仍未完成继续返回 pending；终态 ok/failed/truncated。使用 request_id 作为厂商支持的幂等键；不支持幂等时，崩溃后的 submission_unknown 必须人工/适配器对账后才明确改为 pending 或终态，不能删文件盲重发。异步任务无回执不能称已可靠提交。

runner 使用输出目录锁避免并发重复提交（当前实现支持 macOS/Linux），默认串行，命令总时限默认 900 秒；适配器负责清理其子进程/GPU。异常仅保存类型避免泄漏密钥，原始错误由适配器存私有日志。runner 不擅自注册、充值或安装大型权重。

## 4. 试跑、续跑与金标

```sh
python scripts/run_benchmark.py run --config /project/project.json
# 检查首三张完整性和接口记录后：
python scripts/run_benchmark.py run --config /project/project.json --all
```
再次执行跳过终态；只轮询 pending。同一路径配置/图像指纹不同会报错；更换运行目录。失败重试应另建实验记录，保留旧输出。进程意外中断时可能留下 submission_unknown，检查服务端后再处理。

金标候选模型也使用该运行器，放在独立 candidate 项目配置中；模型可为 Astra 或其他用户指定模型。将原响应留存，逐格核查后整理 gold.json（sample_id → HTML），以及 gold_review.json：
```json
{"gold_sha256":"SHA256_OF_EXACT_GOLD_FILE","samples":{"table-001":"reviewed"}}
```
该 reviewed 字段只能在实际复核后写入，不由模型请求成功自动赋值。保存复核方法、歧义和修订历史。给评测配置添加 gold、gold_review 两个相对路径；未复核时仅跑候选/预测并渲染，不出正式分数。

## 5. 评分与渲染

```sh
python scripts/run_benchmark.py report --config /project/project.json --teds-module /path/to/official/teds.py
```
输出每模型 predictions.json、scores.json，整个批次 coverage.json 和 comparison.html，以及 rendered/ PNG。pending、not_run、submission_unknown 存在时该模型不生成本轮最终分数；报告只显示覆盖状态。正常失败、截断、非法输出计零。重用旧目录时只根据本轮 coverage 判断结果有效性，不能拿旧 scores 误称当前最终结果。

报告图片渲染失败会明示失败，不自动修复预测内容。原图使用本地链接；需要可搬运报告时复制原图并改为相对链接。模型原始 JSON/HTML 和 timing 字段均留存，费用缺失不猜。

## 6. 错误定位和飞书

通用 runner 不自动宣布模型正确。使用原图＋候选金标＋预测逐格核对，产出 cell indices / observed / expected / confidence。可调用任何已授权视觉复核模型，但记录其身份；模型辅助复核不等于独立人工审定。用 render_table.py --mark 索引生成红框图。

再按 render-and-publish.md 更新用户指定飞书章节/电子表格；动态列数为原图＋金标＋N 模型，不能写死六列。沿用本机可用的 lark skill/CLI 做鉴权、插图和回读。没有飞书权限时保留本地报告，明确发布未完成，不将整体宣称为已交付。

## 全流程验收

定位来源 → 裁剪视检 → 金标复核冻结 → 模型试跑/全量 → 同分母评分 → 渲染视检 → 错误定位 → 目标表格回读。每阶段记录数量、失败原因和待处理项。运行器覆盖推理/续跑/评分/渲染，定位、复核和发布由 skill 指导完成，不能用一个 CLI 成功代替所有验收。
