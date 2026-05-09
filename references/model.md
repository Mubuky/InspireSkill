# Model Registry

浏览模型仓库、查看模型版本，或判断 model registry 和 serving 的边界时，先查本手册。模型上传、模型注册、部署创建和 serving 运维不在这里展开；部署生命周期看 [compute-workloads.md](compute-workloads.md) 的 serving 部分。

命令是否存在、参数名和默认值以 CLI help 为准：

```bash
inspire model --help
inspire model <subcommand> --help
```

## 1. 定位与边界

`inspire model` 映射 Web UI 的 `/modelLibrary` 页面，是启智平台模型仓库的浏览入口。

- **纯 Browser API**（SSO session），无 OpenAPI 对应
- 所有当前命令均为**只读**，不包含上传、注册、修改或删除能力
- 模型上传 / 注册仍在 Web UI `/modelLibrary`

## 2. 与 `serving` 的关系

| 命令组 | 定位 | API |
| --- | --- | --- |
| `model` | 浏览模型仓库，选模型 | Browser API |
| `serving` | 部署模型为推理服务 | Browser API + OpenAPI |

流程通常是先在 model registry 找到目标模型，再通过 Web UI 或 OpenAPI 在 `/jobs/modelDeployment` 创建 serving 部署。`model` 是“找模型和看版本”，`serving` 是“消耗模型并管理服务”。

## 3. 操作判断

| 目标 | 入口 | 后续动作 |
| --- | --- | --- |
| 看当前 workspace 有哪些模型 | `model list` | 找到候选模型名后再看详情 |
| 看某个模型的元数据和版本摘要 | `model status <model-name>` | 确认存储路径、版本和可部署性 |
| 看历史版本 | `model versions <model-name>` | 选择要部署或复现的版本 |
| 创建或修改部署服务 | Web UI `/jobs/modelDeployment` 或 serving API | 转到 [compute-workloads.md](compute-workloads.md) |

```bash
inspire model list
inspire model list --workspace <WORKSPACE>
inspire model status <model-name>
inspire model versions <model-name>
```

## 4. 限制

- CLI 不覆盖模型上传或注册；模型首次入库必须通过 Web UI `/modelLibrary`。
- model registry 与 model deployment（`/jobs/modelDeployment`）是两个不同的平台模块；前者是仓库浏览，后者是生命周期管理。
- 日常默认看 human 输出；只有脚本消费字段或需要精确结构时才用 `--json`。
