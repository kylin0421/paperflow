# Paper Flow 开发指南

[返回中文 README](../README.md) | [English](DEVELOPMENT_EN.md)

## 环境要求

- 64 位 Windows 10 或 Windows 11
- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- 构建安装器时需要 Inno Setup；运行构建脚本时可自动获取 WebView2 Bootstrapper

## 从源码运行

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

默认桌面数据目录：

```text
%LOCALAPPDATA%\Paper Flow
```

## 检查与测试

```powershell
uv run pytest
uv run ruff check src tests
python -m compileall src tests
```

当前测试覆盖设置迁移、模型路由、推荐与画像缓存、聊天持久化、API、静态页面和原生窗口行为。

## Windows 构建

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

构建脚本会：

1. 生成确定性的 Paper Flow 图标。
2. 同步精简后的运行与构建依赖。
3. 使用 PyInstaller 生成目录版应用。
4. 收集 PyMuPDF layout/ONNX 等动态资源。
5. 下载并验证微软签名的 WebView2 Bootstrapper。
6. 生成便携 ZIP，并在 Inno Setup 可用时生成当前用户安装程序。

主要输出：

```text
dist\PaperFlow\PaperFlow.exe
dist\PaperFlow-portable.zip
dist\installer\PaperFlow-Setup.exe
```

便携版必须整体分发，不能只复制 `PaperFlow.exe`；`_internal` 包含 Python、WebView、PyMuPDF 和其他运行组件。

## GitHub Actions

- `.github/workflows/ci.yml`：运行测试和质量检查。
- `.github/workflows/windows-release.yml`：构建 Windows 发布产物。

发布前应确认 workflow 使用的 Python、uv、PyInstaller 和本地锁文件一致，并在干净环境中验证安装包和便携包。

## 发布检查

- [x] Windows 原生窗口，不打开外部浏览器。
- [x] 当前用户安装与卸载。
- [x] WebView2 Runtime 准备流程。
- [x] 单实例、原生文件夹选择与本地数据目录。
- [x] 中英文界面、README 与深色模式。
- [x] 旧 Zotero、邮件、bioRxiv/medRxiv 和训练依赖已移除。
- [x] PyMuPDF layout/ONNX 资源包含在目录版构建中。
- [x] 自动化测试和安装包构建脚本。
- [ ] Authenticode 代码签名。
- [ ] 在干净的 Windows 10 和 Windows 11 虚拟机中分别完成人工验收。

## 数据库兼容

新增设置应提供默认值，并考虑旧数据库缺少字段时的继承行为。当前四类模型配置在旧安装中会继承原 `model` 值。新增缓存签名时，应把实际影响结果的模型和输入状态纳入签名，以便设置变化后正确刷新。

不要把 API Key、真实用户数据库、构建目录、便携包或安装器临时下载文件提交到 Git。

## Android 独立版路线图

目标是无需桌面服务即可在手机运行的独立 APK：

1. 固化论文、反馈、兴趣、批次、统计和迁移的数据模型。
2. 使用 Kotlin 与 Jetpack Compose 复刻卡片流、历史、设置、统计、深色模式和双语 UI。
3. 使用 Android Keystore 保存 API Key，原生访问 arXiv 与兼容 OpenAI 的接口。
4. 用 Kotlin 重写轻量 TF-IDF 推荐，避免携带完整 Python 科学计算运行时。
5. 使用 Storage Access Framework 导入 PDF，并按 URI、大小、修改时间和内容指纹维护缓存。
6. 验证双栏、公式和扫描 PDF 的文本解析质量，必要时为解析模块引入专用方案。
7. 使用 WorkManager 处理每日更新、失败重试和通知。
8. 完成签名 APK/AAB、数据库升级、崩溃恢复和发布测试。

浏览、历史、统计和缓存内容应支持离线查看；arXiv 更新、LLM 总结和翻译仍需要网络。
