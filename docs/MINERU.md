# MinerU 与长 PDF 论文对话

[中文](MINERU.md) | [English](MINERU_EN.md) | [返回 README](../README_ZH.md)

## 为什么是可选服务

[MinerU](https://github.com/opendatalab/MinerU) 专门重建科学 PDF 的阅读顺序、公式、表格、OCR 和多栏版面，对论文对话很有价值，但完整本地运行环境明显重于 Paper Flow，并有不同的 Windows/Python 限制。

因此 Paper Flow 把 MinerU 当作外部解析服务。轻量安装继续使用 Python 3.13 与 PyMuPDF；MinerU 可以在独立环境中采用其官方推荐的 Python 版本和加速设备。

## 连接方式

按 MinerU 上游文档安装并启动 `mineru-api`。常见本地服务地址为：

```text
http://127.0.0.1:8000
```

在 Paper Flow 高级设置中：

1. 将 **PDF 解析器** 设为 **自动**（MinerU 失败回退 PyMuPDF），或设为 **MinerU**（必须成功）；
2. 将 **MinerU API URL** 填为服务根地址；
3. 保存后在连接测试中点击 **测试 MinerU**。

Paper Flow 先请求 `GET /health`，再调用 MinerU 3.x 同步 `POST /file_parse`，要求输出 Markdown 和 content list。解析结果按论文 ID 与 PDF SHA-256 指纹缓存。

## 上下文策略

Paper Flow 不把论文机械切成固定长度碎片：

- 短论文保留完整 Markdown 和章节地图；
- 长论文按真实标题切分；
- 按问题相似度选择完整章节，并加入相邻章节维持论证连续性；
- 摘要、方法、目标函数、实验、结果、局限和结论都是锚点候选；
- 模型获得完整章节地图，以及标为 `[S1]`、`[S2]` 的所选证据；
- 回答被要求引用证据编号，聊天界面显示对应章节名。

这种结构优先方案面向“论文数量不算极大、但单篇很长且不规则”的场景，优先保证上下文连续和证据可检查，而不是追求向量数据库规模。

## 失败行为

- **自动**：健康检查、网络、超时或解析失败时回退本地 PyMuPDF；
- **MinerU**：错误直接显示，不静默切换解析器；
- **PyMuPDF**：完全不联系 MinerU。

MinerU 请求超时可通过 SQLite 设置 `mineru_timeout_seconds` 配置，默认 900 秒。相同且未变化的 PDF 会直接使用本地解析缓存，不重复调用解析器。

## 隐私

只有用户主动发送论文对话问题后，PDF 才会发送到配置的 MinerU 地址。本机 localhost 服务不会离开本机；如果配置远程 MinerU，远程运营方会收到 PDF，Paper Flow 无法约束其保留策略。
