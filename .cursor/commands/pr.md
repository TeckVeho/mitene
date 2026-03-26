# PR Command

Create Pull Request with streamlined 2-step process: commit changes and GitHub PR creation with automatic issue linking

## Parameters

- **`issue_url`** (preferred): Full GitHub issue URL. Derive owner, repo, issue_number from URL; doc path = `docs/issues/{repo}/{issue_number}/` (**repo** = short repo name).
- `issue_number` (optional): Issue number in current repo; if omitted, auto-detect from nearest doc.
- `auto_link` (optional): Automatically link PR to issue (defaults to true)

## Instructions

Create Pull Request through interactive AI Agent collaboration with streamlined 2-step process and automatic issue linking.

**Instructions for AI Agent:**

**🔗 CRITICAL: AUTOMATIC ISSUE LINKING 🔗**
- ALWAYS link PR to the corresponding issue
- **Same-repository issue**: Use `Closes #{issue_number}` in commit messages and PR body
- **Cross-repository issue** (issue is in a different repo from the PR): Use `Closes {owner}/{repo}#{issue_number}` format so GitHub can link across repositories
- Determine which format to use by comparing the PR repository (`gh repo view --json nameWithOwner`) with the `repository:` metadata from `issue.md`
- Ensure GitHub automatically closes the issue when PR is merged
- **GitHub Projects Development section**: When PR body contains `Closes #X`, GitHub auto-links the PR to the issue. If the issue is in a Project, the PR appears in the Development section. No extra API call needed.
- This maintains proper issue tracking and project management

**📄 CRITICAL: PR BODY SAVING 📄**
- **CREATE pr.md FILES**: This command MUST create pr.md files in docs/issues/{repo}/{issue_number}/ before committing
- **Evidence Section**: Include test results and execution commands in PR body
- **Pre-commit Documentation**: Save PR body content locally for tracking and review

**Streamlined Workflow**: This command handles committing changes and creating PR with automatic issue linking. Development should be done with `/dev` (no commits), tested with `/test`, then committed and PR created with `/pr`.

## Step 0: Issue Number and Doc Path Determination (doc path = `docs/issues/{repo}/{issue_number}/`, **repo** = short repo name)

1. **Determine Issue Number, Repository, and repo**:
   - If `issue_url` is provided: Extract `owner`, `repo`, `issue_number` from URL. Store `{repository}` = `owner/repo`. Use `--repo {repository}` with all GitHub CLI issue-related calls.
   - If `issue_number` (plain number) is provided: Use current repository: run `gh repo view --json nameWithOwner -q .nameWithOwner` → parse `repo`.
   - If both are omitted: Find most recently modified `docs/issues/*/*/issue.md`; from path get `repo` and `issue_number`; read `repository:` from file and use `--repo {repository}` for gh issue calls.
   - Check for existing `docs/issues/{repo}/{issue_number}/issue.md` file to ensure issue data is available.

## Step 1: Git Status Validation and PR Body Generation

1. **Check Git Status**: Run `git --no-pager status` to show current repository state (with pager disabled)
2. **Display Status Summary**: Show all modified, added, and deleted files with status indicators using `git --no-pager diff --name-status origin/develop..HEAD`
3. **Fetch Issue Data**: Get issue #{issue_number} information using optimized caching strategy (cached local file first, GitHub CLI fallback with `--repo {repository}` when applicable)
4. **Load Test Results**: Read test results from `docs/issues/{repo}/{issue_number}/evidence/test-results.json` if available
5. **Load Screenshots**: Scan `docs/issues/{repo}/{issue_number}/evidence/` directory for PNG/JPG image files:
   - Look for files with extensions: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`
   - Detect current repository info by running: `gh repo view --json nameWithOwner -q .nameWithOwner`
   - Generate GitHub raw URLs with format: `https://github.com/{repo_name_with_owner}/blob/{current_branch}/docs/issues/{repo}/{issue_number}/evidence/{filename}?raw=true`
   - Create descriptive image titles from filenames (remove issue prefix, convert hyphens to spaces)
   - Sort images alphabetically by filename
6. **Generate PR Body**: Create comprehensive PR body including:
   - Issue reference and "Closes #{issue_number}" for automatic linking
   - Implementation summary and key changes
   - **Screenshots Section** with image links using raw GitHub URLs
   - **Evidence Section** with test results and execution details
7. **Save PR Body**: Write PR body content to `docs/issues/{repo}/{issue_number}/pr.md` **BEFORE** committing
8. **Display PR Body Preview**: Show generated PR body content for user review
9. **User Confirmation**: Ask user "Do you want to create a PR? (y/n)" and wait for confirmation
10. **Proceed Only if Confirmed**: Continue to Step 2 only if user confirms with 'y' or 'yes'

## Step 2: Commit and Push Verification

1. **Check Uncommitted Changes**: Run `git --no-pager status --porcelain 2>/dev/null` to check for uncommitted changes (with pager disabled)
2. **Stage and Commit Changes**: If uncommitted changes exist:
   - Run `git add . >/dev/null 2>&1` to stage all changes (includes all source code AND documentation files)
   - **CRITICAL: Include Documentation**: Ensure all development documentation is committed:
     - `docs/issues/{repo}/{issue_number}/issue.md` - Issue details
     - `docs/issues/{repo}/{issue_number}/plan.md` - Implementation plan
     - `docs/issues/{repo}/{issue_number}/dev.md` - Development log
     - `docs/issues/{repo}/{issue_number}/test.md` - Test report
     - `docs/issues/{repo}/{issue_number}/pr.md` - PR body content
     - `docs/issues/{repo}/{issue_number}/evidence/` - Test evidence and coverage data
   - Create comprehensive commit message including:
     - Issue reference and main changes
     - Key improvements and features
     - Test results summary
     - Documentation updates
     - "Closes #{issue_number}" to auto-close issue
   - Run `git commit -m "..." --no-edit --quiet >/dev/null 2>&1` with detailed message
3. **Push to Remote**: Check if local branch exists on remote:
   - Run `git push origin {current_branch} --quiet --no-progress` to push commits
   - Ensure remote branch is up to date before PR creation
   - **Documentation Tracking**: All development documentation will be available in the PR for review

## Step 3: GitHub Pull Request Creation with Issue Linking

1. **Create GitHub PR**: Use `gh pr create` command to create pull request:
   - Title: `{type}: {issue_title}`
   - Body: Generated PR body with Evidence section
   - Base branch: `develop`
   - Head branch: Current branch
2. **Handle PR Creation Errors**: If PR creation fails:
   - Check if commits exist between base and head branches
   - Verify remote branch is properly pushed
   - Retry PR creation after resolving issues
3. **Display PR Information**: Show created PR URL and linked issue status
4. **Confirmation**: Confirm successful PR creation and issue linking

**Process Flow:**
```
Step 0: Issue Number Determination
├── Check if issue_number is provided
├── If not, auto-detect from docs/issues/*/*/issue.md (path gives repo, issue_number)
└── Verify issue exists and is accessible

Step 1: Git Status Check and PR Body Generation
├── Run git --no-pager status (pager disabled)
├── Display file changes with git --no-pager diff --name-status origin/develop..HEAD
├── Fetch issue data for PR content generation
├── Load test results from docs/issues/{repo}/{issue_number}/evidence/test-results.json
├── Generate PR body with Evidence section including test results
├── Save PR body to docs/issues/{repo}/{issue_number}/pr.md BEFORE committing
├── Display PR body preview for user review
└── Ask: "Do you want to create a PR? (y/n)"

Step 2: Commit and Push Verification
├── Check git --no-pager status --porcelain 2>/dev/null for uncommitted changes (pager disabled)
├── If changes exist: git add . >/dev/null 2>&1 && git commit -m "..." --no-edit --quiet >/dev/null 2>&1
│   └── Includes ALL files: source code + documentation (issue.md, plan.md, dev.md, test.md, pr.md, evidence/)
├── Push to remote: git push origin {current_branch} --quiet --no-progress
└── Verify remote branch is up to date

Step 3: GitHub PR Creation with Issue Linking
├── Run gh pr create --title "..." --body "..." --base develop
├── Handle errors: check commits between branches, retry if needed
├── Display PR URL and linked issue status
└── Confirm completion and issue linking
```

**Auto-Detection Process:**
- Search `docs/issues/*/*/issue.md` for the most recently modified file (path: repo / issue_number)
- Extract `repo` and `issue_number` from the directory structure
- Read `repository:` metadata from the found `issue.md`; if present, use `--repo {repository}` for all `gh issue` calls
- Verify the issue exists and is accessible via GitHub CLI

**Issue Data Retrieval Optimization:**
- **Cache Strategy**: Reuse existing issue.md files to avoid repeated GitHub API calls
- **Fallback Support**: Automatic GitHub API fallback if cached data unavailable
- **Speed Improvement**: 1-2 seconds faster execution by eliminating redundant API calls

**🔗 Issue Linking Requirements:**
- **Commit Messages**: MUST include closing reference for automatic issue closure
  - Same-repo: `Closes #{issue_number}`
  - Cross-repo: `Closes {owner}/{repo}#{issue_number}`
- **PR Body**: MUST include the same closing reference to link PR to issue
- **PR Title**: Should follow format "{type}: {issue_title}" for consistency
- **Verification**: Confirm issue linking is successful after PR creation

**Evidence Section Implementation Details:**

1. **Command-Result Pairing**:
   - Each command must be paired with its specific result
   - Use numbered sections (1, 2, 3, 4) for clear organization
   - **Command format**: Use code blocks with bash syntax highlighting
   - **Result format**: Use bullet points with key metrics and status

2. **Test Results Loading**:
   - Read `docs/issues/{repo}/{issue_number}/evidence/test-results.json`
   - Parse backend and frontend test results
   - Extract test counts, pass/fail status, coverage data
   - **CRITICAL: NO TEST RESULT FALSIFICATION**: If test results are missing or unavailable, explicitly state "No test results available" - NEVER create fake or simulated test results

3. **Command Execution Documentation**:
   - **Backend Testing**: Document `yarn test:unit` command and results
   - **Build Verification**: Document `yarn build` command and results
   - **Type Checking**: Document `npx tsc --noEmit --strict` command and results
   - **Code Linting**: Document `npx eslint src` command and results

4. **Result Formatting**:
   - Include key metrics: test counts, coverage percentages, error counts
   - Show execution time for performance-critical commands
   - Display status (SUCCESS/FAILED) clearly
   - **CRITICAL: NO TEST RESULT FALSIFICATION**: If test results are missing or unavailable, explicitly state "No test results available" - NEVER create fake or simulated test results

**Required Commands:**
- `git --no-pager status` - Check repository state (with pager disabled)
- `git --no-pager status --porcelain 2>/dev/null` - Check for uncommitted changes (with pager disabled)
- `git --no-pager diff --name-status origin/develop..HEAD` - Show file changes (with pager disabled)
- `git add . >/dev/null 2>&1` - Stage all changes (if needed)
- `git commit -m "..." --no-edit --quiet >/dev/null 2>&1` - Commit changes with "Closes #{issue_number}" (if needed)
- `git push origin {branch} --quiet --no-progress` - Push commits to remote (if needed)
- `gh issue view {issue_number} [--repo {owner}/{repo}] --json title,body,labels,assignees,state,createdAt,updatedAt,url` - Get issue data for PR content (add `--repo` for cross-repository issues)
- `gh pr create --title "..." --body "..." --base develop` - Create GitHub PR with issue linking
- **File Operations**: Read test-results.json, write pr.md files, scan evidence directory for images

**Screenshots Section Template:**
```markdown
## Screenshots

{screenshot_links}

Each image shows the implementation results and can be viewed by clicking the links above.

**Example Screenshot Link Generation:**
- File: `issue-168-resolved-alerts-tab-with-pagination.png`
- Title: `Resolved Alerts Tab with Pagination`
- Detect repo: `gh repo view --json nameWithOwner -q .nameWithOwner` → e.g. `TeckVeho/your-repo`
- URL: `https://github.com/{repo_name_with_owner}/blob/168-feat-alerts-tab-pagination/docs/issues/{repo}/168/evidence/issue-168-resolved-alerts-tab-with-pagination.png?raw=true`
- Markdown: `![Resolved Alerts Tab with Pagination](https://github.com/{repo_name_with_owner}/blob/168-feat-alerts-tab-pagination/docs/issues/{repo}/168/evidence/issue-168-resolved-alerts-tab-with-pagination.png?raw=true)`
```

**Evidence Section Template:**
```markdown
## Evidence

### 1. Backend Testing
**Command:**
```bash
{backend_test_command}
```

**Result:**
{backend_test_results}

### 2. Build Verification
**Command:**
```bash
{build_command}
```

**Result:**
{build_results}

### 3. Type Checking
**Command:**
```bash
{type_check_command}
```

**Result:**
{type_check_results}

### 4. Code Linting
**Command:**
```bash
{lint_command}
```

**Result:**
{lint_results}
```

**Command-Result Mapping:**
- **Backend Testing**: `cd backend && yarn test:unit` → Test results with coverage
- **Build Verification**: `yarn build` → Build status and error count
- **Type Checking**: `npx tsc --noEmit --strict` → Type check status and error count
- **Code Linting**: `npx eslint src` → Lint status and error/warning count

**When NO test results are available:**
```markdown
### Test Execution Summary
⚠️ **No test results available**
- Tests have not been executed or results are not accessible
- Please run `/test` command to execute tests before creating PR
- Test results file: `docs/issues/{repo}/{issue_number}/evidence/test-results.json` not found
```

**Key Features:**
- **PR Body Saving**: Creates pr.md files in docs/issues/{repo}/{issue_number}/ **BEFORE** committing
- **Evidence Section**: Includes comprehensive test results and execution details in command-result format
- **Command-Result Pairing**: Each command is paired with its specific result for clear traceability
- **Test Integration**: Automatically loads and formats test results from evidence files
- **No Test Falsification**: NEVER creates fake test results - explicitly states when tests are not available
- **Automatic Issue Linking**: Every PR automatically links to its corresponding issue
- **Consistent Formatting**: Standardized PR titles and commit messages
- **Error Handling**: Robust error handling for Git and GitHub operations
- **Pre-commit Documentation**: PR body is generated and saved before any git operations
- **Clear Organization**: Numbered sections (1, 2, 3, 4) for easy navigation and verification
- **Complete Documentation Tracking**: All development documentation (issue.md, plan.md, dev.md, test.md, pr.md, evidence/) is committed and pushed with the PR
- **Documentation Review**: Reviewers can access complete development history and evidence through the PR

**Issue**: {issue_url or issue_number or auto-detected}
**Auto Link**: {auto_link (defaults to true)}
