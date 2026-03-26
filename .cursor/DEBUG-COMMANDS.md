# Debug / try base commands (Cursor)

## What are `/issue`, `/breakdown`, …?

They are **Markdown** files under `.cursor/commands/` — Cursor reads them to **guide the AI** step by step. There is **no** terminal command like `cursor run /issue`.

So:

| What to verify | How |
|----------------|-----|
| Full `/issue` → `/breakdown` flow | In Cursor chat run **`/issue`** (or `@issue`) on a real issue; check GraphQL step and `issue.md` output. |
| `setsp` / `add-to-project` scripts | Run **directly** in terminal (below). |
| GitHub / Project access | **`verify-github-setup.ps1`** (Windows) or **`verify-github-setup.sh`** (Linux/macOS/Git Bash). |

---

## 1. Environment check

See **[CROSS-PLATFORM.md](CROSS-PLATFORM.md)** (Windows vs Linux/macOS table).

```bash
gh auth status
gh auth login
jq --version   # required for .sh scripts / setsp.ps (bash)
```

---

## 2. Quick verify script (GraphQL same as `/issue` step 2b)

From the script directory (after extension copy: `.cursor/resources/script/`):

```powershell
pwsh -File verify-github-setup.ps1
pwsh -File verify-github-setup.ps1 -IssueUrl "https://github.com/OWNER/REPO/issues/123"
```

```bash
bash verify-github-setup.sh
bash verify-github-setup.sh "https://github.com/OWNER/REPO/issues/123"
```

- Without `-IssueUrl` / URL: only checks `gh` login.
- With issue URL: GraphQL lists **projects** the issue is on — same as writing `github_project_v2_id` into `issue.md`.

---

## 3. Try `setsp` (write SP on Project)

**Warning:** This **writes** to the board (if the issue is already on the project).

```powershell
pwsh -File setsp.ps1 -IssueUrl "https://github.com/OWNER/REPO/issues/123" -SpValue "3"
pwsh -File add-to-project.ps1 -IssueUrl "..." -ProjectId "PVT_..."
pwsh -File merge-parent-issue-body.ps1 -Repo "o/r" -ParentNum 887 -ChildUrl "https://..." -Sp 3
```

```bash
bash setsp.ps "https://github.com/OWNER/REPO/issues/123" "3"
bash add-to-project.sh "https://..." "PVT_..."
bash merge-parent-issue-body.sh "owner/repo" 887 "https://..." 3
```

If output is **`No project found.`** → issue is not on Project V2 yet.

---

## 4. Try `add-to-project` (add issue to board)

**Warning:** Adds a real issue to a project. Need `ProjectId` from verify / `issue.md`.  
Sample commands: **PowerShell** / **bash** blocks in §3 (`add-to-project.ps1` / `add-to-project.sh`).

---

## 5. AI not following the command

1. Open the right command file: `.cursor/commands/issue.md` (extension copy).
2. In chat, **state clearly**: follow step 2b in issue.md, run gh graphql, write results to issue.md.
3. **Verbose:** ask the AI to paste `gh` output (redact tokens).

---

## 6. After testing — refresh the base set

- If you changed **`izumi-base-commands-extension`**: **re-copy** `resources/` into `.cursor/` (reinstall extension / extension copy command) or **rebuild `.vsix`** for other machines.
- No base change needed if tests only confirm the flow and no doc/script bug was found.

## 7. Parent issue body mojibake after `/breakdown`

**Cause:** Updating with `gh issue edit --body "..."` on Windows — shell breaks UTF-8 for Japanese.

**Prevent:** Always `--body-file` + UTF-8 without BOM (see `breakdown.md` §5).

**Fix:** On GitHub issue → **Edited** dropdown → **view older revision** → copy correct body → edit manually or `gh issue edit N --body-file restored.md`.

## 8. Manual checklist (one trial issue)

- [ ] `gh auth status` OK  
- [ ] `verify-github-setup.ps1` or `.sh` with `-IssueUrl` / URL prints `project.id`  
- [ ] `issue.md` after `/issue` has correct `github_project_v2_id`  
- [ ] After `/breakdown`, children on same project + SP (if setsp was run)
