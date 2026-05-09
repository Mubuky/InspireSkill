# Image 管理

## 1. 镜像生命周期概述

平台镜像管理涉及以下命令：

```bash
inspire image list          # 浏览可使用的镜像
inspire image save          # 将运行中的 notebook 固化为自定义镜像
inspire image register      # 注册一个外部镜像到平台
inspire image set-default   # 设为项目默认镜像
inspire image delete        # 清理不再需要的自定义镜像
```

本节解释各命令的使用边界，确保 Agent 在 notebook 创建、job 提交前能正确选择或生成镜像。命令参数和默认值以 CLI `--help` 为准。

## 2. `image list`：浏览可用镜像

```bash
inspire image list
inspire image list --source private   # 只列个人/项目可见的自定义镜像
inspire image list --source all       # 全部镜像（含官方 + 自定义）
```

- `--source` 默认 `official`。
- 自定义镜像通过 `save` 或 `register` 创建，状态为 `READY` 后才可被 job / notebook / hpc 使用。

## 3. `image save`：从运行 notebook 固化镜像

适用于"在 notebook 里装好环境，再保存成项目通用基底"：

```bash
inspire image save <notebook-name> -n <img-name> -v v1 --public --wait
```

关键参数：

| 参数 | 说明 |
| --- | --- |
| `-n, --name` | 镜像名，保存后可在 `list` 中看到 |
| `-v, --version` | 版本 tag，默认 `v1` |
| `--public` / `--private` | 可见性；public 对同项目成员可见 |
| `--wait` | 阻塞直到镜像状态变为 `READY` |

保存完成后建议设项目默认镜像，后续 `job create` / `notebook create` 会自动继承，无需显式 `--image`：

```bash
inspire image set-default --job <image-url> --notebook <image-url>
```

基底 notebook 的创建和依赖安装流程参见 [notebook.md §6](notebook.md)。

## 4. `image register`：注册外部 Docker 镜像

适用于镜像已在本地或外部 registry 构建完成，需要注册到平台让其可以被调度的场景。

有两种注册方式：

### Push 工作流（默认）

平台为你创建一个镜像槽并返回 registry URL，你把镜像推上去：

```bash
inspire image register -n my-img -v v1.0
# 根据 CLI 输出的 registry URL 执行：
docker tag <local-image> <registry-url>
docker push <registry-url>
# 平台检测到推送后自动标记为 READY
```

### Address 工作流

镜像已托管在公开或私有 registry，直接注册地址：

```bash
inspire image register -n my-img -v v1.0 --method address
```

## 5. 可见性与权限

- `--public` 使镜像对整个平台或同项目可见（具体范围由平台控制），适合作为项目共享基底。
- `--private` 仅限创建者可见，适合个人实验镜像。
- 镜像可见性翻转：`inspire image set-visibility <name>:<version> --public` 或 `--private`。

## 6. 与 notebook 镜像流程的关系

| 场景 | 推荐命令 |
| --- | --- |
| 在 notebook 里装完环境想固化 | `image save` |
| 本地已构建好 Docker 镜像想上线 | `image register` |
| job / notebook 提交时自动使用默认镜像 | `image set-default` |
| 需要排查某个镜像能否被调度 | `image list` + `image detail` |

完整的环境准备→保存→设置默认流程参见 [notebook.md §6](notebook.md)。
