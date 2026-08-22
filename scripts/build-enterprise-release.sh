#!/bin/bash
# scripts/build-enterprise-release.sh
# This script prepares the "Enterprise Edition" of the repository.
# It strips out the PySetu Cloud proprietary SaaS components (Marketing and Tenant Admin)
# but RETAINS the enterprise features (DLP, SSO, Vault, Compliance).

set -e

ENTERPRISE_REMOTE=${ENTERPRISE_REMOTE:-"git@github.com:pyexechq/PySetuAI-Enterprise.git"}

echo "Creating a temporary clone for Enterprise export..."
TEMP_DIR=$(mktemp -d)
git clone . "$TEMP_DIR"
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

# Only strip the PySetu Cloud specific components
git filter-repo \
  --path frontend/src/components/marketing/ --invert-paths \
  --path frontend/src/app/platform/ --invert-paths \
  --path backend/app/api/v1/platform.py --invert-paths

echo ""
echo "Filtering complete. Your Enterprise Edition repository is ready in $TEMP_DIR."
echo "To push this to your Enterprise distribution repository, run:"
echo ""
echo "  cd $TEMP_DIR"
echo "  git remote add enterprise $ENTERPRISE_REMOTE"
echo "  git push enterprise main --force"
echo ""
echo "(Note: You can safely delete $TEMP_DIR when you are done.)"
