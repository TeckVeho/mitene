# Running the base set on all platforms (Windows / Ubuntu / macOS)

## Common requirements

| Component | Purpose |
|-----------|---------|
| **GitHub CLI (`gh`)** | Required — `gh auth login` (scope **project** if using Projects V2) |
| **UTF-8** | Terminal / IDE UTF-8 so Japanese/Vietnamese text is not corrupted |

---

## By operating system

| Platform | SP / add-project scripts | Parent issue body update (UTF-8) | Notes |
|----------|--------------------------|-----------------------------------|-------|
| **Windows (PowerShell 7+)** | `setsp.ps1`, `add-to-project.ps1` | PowerShell snippet in `breakdown.md` §5 (`UTF8Encoding` no BOM) | `pwsh` available |
| **Windows (PowerShell 5 / CMD)** | Install **Git Bash** or **WSL** → use `.sh` + `setsp.ps` | **Do not** use `gh issue edit --body "$(...)"` with CJK | Or PS7+ only |
| **Ubuntu / Debian** | `bash setsp.ps …`, `add-to-project.sh`, `verify-github-setup.sh` | `merge-parent-issue-body.sh` or `mktemp` + `gh issue edit --body-file` | `sudo apt install jq` |
| **macOS** | Same as Linux | Same as Linux | `brew install gh jq` |
| **WSL (Windows)** | `.sh` + Linux `gh`; may call `gh.exe` via Windows path | `.sh` with UTF-8 locale | `setsp.ps` supports `wslpath` for gh.exe |

---

## Script paths (after extension copies into `.cursor`)

```
.cursor/resources/script/
├── setsp.ps1          ← Windows PowerShell
├── setsp.ps           ← Bash (Linux, macOS, Git Bash, WSL)
├── add-to-project.ps1 ← Windows PowerShell
├── add-to-project.sh  ← Bash
├── verify-github-setup.ps1
├── verify-github-setup.sh
├── merge-parent-issue-body.ps1 ← Windows PowerShell
└── merge-parent-issue-body.sh  ← Bash
```

### Example commands

```powershell
# Windows — PowerShell 7
pwsh -File .cursor/resources/script/setsp.ps1 -IssueUrl "https://github.com/o/r/issues/1" -SpValue "3"
pwsh -File .cursor/resources/script/add-to-project.ps1 -IssueUrl "..." -ProjectId "PVT_..."
pwsh -File .cursor/resources/script/merge-parent-issue-body.ps1 -Repo "owner/repo" -ParentNum 887 -ChildUrl "https://..." -Sp 3
```

```bash
# Ubuntu / macOS / Git Bash / WSL
bash .cursor/resources/script/setsp.ps "https://github.com/o/r/issues/1" "3"
bash .cursor/resources/script/add-to-project.sh "https://github.com/o/r/issues/1" "PVT_..."
bash .cursor/resources/script/verify-github-setup.sh "https://github.com/o/r/issues/1"
bash .cursor/resources/script/merge-parent-issue-body.sh "owner/repo" 887 "https://github.com/owner/repo/issues/899" 3
```

Detailed audit: [PLATFORM-AUDIT.md](PLATFORM-AUDIT.md).

---

## Cursor commands (`/issue`, `/breakdown`)

The AI Agent picks **one** of two stacks depending on the user environment:

- **`pwsh`** / user on Windows PowerShell → prefer `.ps1`
- **`bash`** + **`jq`** (Linux, macOS, Git Bash) → prefer `.sh` / `setsp.ps`

If unsure: ask the user or try `command -v pwsh` / `command -v bash`.

---

## WSL + repo on Windows drive (`/mnt/c/...`)

- Run `.sh` from WSL; `gh` should be Linux WSL (`which gh`).
- `setsp.ps` / `add-to-project.sh` may rewrite temp paths for `gh.exe` when configured that way.

---

## Summary

1. **`gh`** everywhere.  
2. **Bash stack:** `jq` + `.sh` scripts.  
3. **Windows native:** `pwsh` + `.ps1`.  
4. **CJK body:** always **`--body-file`** + UTF-8 no BOM (see `breakdown.md` §5).
