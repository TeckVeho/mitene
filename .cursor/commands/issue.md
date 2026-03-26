# Issue Command

Get GitHub issue information, create development branch first, then save issue.md in the new branch with AI Agent

## Purpose (Goal)

-   Retrieve GitHub issue details
-   Create a dedicated development branch before starting work
-   Save a structured `issue.md` document in the new branch
-   Keep the original branch clean and isolated from issue-specific changes
-   Capture codebase paths so downstream steps can read the right source code
-   **Detect GitHub Project V2** the issue belongs to — save `project id` in `issue.md` so `/breakdown` can add child issues to the **same project**

## Pre-questions (Input Collection)

**Flow:** (1) Issue URL required → (2) **Auto-detect** paths by scanning the repo → (3) **Once** show a summary table for user confirmation → (4) User **accepts / says “ok” / Enter** → use all detected values; user edits specific lines → only those fields change.

### 1. Issue URL (required)

- Format: `https://github.com/{owner}/{repo}/issues` or `.../issues/{number}`
- Validate: `https://github.com/.*/issues(\/\d+)?`

### 2. Auto-detect paths (before asking user)

The AI Agent **MUST** scan the workspace/repo (list dir, glob, read `package.json`/`composer.json` if needed) using the **priority order** below. Paths are **relative to the scan root** (usually current git root or `workspace_root` in a monorepo).

| Field | Heuristic (first matching directory, short note) |
|--------|--------------------------------------------------|
| **workspace_root** | `.` by default. If `apps/web` + `apps/api` exist → suggest `.` as monorepo root. |
| **frontend_path** | Exists with FE signals: `frontend/`, `packages/web/`, `apps/web/`, `client/`, `web/`, `src/` (with `package.json` containing `vue`/`react`/`nuxt`/`next`), `ui/`. |
| **backend_path** | `backend/`, `server/`, `api/`, `packages/api/`, `apps/api/`, Laravel `app/` + `artisan` at root → `.`, Nest `apps/server/`. |
| **migrations_path** | `prisma/migrations`, `database/migrations` (Laravel), `{backend_path}/migrations` if present, `db/migrations`, `supabase/migrations`. |
| **api_docs_path** | `openapi.yaml`, `openapi.json`, `docs/openapi.yaml`, `swagger.json`, `backend/swagger`, `swagger/` dir. *(Empty if not found.)* |
| **tests_path** | `tests/` (root), `__tests__/`, `{frontend_path}/__tests__`, `{backend_path}/tests`, `test/` (PHPUnit). *(Empty if unclear — may suggest `tests/` if it exists.)* |

If **nothing matches**: static fallback `frontend_path=./frontend`, `backend_path=./backend`, `migrations_path=./backend/migrations` or `./db/migrations` (only if those dirs exist), else `./backend/migrations`.

### 3. Confirmation block (single message)

Display like:

```text
Repo scanned. Confirm paths (reply "ok" or Enter to keep as-is, or specify changes):
- frontend_path: ./packages/web   (detected: package.json + Nuxt)
- backend_path: ./api
- migrations_path: ./api/prisma/migrations
- api_docs_path:   (empty)
- tests_path: ./packages/web/tests
- workspace_root: .
```

**Rule:** User **ok / agrees / no further reply** → use **exactly** the detected table. User changes one line → only that field updates; rest stay detected.

### 4. `--no-prompts`

Skip confirmation: run **only** auto-detect (same heuristics), write `issue.md`, do not ask.

---

**Note:** Paths are relative to `workspace_root` or repo root. Store in `issue.md` (Context / Codebase Paths) for `/plan`, `/breakdown`, `/dev`.

## Parameters

-   **`issue_url`** (preferred): Full GitHub issue URL, e.g. `https://github.com/owner/repo/issues/129`. From URL derive owner, repo, issue_number; doc path uses **repo** (repo name) as folder name.
-   `issue_number` (optional): Issue number when working in current repo; if omitted and pre-questions run, take from Issue URL.
-   `--auto` / `--workflow` (optional): Run full pipeline (`/issue → /plan → /breakdown → /dev → /test → /pr`)
-   `--skip-plan` / `--skip-breakdown` (optional): Skip that phase in auto mode
-   `--no-prompts` (optional): Skip pre-questions; use when issue_url + paths are already passed in the command

## Workflow Position

-   This command should be run **at the very beginning** of the workflow
-   If `--auto` is provided, it will trigger the subsequent phases automatically

## Critical Rules

**⛔ ABSOLUTE PROHIBITION: DO NOT EXECUTE ANY GIT COMMIT COMMANDS ⛔**

-   NEVER run `git commit` in any form
-   NEVER run `git add . && git commit`
-   NEVER suggest or execute commit operations
-   NEVER open browser for checking GitHub issue (use gh command)
-   All changes MUST remain uncommitted during issue processing

---

## Instructions for AI Agent

0. **Collect Inputs (Pre-questions)** — Unless `--no-prompts`

    - Ask for **Issue URL** first; validate pattern.
    - **Auto-detect** paths per **Pre-questions §2** (real scan, no guessing).
    - Show summary **once**; user ok → use detection; user edits → merge.
    - With `--no-prompts`: auto-detect only, no questions.
    - Store everything in context for step 4 (`issue.md`).

1. **Parse Issue Input**

    - Extract owner, repo, and issue number from `issue_url` (pre-questions or command args).
    - Accepted formats:
        - Full URL: `https://github.com/{owner}/{repo}/issues/{number}` → extract `owner`, `repo`, `number`. Doc path uses **repo** as folder name.
        - Number only: `129` → current repo: `gh repo view --json nameWithOwner -q .nameWithOwner` → parse `repo` for doc path.
    - Store `owner`, `repo`, `issue_number`. Doc path = `docs/issues/{repo}/{issue_number}/`.

2. **Fetch Issue Information**

    - Do not open a browser.
    - Always use GitHub CLI (`gh`)
    - If owner/repo from URL: `gh issue view {issue_number} --repo {owner}/{repo} --json title,body,labels,assignees,state,createdAt,updatedAt,url`
    - If number only: `gh issue view {issue_number} --json title,body,labels,assignees,state,createdAt,updatedAt,url`

2b. **Detect GitHub Project V2** (for `/breakdown`)

    - GraphQL for all projects containing this issue (single-line query, `title` sibling of `projectItems` — avoids parse errors):
      ```bash
      gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){issue(number:$n){title projectItems(first:20){nodes{project{id title}}}}}}' -f o={owner} -f r={repo} -F n={issue_number}
      ```
      Or: `pwsh -File .cursor/resources/script/verify-github-setup.ps1 -IssueUrl "<issue_url>"` **(Windows)** / `bash .cursor/resources/script/verify-github-setup.sh "<issue_url>"` **(Linux, macOS, Git Bash)**.
    - **0 projects:** In `issue.md` leave `github_project_v2_id` empty; note issue not on board — after `/breakdown` add children manually or add parent to project first.
    - **1 project:** Save `github_project_v2_id` + `github_project_title` (for `add-to-project.ps1` / `add-to-project.sh`).
    - **Multiple projects:** List names; user **picks one** for child issues (default: first if user accepts immediately). Save chosen id to `github_project_v2_id`; optional `github_projects_detected` list in comments or YAML.
    - **`--no-prompts` with multiple projects:** Use **first** project in GraphQL response.

3. **Branch Creation**

    - Check `git status` for uncommitted changes
    - If changes exist, prompt user (stash / discard / cancel)
        > ⚠️ Do **not** suggest commit here
    - Branch name: `{issue_number}-feat-{short-desc}`
    - **GitHub Development linking**: Branch name MUST include `{issue_number}`. Example `123-feat-add-login` links to issue #123.
    - Run `git checkout -b {branch_name}`
    - Display branch information

4. **Generate Issue Document**

    - **Doc path:** `docs/issues/{repo}/{issue_number}/`, **repo** from URL or `gh repo view`.
    - Create `docs/issues/{repo}/{issue_number}/issue.md`
    - Include:
        - **Context / Codebase Paths** (from pre-questions):
            - `repository` (owner/repo), `repo`, `issue_url`
            - `frontend_path`, `backend_path`, `migrations_path`, `api_docs_path` (optional), `tests_path` (optional), `workspace_root` (optional)
            - **`github_project_v2_id`**, **`github_project_title`**: for `/breakdown` add child (step 2b)
        - Issue metadata (title, body, labels, assignees, status, URL, timestamps)
        - Implementation checklist
        - Notes / review section
    - `/plan`, `/breakdown`, `/dev` read Codebase Paths from same doc path.

5. **Save Document**

    - Save `issue.md` in the new branch (WITHOUT committing)

6. **Auto-Workflow (Optional)**
    - If `--auto` or `--workflow`: `/issue` → `/plan` → `/breakdown` → `/dev` → `/test` → `/pr`
    - Respect `--skip-plan` and `--skip-breakdown`

---

## Branch Naming Convention

-   Feature: `{issue_number}-feat-{desc}`
-   Fix: `{issue_number}-fix-{desc}`
-   Hotfix: `{issue_number}-hotfix-{desc}`

---

## Output

-   `docs/issues/{repo}/{issue_number}/issue.md`. Example **Context / Codebase Paths**:

    ```yaml
    # Context / Codebase Paths (from pre-questions)
    repository: {owner}/{repo}
    repo: {repo}
    issue_url: https://github.com/{owner}/{repo}/issues/{issue_number}
    github_project_v2_id: PVT_kwDO...   # empty if not on Project; for /breakdown
    github_project_title: Sprint Q1      # empty if none
    frontend_path: ./frontend
    backend_path: ./backend
    migrations_path: ./backend/migrations
    api_docs_path:   # optional
    tests_path:      # optional
    workspace_root: .
    ```

---

## Usage Examples

**Default (with pre-questions)**

```
/issue
```
→ Ask Issue URL → auto-detect paths → one confirmation table (ok = use detection).

**Standard**

```
/issue 129
/issue https://github.com/owner/repo/issues/129
```

**Skip prompts**

```
/issue 129 --no-prompts
```
→ Use when issue number/URL and paths are already known (e.g. rules/project config).

**Auto workflow**

```
/issue 129 --auto
/issue 129 --workflow
/issue 129 --auto --skip-plan
/issue 129 --workflow --skip-breakdown
```
