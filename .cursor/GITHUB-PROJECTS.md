# GitHub Projects V2 — integration with Base Commands

How the command set interacts with GitHub Projects V2 (custom fields, add item, Development section).

## Scripts

| Script | Purpose |
|--------|---------|
| `script/add-to-project.ps1` / `add-to-project.sh` | Add issue to Project V2 (Windows vs Linux/macOS/Git Bash) |
| `script/setsp.ps` | Update custom SP field — **Bash**, needs `jq` |
| `script/setsp.ps1` | Update custom SP field — **PowerShell** — **same logic as `setsp.ps`** |

Use **one** of `setsp.ps` or `setsp.ps1` depending on shell. Not an error if both work.

## Why doesn’t SP show on Project? (PM / double-check)

1. **Issue not on Project** — `setsp` only updates items already on the board. Add the issue first (`add-to-project.ps1` or drag on GitHub). If log shows `No project found.` → this case.
2. **setsp not run** — GitHub label `sp:3` does **not** fill the Project SP column.
3. **Different column name** — Scripts match fields named like SP / Story Point. If your field is named differently (e.g. `Estimate`), adjust the script or rename the field on Project.

## Custom fields

- **SP (Story Points):** Both `setsp.ps` and `setsp.ps1` look for `SP`, `Story Point`, `Story Points` (normalized non-alphanumeric).
- **Status, Priority:** Extend scripts or use GraphQL `updateProjectV2ItemFieldValue` with `singleSelectOptionId`.

## Relationships (Parent/Child, Blocked by, Relates to)

- **In issue body:** Each child has `Parent: #{parent_number}` — enough for basic tracking.
- **In GitHub Projects:** If the project has a **Relationships** field, you can use GraphQL `updateProjectV2ItemFieldValue` with `projectV2ItemRelationships: { parentIds: [...] }`. The base set does not call this yet; add later if your project uses Relationships.

## Development section (branch, PR)

- **Branch:** Branch name contains `{issue_number}` (e.g. `123-feat-add-login`) → GitHub links branch to issue under Development.
- **PR:** PR body has `Closes #123` → GitHub links PR; if issue is on a Project, PR appears under Development.

## Flow `/issue` → `/breakdown`

1. **`/issue`:** GraphQL `projectItems` on parent issue → save **`github_project_v2_id`** + **`github_project_title`** in `issue.md`. Multiple projects → user picks one (or `--no-prompts` → first).
2. **`/breakdown`:** Read `github_project_v2_id` from `issue.md` **first**; query parent again only if empty.

## `/breakdown` flow (detail)

1. Create child issues  
2. `project_id` from `issue.md` or parent query  
3. Add each child: `add-to-project.ps1` or `add-to-project.sh`  
4. Set SP: `setsp.ps` / `setsp.ps1`  
5. Inject tasklist into parent issue body  
