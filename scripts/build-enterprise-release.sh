#!/bin/bash
# scripts/build-enterprise-release.sh
# This script prepares the "Enterprise Edition" of the repository.
# It strips out the PySetu Cloud proprietary SaaS components (Marketing and Tenant Admin)
# but RETAINS the enterprise features (DLP, SSO, Vault, Compliance).

set -e

ENTERPRISE_REMOTE=${ENTERPRISE_REMOTE:-"https://github.com/pyexechq/PySetuAI-Enterprise.git"}

echo "Creating a temporary clone for Enterprise export..."
TEMP_DIR=$(mktemp -d)
git clone --no-local . "$TEMP_DIR"
cd "$TEMP_DIR"

echo "Injecting Enterprise License..."
cp licenses/LICENSE-ENTERPRISE.md LICENSE
git add LICENSE
git commit -m "chore: Apply Commercial Enterprise License" || true

echo "Removing SaaS/Marketing directories from history..."
if ! command -v git-filter-repo &> /dev/null; then
    echo "git-filter-repo could not be found. Installing via pip..."
    pip install git-filter-repo
fi

git filter-repo --force \
  --path frontend/src/components/marketing/ --invert-paths \
  --path frontend/src/components/platform/ --invert-paths \
  --path frontend/src/app/platform/ --invert-paths \
  --path backend/app/api/v1/platform.py --invert-paths

echo "Pushing Enterprise Edition to $ENTERPRISE_REMOTE..."
git remote add enterprise "$ENTERPRISE_REMOTE"
git push enterprise main --force

echo ""
echo "Enterprise Edition export and push complete!"
