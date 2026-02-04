# GitLab/MySQL 列表分页设计

日期：2026-02-04

## 目标与范围
- 目标：GitLab 用户/项目/分支/提交 与 MySQL 库/表列表统一分页，默认每页 20 条，前后端一致。
- 范围：
  - GitLab 列表：`/api/v1/gitlab/users`、`/api/v1/gitlab/projects`、`/api/v1/gitlab/branches`、`/api/v1/gitlab/commits`
  - MySQL 列表：`/api/v1/mysql/databases`、`/api/v1/mysql/tables`、`/api/v1/mysql/manage/databases`、`/api/v1/mysql/manage/tables`
- 非范围：提交 diff 与表结构详情仍按当前全量/详情方式返回（必要时后续再扩展）。

## API 约定
- 查询参数：`page`（>=1，默认 1）、`page_size`（1-200，默认 20）
- 响应结构：`{ items, total, page, page_size }`
- 保留现有参数：如 `include_disabled`、`refresh`、`project_id`、`database` 等。

## 后端设计
- 为每个列表接口增加分页参数解析与校验，统一计算 `offset = (page - 1) * page_size`。
- 列表查询使用 `offset/limit` + `order_by`，`total` 使用同条件 `count(*)`。
- `refresh=true` 时保持“先同步再分页返回”，同步逻辑不变。
- 分页越界时返回空 `items` 与正确 `total`，不报错。

## 前端设计
- API 层改为返回分页结构，不再只返回 `items`。
- 管理页面与抽屉列表引入分页状态（`page`、`pageSize`、`total`）。
- `page`/`pageSize` 变化触发重新请求；切换上下文（项目/数据库/Tab）重置 `page=1`。
- 在表格下方添加 `el-pagination`，默认 20 条/页，可选 10/20/50/100。

## 错误处理与边界
- `page` 或 `page_size` 非法：返回 400 与明确错误提示。
- `refresh` 同步失败：返回缓存数据（如有）并提示用户。
- 过滤条件变化导致分页越界：前端自动回退到最大页并重新请求。

## 测试与验证
- 后端：新增接口级测试，验证分页参数校验、`total` 正确、排序稳定。
- 前端：验证分页切换、pageSize 变化、抽屉分页重置与刷新逻辑。

## 迁移与兼容
- 旧前端依赖 `items` 的调用需同步更新，避免分页结构变更导致渲染错误。
- 若有外部调用方，需同步更新其分页处理逻辑。
