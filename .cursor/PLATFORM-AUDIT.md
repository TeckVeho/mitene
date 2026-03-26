# Cross-platform support audit (Windows / Ubuntu / macOS)

*Updated for current `resources/` state.*

## Summary

| Component | Windows (pwsh) | Windows (Git Bash) | Ubuntu | macOS |
|-----------|------------------|-------------------|--------|-------|
| Markdown commands (`/issue` …) | ✅ AI instructions only | ✅ | ✅ | ✅ |
| `gh` CLI | ✅ | ✅ | ✅ | ✅ |
| SP Project (`setsp`) | `setsp.ps1` | `setsp.ps` + jq | `setsp.ps` + jq | `setsp.ps` + jq |
| Add child → Project | `add-to-project.ps1` | `add-to-project.sh` + jq | `add-to-project.sh` | `add-to-project.sh` |
| Verify project | `verify-github-setup.ps1` | `verify-github-setup.sh` | `verify-github-setup.sh` | `verify-github-setup.sh` |
| Parent body update (UTF-8) | `merge-parent-issue-body.ps1` or §5 snippet | `merge-parent-issue-body.sh` | `merge-parent-issue-body.sh` | `merge-parent-issue-body.sh` |
| `setup.sh` (symlink) | ⚠️ Needs Git Bash / WSL | ✅ | ✅ | ✅ |
| `issue-cache.js` (Node) | ✅ | ✅ | ✅ | ✅ |

**Conclusion:** Base set is **sufficient** for Windows (PowerShell 7 or Git Bash), Ubuntu, and macOS. **Windows CMD only, no pwsh, no bash** → install [PowerShell 7](https://aka.ms/powershell) or [Git for Windows](https://git-scm.com/) (Git Bash).

---

## Per-file notes

| File / folder | Cross-platform note |
|---------------|---------------------|
| `commands/*.md`, `workspace-commands/*.md` | OS-agnostic; AI runs `gh`/`git` per docs. |
| `breakdown.md` §5 | PowerShell + Bash + merge script. |
| `CROSS-PLATFORM.md` | OS ↔ tool matrix. |
| `script/setsp.ps1` / `setsp.ps` | Windows vs Unix. |
| `script/add-to-project.ps1` / `.sh` | Same idea. |
| `script/verify-github-setup.*` | Same. |
| `script/merge-parent-issue-body.ps1` / `.sh` | Safe parent body with CJK. |
| `setup.sh` | Unix shell; on Windows use extension copy instead of symlink. |
| `breakdown_old.md`, `README_new.md` | Legacy; not primary source. |

---

## What users need per OS

- **Windows:** `gh`, recommend `pwsh` **or** Git Bash + `jq` (`choco install jq` / scoop).
- **Ubuntu:** `sudo apt install gh jq` (or snap gh).
- **macOS:** `brew install gh jq`.

---

## Known limitations

1. **PowerShell 5** on old Windows Server: UTF-8 snippet in breakdown preferable to raw PS5; or use `merge-parent-issue-body.ps1` (same approach).
2. **No `jq` on plain Windows CMD:** install Git Bash/WSL or use `.ps1` only (add-project/setsp via ps1; verify needs pwsh or jq on bash).
