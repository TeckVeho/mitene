# Breakdown Command

親issueを元に、Frontend/Backend別の個別issueを作成し、Story Point (SP)を算出して**親IssueのTasklistに注入（Inject）**します。

## Purpose (Goal)

* Plan.mdを解析してタスクをFE/BE個別issueに分解
* 各issueに対してSP（1 SP = 1時間）を算出
* **親IssueのTasklistに子IssueのリンクとSPを追記**
* **子Issueを親と同じProjectに追加し、SP custom fieldを設定**
* **Scope**: Implementation and unit tests only

## Parameters

* **`issue_url`** (preferred): Full GitHub issue URL (e.g. `https://github.com/owner/repo/issues/129`). From URL derive owner, repo, issue_number; doc path = `docs/issues/{repo}/{issue_number}/` (**repo** = repo folder name).
* `issue_number` (optional): Issue number in current repo; if omitted, auto-detect from latest doc.
* `--dry-run` (optional): 実際にissueを作成せず、分解計画のみを表示

## Workflow Position

* `/issue` → `/plan` → **`/breakdown`** → `/dev` → `/test` → `/pr`
* Planが完成した後、実装に入る前に実行

## Critical Rules

**⛔ ABSOLUTE PROHIBITION: DO NOT EXECUTE ANY GIT COMMIT COMMANDS ⛔**

* NEVER run `git commit` in any form
* NEVER run `git add . && git commit`
* NEVER suggest or execute commit operations
* All changes MUST remain uncommitted during breakdown processing

---

## Instructions for AI Agent

### 0. Determine Issue Number, Repository, and Doc Path (doc path = `docs/issues/{repo}/{issue_number}/`, **repo** = repo folder name)

* If `issue_url` is provided: Extract `owner`, `repo`, `issue_number` from URL. Store `{repository}` = `owner/repo`. Use `--repo {repository}` with all subsequent `gh` commands.
* If `issue_number` (plain number) is provided: Current repo: `gh repo view --json nameWithOwner -q .nameWithOwner` → parse `repo`.
* If both are omitted: Find most recently modified `docs/issues/*/*/issue.md`; from path get `repo` and `issue_number`; read `repository:` from file and use `--repo {repository}` with all `gh` commands.
* **Read `issue.md` at same doc path:** Take **`github_project_v2_id`** (and `github_project_title` for logging). This is the project `/issue` detected — **prefer this id** at step 3.5 instead of re-querying (avoids mismatch when parent is on multiple projects and user picked one).

### 1. Load Plan Information

* Read `docs/issues/{repo}/{issue_number}/plan.md`
* Extract tasks with their descriptions, requirements, and dependencies
* Identify task types (Frontend/Backend)

### 2. Analyze and Split Tasks Intelligently

**🎯 Default Strategy: ONE FE Issue + ONE BE Issue**

For most features, create exactly **2 issues total**:

* **1 Frontend Issue**: All FE tasks grouped together (UI components, state management, API client integration, routing, forms, frontend unit tests)
* **1 Backend Issue**: All BE tasks grouped together (API endpoints, business logic, database operations, authentication, middleware, migrations, backend unit tests)

**Benefits of Single FE/BE Issue Approach:**

* ✅ Clear ownership per layer
* ✅ Reduced coordination overhead
* ✅ Simpler dependency management
* ✅ Easier to track progress (1 FE developer + 1 BE developer)
* ✅ Natural parallel development (FE and BE teams work simultaneously)
* ✅ Comprehensive testing within each layer

**When to Create Multiple Issues (Exceptions):**
Only split into multiple FE or BE issues if:

* Feature is exceptionally large (total SP > 20)
* Clear independent sub-features exist (e.g., User Management + Reporting Dashboard)
* Different developers will work on truly independent parts
* Phased delivery is required (MVP first, then enhancements)

**Task Organization Within Single Issue:**

* Group all related FE tasks in one comprehensive FE issue body
* Group all related BE tasks in one comprehensive BE issue body
* Use numbered sections (1.1, 1.2, 1.3) to organize sub-tasks within the issue
* Include all acceptance criteria for the entire layer

**Dependency Analysis:**

* FE issue depends on BE issue for integration testing
* BE issue can be developed independently
* Mark clear integration points in issue descriptions

### 3. Create GitHub Issues

For each split task, create a GitHub issue using:

```bash
gh issue create \
  --repo {owner}/{repo} \
  --title "[FE] Feature Name: Task Description" \
  --body "Detailed description with context from plan.md" \
  --label "frontend" \
  --label "enhancement" \
  --label "Child issue" 
```

If working against the current repository (no cross-repo URL was provided), omit the `--repo` flag.

**⚠️ IMPORTANT: Project Board Rules**

* **ADD** child issues to the **same GitHub Project** as the Parent Issue (see step 3.6).
* Child issues inherit the project context for SP tracking and Development section linking.

**Issue Title Format (Bilingual - Japanese/Vietnamese):**

* `[FE] {日本語タイトル} / {Vietnamese Title}` for Frontend
* `[BE] {日本語タイトル} / {Vietnamese Title}` for Backend
* Example: `[FE] 認証: ログインUIコンポーネント / {Vietnamese title for same feature}`
* Keep concise but descriptive
* Be mindful of GitHub's 256 character title limit

**Issue Body Template (Bilingual - Japanese/Vietnamese):**

```markdown
## 日本語 / Japanese

### 親Issue
Parent: #{parent_issue_number}

### 説明
{日本語での詳細なタスク説明}

### 要件
{日本語での具体的な要件}

### 技術詳細
{日本語での実装ヒント、APIエンドポイント、変更するコンポーネント}

### 受け入れ基準
- [ ] 実装完了
- [ ] ユニットテスト作成・合格
- [ ] プロジェクト規約に準拠
- [ ] 既存機能への破壊的変更なし

### 依存関係
{日本語でのブロッキングissueのリスト（存在する場合）}

---

## Tiếng Việt / Vietnamese

### Issue cha
Parent: #{parent_issue_number}

### Mô tả
{ベトナム語での詳細なタスク説明}

### Yêu cầu
{ベトナム語での具体的な要件}

### Chi tiết kỹ thuật
{ベトナム語での実装ヒント、APIエンドポイント、変更するコンポーネント}

### Tiêu chí chấp nhận
- [ ] Hoàn thành việc triển khai
- [ ] Tạo và vượt qua unit tests
- [ ] Tuân thủ quy ước dự án
- [ ] Không có thay đổi phá vỡ chức năng hiện có

### Phụ thuộc
{ベトナム語でのブロッキングissueのリスト（存在する場合）}

```

**Labels:**

* `frontend` - For FE tasks
* `backend` - For BE tasks
* `enhancement` / `bug` / `refactor` - Based on task type
* **`sp:{value}`** - Assign the calculated SP as a label (e.g., `sp:3`) for automated rollup.

### 3.5. Add Child Issues to Project (Same as Parent)

If a **GitHub Project V2** applies (from `issue.md` or query), add each child to **that project**:

1. **Get `project_id` (priority):**
   - **(a)** `github_project_v2_id` in `docs/issues/{repo}/{issue_number}/issue.md` — if non-empty, use it.
   - **(b)** If empty or missing file: GraphQL parent (same shape as `/issue` step 2b — `title` sibling of `projectItems`):
     ```bash
     gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){issue(number:$n){title projectItems(first:5){nodes{project{id title}}}}}}' -f o={owner} -f r={repo} -F n={parent_issue_number}
     ```
   - If still no project → **skip** add + setsp on board (child keeps SP label only).

2. **Add each child to project** — pick by OS:
   - **Windows (PowerShell):** `pwsh -File .cursor/resources/script/add-to-project.ps1 -IssueUrl "{child_url}" -ProjectId "{project_id}"`
   - **macOS / Ubuntu / Git Bash / WSL:** `bash .cursor/resources/script/add-to-project.sh "{child_url}" "{project_id}"` *(needs `jq`)*
   See [CROSS-PLATFORM.md](../CROSS-PLATFORM.md).

### 3.6. Set Story Points in Project (Custom Field)

**Required:** Issue must **already be on Project V2** (step 3.5). Otherwise the script prints `No project found.` and **does not set SP** on the board.

**Two equivalent scripts** (same GraphQL logic):

| Environment | Command |
|-------------|---------|
| **PowerShell** (Windows, `pwsh`) | `pwsh -File .cursor/resources/script/setsp.ps1 -IssueUrl "{child_url}" -SpValue "{sp_value}"` |
| **Bash** (Ubuntu, macOS, Git Bash, WSL) — needs `jq` | `bash .cursor/resources/script/setsp.ps "{child_url}" "{sp_value}"` |

Run for **each** child. Script matches SP-like field names. Label `sp:3` on the issue **does not** sync to the Project SP column by itself — only `setsp.ps` / `setsp.ps1` do.

### 3.7. Translate Content to Vietnamese

Before creating GitHub issues, translate all Japanese content to Vietnamese:

**Translation Guidelines:**

* Maintain technical accuracy - preserve technical terms in English when appropriate
* Use professional/formal tone (similar to Japanese business style)
* Keep formatting consistent (bullet points, checkboxes, line breaks)
* Translate code comments if present in descriptions
* Common technical terms to preserve in English:
* API, endpoint, component, migration, middleware, unit test
* Framework names: Vue, Nuxt, Laravel, Jest, PHPUnit
* Git terminology: commit, merge, branch, pull request
* Database terms: schema, query, transaction, index
* Architecture patterns: MVC, repository, service layer



**Translation Process:**

1. Create Japanese title and body first based on plan.md
2. Translate the title to Vietnamese
3. Translate each body section to Vietnamese (説明→Mô tả, 要件→Yêu cầu, etc.)
4. Combine into bilingual format: Japanese section first, then Vietnamese section
5. Verify technical terms are consistent across both languages
6. Ensure formatting (checkboxes, lists, line breaks) is preserved

**Quality Checks:**

* Technical terms should be the same in both languages (e.g., "API", "component")
* Code examples should not be translated
* Issue numbers and references should remain unchanged
* Checkbox formatting must be preserved: `- [ ]`

### 4. Calculate Story Points (SP)

> **SP見積りは `sp-estimation` スキルの手順に従うこと。**
> Cursor がスキルを自動ロードするため、以下の要点のみ記載する。

**Key rules:**

* 1 SP = 1時間
* フィボナッチ値 (1, 2, 3, 5, 8, 13) で割り当てる
* 13 SP 超は MUST split
* **6軸フレームワーク** (コード量・複雑度・テスト・アーキテクチャ影響・外部依存・不確実性) で評価
* **MUST assign a single concrete number** (e.g., 3 SP) based on the specific task.

### 5. Inject into Parent Issue Tasklist

**Goal:** Update the Parent Issue to include links to the newly created child issues, enabling centralized tracking.

**⛔ UTF-8 / Japanese / Vietnamese content — AVOID MOJIBAKE**

* **Cause:** On **Windows**, `gh issue edit --body "$(gh issue view ... -q .body)..."` passes content through **CMD/PowerShell** with default encoding (CP932/1252) → **entire parent body** replaced with corrupted text (文字化け). Child issues created with short body or `--body-file` usually **stay correct**.
* **Required** when parent has **Japanese / CJK / Unicode**:
  1. Get current body from JSON, append tasklist line, write **one `.md` file** as **UTF-8 without BOM**.
  2. Run **`gh issue edit {n} --repo {owner}/{repo} --body-file path/to/file.md`** — do **not** use `--body` with long CJK strings.

**PowerShell (UTF-8 safe):**

```powershell
$repo = "owner/repo"
$num = 887
$body = (gh issue view $num --repo $repo --json body | ConvertFrom-Json).body
$newLine = "- [ ] https://github.com/owner/repo/issues/899 (SP: 3)"
$merged = $body + "`n" + $newLine
$path = Join-Path $env:TEMP "gh-issue-parent-body.md"
[System.IO.File]::WriteAllText($path, $merged, [System.Text.UTF8Encoding]::new($false))
gh issue edit $num --repo $repo --body-file $path
```

**Or single command (PowerShell):**  
`pwsh -File .cursor/resources/script/merge-parent-issue-body.ps1 -Repo "owner/repo" -ParentNum 887 -ChildUrl "https://..." -Sp 3`

**Bash (Ubuntu / macOS / Git Bash / WSL):**

```bash
export LANG=en_US.UTF-8
bash .cursor/resources/script/merge-parent-issue-body.sh "owner/repo" 887 "https://github.com/owner/repo/issues/899" 3
```

Or use `mktemp`, write body + new line as UTF-8, then `gh issue edit --body-file`.

**Child issues with bilingual body:** prefer **`gh issue create ... --body-file path.md`** (UTF-8 no BOM); do not pass long body via `--body "..."` on Windows.

**Instructions:**

1. **Retrieve current body:** `gh issue view` JSON → field `body`.
2. **Task list line:** `- [ ] {child_issue_url} (SP: {sp_value})` per new child.
3. **Update parent:** Concatenate old body + new line → **UTF-8 file** → **`gh issue edit --body-file`**.

**Do not use** (breaks encoding on Windows with Japanese body):

```bash
# FORBIDDEN — old pattern, mojibake when body contains Japanese
gh issue edit N --body "$(gh issue view N --json body -q .body)..."
```

---

## Output Files

* GitHub Issues created (but NOT on Project Board)
* Parent Issue updated with Tasklist links

---

## Usage Examples

**Standard Breakdown**

```
/breakdown 129

```

**Dry Run (Preview Only)**

```
/breakdown 129 --dry-run

```

---

## Integration with Other Commands

* **After `/plan**`: Use `/breakdown` to split plan into actionable issues.
* **Tasklist Tracking**: Developers click links in the Parent Issue to access Child Issues.
* **SP Rollup**: The `sp:{value}` label and Parent Tasklist entry allow automated tools to calculate total SP.

---

## Best Practices

1. **Default to 1 FE + 1 BE Issue**: Unless feature is exceptionally large (SP > 20), create exactly 2 issues total
2. **Review Plan First**: Ensure plan.md is complete and approved before breakdown
3. **Group Related Tasks**: Combine all FE tasks into one comprehensive FE issue, all BE tasks into one BE issue
4. **Balance Workload**: Try to balance SP between FE and BE teams (typically 5-10 SP per issue)
5. **Clear Dependencies**: Mark BE as independent, FE depends on BE for integration testing
6. **Size Appropriately**: Target 5-10 SP per issue for optimal sprint planning
7. **Comprehensive Acceptance Criteria**: Include all acceptance criteria for the entire layer in single issue
8. **Add Child to Project**: Add child issues to the same project as parent for SP tracking and Development linking
9. **Check Parent Link**: Verify that the Parent Issue contains the correct links in its Tasklist
10. **Resist Over-Splitting**: Don't create multiple issues just because there are multiple tasks - group them by layer

---

## Troubleshooting

**Issue Creation Fails:**

* Verify `gh auth status`
* Check repository permissions

**Parent Injection Fails:**

* Ensure you have write permissions to the Parent Issue.
* If automatic update fails, manually edit the Parent Issue to add: `- [ ] {child_url} (SP: {val})`

---

## Example Breakdown Scenario

**Input (from plan.md):**

* Feature: Implement user authentication with JWT
* Backend tasks: JWT generation, validation, login/logout API endpoints, backend unit tests
* Frontend tasks: Login/logout UI components, Vuex token management, frontend unit tests

**Output (breakdown with bilingual titles - Default Strategy):**

### ✅ Recommended: 2 Issues (1 FE + 1 BE)

* **Issue #465**: `[FE] 認証: ログイン/ログアウトUI・トークン管理・ユニットテスト / Xác thực: UI đăng nhập/đăng xuất, quản lý token với Unit Tests` **(8 SP)**

  * **Includes all FE tasks:**
    * 1.1. ログインフォームUIコンポーネント (Login form UI component)
    * 1.2. ログアウトボタンコンポーネント (Logout button component)
    * 1.3. Vuexでの認証状態管理 (Authentication state management in Vuex)
    * 1.4. トークン保存・取得ロジック (Token storage/retrieval logic)
    * 1.5. API client integration
    * 1.6. フロントエンドユニットテスト (Frontend unit tests)
  * Vietnamese body includes all corresponding Vietnamese translations
  * **Dependency**: Requires BE issue (#466) for integration testing

* **Issue #466**: `[BE] 認証: JWT生成・検証・API・ユニットテスト / Xác thực: Tạo JWT, xác thực, API với Unit Tests` **(6 SP)**
  * **Includes all BE tasks:**
    * 1.1. JWT生成ロジック (JWT generation logic)
    * 1.2. トークン検証ミドルウェア (Token validation middleware)
    * 1.3. ログインAPIエンドポイント (Login API endpoint)
    * 1.4. ログアウトAPIエンドポイント (Logout API endpoint)
    * 1.5. リクエスト検証 (Request validation)
    * 1.6. バックエンドユニットテスト (Backend unit tests)
  * Vietnamese body includes all corresponding Vietnamese translations
  * **Dependency**: None (can be developed independently)

**Total:** 2 issues, 14 SP (~14 hours)
**Parallel Development:** BE (#466) and FE (#465) can be developed simultaneously
**Integration Point:** After both are complete, conduct integration testing

**Parent Issue #100 Updated:**
```markdown
(Existing content...)

## Implementation Tasks
- [ ] https://github.com/org/repo/issues/465 (SP: 8)
- [ ] https://github.com/org/repo/issues/466 (SP: 6)

```

---

### ⚠️ Legacy Approach (Not Recommended): Multiple Small Issues

The old approach would create 4 separate issues:

* Issue #130: JWT logic only (4 SP)
* Issue #131: Login/logout API only (3 SP)
* Issue #132: UI components only (3 SP)
* Issue #133: Vuex management only (2 SP)

**Why this is NOT recommended:**

* ❌ More coordination overhead (4 issues instead of 2)
* ❌ Harder to track progress across related tasks
* ❌ Increased risk of inconsistent implementation
* ❌ More complex dependency management
* ❌ Difficult to assign clear ownership

**When to use multiple issues:**
Only when feature is exceptionally large (total SP > 20) or has truly independent sub-features.

**Note:** Each issue contains full bilingual body with all sections (Description, Requirements, Technical Details, Acceptance Criteria, Dependencies) in both Japanese and Vietnamese as per the template.
