# 接入指南 / Onboarding

## 选择你的方式

| 方式 | 需要什么 | 如何开始 |
| --- | --- | --- |
| 独立 CLI | Python 3.9+、Git | clone 到任意目录，运行 `scripts/wiki.py` |
| 本地 Agent / IDE 助手 | 能读写文件；执行命令可选 | 打开 wiki，明确让它先读 `AGENTS.md` |
| Agent Skills 宿主 | 宿主支持加载 SKILL.md | 按该宿主文档安装此仓库，可选项目级安装 |
| 普通聊天窗口 | 你负责文件读写 | 粘贴协议与来源，审核并保存生成的 Markdown |
| 只读 / 手动维护 | Markdown 编辑器 | 不需要任何 Agent、模型或 Skill 系统 |

不要求 Pi、Claude Code、Codex、MCP 或 Obsidian。各工具自动发现配置文件的行为
不同：不能把“支持读取协议”宣传为“都能自动加载”。最通用入口是这段自然语言：

> 先阅读这个目录下的 AGENTS.md 和 wiki/index.md，遵循其中的维护协议。
> 帮我整理这份资料，保留来源，列出你的改动，未经确认不要推送。

## 安装与初始化

```bash
git clone https://github.com/feeeeling/llm-wiki-skill.git
python3 llm-wiki-skill/scripts/wiki.py init my-wiki
cd my-wiki
python3 scripts/wiki.py doctor
```

没有 pip 依赖。`init` 创建骨架和本地 Git 仓，但不 stage、commit、push，不要求
预先配置 Git 身份。目标必须为空，避免覆盖已有笔记。初始化失败时先检查已生成
文件，再选择新的空目录；不要直接删除已有资料。

Windows 可用 `python` 或 `py -3` 代替 `python3`。本地 Hook 需要 Git Bash/WSL
提供的 POSIX shell；纯 Python CLI 不依赖 Bash。尚未在你的设备上验证的宿主
必须先做小规模试用，不能根据 SKILL.md 的存在推断兼容性。

## 代码来源

```bash
python3 scripts/wiki.py register project --repo /path/to/code \
  --track src/ --track README.md --page wiki/concepts/project.md
```

生成：

- `sources/project.json`：可同步的 URL、跟踪范围、页面列表和版本基线。
- `.llm-wiki.local.json`：此设备的路径绑定，自动忽略，不放进 GitHub。

先做初次 ingest，再在 JSON 中填写实际核对的提交 SHA。空的 `compiled_rev`
会让 `doctor/check` 报告需要初次整理，这是预期，而不是自动把 HEAD 当已完成。

`track` 默认为整个仓库；可以重复 `--track` 限定范围，Git pathspec 支持通配符。
不支持以 `:` 开头的高级 pathspec。`pages` 暂为来源级映射，不会自动推导函数依赖。

```bash
python3 scripts/wiki.py check --all
python3 scripts/wiki.py status
python3 scripts/wiki.py hooks --source project
```

`check` 只对本地可访问来源进行比较，不 fetch 网络、不读取未提交改动、不调用模型。
判断基线始终是 `compiled_rev`；不会用最近一次 checkout/merge 的旧 SHA 替代它。
生成工单不等于语义更新已完成。

返回码：0 = 命令完成；1 = 配置/访问/初次整理等问题；加 `--fail-on-drift` 时，
2 = 存在未完成工单。`status` 只看已有队列，不能证明来源没有变化。

## GitHub 与第二台设备

在 GitHub 新建空的私有仓库。检查文件和 Git 身份，然后按 wiki 自带 README
的命令选择文件、提交、添加 remote、推送。不提供后台自动同步。

```bash
git clone https://github.com/YOU/YOUR_WIKI.git
cd YOUR_WIKI
python3 scripts/wiki.py bind project --repo /this/device/code
python3 scripts/wiki.py doctor
```

没有代码仓时也能阅读已有快照，但不可将其描述为已经和最新代码核对。
重新安装 Hook（可选）。GitHub 的权限不自动授权模型访问私有源。

## 旧版迁移

新版使用统一 Python CLI，旧 `.sh` 文件仅为兼容入口，需要同目录 `wiki.py`。
不要只复制新的 shell 包装脚本而漏掉 Python 文件。

已有知识库不要重跑 init。先备份/提交，手动更新 `scripts/` 的受管脚本，合并
新版协议，而不是覆盖整个 `AGENTS.md`。从新模板复制所需指南。
旧的 scalar + block-list YAML 来源可读取；复杂 YAML 请转成 JSON。
`compiled_rev` 和原有页面不能在迁移时重置。

老版本 Hook 可能安装在错误目录，或依赖旧 `--old` 参数。先核对实际
`git rev-parse --git-path hooks`，保留原文件备份并手动移除旧的 llm-wiki 片段，
再安装新 Hook。安装器会拒绝覆盖任何已有的非同一内容 Hook。

`--force` 和 `--old` 不再支持；前者可能覆盖配置，后者可能漏掉未整理过的变更。

## 当前限制

文件替换是原子的，同一版本的重复检测会复用工单；但没有覆盖 Agent 编辑的全局锁。
同一 wiki 的注册、绑定和人工维护请串行进行，不支持多个写入者无协调地并发修改。
代码检测只覆盖 Git 提交，不提供网页变化监控、未提交代码监控或事实真伪判定。
Windows CI 检查 Python CLI；POSIX Hook 执行测试在 Linux/macOS 跑，Windows Hook
仍需在实际 Git Bash/WSL 环境另行验证。

## 更新与反馈

Skill 更新不自动修改已有 wiki 的脚本或协议，避免破坏用户定制。按照上述迁移
步骤审核变更。复现问题时附 CLI 命令、Python/Git 版本、脱敏错误，不上传源代码
或 `.llm-wiki.local.json` 中的个人路径。
