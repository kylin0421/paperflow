# Paper Flow

[简体中文](README.md) | [English](README_EN.md)

<img src="branding/paperflow.svg" alt="Paper Flow" width="96">

Paper Flow 是一个本地优先的 Windows arXiv 论文推荐应用。它从你的本地 PDF 论文库建立初始兴趣，并根据“感兴趣 / 还行 / 不感兴趣”反馈持续调整推荐。

当前版本：**v0.0.0 pre-release**

## 主要功能

- 每日获取所选 arXiv 分类中的新论文，并显示 arXiv 发布时间。
- 初次推荐只使用标题、abstract、分类等 metadata，不下载或读取全文。
- “感兴趣 / 还行 / 不感兴趣”只记录偏好，不会打开 PDF、下载全文或调用 LLM，三种选择可以随时修改。
- 论文行为独立为“打开原 PDF”和“Chat with this paper”，不会暗中改变兴趣反馈。
- 论文聊天默认问题是“为我详细介绍这篇论文的方法”，也可以自由追问实验、公式、局限或任意感兴趣的细节。
- 论文聊天使用可拖动、缩放和最小化的独立原生窗口，左侧按最近活动显示持久化对话历史。
- 语义筛选、推荐总结、兴趣画像和论文聊天可以分别指定兼容当前 Base URL 的模型。
- 本地 PDF 解析结果持久缓存，只有文件新增、修改或删除时才更新。
- 已生成的 TL;DR、推荐原因与翻译会缓存，避免重复消耗 Token。
- 中文与 English 界面、摘要和推荐原因。
- 显示真实的 arXiv 请求、兴趣初筛、LLM 语义筛选、摘要生成和保存进度，并支持深色模式与推荐原因标签。
- 使用统计、每日活动热力图、LLM 细粒度研究主题分布和当前兴趣画像。
- 可以用关键词或自然语言描述检索推送历史，并查看完整推荐记录。
- 可以直接新增或删除任意偏好、回避方向；人工标签使用高于自动学习结果的排序权重。
- 数据、设置、API Key、反馈和历史均保存在本机 SQLite 中。

## Windows 安装

### 推荐方式：安装程序

1. 从 Release 下载 `PaperFlow-Setup.exe`。
2. 双击运行，选择是否创建桌面快捷方式。
3. 安装完成后启动 Paper Flow。
4. 首次启动选择本地 PDF 文件夹，并填写兼容 OpenAI Chat Completions 的 API Key、Base URL 和模型名称。

安装器会按系统语言显示简体中文或英文，按当前用户安装，不需要管理员权限，并会自动准备 Microsoft Edge WebView2 Runtime。卸载应用不会删除 `%LOCALAPPDATA%\Paper Flow` 中的个人数据库。

> v0.0.0 暂未进行商业代码签名。Windows SmartScreen 可能显示“未知发布者”。正式公开分发前建议为 EXE 和安装器增加 Authenticode 签名。

### 便携版

解压完整的 `PaperFlow-portable.zip`，运行其中的 `PaperFlow.exe`。不要只复制 EXE；旁边的 `_internal` 文件夹包含运行所需组件。

### 系统要求

- 64 位 Windows 10 或 Windows 11。
- 可访问 arXiv 和所配置 LLM API 的网络。
- 一个包含 PDF 论文的本地文件夹。

## 首次使用

基础设置只有两项必填：

1. **本地论文库**：扫描所选文件夹第一层的 `.pdf`，用于学习初始兴趣；不会修改原文件。
2. **LLM API Key**：用于 metadata TL;DR、语义兴趣画像、筛选、翻译及按需论文对话。

高级设置可以修改下载文件夹、arXiv 分类、每批数量、回溯天数、API Base URL、四类功能模型和语言。

Paper Flow 默认使用兼容 OpenAI Chat Completions 的接口。模型名称必须由所填写的 Base URL 实际支持；二者不匹配时，界面会显示 API 返回的错误并在可行时回退显示完整 abstract。旧版本只有一个“模型”设置，升级后四个模型槽位会先继承旧值，直到用户分别保存新配置。

### 细粒度模型配置

| 配置 | 实际职责 | 为什么共用或拆分 |
| --- | --- | --- |
| 语义筛选模型 | 对 arXiv 候选论文做兴趣概率判断和拒绝决策 | 与摘要生成是独立调用，可使用更擅长相关性判断的模型 |
| 推荐总结模型 | metadata TL;DR、推荐理由、细粒度主题标签，以及已有推荐文案翻译 | 这些内容共享同一套推荐文案与结构化输出链路 |
| 兴趣画像模型 | 后台总结本地论文、反馈和人工标签，生成规范化兴趣方向 | 独立缓存、独立后台刷新 |
| 论文聊天模型 | 基于全文的多轮论文问答 | 上下文最长、回答要求最高，适合单独选择模型 |

## 数据与隐私

桌面版数据库位置：

```text
%LOCALAPPDATA%\Paper Flow\state.db
```

- API Key 只保存在本机数据库，不会发送给项目作者。
- 为生成初始语义兴趣画像，最多会把 12 篇本地 PDF 的截断开头文本发送给用户配置的 LLM API；画像按论文库与反馈状态缓存，不会在每次打开统计页时重复生成。
- 只有用户主动打开“Chat with this paper”并发送问题时，才会下载、解析并把该论文的截断全文发送给配置的 LLM API。
- 论文聊天线程和消息历史保存在本机 SQLite；切换左侧历史不会调用 LLM。
- 初次推荐只发送 arXiv metadata。
- 切换语言时只发送已有摘要和推荐原因，不重新发送论文原文。
- “清除推荐记录”和“清除本地论文解析缓存”相互独立，均不会删除磁盘上的 PDF。

首次桌面启动时，如果发现旧开发版的 `~/.arxiv-daily/state.db`，会自动复制到新的数据目录；已有目标数据库时不会覆盖。

## 核心技术：混合论文推荐

Paper Flow 采用工业推荐系统常见的“候选召回 → 精细评分 → 结果重排”结构。Google 的推荐系统资料将其概括为 candidate generation、scoring 和 re-ranking 三阶段；YouTube 的公开论文也使用候选生成与排序分离的架构。Paper Flow 在本地优先、单用户、小数据和冷启动场景下做了轻量化适配，不需要训练神经网络或部署向量数据库。

1. **arXiv 分页候选生成**：按用户设置的 arXiv 大类和回溯时间获取最新论文。用户设置的是最终“推荐批次”，内部另用更大的“检索批次”。Paper Flow 每次从 arXiv 直接读取 200 条网络页，再以 `max(推荐批次 × 3, 60)` 条为一个 LLM 检索/重排块；通过阈值的论文不足时继续处理下一块，必要时直接请求 `offset=200/400/...` 的后续页，不重复下载前面的结果。只有最终批次已满或回溯窗口耗尽才停止。arXiv 大类只负责限定搜索空间，不再被当作用户研究主题。
2. **加权多兴趣召回**：使用标题与 abstract 的 TF-IDF n-gram 表示，分别保留多个兴趣原型，而不是把所有论文平均成一个容易被稀释的兴趣中心。“感兴趣”是强正反馈，“还行”是弱正反馈；“不感兴趣”和人工回避主题作为更强的负向原型。
3. **LLM 语义重排与拒绝**：只把本地召回后的小候选池及其 arXiv metadata 交给 LLM。LLM 会同时读取缓存的语义兴趣画像、最近真实正负反馈和最高权重的人工标签，再评估语义相关性。只有兴趣概率达到阈值且没有命中回避方向的论文才能进入最终批次；宁可返回少于设置数量的论文，也不会用低相关候选强行填满。API 失败或返回格式异常时自动退回本地排序。
4. **新鲜度与多样性重排**：新论文获得小幅时间加权；最终批次使用 Maximal Marginal Relevance（MMR）思想，在相关性与论文间差异之间取平衡，减少同一小方向的近重复论文占满整批。
5. **显式反馈闭环**：选择后论文才会从候选中排除；未选择论文可以再次出现。三档反馈会立即改变下一批的兴趣权重，但与打开 PDF、论文聊天等行为完全解耦。

### LLM 语义兴趣画像

统计页中的兴趣画像不使用原始 TF-IDF 高频词。LLM 会综合本地论文的截断开头、正负反馈和人工兴趣，输出一句画像总结以及 5–12 个完整、可解释的研究方向。结果会过滤 `et al`、`omitted picture`、`learning` 等论文解析或排版噪声，并复用与细粒度主题词表相同的规范化合并逻辑。

画像采用事件驱动的后台更新：程序启动、本地论文缓存变化、用户反馈、设置变化或人工标签变化时，会触发一个可合并的后台任务。统计页只读取 SQLite 缓存，不发起 LLM 请求，因此打开时不会等待模型响应。短时间内连续发生多次变化时只保留一次后续刷新，避免重复消耗 Token。

人工兴趣不经过自然语言指令解析。用户可以直接新增或删除完全自由的“偏好方向”和“回避方向”，这些标签以最高的 `2.5` 原型权重进入本地召回，高于“感兴趣”论文的 `1.8` 和“还行”论文的 `0.45`。

### 论文对话

“Chat with this paper”会打开独立原生窗口。该窗口可以像普通 Windows 应用一样拖动、缩放和最小化；左侧列出持久化的论文对话，右侧显示当前线程。发送第一个问题时才会按需下载并解析全文。默认问题“为我详细介绍这篇论文的方法”覆盖原来的详细 TL;DR 使用场景，但聊天 system prompt 保持通用：它根据用户的实际问题解释方法、实验、公式、假设、对比或局限，不强制固定摘要结构。点击聊天、切换历史或打开 PDF 都不会自动修改兴趣反馈。

### 推送历史与记忆检索

所有推送过的论文都可以在“历史与检索”中按时间查看。搜索会同时索引标题、abstract、metadata TL;DR、旧版本中已保存的详细 TL;DR 和 LLM 细粒度主题，支持关键词以及描述性的自然语言查询；搜索完全在本机执行。论文聊天历史则在独立聊天窗口左侧查看，两类历史都不会发送给外部搜索服务。

### LLM 细粒度主题词表

统计页的“分类分布”来自 LLM 根据标题和 abstract 生成的 1–3 个细粒度研究主题，例如 `self-supervised vision foundation models`、`test-time adaptation for vision foundation models`，而不是 `cs.CV`、`cs.LG` 等 arXiv 大类。

为避免主题标签无限增长，Paper Flow 维护一个增量式规范词表：

- 每次生成标签时把现有高频词表提供给 LLM，要求语义等价时复用已有标签，仅为真正不同的研究问题创建新标签。
- LLM 输出后再进行本地规范化，合并大小写、标点、连字符、单复数和词序差异，并限制每篇最多三个主题。
- 主题生成与普通 metadata TL;DR 共用一次请求，不读取或上传论文全文。

这一设计借鉴了科学论文的 LLM taxonomy 研究：先抽取能够区分论文的具体方面，再保持 taxonomy 的语义一致性；当前实现选择增量词表而非全量聚类，以适应本地应用不断加入新论文的场景。

设计参考：

- [Google Recommendation Systems Overview](https://developers.google.com/machine-learning/recommendation/overview/types)
- [Deep Neural Networks for YouTube Recommendations](https://research.google.com/pubs/archive/45530.pdf)
- [The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries](https://aclanthology.org/X98-1025.pdf)
- [Context-Aware Hierarchical Taxonomy Generation for Scientific Papers via LLM-Guided Multi-Aspect Clustering](https://aclanthology.org/2025.emnlp-main.788/)

这些方法在 Paper Flow 中是面向单用户论文流的工程化适配，并不声称复现上述商业系统的训练规模或完整模型。

## 从源码运行

需要 Python 3.13 和 [uv](https://docs.astral.sh/uv/)。

```powershell
git clone <repository-url> paperflow
cd paperflow
uv sync --group dev
uv run paperflow-desktop
```

调试浏览器版本：

```powershell
uv run paperflow --host 127.0.0.1 --port 8765
```

## 构建 Windows 发布包

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

脚本会：

1. 生成确定性的 Paper Flow 图标。
2. 同步精简后的运行与构建依赖。
3. 使用 PyInstaller 生成快速启动目录版。
4. 下载并验证微软签名的 WebView2 Bootstrapper。
5. 使用 Inno Setup 生成当前用户安装程序。

输出：

```text
dist\PaperFlow\PaperFlow.exe
dist\PaperFlow-portable.zip
dist\installer\PaperFlow-Setup.exe
```

测试：

```powershell
uv run pytest
```

## v0.0.0 发布检查

- [x] Windows 原生窗口，不打开外部浏览器。
- [x] 当前用户安装与卸载。
- [x] 自动安装 WebView2 运行时。
- [x] 单实例、原生文件夹选择与本地数据目录。
- [x] 中英文界面和深色模式。
- [x] 精简旧 Zotero、邮件、bioRxiv/medRxiv 和模型训练依赖。
- [x] 自动化测试和安装包构建脚本。
- [ ] Authenticode 代码签名。
- [ ] 在干净的 Windows 10 与 Windows 11 虚拟机中各完成一次人工验收。

## Android 独立 APK 计划

目标是手机上独立运行的 APK：推荐、SQLite、arXiv 请求、兴趣分析和 PDF 管理均在设备上执行；只有获取新论文和调用用户配置的 LLM API 时需要联网，不依赖桌面电脑或自建服务。

计划路线：

1. 固化论文、反馈、兴趣、批次、统计与数据库迁移的数据模型。
2. 使用 Kotlin + Jetpack Compose 复刻当前卡片流、设置、加载转场、统计面板、深色模式和双语 UI。
3. 使用 Android Keystore 保存 API Key，原生网络层直接访问 arXiv 和兼容 OpenAI 的 API。
4. 用 Kotlin 重写轻量 TF-IDF 推荐，避免携带 scikit-learn、SciPy 和完整 Python 运行时。
5. 使用 Storage Access Framework 导入 PDF，并通过 URI 权限、大小、修改时间与内容指纹维护缓存。
6. 评估 Android PDF 文本解析对双栏论文、公式和扫描件的质量；必要时只为解析模块引入 Chaquopy 或专用原生库。
7. 使用 WorkManager 处理每日更新、失败重试和通知，不运行常驻 localhost 服务。
8. 完成签名 APK/AAB、数据库升级、崩溃恢复和发布测试。

浏览、历史、统计和已缓存内容应支持离线查看；arXiv 更新、TL;DR 生成和翻译需要网络。

## 项目来源

Paper Flow 基于 [TideDra/zotero-arxiv-daily](https://github.com/TideDra/zotero-arxiv-daily) 开发。项目保留了原项目在 arXiv、LLM 与论文解析方面的启发与部分能力，但 v0.0.0 已移除 Zotero、邮件推送、bioRxiv/medRxiv 和旧 GitHub Actions 工作流，重构为本地桌面交互应用。

## License

AGPL-3.0-or-later，详见 [LICENSE](LICENSE)。
