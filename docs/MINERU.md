# MinerU 与长 PDF 论文对话

[中文](MINERU.md) | [English](MINERU_EN.md) | [返回 README](../README_ZH.md)

## 本机托管运行时

Paper Flow 0.1.1 可以在本机安装和管理 [MinerU](https://github.com/opendatalab/MinerU)。用户不需要手动创建虚拟环境、选择端口、启动 `mineru-api` 或填写 API URL。

Windows 应用随包提供 `uv`。点击 **安装本机 MinerU** 后，Paper Flow 会：

1. 在 Paper Flow 数据目录创建由应用管理的 Python 3.12；
2. 创建隔离虚拟环境；
3. 安装固定版本的 `mineru[pipeline]`；
4. 验证安装，并记录版本和磁盘占用。

MinerU 及其模型是可选的按需下载，不会塞进 `PaperFlow.exe`。主应用继续使用 Python 3.13，轻量 PyMuPDF 解析器始终可用。从源码运行时使用 `PATH` 中的 `uv`。

## Worker 生命周期

托管 Worker 采用懒启动：完成安装后不会长期运行后台服务。首次需要解析论文或点击 **启动并测试** 时，Paper Flow 才会在未占用的本机回环端口启动 `mineru-api`。

- 端口和 URL 是内部实现细节，不需要用户配置；
- 多篇论文复用同一个 Worker，避免反复加载模型；
- Worker 被关闭或崩溃后，下次请求会自动重启；
- 切换模型来源会使用新环境重启 Worker；
- 停止、取消、退出 Paper Flow 和卸载都会终止子进程；
- 安装日志和 Worker 日志保存在托管运行时目录，便于诊断。

设置面板显示安装阶段、进度、MinerU/Python 版本、磁盘占用、Worker 状态和错误。**修复 / 更新** 会重新执行固定版本安装；**卸载** 只删除托管 MinerU 环境与模型。

## 运行模式与回退

高级设置提供两种部署方式：

- **本机托管**（默认）：Paper Flow 管理 Python 3.12 环境和 localhost Worker；
- **远程服务**：高级用户仍可填写独立部署的 MinerU 3.x API URL。

PDF 解析器行为保持明确：

- **自动**：本机 MinerU 已安装时优先使用，或使用配置好的远程服务；启动、健康检查、超时或解析失败后回退 PyMuPDF；
- **MinerU**：必须成功使用所选 MinerU 部署，错误直接显示；
- **PyMuPDF**：完全不启动或联系 MinerU。

Worker 启动超时和解析超时分别保存在 `mineru_worker_startup_seconds`、`mineru_timeout_seconds`。解析结果按论文 ID 与 PDF SHA-256 指纹缓存。

## 解析和上下文策略

Paper Flow 先检查 `GET /health`，再调用 MinerU 同步 `POST /file_parse`，要求输出 Markdown 和 content list。随后采用结构感知的上下文选择，而不是固定长度 RAG 切片：

- 短论文保留完整 Markdown 和章节地图；
- 长论文按真实标题切分；
- 根据问题选择完整章节，并加入相邻章节；
- 摘要、方法、目标函数、实验、结果、局限和结论是锚点候选；
- 所选证据标记为 `[S1]`、`[S2]` 等编号，供 Paper Chat 引用。

MinerU content list 会被缓存，为后续页码、表格和图片级证据预留；0.1.1 的上下文选择主要使用重建后的 Markdown。

## 隐私与资源占用

托管模式只绑定 `127.0.0.1`，PDF 不会离开本机。远程模式会把完整 PDF 发送给所配置的服务。可选环境与模型可能占用数 GB，首次解析还可能下载模型，因此安装前界面会明确请求确认。
