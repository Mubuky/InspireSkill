# Model Registry

## 1. 定位与边界

`inspire model` 是启智平台模型仓库的只读浏览命令组，映射到 Web UI 的 `/modelLibrary` 页面。

- **纯 Browser API**（SSO session），无 OpenAPI 对应
- 所有子命令均为**只读**，不包含上传、注册、修改或删除能力
- CLI 覆盖 `list`、`status`、`versions`；模型上传 / 注册仍在 Web UI `/modelLibrary`

## 2. 与 `serving` 的关系

| 命令组 | 定位 | API |
| --- | --- | --- |
| `model` | 浏览模型仓库，选模型 | Browser API |
| `serving` | 部署模型为推理服务 | Browser API + OpenAPI |

流程通常是先在 model registry 找到目标模型（`model list` / `model status`），再通过 Web UI 或 OpenAPI 在 `/jobs/modelDeployment` 创建 serving 部署。`model` 是浏览仓库，`serving` 是消费模型。

## 3. 子命令说明

### `model list`

```bash
inspire model list
inspire model list --workspace <WORKSPACE>
```

列出当前 workspace（或指定 workspace）中的模型仓库条目。支持分页和全量拉取（`--page-size -1`）。

### `model status`

```bash
inspire model status <model-name>
```

查看特定模型的详细信息：版本列表、元数据、关联的存储路径等。

### `model versions`

```bash
inspire model versions <model-name>
```

列出模型的所有历史版本。

## 4. 限制

- CLI 不覆盖模型上传或注册；模型首次入库必须通过 Web UI `/modelLibrary`
- model registry 与 model deployment（`/jobs/modelDeployment`）是两个不同的平台模块；前者是仓库浏览，后者是生命周期管理
