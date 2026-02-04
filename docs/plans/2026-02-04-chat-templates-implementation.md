# Chat Templates Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add mode-specific chat templates surfaced via `#` in the chat UI, backed by backend prompt templates and a new API endpoint.

**Architecture:** Define template lists in `backend/app/agents/prompts.py`, expose them via `GET /api/v1/chat/templates`, then integrate a `#` trigger in `Chat.vue` that fetches and displays templates using the existing picker component. A small frontend utility handles trigger replacement and is unit-tested.

**Tech Stack:** FastAPI, Vue 3, TypeScript, Vitest, Element Plus.

---

### Task 0: Create a dedicated worktree (required by planning process)

**Files:**
- Create: none

**Step 1: Create worktree**

Run:
```bash
git worktree add ../zyk-ai-agent-chat-templates
```
Expected: new worktree created at `../zyk-ai-agent-chat-templates`.

**Step 2: Use the new worktree for all following tasks**

Run:
```bash
cd ../zyk-ai-agent-chat-templates
```
Expected: subsequent commands and file edits happen in the worktree.

---

### Task 1: Add backend template constants with tests

**Files:**
- Modify: `backend/app/agents/prompts.py`
- Modify: `backend/tests/test_prompts.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_prompts.py`:
```python
def test_chat_templates_exist():
    assert isinstance(prompts.CHAT_TEMPLATES, list)
    assert isinstance(prompts.DATA_ANALYSIS_TEMPLATES, list)
    assert isinstance(prompts.CODE_REVIEW_TEMPLATES, list)
    assert "data_analysis" in prompts.TEMPLATES_BY_MODE
```

**Step 2: Run test to verify it fails**

Run:
```bash
python3 -m pytest backend/tests/test_prompts.py::test_chat_templates_exist -v
```
Expected: FAIL with `AttributeError` because constants don’t exist yet.

**Step 3: Write minimal implementation**

Add the three template lists plus `TEMPLATES_BY_MODE` in `backend/app/agents/prompts.py` with `id/name/description/content` fields per template.

**Step 4: Run test to verify it passes**

Run:
```bash
python3 -m pytest backend/tests/test_prompts.py::test_chat_templates_exist -v
```
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/agents/prompts.py backend/tests/test_prompts.py
git commit -m "feat: add chat templates definitions"
```

---

### Task 2: Add backend templates endpoint + helper test

**Files:**
- Modify: `backend/app/api/chat.py`
- Create: `backend/tests/test_chat_templates.py`

**Step 1: Write the failing test**

Create `backend/tests/test_chat_templates.py`:
```python
import pytest
from app.api import chat


def test_get_chat_templates_by_mode_normal():
    items = chat.get_chat_templates_by_mode("normal")
    assert isinstance(items, list)
    assert items


def test_get_chat_templates_by_mode_invalid():
    with pytest.raises(ValueError):
        chat.get_chat_templates_by_mode("unknown")
```

**Step 2: Run test to verify it fails**

Run:
```bash
python3 -m pytest backend/tests/test_chat_templates.py -v
```
Expected: FAIL because `get_chat_templates_by_mode` doesn’t exist.

**Step 3: Write minimal implementation**

In `backend/app/api/chat.py`:
- Import `TEMPLATES_BY_MODE` from `app.agents.prompts`.
- Add `get_chat_templates_by_mode(mode: str) -> list[dict]` that validates and returns templates, raising `ValueError` on invalid mode.
- Add `@router.get("/templates")` endpoint with `mode` query param (default `normal`) that returns the list or raises 400 if invalid.

**Step 4: Run test to verify it passes**

Run:
```bash
python3 -m pytest backend/tests/test_chat_templates.py -v
```
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/api/chat.py backend/tests/test_chat_templates.py
git commit -m "feat: expose chat templates endpoint"
```

---

### Task 3: Add frontend template types + API client

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/chat.ts`

**Step 1: Write the failing test**

Create `frontend/src/utils/triggerInsert.test.ts` (placeholder to ensure test harness is ready):
```ts
import { describe, it, expect } from 'vitest'

it('placeholder test for template insertion util', () => {
  expect(true).toBe(true)
})
```

**Step 2: Run test to verify it passes**

Run:
```bash
cd frontend
npm run test -- src/utils/triggerInsert.test.ts
```
Expected: PASS (sanity check for test harness).

**Step 3: Write minimal implementation**

- Extend `MentionItem` to allow `type: 'template'` and optional `content`.
- Add `ChatTemplate` interface if preferred (id/name/description/content/type).
- Add `getChatTemplates(mode)` to `frontend/src/api/chat.ts` calling `/chat/templates`.

**Step 4: Run test to verify it still passes**

Run:
```bash
cd frontend
npm run test -- src/utils/triggerInsert.test.ts
```
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/chat.ts frontend/src/utils/triggerInsert.test.ts
git commit -m "feat: add chat templates api types"
```

---

### Task 4: Add trigger replacement utility with tests

**Files:**
- Create: `frontend/src/utils/triggerInsert.ts`
- Modify: `frontend/src/utils/triggerInsert.test.ts`

**Step 1: Write the failing test**

Update `frontend/src/utils/triggerInsert.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { replaceTriggerText } from './triggerInsert'


describe('replaceTriggerText', () => {
  it('replaces text between trigger and cursor with replacement', () => {
    const result = replaceTriggerText('hello #tem', 6, 10, 'TEMPLATE')
    expect(result).toBe('hello TEMPLATE')
  })

  it('keeps suffix after cursor', () => {
    const result = replaceTriggerText('hi #tem world', 3, 7, 'TEMPLATE')
    expect(result).toBe('hi TEMPLATE world')
  })
})
```

**Step 2: Run test to verify it fails**

Run:
```bash
cd frontend
npm run test -- src/utils/triggerInsert.test.ts
```
Expected: FAIL because `replaceTriggerText` is missing.

**Step 3: Write minimal implementation**

Create `frontend/src/utils/triggerInsert.ts`:
```ts
export function replaceTriggerText(
  value: string,
  triggerIndex: number,
  cursorIndex: number,
  replacement: string
): string {
  const before = value.slice(0, triggerIndex)
  const after = value.slice(cursorIndex)
  const normalized = replacement.endsWith(' ') ? replacement : `${replacement} `
  return `${before}${normalized}${after}`.trimEnd()
}
```

**Step 4: Run test to verify it passes**

Run:
```bash
cd frontend
npm run test -- src/utils/triggerInsert.test.ts
```
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/utils/triggerInsert.ts frontend/src/utils/triggerInsert.test.ts
git commit -m "feat: add trigger insertion utility"
```

---

### Task 5: Add template picker support + # trigger in Chat.vue

**Files:**
- Modify: `frontend/src/components/MentionPicker.vue`
- Modify: `frontend/src/views/Chat.vue`

**Step 1: Write the failing test**

Add to `frontend/src/utils/triggerInsert.test.ts` (or a new test file) a case that matches Chat.vue usage if needed (optional if already covered).

**Step 2: Run test to verify it fails (if new test added)**

Run:
```bash
cd frontend
npm run test -- src/utils/triggerInsert.test.ts
```
Expected: FAIL if a new case is added and not supported.

**Step 3: Write minimal implementation**

- `MentionPicker.vue`: extend `type` to include `template`, update title map to show “快捷模板”.
- `Chat.vue`:
  - Add template cache by mode (`Record<string, MentionItem[]>`).
  - Add `mentionTriggerIndex` and `mentionTriggerChar` tracking.
  - Extend `handleInput` to detect `#` (same rules as `@`) and choose the closest valid trigger before cursor.
  - On `#` trigger, fetch templates via `getChatTemplates(currentMode.value)` if cache empty, then show picker.
  - Update `handleMentionSelect` to insert template `content` using `replaceTriggerText` when `item.type === 'template'`.

**Step 4: Run tests to verify they pass**

Run:
```bash
cd frontend
npm run test -- src/utils/triggerInsert.test.ts
```
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/components/MentionPicker.vue frontend/src/views/Chat.vue
git commit -m "feat: add chat template picker" 
```

---

### Task 6: Manual verification checklist

**Files:**
- No code changes

**Step 1: Start frontend + backend**

Run:
```bash
# in backend
python3 backend/main.py
# in frontend
cd frontend
npm run dev
```

**Step 2: Verify behavior**
- Normal 模式输入 `#`，出现通用模板，选择后插入。
- 数据分析模式输入 `#`，模板聚焦医院/订单/趋势/员工。
- 研发质量模式输入 `#`，模板聚焦项目代码质量、提交数量。
- `@` 功能仍可用，且与 `#` 不冲突。

---

## Execution Notes
- Run tasks in the worktree created in Task 0.
- Keep commits scoped to each task.
- If any test command fails due to missing deps, install in the relevant directory.

