# Plan Command

Generate implementation plan document for issue with AI Agent

## Parameters

-   **`issue_url`** (preferred): Full GitHub issue URL (e.g. `https://github.com/owner/repo/issues/129`). From URL derive owner, repo, issue_number; doc path = `docs/issues/{repo}/{issue_number}/` (**repo** = repo folder name).
-   `issue_number` (optional): Issue number in current repo; if omitted, auto-detect from latest doc.

## Instructions

Generate a detailed implementation plan document for the specified issue through interactive AI Agent collaboration.

**Instructions for AI Agent:**

**⛔ ABSOLUTE PROHIBITION: DO NOT EXECUTE ANY GIT COMMIT COMMANDS ⛔**

-   NEVER run `git commit` in any form
-   NEVER run `git add . && git commit`
-   NEVER suggest or execute commit operations
-   Planning phase MUST end with uncommitted changes

1. **Determine Issue and Doc Path** (doc path = `docs/issues/{repo}/{issue_number}/`, **repo** = repo folder name):
    - If `issue_url` is provided: Extract `owner`, `repo`, `issue_number` from URL. Use `gh issue view {issue_number} --repo {owner}/{repo}` for GitHub CLI.
    - If `issue_number` (plain number) is provided: Current repo: `gh repo view --json nameWithOwner -q .nameWithOwner` → parse `repo`.
    - If both omitted: Find most recently modified `docs/issues/*/*/issue.md`; from path get `repo` and `issue_number`; read `repository:` from file and use `--repo {repository}` for gh calls.
    - Verify `docs/issues/{repo}/{issue_number}/issue.md` exists.
2. **Fetch Issue Information**: Use optimized issue data retrieval (cached `docs/issues/{repo}/{issue_number}/issue.md` first, GitHub CLI fallback with `--repo` when applicable)
3. **Interactive Analysis**: Analyze the issue content and discuss implementation approach with the user
4. **Generate Implementation Plan**: Create a comprehensive implementation plan using the integrated template structure with dynamic task breakdown
5. **Save Document**: Save the plan to {output_path} (default: `docs/issues/{repo}/{issue_number}/plan.md`) (WITHOUT committing)

**🚨 CRITICAL: NEVER COMMIT CHANGES DURING PLANNING PHASE 🚨**

**STRICT RULE**: Do NOT use `git commit`, `git add && git commit`, or any commit commands during planning phase.

-   All changes MUST remain uncommitted
-   Changes will be committed later in the `/pr` phase
-   This ensures proper workflow separation and testing before committing
-   Violating this rule breaks the development workflow

**Implementation Plan Document Structure:**

```markdown
# Issue #{issue_number}: {title} - Implementation Plan

## 概要 (Overview)

{brief_overview_of_requirements_and_current_vs_improved_state}

---

## FE (Frontend)

### 1. Files need to edit:

#### 1.1. File: {frontend_file_path_1}

##### 1.1.1. {frontend_task_1_name}

{frontend_task_1_description}

**既存コード** (line X-Y):

-   {description_of_existing_code}

**変更内容:**

-   {detailed_changes_needed}

##### 1.1.2. {frontend_task_2_name}

{frontend_task_2_description}

**変更内容:**

-   {detailed_changes_needed}

{Additional frontend tasks as needed...}

#### 1.2. File: {frontend_file_path_2} (if needed)

##### 1.2.1. {frontend_task_name}

{task_description_and_changes}

---

## BE (Backend)

### 1. Files need to edit:

#### 1.1. File: {backend_file_path_1}

##### 1.1.1. {backend_task_1_name}

{backend_task_1_description}

**現在の実装** (line X-Y):

-   {description_of_current_implementation}

**変更内容:**

-   {detailed_changes_needed}
-   {code_examples_if_helpful}

##### 1.1.2. {backend_task_2_name}

{backend_task_2_description}

**変更内容:**

-   {detailed_changes_needed}

{Additional backend tasks as needed...}

#### 1.2. File: {backend_file_path_2} (if needed)

##### 1.2.1. {backend_task_name}

{task_description_and_changes}

---

## 実装順序 (Implementation Order)

1. **Backend 実装** (dependency_status)

    - Task references

2. **Frontend 実装** (dependency_status)

    - Task references

3. **統合テスト**
    - Integration points to test

---

## 見積もり工数 (Estimated Effort)

-   **Backend**: X-Y 時間

    -   Task breakdown with hours

-   **Frontend**: X-Y 時間
    -   Task breakdown with hours

**合計**: X-Y 時間

---

## 技術的な注意事項 (Technical Notes)

1. **パフォーマンス考慮:**

    - Performance considerations

2. **UX 考慮:**

    - UX considerations

3. **データ整合性:**

    - Data integrity considerations

4. **既存機能との互換性:**
    - Compatibility with existing features
```

**Issue Resolution Order (all commands):**

1. `issue_url` provided → parse `owner/repo/number` from URL; use `--repo owner/repo` with all `gh` calls; doc path = `docs/issues/{repo}/{issue_number}/`
2. `issue_number` provided → current repo: get owner/repo via `gh repo view`; doc path = `docs/issues/{repo}/{issue_number}/`
3. Neither provided → auto-detect: search `docs/issues/*/*/issue.md` (most recently modified); from path extract `repo` and `issue_number`; read `repository:` from file and use `--repo {repository}` for gh calls

**Auto-Detection Process:**

-   Search `docs/issues/*/*/issue.md` for the most recently modified file (pattern: repo / issue_number)
-   From directory structure extract `repo` and `issue_number`
-   Read `repository:` from the found `issue.md`; if present, pass `--repo {repository}` to GitHub CLI calls
-   Verify the issue exists and is accessible via GitHub CLI

**Content Generation Process:**

-   Determine issue number and repo (from parameter or most recent `/issue` command)
-   Retrieve issue data using optimized caching strategy:
    -   First: Try cached `docs/issues/{repo}/{issue_number}/issue.md`
    -   Fallback: GitHub CLI if cached file not available
-   **Search and analyze codebase** to identify files that need modification:
    -   Use `codebase_search` to find relevant components, pages, APIs
    -   Use `grep` to find specific functions, methods, endpoints
    -   Read existing code to understand current implementation
-   **Organize tasks by layer** (Frontend / Backend):
    -   **Frontend (FE)**: Separate section for all UI-related changes
        -   List each file that needs editing
        -   Break down each file into specific tasks (numbered 1.1.1, 1.1.2, etc.)
        -   Include line numbers of existing code
        -   Provide detailed change descriptions
    -   **Backend (BE)**: Separate section for all server-side changes
        -   List each file that needs editing (Controllers, Repositories, Models, etc.)
        -   Break down each file into specific tasks (numbered 1.1.1, 1.1.2, etc.)
        -   Include line numbers of current implementation
        -   Provide code examples where helpful
-   **Identify dependencies and implementation order**:
    -   Determine if FE and BE can be developed in parallel
    -   Mark which tasks must be completed before others
    -   Note integration points between layers
-   **Estimate effort** for each layer:
    -   Separate estimates for Backend and Frontend
    -   Break down by individual tasks
    -   Provide total estimate range
-   **Include technical notes**:
    -   Performance considerations
    -   UX considerations
    -   Data integrity concerns
    -   Compatibility with existing features
-   Save to specified file path

**Template Usage Guidelines:**

-   Use hierarchical numbering for tasks (1.1.1, 1.1.2, 1.2.1, etc.)
-   Always reference line numbers when describing existing code
-   Provide concrete examples and code snippets where helpful
-   Keep FE and BE sections strictly separated
-   Write detailed change descriptions, not just task names
-   Include both Japanese headers and English content for clarity

**Performance Optimization:**

-   **Cache Strategy**: Reuse existing `docs/issues/{repo}/{issue_number}/issue.md` to avoid repeated GitHub API calls
-   **Fallback Support**: Automatic GitHub API fallback if cached data unavailable
-   **Speed Improvement**: 1-2 seconds faster execution by eliminating redundant API calls

**Issue**: {issue_url or issue_number or auto-detected}
**Output**: `docs/issues/{repo}/{issue_number}/plan.md`
