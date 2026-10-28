# 模型接入与运行

本 skill 现在提供通用模型运行器；新增模型优先读取 [适配器协议](adapters.md)。下面六模型只是此前配置实例，不限制待测模型或金标模型。使用项目内已有适配器或依照官方当前接口建立适配；接口版本、权重版本和授权须当次核验。

| 模型 | 此前成功配置 | 输出适配 |
|---|---|---|
| DeepSeek-OCR | API，基线输出上限 4096 | choices/message/content；finish_reason=length 是截断 |
| MinerU 官网 API | vlm，用户要求按 2.5 Pro 暂记；后端版本未核实 | ZIP 内 content_list 的全部 table_body |
| PaddleOCR-VL-1.5 | 官方 API | JSONL 内 layoutParsingResults 的 table block_content |
| UniTable | M2 MPS FP32 | 结构/单元格/文字阶段按官方流程组合 HTML |
| TRivia-3B | MPS FP16、SDPA、max_pixels=1048576 | 官方 OTSL 转 HTML；记录实际视觉网格 |
| dots.ocr | MPS BF16、max_pixels=1048576 | 兼容直接 HTML 和布局 JSON 中 table 项 |

FP16/FP32/BF16 是运算精度；1MP 指预处理像素上限约 104 万，不改原 PNG。三模型在 M2 16GB 上串行，每样本进程超时 900 秒。TRivia 全尺寸曾内存不足；1MP 配置应整批统一跑，不能与旧全尺寸结果混合。dots 的 FP16 曾输出重复感叹号，进程正常退出不代表 OCR 成功；保留失败尝试，BF16 结果另存。

先三张验证完整表格、结束原因、token 上限与语义输出，再扩到剩余样本。官方配置要求变化时记录变更。禁止关闭内存保护来伪装部署成功。

每次运行记录 sample_id、image_sha256、model/revision、config/config_sha256、run_id、raw_response_path、html、status、submitted_at、observed_complete_at、request_seconds、generation_seconds、wall_seconds_including_load、actual_image_size、output_tokens、usage、confirmed_cost。

已有任务 ID 先轮询，不重复上传；重试另写 attempt，明确是否可能已计费。凭据只从当前环境变量或指定安全存储读取。新服务注册/充值不属于本 skill 的默认授权。

API 请求耗时、排队加轮询耗时、本地纯推理耗时不能直接排速度榜；未采集的历史耗时、显存和费用写缺失，不推测。DeepSeek 单张提高到 7000 的补充实验不替换 4096 统一基线。
