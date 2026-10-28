# 采集和金标

## 样本选择与溯源

从 Dingo 的问题描述定位 PDF 内的具体表；区分“来源属于 Dingo”与“已确认对应这条问题”。公开同文献副本可作为替代来源，但记录替代关系及核验方法，不冒称字节相同。只下载清单文件，不下载整个 S3 桶。遇到 403、NoSuchBucket、超时分别记录，不能把权限问题统一写成文件不存在。

manifest 每条至少包含：sample_id、problem_ids、problem_categories、source_ref（私有清单中）、source_sha256、page_1based、page_rotation、bbox_pdf_points、coordinate_space、dpi、image_path、image_sha256、complexity_tags、selection_reason、verification_status、continuation_group。

困难结构包括跨行跨列合并、多层表头、分组行、弱线框、密集长表、跨页续表。允许多标签。排除纯普通 OCR 错字的规则只适用于困难集任务，不适用于用户要求的全量问题表。

## 裁剪

默认 300 DPI、RGB、PNG；表格外扩 2 PDF 点，若碰到正文手动缩小。保留全部表头、表体、边框和表内脚注；排除独立标题与页眉页脚。跨页按页分别保存并关联，不拼接、不补造表头。坐标以 PyMuPDF 未旋转页面空间为准；旋转页面必须记录并视检。像素尺寸应接近裁剪尺寸乘 DPI/72。不要锐化、补字或 AI 增强。

原则参考 OmniDocBench 的表格裁剪评测以及 PubTabNet、FinTabNet、PubTables-1M 的表格识别任务；300 DPI 是本项目设置，不宣称这些数据集都采用同一 DPI。CC-OCR 原图可能含表外内容，使用前逐图核验边界。

## 可配置模型候选与复核

候选金标模型由用户选择；用户指定时用 `gpt-6-astra`，请求必须真正包含原图，保存原始响应、模型标识、参数、finish_reason、时间与用量。提示应要求：只转录可见内容；输出所有表格分段；保留空格位与 rowspan/colspan；不能推算不可读数字；歧义单列。

建议 JSON：`{sample_id, html, tables, uncertainties, review_status, provenance}`。HTML 是评分源；JSON 保存溯源、复核证据和结构元信息，不另外维护易失同步的第二份正文。

按分段→行→列逐格对照原图，核对首尾行、右侧独立列、负号、小数、脚注及纵排阅读顺序。原始输出到整理后的 HTML 必须检查分段数、行数及首尾文本，曾出现整理时漏掉整个分段的情况。参考金标也可能错；不能仅凭与金标不同就标模型错误。

保留候选和复核后版本，歧义未解决就标 pending。版本改变时另存新冻结文件和哈希，重算所有模型并说明变化，不覆盖历史评分。图形连线、化学结构等不能用纯 HTML 表格充分表达，需另设任务或单列局限。
