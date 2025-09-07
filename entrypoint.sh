#!/bin/bash
set -e

echo "🚀 Starting Upstream Documentation Enhancer GitHub Action"

# Setup environment variables for GitHub Actions context
# For issue_comment events (commenting on PR), get PR number from event payload
if [ -n "$GITHUB_EVENT_PATH" ] && [ -f "$GITHUB_EVENT_PATH" ]; then
  export PR_NUMBER=$(jq -r '.issue.number // .pull_request.number // empty' "$GITHUB_EVENT_PATH")
else
  export PR_NUMBER=""
fi

# Set PR base branch
export PR_BASE="${GITHUB_BASE_REF:-origin/main}"

# Validate required inputs
if [ -z "$GEMINI_API_KEY" ]; then
  echo "❌ Error: gemini-api-key input is required"
  exit 1
fi

if [ -z "$DOCS_REPO_URL" ]; then
  echo "❌ Error: docs-repo-url input is required"  
  exit 1
fi

if [ -z "$GH_TOKEN" ]; then
  echo "❌ Error: github-token input is required"
  exit 1
fi

# Build command arguments
ARGS=""
if [ "$DRY_RUN" = "true" ]; then
  ARGS="$ARGS --dry-run"
  echo "🔍 Running in dry-run mode"
fi

echo "📊 Environment:"
echo "  PR_NUMBER: $PR_NUMBER"
echo "  PR_BASE: $PR_BASE" 
echo "  BRANCH_NAME: ${BRANCH_NAME:-doc-update-from-pr}"
echo "  DRY_RUN: ${DRY_RUN:-false}"
echo "  DOCS_REPO_URL: $DOCS_REPO_URL"

# Map GH_TOKEN to GH_PAT for the original script
export GH_PAT="$GH_TOKEN"

echo ""
echo "🎯 Running documentation enhancer with args: $ARGS"

# Run the documentation enhancer
if python /app/suggest_docs.py $ARGS; then
  echo "✅ Documentation enhancer completed successfully"
  
  # Set GitHub Actions outputs (if result data is available)
  if [ -n "$GITHUB_OUTPUT" ]; then
    echo "status=success" >> "$GITHUB_OUTPUT"
    echo "pr-created=true" >> "$GITHUB_OUTPUT"
  fi
  
  exit 0
else
  echo "❌ Documentation enhancer failed"
  
  # Set GitHub Actions outputs
  if [ -n "$GITHUB_OUTPUT" ]; then
    echo "status=failed" >> "$GITHUB_OUTPUT"
    echo "pr-created=false" >> "$GITHUB_OUTPUT"  
  fi
  
  exit 1
fi
