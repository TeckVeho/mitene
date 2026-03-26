# Dev Command

Develop code using flexible development methodology with AI Agent

## Purpose (Goal)
- Implement requested functionality based on issue requirements
- Record development process, logs, and decisions
- Ensure changes remain uncommitted for testing and review phases

## Parameters
- **`issue_url`** (preferred): Full GitHub issue URL. Derive owner, repo, issue_number from URL; doc path = `docs/issues/{repo}/{issue_number}/` (**repo** = short repo name).
- `issue_number` (optional): Issue number in current repo; if omitted, auto-detect from nearest doc.
- `output_path` (optional): Output directory path (defaults to current directory)
- `--parent` (optional): Parent issue number (for child issues created by `/breakdown`)

## Workflow Position
- This command should be run **after `/issue` (issue creation)** and **before `/test` (validation)**

## Critical Rules
**⛔ ABSOLUTE PROHIBITION: DO NOT EXECUTE ANY GIT COMMIT COMMANDS ⛔**
- NEVER run `git commit` in any form
- NEVER run `git add . && git commit`
- NEVER suggest or execute commit operations
- Development phase MUST end with uncommitted changes

---

## Instructions for AI Agent

1. **Determine Issue Number and Doc Path** (doc path = `docs/issues/{repo}/{issue_number}/`, **repo** = short repo name)
   - If `issue_url` is provided: Extract `owner`, `repo`, `issue_number` from URL. Use `--repo {owner}/{repo}` with all GitHub CLI calls.
   - If `issue_number` (plain number) is provided: Use current repository: run `gh repo view --json nameWithOwner -q .nameWithOwner` → parse `repo`.
   - If both are omitted: Find most recently modified `docs/issues/*/*/issue.md`; from path get `repo` and `issue_number`; read `repository:` from file and use `--repo {repository}` for gh calls.
   - Verify that `docs/issues/{repo}/{issue_number}/issue.md` exists

2. **Check Parent-Child Relationship** (if applicable)
   - If `--parent` is specified or issue body contains "Relates to #" or "Parent Issue":
     - Extract parent issue number (and parent repo from context or matching doc path)
     - If `docs/issues/{repo}/{parent_issue_number}/breakdown.md` exists, use it; otherwise continue with plan only
     - Load parent context (`plan.md`, `breakdown.md` if present) from `docs/issues/{repo}/{parent_issue_number}/` for reference
     - Display parent issue link and relationship type ([FE]/[BE])
     - Identify dependencies from breakdown report
   - If this is a standalone issue:
     - Load plan.md if available for context
     - Proceed with standard development workflow

3. **Choose Development Approach**
   - TDD (Test-Driven Development) or Direct Implementation
   - Decide based on complexity and testability of functionality
   - For child issues: Follow task specifications from parent plan

4. **Interactive Development Process**
   - Guide the user through the chosen approach
   - Provide implementation support with explanations
   - Reference parent plan and dependencies if applicable

5. **Code Implementation**
   - Assist in implementing required functionality
   - Ensure code quality, readability, and maintainability
   - Follow architecture decisions from parent plan

6. **Validation**
   - Guide user through manual or automated validation
   - Do NOT commit during validation
   - Verify integration points with related issues if applicable

7. **Refactoring**
   - Suggest and apply improvements
   - Maintain working functionality

8. **Final Check**
   - Confirm all changes remain uncommitted
   - Record development details in `docs/issues/{repo}/{issue_number}/dev.md`
   - Include parent issue reference if applicable

---

## Development Workflow Phases

### Phase 1: Requirements Analysis
- Analyze issue requirements
- Choose development approach
- Clarify functionality and strategy

### Phase 2: Implementation
- **TDD**: Write tests first, then minimal code
- **Direct**: Implement functionality directly
- Focus on correctness and clarity

### Phase 3: Validation
- Run tests (if TDD) or manual checks (if direct)
- Verify expected behavior

### Phase 4: Refactoring
- Clean up code
- Improve readability and maintainability
- Ensure functionality remains intact

---

## 🔒 Development Output Requirements 🔒
- All changes MUST remain uncommitted
- Development log must be saved at:
  - `docs/issues/{repo}/{issue_number}/dev.md`

---

## Code Quality Guidelines
- **Simple**: Implement simplest working solution
- **Readable**: Code should be self-explanatory
- **Maintainable**: Easy to extend or modify
- **Efficient**: Performant enough for context
- **Secure**: Handle errors gracefully

---

**Issue**: {issue_url or issue_number or auto-detected}
**Output**: `docs/issues/{repo}/{issue_number}/dev.md`
