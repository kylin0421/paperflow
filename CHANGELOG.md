# Changelog

## 0.0.0 - Unreleased

首次 Paper Flow 预发布版本。

### Added

- Windows 原生桌面窗口与当前用户安装程序。
- 本地 PDF 增量解析缓存、LLM 细粒度主题画像和多路混合召回。
- arXiv 分页候选检索、429 退避、语义筛选、批次补足与多样性重排。
- “很感兴趣 / 还行 / 不感兴趣”三档显式反馈，并与打开 PDF、论文对话行为解耦。
- 推荐记录的自然语言检索、完整历史浏览，以及自由增删的高权重人工偏好与回避标签。
- 独立的论文对话窗口：可拖动、缩放、最小化，支持左侧持久化会话历史和自由追问。
- 语义检索、推荐摘要、兴趣画像、论文对话四类独立模型配置，并兼容旧版单模型设置。
- 中英文界面与 README、Markdown 渲染、深色模式和细粒度实时进度提示。
- 使用统计、活动热力图、细粒度兴趣分布，以及后台自动刷新兴趣画像。
- 推荐记录、本地解析缓存、论文对话历史的独立管理。
- PyInstaller 资源收集规则，完整打包 PyMuPDF layout/ONNX 运行时资源。

### Changed

- 项目包名与产品名统一为 Paper Flow / `paperflow`。
- 默认桌面数据目录迁移到 `%LOCALAPPDATA%\Paper Flow`。
- 详细论文介绍并入通用的 Chat with Paper，默认问题为“为我详细介绍这篇论文的方法”。

### Removed

- Zotero 数据源与认证。
- 邮件生成和 SMTP 推送。
- bioRxiv 与 medRxiv 抓取。
- 旧 reranker、Hydra 配置和 GitHub 定时邮件工作流。
- Torch、Transformers、Sentence Transformers、PEFT 等未使用依赖。
