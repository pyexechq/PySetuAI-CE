#!/bin/bash
# scripts/export-community.sh
# This script exports the current repository to a public "Community Edition" repository,
# stripping out proprietary SaaS, Marketing, and Enterprise directories from the entire git history.

set -e

# Default to the current public repo URL if not provided via ENV var
PUBLIC_REPO_URL=${PUBLIC_REPO_URL:-"https://github.com/pyexechq/PySetuAI-CE.git"}
EXPORT_BRANCH="main"

echo "Creating a temporary clone for export..."
TEMP_DIR=$(mktemp -d)
git clone --no-local . "$TEMP_DIR"
cd "$TEMP_DIR"

echo "Injecting Community License..."
cp licenses/LICENSE-COMMUNITY.md LICENSE
git add LICENSE
git commit -m "chore: Apply Apache 2.0 Community License" || true

echo "Removing proprietary directories from history..."
# We use git-filter-repo to rewrite history so proprietary files never existed in the public history.
if ! command -v git-filter-repo &> /dev/null; then
    echo "git-filter-repo could not be found. Installing via pip..."
    pip install git-filter-repo
fi

# --invert-paths removes these specific paths from the repo entirely
git filter-repo --force \
  --path frontend/src/components/marketing/ --invert-paths \
  --path frontend/src/app/platform/ --invert-paths \
  --path backend/app/api/v1/platform.py --invert-paths \
  --path backend/app/api/v1/oidc.py --invert-paths \
  --path backend/app/api/v1/compliance.py --invert-paths

echo "Pushing Community Edition to $PUBLIC_REPO_URL..."
git remote add public "$PUBLIC_REPO_URL"
git push public main --force

echo ""
echo "Community Edition export and push complete!"
