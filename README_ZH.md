# Paper Flow

[简体中文](README_ZH.md) | [English](README.md)

<img src="branding/paperflow.svg" alt="Paper Flow" width="96">

Paper Flow 是一个本地优先的 Windows arXiv 论文推荐应用。它从你的本地 PDF 论文库和显式反馈中学习兴趣，用轻量本地召回与 LLM 语义筛选推荐论文。

当前版本：**v0.0.0 pre-release**

## 核心能力

- 按 arXiv 发布时间发现论文，候选不足时自动翻页并扩大检索范围。
- “感兴趣 / 还行 / 不感兴趣”只记录偏好，与打开 PDF、论文聊天完全解耦。
- 使用 LLM 生成细粒度兴趣方向并合并近义标签，不再把 `cs.CV` 等大类当作兴趣画像。
- 支持自由增删高权重的偏好与回避方向，以及对历史推荐进行自然语言检索。
- 独立的 Chat with Paper 窗口支持拖动、缩放、最小化、历史记录和自由追问。
- 语义筛选、推荐总结、兴趣画像、论文聊天可分别配置模型。
- 显示 arXiv 请求、筛选、总结、保存等真实进度，支持中英文和深色模式。
- PDF 解析、推荐文案、兴趣画像和聊天历史均在本机缓存。

推荐系统、模型边界、主题合并、缓存与隐私策略详见[技术说明](docs/TECHNICAL.md)。

## Windows 安装

### 安装程序

1. 从 Releases 下载 `PaperFlow-Setup.exe`。
2. 运行安装器并启动 Paper Flow。
3. 选择本地 PDF 文件夹，填写兼容 OpenAI Chat Completions 的 API Key、Base URL 和模型名称。

安装器按当前用户安装，不需要管理员权限，并会在需要时准备 Microsoft Edge WebView2 Runtime。卸载不会删除 `%LOCALAPPDATA%\Paper Flow` 中的个人数据库。

> 当前预发布版本尚未进行商业代码签名，Windows SmartScreen 可能显示“未知发布者”。

### 便携版

解压完整的 `PaperFlow-portable.zip` 后运行 `PaperFlow.exe`。不要单独复制 EXE；相邻的 `_internal` 文件夹包含运行组件。

系统要求：64 位 Windows 10/11、可访问 arXiv 与所配置 LLM API 的网络，以及一个本地 PDF 论文文件夹。

## 首次配置

基础设置包括本地论文库和 LLM API Key。高级设置可以配置下载目录、arXiv 分类、推荐批次数量、回溯天数、API Base URL、界面语言以及四类功能模型。

旧版本的单模型配置会自动继承到四个模型槽位；模型名称必须由当前 Base URL 实际支持。推荐阶段只使用 arXiv metadata，只有用户在论文聊天中发送问题后才会按需处理全文。

## 从源码运行

需要 Python 3.13 和 [uv](https://docs.astral.sh/uv/)。

```powershell
git clone https://github.com/kylin0421/paperflow.git
cd paperflow
uv sync --group dev
uv run paperflow-desktop
```

浏览器调试模式：

```powershell
uv run paperflow --host 127.0.0.1 --port 8765
```

## 构建 Windows 发布包

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

主要输出：

```text
dist\PaperFlow\PaperFlow.exe
dist\PaperFlow-portable.zip
dist\installer\PaperFlow-Setup.exe
```

测试：`uv run pytest`

完整的开发、打包和发布检查见[开发指南](docs/DEVELOPMENT.md)。

## 数据与隐私

- 数据库位于 `%LOCALAPPDATA%\Paper Flow\state.db`，API Key、反馈、历史和设置均保存在本机。
- 初始兴趣画像会向用户配置的 LLM 发送最多 12 篇本地 PDF 的截断开头；结果会缓存并在后台按变化更新。
- 论文全文只在用户主动发送聊天问题时处理；打开 PDF 或切换聊天历史不会调用 LLM，也不会改变兴趣反馈。

更完整的数据边界见[技术说明：数据、缓存与隐私](docs/TECHNICAL.md#数据缓存与隐私)。

## 文档

- [技术说明：推荐架构、LLM、兴趣画像与隐私](docs/TECHNICAL.md)
- [开发指南：运行、构建、发布检查与路线图](docs/DEVELOPMENT.md)
- [更新记录](CHANGELOG.md)

## 项目来源

Paper Flow 基于 [TideDra/zotero-arxiv-daily](https://github.com/TideDra/zotero-arxiv-daily) 开发。当前版本已移除 Zotero、邮件推送、bioRxiv/medRxiv 和旧定时工作流，重构为本地桌面交互应用。

## License

AGPL-3.0-or-later，详见 [LICENSE](LICENSE)。
