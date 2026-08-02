#!/bin/bash
# OmniVerse Wealth — Deployment Script
# Usage: ./deploy.sh [stage]
# Stages: dev, prod (default: prod)

set -e

STAGE=${1:-prod}
INFRA_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$INFRA_DIR")"

echo "🌌 OmniVerse Wealth — Deploying to ${STAGE}"
echo "================================================"

# Step 1: Build frontend
echo "📦 Building frontend..."
cd "$PROJECT_ROOT/frontend"
npm run build
npx next export -o out 2>/dev/null || echo "Using static export from build"

# Step 2: Package Lambda layer
echo "📦 Packaging Lambda dependencies layer..."
cd "$INFRA_DIR"
mkdir -p lambda/layers/deps/python
pip install -r lambda/layers/deps/requirements.txt -t lambda/layers/deps/python --quiet

# Step 3: CDK Deploy
echo "☁️  Deploying AWS infrastructure..."
cd "$INFRA_DIR"
pip install -r requirements.txt --quiet

cdk bootstrap --quiet 2>/dev/null || true
cdk deploy --all --require-approval never

echo ""
echo "✅ Deployment complete!"
echo "================================================"
echo "Check the CloudFormation outputs for URLs."
