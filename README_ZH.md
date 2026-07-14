# Paper Flow

[简体中文](README_ZH.md) | [English](README.md)

<img src="branding/paperflow.svg" alt="Paper Flow" width="64">

Paper Flow 是一个隐私优先、本地运行的 arXiv 论文推荐器。它从本地 PDF 论文库、显式评分和用户自由编辑的兴趣中学习，结合本地混合召回、LLM 语义筛选与带证据的全文论文对话。

当前版本：**v0.1.0**

## 轻量 localhost 部署

这是依赖最少、跨平台的运行方式，不需要 Windows 桌面壳、WebView2 或 MinerU。

需要 Python 3.13 和 [uv](https://docs.astral.sh/uv/)：

```bash
git clone https://github.com/kylin0421/paperflow.git
cd paperflow
uv sync
uv run paperflow --host 127.0.0.1 --port 8765
```

打开 `http://127.0.0.1:8765`，选择包含 PDF 的本地论文文件夹，并填写兼容 OpenAI API 的 Key、Base URL 与模型名称。

## Windows 应用

从 [Releases](https://github.com/kylin0421/paperflow/releases) 下载 `PaperFlow-Setup.exe` 或 `PaperFlow-portable.zip`。便携版必须完整解压，不能只复制 `PaperFlow.exe`。

从源码启动桌面版：

```powershell
uv sync --extra desktop
uv run paperflow-desktop
```

v0.1.0 尚未进行商业代码签名，Windows SmartScreen 可能提示未知发布者。安装器按当前用户安装，不需要管理员权限，卸载不会自动删除个人数据库。

## v0.1.0 核心能力

- 用 LLM 生成细粒度兴趣方向并合并近义标签，不再把 arXiv 大类当作兴趣；偏好与回避方向可无限、自由增删。
- 词级/字符级混合召回、可选 embedding、反馈时间衰减、自动校准语义筛选、多兴趣配额、MMR 多样性，以及精准/均衡/探索三种模式。
- 持久化 arXiv 候选缓存，区分检索批次与最终推荐批次，未凑满时继续翻页，并对 429 持久退避。
- 记录每轮召回分数、LLM 拒绝理由、决策路径，并用真实反馈统计推荐命中率与空批次率。
- 自然语言历史检索、中英文界面、深色模式、细粒度进度和长任务取消。
- 独立论文对话窗口、持久历史、Markdown 渲染、分功能模型，以及带章节证据的长文问答。
- 可通过外部 `mineru-api` 使用 MinerU 3.x 结构化解析，失败时自动回退本地 PyMuPDF。
- 带版本的 SQLite 迁移、API Key 加密、连接测试和内置备份恢复。

“感兴趣 / 还行 / 不感兴趣”只改变偏好；打开原 PDF 和论文对话是独立行为，不会自动评分。

## 可选 MinerU

将 [MinerU](https://github.com/opendatalab/MinerU) 作为独立服务运行，然后在高级设置中填写地址（例如 `http://127.0.0.1:8000`）。Paper Flow 使用其结构化 Markdown 做长论文的完整章节选择与证据编号；默认轻量版不安装 MinerU，服务不可用时使用 PyMuPDF。

部署选择与设计细节见 [MinerU 与长 PDF 对话](docs/MINERU.md)。

## 隐私

SQLite 数据库保存在本地（Windows 应用为 `%LOCALAPPDATA%\Paper Flow\state.db`，localhost 默认为 `~/.paperflow/state.db`）。API Key 在 Windows 上使用 DPAPI，在其他系统使用本安装实例的加密密钥保护。推荐阶段只处理 arXiv metadata；仅当用户主动发送论文对话问题后才处理全文。设置中提供备份、恢复和缓存管理。

## 文档

- [技术架构](docs/TECHNICAL.md)
- [MinerU 与长 PDF 对话](docs/MINERU.md)
- [开发、打包与发布](docs/DEVELOPMENT.md)
- [更新记录](CHANGELOG.md)

## 项目来源与许可证

Paper Flow 基于 [TideDra/zotero-arxiv-daily](https://github.com/TideDra/zotero-arxiv-daily) 开发，已将 Zotero、邮件推送和定时工作流重构为本地交互应用。

许可证为 AGPL-3.0-or-later，详见 [LICENSE](LICENSE)。
