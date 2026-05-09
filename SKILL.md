---
name: inspire
description: "Execution-first Inspire platform playbook for agents driving the inspire CLI as a black-box tool, with on-demand references for platform workflows."
---

# Inspire Skill

把 `inspire` CLI 当黑盒工具使用。不要读 CLI 源码来推断平台状态；状态、事件、日志、资源余量全部通过命令实时查询。

本文是入口和路由层：它告诉 Agent 先查什么、加载哪份 reference、哪些事实必须实时验证。具体平台语义放在 reference 中；命令是否存在、参数叫什么、默认值是什么，永远以 CLI help 为准。

## 1. 使用流程

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

每次任务按这个顺序走：

1. 用 help 确认命令和参数。
2. 加载一份最相关的 reference。
3. 任务跨边界时，再加载第二份 reference。
4. 执行前用 CLI 实时查询确认平台状态。

## 2. 按需加载索引

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

## 3. 项目上下文

仓库根可用 `INSPIRE.md` 记录非配置性上下文，建议包含：

- `Default Image`
- `Path Conventions`
- `Public Directory Layout`
- `Existing Notebooks`
- `Ongoing Jobs`

不要把账号配置、密码、代理密钥或 `.inspire/config.toml` 内容复制进 `INSPIRE.md`。配置由 CLI 合并和展示。
