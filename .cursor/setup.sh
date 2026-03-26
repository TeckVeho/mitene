#!/usr/bin/env bash
set -euo pipefail

# Determine the directory where this script (and the submodule) lives.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve the project root: the parent of the directory containing this submodule.
# Typical layout: <project-root>/.cursor-shared-skills/setup.sh
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

CURSOR_DIR="${PROJECT_ROOT}/.cursor"
COMMANDS_LINK="${CURSOR_DIR}/commands"
COMMANDS_TARGET="${SCRIPT_DIR}/commands"

echo "=== cursor-shared-skills setup ==="
echo "Project root : ${PROJECT_ROOT}"
echo "Submodule    : ${SCRIPT_DIR}"
echo ""

# 1. Ensure .cursor/ exists
if [ ! -d "${CURSOR_DIR}" ]; then
  mkdir -p "${CURSOR_DIR}"
  echo "[+] Created ${CURSOR_DIR}"
fi

# 2. Handle existing .cursor/commands
if [ -e "${COMMANDS_LINK}" ] || [ -L "${COMMANDS_LINK}" ]; then
  BACKUP="${COMMANDS_LINK}.bak.$(date +%Y%m%d_%H%M%S)"
  mv "${COMMANDS_LINK}" "${BACKUP}"
  echo "[!] Existing ${COMMANDS_LINK} backed up to ${BACKUP}"
fi

# 3. Create relative symlink: .cursor/commands -> ../.cursor-shared-skills/commands
#    The link must be relative so it remains valid after cloning on another machine.
RELATIVE_TARGET="$(python3 -c "import os; print(os.path.relpath('${COMMANDS_TARGET}', '${CURSOR_DIR}'))")"
ln -s "${RELATIVE_TARGET}" "${COMMANDS_LINK}"
echo "[+] Symlink created: ${COMMANDS_LINK} -> ${RELATIVE_TARGET}"

# 4. Grant execute permission to shell scripts under script/
if [ -d "${SCRIPT_DIR}/script" ]; then
  find "${SCRIPT_DIR}/script" -type f \( -name "*.sh" -o -name "*.ps" \) -exec chmod +x {} \;
  echo "[+] Execute permission granted to scripts in ${SCRIPT_DIR}/script/"
fi

# 5. Create per-skill symlinks: .cursor/skills/{skill-name} -> ../../.cursor-shared-skills/skills/{skill-name}
SKILLS_SOURCE_DIR="${SCRIPT_DIR}/skills"
SKILLS_LINK_DIR="${CURSOR_DIR}/skills"

if [ -d "${SKILLS_SOURCE_DIR}" ]; then
  if [ ! -d "${SKILLS_LINK_DIR}" ]; then
    mkdir -p "${SKILLS_LINK_DIR}"
    echo "[+] Created ${SKILLS_LINK_DIR}"
  fi

  for skill_dir in "${SKILLS_SOURCE_DIR}"/*/; do
    [ -d "${skill_dir}" ] || continue
    skill_name="$(basename "${skill_dir}")"
    skill_link="${SKILLS_LINK_DIR}/${skill_name}"
    skill_target="$(python3 -c "import os; print(os.path.relpath('${skill_dir%/}', '${SKILLS_LINK_DIR}'))")"

    if [ -e "${skill_link}" ] || [ -L "${skill_link}" ]; then
      SKILL_BACKUP="${skill_link}.bak.$(date +%Y%m%d_%H%M%S)"
      mv "${skill_link}" "${SKILL_BACKUP}"
      echo "[!] Existing ${skill_link} backed up to ${SKILL_BACKUP}"
    fi

    ln -s "${skill_target}" "${skill_link}"
    echo "[+] Skill symlink created: ${skill_link} -> ${skill_target}"
  done
else
  echo "[~] No skills/ directory found in submodule, skipping skill symlinks."
fi

echo ""
echo "=== Setup complete ==="
echo "Cursor will now load commands from .cursor-shared-skills/commands/"
echo "Cursor will now load skills from .cursor-shared-skills/skills/"
echo ""
echo "Tip: add the following lines to your project .gitignore:"
echo "  .cursor/commands"
echo "  .cursor/skills"
