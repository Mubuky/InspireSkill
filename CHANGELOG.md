# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 的记录结构，版本号遵循语义化版本风格。未发布变更先进入 `Unreleased`，发布时再归档到具体版本。

## Unreleased

当前无未发布变更。

## 4.1.2（2026-05-09）

### Fixed

- 强化 `inspire update` 的全局更新路径：从本地 checkout 或 repo venv 运行时，也会更新 `uv tool` / `pipx` 管理的全局 `inspire`。
- `uv tool` 安装源如果残留为本地 `file://` 路径，`inspire update` 会重置为官方 PyPI 包，避免开发机路径污染全局安装。
- `inspire update` 完成后会验证全局 executable、agent skill 目录和旧 `INSPIRE_TARGET_DIR` / 长环境前缀残留，避免 CLI 最新但 Agent 仍读取旧文档。
- CLI 最新版本检查改为以 PyPI 发布版本为主，GitHub `main` 只作为网络或包索引失败时的 fallback。

## 4.1.0（2026-05-08）

### Added

- 新增 pre-commit 配置，用于提交前检查 YAML、TOML、合并冲突、大文件、行尾和 Ruff 关键错误。
- 新增 GitHub Issue 模板、Pull Request 模板、贡献指南、CI workflow 和 mypy 检查入口，补齐基础协作入口。
- 新增 `inspire job shell`，支持进入 running training job 实例，包含 `--rank`、`--instance` 和 `--pick` 选择器。

### Changed

- `inspire init` 默认进入 discover 流程；首次没有账号时会内联创建 `default` 账号并继续初始化。
- `scripts/install.sh` 安装 CLI 后会尽量自动安装 Playwright Chromium，减少首次 SSO 登录的中断。
- `inspire job create` 的远端日志包装改为 `tee`，同时保留网页 stdout/stderr 和共享盘日志文件，并默认设置 `PYTHONUNBUFFERED=1`。

### Fixed

- `inspire notebook exec` 在没有项目远端路径配置时回落到远端默认登录目录，不再要求 `INSPIRE_TARGET_DIR`。
- `inspire notebook ssh --command` 现在转发本机 stdin，支持管道输入到远端命令。
- `inspire notebook scp`、`notebook connections` 和 `ssh --command` 共用 active account 的 tunnel cache。

## 4.0.0

### Added

- 发布面向 Inspire 平台的 agent-native CLI，覆盖 notebook 生命周期、作业提交、资源查询、SSH、镜像和路径操作。
