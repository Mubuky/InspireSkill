---
name: inspire
description: "Execution-first Inspire platform playbook for agents driving the inspire CLI as a black-box tool, with on-demand references for platform workflows."
---

# Inspire Skill

把 `inspire` CLI 当黑盒工具使用。不要读 CLI 源码来推断平台状态；状态、事件、日志、资源余量全部通过命令实时查询。

本文是入口和路由层：它告诉 Agent 先查什么、加载哪份 reference、哪些事实必须实时验证。具体平台语义放在 reference 中；命令是否存在、参数叫什么、默认值是什么，永远以 CLI help 为准。

## 1. 运维约束

| 主题 | 约束 |
| --- | --- |
| 输出观察面 | Agent 默认使用人类格式。人类输出更短，隐藏低价值 raw ID，适合直接决策。`--json` 是脚本接口，只在写脚本、接 `jq` 或必须消费结构化字段时使用。 |
| 代理配置 | 代理通过 `inspire account add`、账号级 config、`inspire config show` 和 `inspire config check` 管理。任务命令直接写 `inspire <cmd>`，CLI 会读取持久配置。 |
| 项目路径 | 项目远端路径只通过仓库级 `[path_aliases]` 表达。`inspire init --discover` 会写入 `me`、`public`、`global-me` 和按存储池区分的 alias；`notebook exec` / `shell` 默认用 `me`，临时切目录用 `--cwd me:<subdir>`，新增持久 alias 用 `inspire notebook set-path ... as <alias>`。 |
| 实时事实源 | `job list`、`notebook list`、`resources specs` / `list` / `nodes` 等状态查询以平台实时结果为准。本地 cache 只能存放 SSH 会话、事件副本等非权威辅助信息。 |
| 资源申请 | 先查实时空余，再按真实需求申请。不要因为模型保守而主动缩小规模；只有调度语义、项目配额或实时空余明确不足时才降档。 |
| 默认 workspace | 默认只主动使用 `CPU 资源空间` 和 `分布式训练空间`。其它 workspace 需要仓库级 `INSPIRE.md` 或用户明确指定。 |
| 优先级 | `--priority` 接受 1 到 10。1 到 3 是低优先级，4 是普通优先级，5 到 10 是高优先级。需要稳定运行时传 5 或更高，并用 `inspire job status <name>` 核对人类输出中的优先级。 |
| 排错入口 | 任务 PENDING、CREATING 过久或 FAILED 原因不明时，第一步查 `inspire <res> events <name>`。不要凭猜测重试或重提。 |
| 健康度观察 | 任务已启动但吞吐、显存、CPU、内存或网络状态不明时，查 `inspire notebook|job|hpc|serving metrics <name>`。`events` 看调度和生命周期原因；`metrics` 看资源利用率和多 pod 是否均衡。 |
| 清理 | 终态且不再需要的资源用 `<res> delete <name> --yes` 清理；running 先 stop。不确定是否仍有人使用时跳过。 |
| 大操作 | 共享盘大规模 `mv`、`cp`、`rm` 前先看文件量和大小分布。超过 20 分钟的远程操作使用后台任务 + sentinel 文件，不要让 `notebook exec` 长时间同步挂住。 |

## 2. CLI 命令查询入口

命令列表、子命令功能和参数说明以 CLI help 为准，不在 SKILL 或 references 中维护硬编码清单。需要确认某个操作时，先查 help，再执行实时查询或提交。不要把旧文档、记忆或历史示例当作命令存在性的事实来源。

```bash
inspire --help
inspire <command-group> --help
inspire <command-group> <subcommand> --help
```

在本仓库源码 checkout 内验证 CLI 行为时，用：

```bash
cd cli
uv run inspire --help
uv run inspire notebook --help
uv run inspire hpc create --help
```

`inspire --help` 的 `Commands` 区给出当前版本真实命令组；`inspire <command-group> --help` 给出该组所有子命令；`inspire <command-group> <subcommand> --help` 给出参数、默认值、必填项和注意事项。

执行顺序：

1. 用 help 确认命令和参数。
2. 加载一份最相关的 reference，理解平台语义和坑位。
3. 如果需要选择 workspace、compute group、quota 或远端路径，额外加载 [references/resources-and-paths.md](references/resources-and-paths.md)。
4. 执行前查实时状态；失败或卡住先看 events；已运行但健康度不明时看 metrics。

## 3. 按需加载索引

每次优先只加载一份业务 reference；任务跨边界时再加载第二份。reference 之间按下表分工，不互相维护完整命令清单。

| 任务判断 | 首选 reference | 本文档负责 | 不负责，转交 |
| --- | --- | --- | --- |
| 选择 workspace、compute group、quota、项目配额、存储池、path alias 或解释路径不可见 | [references/resources-and-paths.md](references/resources-and-paths.md) | 资源和路径概念、`--quota` 三元组、挂载隔离、项目 / 用户元数据入口 | notebook / job 的生命周期操作 |
| 创建、连接、执行、传文件、诊断、暴露 notebook 容器端口，或处理 SSH bootstrap | [references/notebook.md](references/notebook.md) | notebook 运行时语义、`shell` / `exec` / `scp`、HTTPS proxy、events / metrics、大文件操作、基底 notebook 准备 | 镜像 registry 语义转交 image；资源选择转交 resources |
| 提交或排查 GPU job、HPC、Ray、serving | [references/compute-workloads.md](references/compute-workloads.md) | 训练 / 计算任务的运行模型、优先级、事件、指标、异常对照 | 远端路径基础转交 resources；镜像生命周期转交 image |
| 一个项目要从环境准备、数据处理推进到训练 | [references/workflows.md](references/workflows.md) | 跨阶段编排、检查点、什么时候从 notebook 切到 HPC / Ray / job | 单命令参数和完整领域细节 |
| 浏览、注册、保存、设置默认或清理镜像 | [references/image-management.md](references/image-management.md) | 镜像来源、可见性、READY 状态、默认镜像配置、save 与 register 的选择 | notebook 如何安装依赖转交 notebook |
| 浏览模型仓库，判断 model registry 和 serving 的关系 | [references/model.md](references/model.md) | 模型仓库只读边界、版本浏览、和 serving 的职责拆分 | serving 生命周期转交 compute-workloads |
| 安装、更新、账号、项目初始化、代理 setup | [references/setup/install-and-config.md](references/setup/install-and-config.md)、[references/setup/proxy-setup.md](references/setup/proxy-setup.md) | 本机安装、账号 config、项目 `.inspire/config.toml`、代理配置 | 平台任务运行细节 |
| 需要维护 CLI 封装或对照平台 API | [references/dev/openapi.md](references/dev/openapi.md)、[references/dev/browser-api.md](references/dev/browser-api.md) | API 认证、端点、Browser API / OpenAPI 边界 | 日常 Agent 执行工作流 |

## 4. 项目上下文

仓库根可用 `INSPIRE.md` 记录非配置性上下文，建议包含：

- `Default Image`
- `Path Conventions`
- `Public Directory Layout`
- `Existing Notebooks`
- `Ongoing Jobs`

不要把账号配置、密码、代理密钥或 `.inspire/config.toml` 内容复制进 `INSPIRE.md`。配置由 CLI 合并和展示。
