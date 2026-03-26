# Cursor Commands — Full Workflow Guide

This guide explains how to use the Cursor custom commands for a full **issue → plan → breakdown → dev → test → pr** workflow. Commands are defined in `.cursor/commands/` and can be shared via a git submodule (e.g. `cursor-shared-skills`).

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Setup (first time or new clone)](#2-setup-first-time-or-new-clone)
3. [Doc path convention](#3-doc-path-convention)
4. [Workflow overview](#4-workflow-overview)
5. [Step-by-step: each command](#5-step-by-step-each-command)
6. [Parameters and auto-detection](#6-parameters-and-auto-detection)
7. [Updating commands / submodule](#7-updating-commands--submodule)
8. [File structure](#8-file-structure)
9. [Skills (optional)](#9-skills-optional)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

| Tool | How to install | Purpose |
|------|----------------|---------|
| **GitHub CLI (`gh`)** | [cli.github.com](https://cli.github.com) → run `gh auth login` | Fetch issues, create PRs, link issues |
| **Git** | Standard install | Branching, commits, submodule |
| **jq** (optional) | `brew install jq` (macOS) / `apt install jq` (Linux) | Used by some scripts (e.g. setsp) |

Ensure you are logged in: `gh auth status`.

---

## 2. Setup (first time or new clone)

### Option A: Commands are in this repo (no submodule)

If `.cursor/commands/` already exists with the command `.md` files, no setup is needed. Skip to [§3 Doc path convention](#3-doc-path-convention).

### Option B: Commands come from a submodule (e.g. cursor-shared-skills)

**First time adding the submodule:**

```bash
# From repository root
git submodule add https://github.com/TeckVeho/cursor-shared-skills.git .cursor-shared-skills
bash .cursor-shared-skills/setup.sh
```

Add to `.gitignore` (so symlinks are not committed):

```bash
echo ".cursor/commands" >> .gitignore
echo ".cursor/skills" >> .gitignore
```

Then commit:

```bash
git add .gitmodules .cursor-shared-skills .gitignore
git commit -m "chore: add cursor-shared-skills submodule"
```

**After someone else clones the repo:**

```bash
git clone <repo-url>
cd <repo>
git submodule update --init --recursive
bash .cursor-shared-skills/setup.sh
```

`setup.sh` creates (or updates) symlinks so that `.cursor/commands` and `.cursor/skills` point to the submodule. Cursor will then see all commands under `.cursor/commands/`.

---

## 3. Doc path convention

All issue-related docs are stored under:

- **`docs/issues/{repo}/{issue_number}/`**

Where:

- **`repo`** = repository name (e.g. `izumi-works`), derived from the issue URL or from `gh repo view`.
- **`issue_number`** = GitHub issue number (e.g. `129`).

**Examples:**

- `docs/issues/izumi-works/129/issue.md`
- `docs/issues/izumi-works/129/plan.md`
- `docs/issues/izumi-works/129/dev.md`
- `docs/issues/izumi-works/129/test.md`
- `docs/issues/izumi-works/129/pr.md`
- `docs/issues/izumi-works/129/evidence/` (test outputs, screenshots, etc.)

Every command that needs the “current issue” can infer `repo` and `issue_number` from **issue_url** (preferred) or from the most recently modified `docs/issues/*/*/issue.md`.

---

## 4. Workflow overview

Run the commands in this order:

```
/issue  →  /plan  →  /breakdown  →  /dev  →  /test  →  /pr
```

| Step | Command | What it does |
|------|---------|--------------|
| 1 | `/issue` | Asks for issue URL (and paths), creates branch, fetches issue, saves `issue.md` under `docs/issues/{repo}/{issue_number}/`. **No commit.** |
| 2 | `/plan` | Reads issue (and codebase), generates implementation plan, saves `plan.md`. **No commit.** |
| 3 | `/breakdown` | Splits plan into FE/BE child issues, assigns Story Points, updates parent issue task list. **No commit.** |
| 4 | `/dev` | Implements code (and optional tests) per plan/breakdown; writes `dev.md`. **No commit.** |
| 5 | `/test` | Runs tests, saves evidence under `evidence/`, writes `test.md`. **No commit.** |
| 6 | `/pr` | Builds PR body (with evidence), saves `pr.md`, then **commits**, pushes, and creates the PR (with issue link). |

**Important:** Commits happen **only** in `/pr`. Do not commit in `/issue`, `/plan`, `/breakdown`, `/dev`, or `/test`.

---

## 5. Step-by-step: each command

### Step 1: `/issue`

**Purpose:** Start from a GitHub issue: get details, create a dev branch, and save structured context for the rest of the workflow.

**What you need:**

1. **Issue URL** (required when prompted)  
   Example: `https://github.com/owner/repo/issues/129`  
   Must match: `https://github.com/.*/issues(/\d+)?`

2. **Paths** (you can accept defaults or override):  
   - Frontend path (e.g. `./frontend`)  
   - Backend path (e.g. `./backend`)  
   - Migrations path (e.g. `./backend/migrations`)  
   - Optional: API docs, tests path, workspace root  

**What the agent does:**

- Parses issue URL → `owner`, `repo`, `issue_number`; doc path uses **repo** (repo name).
- Fetches issue via `gh issue view` (no browser).
- Creates branch: `{issue_number}-feat-{short-desc}` (or fix/hotfix).
- Creates `docs/issues/{repo}/{issue_number}/issue.md` with Context/Codebase Paths and issue metadata.
- Does **not** commit.

**Example:**

```
/issue
```
Then answer the prompts (Issue URL, frontend path, backend path, etc.).

Or with URL and no prompts (if paths are already configured):

```
/issue https://github.com/owner/repo/issues/129 --no-prompts
```

**Optional:** Run the full pipeline in one go:

```
/issue 129 --auto
```
Respects `--skip-plan` and `--skip-breakdown` if you want to skip those phases.

---

### Step 2: `/plan`

**Purpose:** Produce a detailed implementation plan (FE/BE tasks, order, effort) and save it as `plan.md`.

**Input:** Prefer **issue_url**; otherwise issue number for current repo, or auto-detect from the latest `docs/issues/*/*/issue.md`.

**What the agent does:**

- Resolves issue (from URL, number, or auto-detect) and doc path `docs/issues/{repo}/{issue_number}/`.
- Reads issue from cached `issue.md` or fetches via `gh`.
- Analyzes codebase (search/grep) to find files to change.
- Writes a structured plan (FE section, BE section, order, estimates, technical notes) to `docs/issues/{repo}/{issue_number}/plan.md`.
- Does **not** commit.

**Example:**

```
/plan https://github.com/owner/repo/issues/129
/plan 129
/plan
```
(last form uses auto-detect)

---

### Step 3: `/breakdown`

**Purpose:** Turn the plan into actionable GitHub issues: typically **one FE issue** and **one BE issue**, with Story Points and a task list on the parent issue.

**Input:** Same as `/plan`: **issue_url** preferred, then issue number, then auto-detect.

**What the agent does:**

- Reads `docs/issues/{repo}/{issue_number}/plan.md`.
- Creates child issues via `gh issue create` (FE and BE, with labels e.g. `frontend`, `backend`, `sp:N`).
- Does **not** add child issues to the Project Board (only the parent stays on the board).
- Updates the **parent** issue body with a task list: `- [ ] <child_issue_url> (SP: N)`.
- Uses the **sp-estimation** skill (if loaded) for Story Points (e.g. 1 SP = 1 hour, Fibonacci).
- Does **not** commit.

**Example:**

```
/breakdown https://github.com/owner/repo/issues/129
/breakdown 129 --dry-run
```

Use `--dry-run` to see the breakdown without creating issues.

---

### Step 4: `/dev`

**Purpose:** Implement the feature (or fix) following the plan and optional breakdown; log decisions in `dev.md`.

**Input:** **issue_url** preferred, or issue number, or auto-detect. Optional `--parent` for child issues.

**What the agent does:**

- Resolves issue and doc path `docs/issues/{repo}/{issue_number}/`.
- If `--parent` or “Parent Issue” in body: loads parent context from `docs/issues/{repo}/{parent_issue_number}/` (plan.md, breakdown.md if present).
- Implements code (TDD or direct), keeps changes uncommitted.
- Writes `docs/issues/{repo}/{issue_number}/dev.md`.
- Does **not** commit.

**Example:**

```
/dev https://github.com/owner/repo/issues/129
/dev 129 --parent 100
```

---

### Step 5: `/test`

**Purpose:** Run tests, store evidence (logs, coverage, screenshots), and write a test/review report in `test.md`.

**Input:** **issue_url** preferred, or issue number, or auto-detect.

**What the agent does:**

- Resolves issue and doc path `docs/issues/{repo}/{issue_number}/`.
- Runs the project’s test suite (e.g. Jest, pytest).
- Saves raw results under `docs/issues/{repo}/{issue_number}/evidence/` (e.g. `test-results.json`, logs).
- Writes `docs/issues/{repo}/{issue_number}/test.md` (summary, pass/fail, coverage, requirements vs implementation, review notes).
- Does **not** commit. Does **not** fabricate results; if tests are missing or fail, that is stated clearly.

**Example:**

```
/test 129
/test
```

---

### Step 6: `/pr`

**Purpose:** Generate PR body (with evidence), save it to `pr.md`, then commit, push, and create the PR with automatic issue linking.

**Input:** Same as above: **issue_url** preferred, or issue number, or auto-detect.

**What the agent does:**

1. **Resolve issue and doc path** (`docs/issues/{repo}/{issue_number}/`).
2. **Build PR body:** issue reference, summary, screenshots (from `evidence/`), test evidence (from `evidence/test-results.json`). No fake test data.
3. **Save** PR body to `docs/issues/{repo}/{issue_number}/pr.md` **before** any commit.
4. **Ask for confirmation** (“Do you want to create a PR? (y/n)”).
5. If yes: **stage all** (code + docs: issue.md, plan.md, dev.md, test.md, pr.md, evidence/), **commit** (message includes “Closes #123” or cross-repo “Closes owner/repo#123”), **push**.
6. **Create PR** with `gh pr create` (base: `develop`), so the issue is linked and will close on merge.

**Example:**

```
/pr 129
/pr
```

---

## 6. Parameters and auto-detection

**Preferred input:** **`issue_url`** (full URL, e.g. `https://github.com/owner/repo/issues/129`).  
From the URL the agent gets `owner`, `repo`, and `issue_number`; doc path is always `docs/issues/{repo}/{issue_number}/`.

**Alternative:**

- **`issue_number`** only: use current repository (agent runs `gh repo view` to get repo name for the doc path).
- **Nothing:** auto-detect from the **most recently modified** `docs/issues/*/*/issue.md`; the path gives `repo` and `issue_number`; `issue.md` may contain `repository: owner/repo` for `gh` calls.

**Cross-repository:** If the issue is in another repo, always pass **issue_url**. The agent will use `--repo owner/repo` for `gh` and, for PR/commit, use “Closes owner/repo#123” so the issue links and closes correctly.

---

## 7. Updating commands / submodule

If commands are updated in the submodule repository:

```bash
cd .cursor-shared-skills
git pull origin main
cd ..
bash .cursor-shared-skills/setup.sh
git add .cursor-shared-skills
git commit -m "chore: update cursor-shared-skills submodule"
```

---

## 8. File structure

**Repository root (with submodule):**

```
<project-root>/
├── .cursor-shared-skills/     # submodule
│   ├── commands/
│   │   ├── issue.md
│   │   ├── plan.md
│   │   ├── breakdown.md
│   │   ├── dev.md
│   │   ├── test.md
│   │   └── pr.md
│   ├── skills/
│   │   └── sp-estimation/
│   │       └── SKILL.md
│   ├── script/
│   ├── utils/
│   └── setup.sh
└── .cursor/
    ├── commands/   → symlink to submodule commands
    └── skills/     → symlink(s) to submodule skills
```

**Generated per issue (under `docs/issues/{repo}/{issue_number}/`):**

- `issue.md` — context, paths, issue metadata  
- `plan.md` — implementation plan  
- `dev.md` — development log  
- `test.md` — test/review report  
- `pr.md` — PR body (saved before commit)  
- `evidence/` — test outputs, coverage, screenshots  

---

## 9. Skills (optional)

Cursor can load **skills** from `.cursor/skills/*/SKILL.md`. They are applied automatically when relevant (e.g. when running `/breakdown` and talking about “SP” or “Story Points”).

- **sp-estimation:** Story Point estimation (1 SP = 1 hour, Fibonacci, 6-axis framework). Used during `/breakdown` to assign `sp:N` labels.

No need to “run” a skill manually; the agent uses it when the conversation matches.

---

## 10. Troubleshooting

| Problem | What to do |
|--------|------------|
| Commands not visible in Cursor | Ensure `.cursor/commands/` exists and contains the `.md` files (or symlink to submodule). Restart Cursor if needed. |
| `gh` permission errors | Run `gh auth login` and `gh auth status`. |
| Wrong doc path / wrong issue | Pass **issue_url** explicitly so `repo` and `issue_number` are unambiguous. |
| Auto-detect picks wrong issue | Rely on **issue_url** or **issue_number** instead of auto-detect. |
| PR does not link/close issue | Use **issue_url** (or ensure `issue.md` has correct `repository:`). Commit message and PR body must include “Closes #N” or “Closes owner/repo#N”. |
| Child issues on Project Board | Breakdown command is instructed not to add child issues to the board; only the parent should be on the board. |
| Tests not run or no evidence | Run `/test` before `/pr`; evidence is read from `docs/issues/{repo}/{issue_number}/evidence/`. If no results, PR body will say “No test results available” (no fabrication). |

---

**Quick reference:** Prefer **issue_url** for every command. Doc path is always **`docs/issues/{repo}/{issue_number}/`** with **repo** = repository name. Do not commit until **`/pr`**.
