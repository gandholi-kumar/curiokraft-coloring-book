#!/usr/bin/env bash
#
# Sensitive-file guard for CurioKraft Coloring Book Engine.
#
# Blocks staging of files that must never be version-controlled:
#   - Amazon KDP form dumps (private publishing metadata)
#   - Environment files and credentials
#   - API keys
#
# Used by both:
#   - .git/hooks/pre-commit            (standalone, no dependencies)
#   - .pre-commit-config.yaml          (local hook, via `pre-commit install`)
#
# Exit codes:
#   0 - no sensitive files staged
#   1 - sensitive files staged (commit must be blocked)
#
# Bypass (emergency only, understand the implications first):
#   git commit --no-verify

set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Patterns matched against staged paths (extended regex)
sensitive_patterns=(
    'inbox/kdp_forms/.*\.(html|htm|json)'
    '(^|/)\.env$'
    '(^|/)\.env\.(local|production|staging)$'
    '.*_credentials\.json$'
    '.*_api_key.*'
)

staged_files=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$staged_files" ]; then
    exit 0
fi

found_sensitive=false
matched_files=""

for pattern in "${sensitive_patterns[@]}"; do
    matches=$(printf '%s\n' "$staged_files" | grep -E "$pattern" || true)
    if [ -n "$matches" ]; then
        found_sensitive=true
        matched_files="${matched_files}${matches}"$'\n'
    fi
done

if [ "$found_sensitive" = true ]; then
    echo -e "${RED}ERROR: Attempting to commit sensitive files${NC}"
    echo ""
    echo -e "${YELLOW}Blocked:${NC}"
    printf '%s' "$matched_files" | sort -u | sed 's/^/    - /'
    echo ""
    echo -e "${YELLOW}Why this is blocked:${NC}"
    echo "  - KDP forms contain private publishing metadata"
    echo "  - Credentials and API keys must not be version controlled"
    echo ""
    echo -e "${YELLOW}To fix:${NC}"
    echo "  git reset HEAD <file>   # Unstage specific file"
    echo "  git reset HEAD .        # Unstage all files"
    echo ""
    echo -e "${YELLOW}To bypass this check (not recommended):${NC}"
    echo "  git commit --no-verify"
    echo ""
    exit 1
fi

# Nudge if the KDP forms directory is not covered by .gitignore
if [ -f .gitignore ] && ! grep -qE '^inbox/kdp_forms/' .gitignore; then
    echo -e "${YELLOW}Warning: inbox/kdp_forms/ not covered by .gitignore${NC}"
    echo "   Consider adding it for automatic protection"
fi

exit 0
