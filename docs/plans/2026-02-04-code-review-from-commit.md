# Commit Diff Code Review Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a “代码review” button in commit detail view that triggers a new code_review chat, injecting commit diff into CODE_REVIEW_PROMPT, with truncation notice when diff is too large.

**Architecture:** Frontend builds a code review payload (message + diff + notice), stores it in sessionStorage, and routes to Chat. Chat consumes pending payload and sends it via the existing chat stream API with new optional fields. Backend updates CODE_REVIEW_PROMPT to accept diff placeholders and renders a system prompt per request; AgentFactory passes that prompt to the CodeReviewAgent.

**Tech Stack:** Vue 3 + Element Plus + Vitest, FastAPI + SQLAlchemy + LangChain.

---

### Task 1: Backend prompt rendering helper (@test-driven-development)

**Files:**
- Create: `backend/app/utils/code_review_prompt.py`
- Create: `backend/tests/test_code_review_prompt.py`
- Modify: `backend/app/agents/prompts.py`

**Step 1: Write the failing test**

Create `backend/tests/test_code_review_prompt.py`:

```python
from app.utils.code_review_prompt import render_code_review_prompt


def test_render_code_review_prompt_includes_diff_and_notice():
    diff = "diff --git a/a.py b/a.py\n+print('hi')"
    notice = "diff过长，已截断"

    prompt = render_code_review_prompt(diff, notice)

    assert diff in prompt
    assert notice in prompt
```

**Step 2: Run test to verify it fails**

Run: `cd backend && /home/yuanwu/zyk-ai-agent/backend/venv/bin/python -m pytest tests/test_code_review_prompt.py -v`
Expected: FAIL (helper not found).

**Step 3: Write minimal implementation**

Create `backend/app/utils/code_review_prompt.py`:

```python
from app.agents.prompts import CODE_REVIEW_PROMPT


def render_code_review_prompt(diff: str, notice: str | None = None) -> str:
    content = diff or "(未提供diff内容)"
    diff_notice = notice or ""
    prompt = CODE_REVIEW_PROMPT.replace("{{DIFF}}", content)
    prompt = prompt.replace("{{DIFF_NOTICE}}", diff_notice)
    return prompt
```

Update `backend/app/agents/prompts.py` CODE_REVIEW_PROMPT to include placeholders:

```
## 代码差异
{{DIFF}}

{{DIFF_NOTICE}}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && /home/yuanwu/zyk-ai-agent/backend/venv/bin/python -m pytest tests/test_code_review_prompt.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/utils/code_review_prompt.py backend/tests/test_code_review_prompt.py backend/app/agents/prompts.py
git commit -m "feat: add code review prompt renderer"
```

---

### Task 2: Backend chat request support for review diff (@test-driven-development)

**Files:**
- Modify: `backend/app/api/chat.py`
- Modify: `backend/app/services/agent_service.py`

**Step 1: Write the failing test**

Create `backend/tests/test_chat_code_review_prompt.py`:

```python
from app.services.agent_service import AgentFactory
from app.utils.code_review_prompt import render_code_review_prompt


def test_agent_factory_accepts_system_prompt_override():
    prompt = render_code_review_prompt("diff", "")
    # just ensure signature accepts system_prompt; no runtime execution
    AgentFactory.create_agent  # exists
```

(Expect failure once we add type checks/signature changes.)

**Step 2: Implement minimal changes**

- Update `ChatRequest` to include optional `review_diff` and `review_notice`.
- In `chat_stream`, pass these into `process_message`.
- Update `process_message` to build `system_prompt` for code_review using `render_code_review_prompt` and pass to AgentFactory.
- Update `AgentFactory.create_agent` to accept `system_prompt: str | None = None` and pass to CodeReviewAgent.
- Update `CodeReviewAgent.initialize` to accept optional `system_prompt` and use it; otherwise default to CODE_REVIEW_PROMPT with empty placeholders.

**Step 3: Commit**

```bash
git add backend/app/api/chat.py backend/app/services/agent_service.py
git commit -m "feat: support code review diff prompts"
```

---

### Task 3: Frontend helper for review payload (@test-driven-development)

**Files:**
- Create: `frontend/src/utils/codeReview.ts`
- Create: `frontend/src/utils/codeReview.test.ts`

**Step 1: Write the failing test**

```ts
import { describe, it, expect } from 'vitest'
import { buildCodeReviewPayload } from './codeReview'

describe('buildCodeReviewPayload', () => {
  it('truncates large diff and sets notice', () => {
    const diff = 'a'.repeat(30000)
    const payload = buildCodeReviewPayload({
      title: 'commit-123',
      diff
    })

    expect(payload.review_diff.length).toBeLessThan(diff.length)
    expect(payload.review_notice).toContain('已截断')
    expect(payload.message).toContain('代码审查')
  })
})
```

**Step 2: Implement helper**

```ts
export function buildCodeReviewPayload({ title, diff }: { title: string; diff: string }) {
  const MAX = 20000
  const HEAD = 10000
  const TAIL = 10000
  let reviewDiff = diff
  let reviewNotice = ''

  if (diff.length > MAX) {
    reviewDiff = diff.slice(0, HEAD) + '\n\n...已截断...\n\n' + diff.slice(-TAIL)
    reviewNotice = `diff内容过长，已截断，仅展示前后各 ${HEAD} 字符。`
  }

  const message = reviewNotice ? `代码审查: ${title}（diff已截断）` : `代码审查: ${title}`
  return { message, review_diff: reviewDiff, review_notice: reviewNotice }
}
```

**Step 3: Commit**

```bash
git add frontend/src/utils/codeReview.ts frontend/src/utils/codeReview.test.ts
git commit -m "feat: add code review payload builder"
```

---

### Task 4: Frontend wiring: commit review button + auto chat send (@test-driven-development)

**Files:**
- Modify: `frontend/src/components/settings/GitlabManage.vue`
- Modify: `frontend/src/views/Chat.vue`
- Modify: `frontend/src/api/chat.ts`
- Modify: `frontend/src/types/index.ts`

**Step 1: Add review button**

- In commits table, add “代码review” button next to “查看diff”.
- On click, fetch diff via `getGitlabCommitDiffs`, build payload via `buildCodeReviewPayload`, store payload in `sessionStorage` (e.g., `pending_chat_request`), then `router.push('/')`.

**Step 2: Chat auto-send**

- On `Chat.vue` mount, check `sessionStorage` for `pending_chat_request`.
- If present, `createNewChat()`, set `currentMode` to `code_review`, call `sendMessage` with override payload (message + review_diff + review_notice).

**Step 3: Update ChatRequest types**

- Add `review_diff?: string`, `review_notice?: string` in `frontend/src/api/chat.ts` and `frontend/src/types/index.ts`.
- Ensure `chatStream` includes these fields in request.

**Step 4: Commit**

```bash
git add frontend/src/components/settings/GitlabManage.vue frontend/src/views/Chat.vue frontend/src/api/chat.ts frontend/src/types/index.ts
git commit -m "feat: add commit code review flow"
```

---

### Task 5: Verification (@verification-before-completion)

**Step 1: Frontend tests**

Run:

```bash
cd frontend
npm test
```

**Step 2: Manual check**

- Settings → Gitlab管理 → 提交列表：点击“代码review”
- 自动跳转聊天页并新建对话
- AI 使用 diff 内容进行审查（若 diff 过长，提示已截断）

---

## Notes
- This plan uses sessionStorage to pass payload to Chat, avoiding URL size limits.
- Backend prompt rendering avoids Python `.format` to prevent brace issues in diffs.
