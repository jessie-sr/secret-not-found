#!/usr/bin/env bash
#
# run_diagram.sh – wrapper for ai_diagram_generator.py
# ---------------------------------------------------
# • Prompts for an optional repository path/URL.
# • Accepts:
#     – blank input  ➜ run script with no --target
#     – existing local path (file or directory)
#     – GitHub HTTPS URL  (https://github.com/user/repo[.git])
#     – GitHub SSH URL    (git@github.com:user/repo.git)
# • Any other input: show error and ask again.
#

is_github_url() {
  [[ "$1" =~ ^https://github\.com/[^[:space:]]+(\.git)?$ ]] \
  || [[ "$1" =~ ^git@github\.com:[^[:space:]]+\.git$ ]]
}

while true; do
  read -rp "Path to target repo (leave blank to skip): " TARGET

  # Case 1 – blank input
  if [[ -z "$TARGET" ]]; then
    echo "→ Running: python3 ai_diagram_generator.py"
    exec python3 ai_diagram_generator.py
  fi

  # Case 2 – GitHub URL/SSH
  if is_github_url "$TARGET"; then
    echo "→ Running: python3 ai_diagram_generator.py --target \"$TARGET\""
    exec python3 ai_diagram_generator.py --target "$TARGET"
  fi

  # Case 3 – local filesystem path that exists
  if [[ -e "$TARGET" ]]; then
    echo "→ Running: python3 ai_diagram_generator.py --target \"$TARGET\""
    exec python3 ai_diagram_generator.py --target "$TARGET"
  fi

  # Anything else → invalid
  echo "✖  \"$TARGET\" is not a valid GitHub repo URL/SSH spec or a local path that exists."
  echo "    Please try again."
done