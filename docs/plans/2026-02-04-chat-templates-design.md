# Chat 模式快捷模板设计

## 背景与目标
当前仅支持 `@` 选择对象（数据库/表/研发人员）。希望在输入 `#` 时弹出“快捷模板”，按三种对话模式提供常用提示词，提升用户提问效率，并保证模板与后端提示词统一管理。

目标：
- 为 `normal` / `data_analysis` / `code_review` 提供模式化模板列表。
- 前端输入 `#` 弹出对应模板，选择后插入模板内容。
- 模板来源统一由后端 `prompts.py` 管理，并通过 API 下发。

非目标：
- 模板后台管理界面、数据库存储、权限系统。
- 复杂富文本模板编辑。

## 方案概览
采用“后端统一模板 + 前端按模式展示”的方案：
- 后端新增模板常量与 `GET /api/v1/chat/templates` 接口。
- 前端新增模板接口与 `#` 触发弹层。
- 交互与 `@` 选择共存，不改变对话处理逻辑。

## 数据结构
后端 `prompts.py` 新增：
- `CHAT_TEMPLATES`
- `DATA_ANALYSIS_TEMPLATES`
- `CODE_REVIEW_TEMPLATES`
- `TEMPLATES_BY_MODE`

模板字段：
- `id`: 唯一标识（string）
- `name`: 展示名（string）
- `description`: 简短说明（string）
- `content`: 插入内容（string）

## API 设计
新增接口：
- `GET /api/v1/chat/templates?mode=normal|data_analysis|code_review`
- 返回：`[{ id, name, description, content }]`

错误处理：
- mode 非法：HTTP 400 + 明确错误信息。
- 无模板：返回空数组。

## 前端交互
- 新增 `getChatTemplates(mode)` API。
- `Chat.vue`：监听 `#` 触发，显示模板选择弹层。
- 选择模板后，替换 `#` 到光标之间内容为模板 `content` 并追加空格。
- 维护按 mode 的内存缓存，首次触发时请求，后续复用。
- `MentionPicker` 扩展 `type: 'template'` 与标题“快捷模板”。

## 模板内容
### 数据分析（data_analysis）
强调医院/订单总量统计、趋势、员工工作情况，例如：
- 近 30 天医院订单总量与日趋势，Top10 医院。
- 按区县订单量/占比与趋势变化。
- 员工操作量与效率分布，负荷最高人员。
- 异常类型与医院分布。
- 药品消耗总量与趋势。

### 研发质量（code_review）
强调项目最近代码质量与提交数量，例如：
- 项目最近 30 天提交质量总结（主要问题类型）。
- 提交数量趋势与主要提交人。
- 指定分支最近 N 次提交质量概览。

### 普通对话（normal）
提供通用模板（总结、清单、解释、改写等）。

## 测试与验证
- 后端：模板接口返回格式正确，mode 校验生效。
- 前端：三种模式下 `#` 弹层正确展示，插入文本正确，与 `@` 互不影响。

## 风险与兼容性
- 若 GitLab/MySQL 等工具不可用，模板仅作为输入辅助，不影响对话流程。
- 模板内容维护在后端，前端无需更新即可生效。

