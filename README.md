# Upstream Documentation Enhancer - GitHub Action

[![GitHub Action](https://img.shields.io/badge/GitHub-Action-blue.svg)](https://github.com/marketplace/actions/upstream-docs-enhancer)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A GitHub Action that uses AI to automatically analyze code changes and update documentation using Gemini AI. Perfect for keeping documentation in sync with code changes across repositories.

## 🚀 Quick Start

Add this workflow file to your repository at `.github/workflows/docs-enhancer.yml`:

```yaml
name: Auto-Update Documentation

on:
  issue_comment:
    types: [created]

jobs:
  update-docs:
    if: |
      github.event.issue.pull_request && 
      contains(github.event.comment.body, '[update-docs]')
    runs-on: ubuntu-latest
    steps:
      - name: Checkout PR branch
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GH_TOKEN }}
          ref: ${{ github.event.pull_request.head.ref }}
          fetch-depth: 0
          
      - name: Update Documentation
        uses: csoceanu/code-to-docs@v1.0.0
        with:
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
          docs-repo-url: ${{ secrets.DOCS_REPO_URL }}
          github-token: ${{ secrets.GH_TOKEN }}
```

**Then just comment `[update-docs]` on any Pull Request to trigger automatic documentation updates!**

## 🎯 How It Works

1. **Triggered by PR Comments**: When someone comments `[update-docs]` on a Pull Request
2. **Analyzes Code Changes**: Examines git diffs from your PRs using AI
3. **Smart File Selection**: Identifies relevant documentation files automatically  
4. **Content Generation**: Generates updated documentation content in proper AsciiDoc format
5. **Automated PRs**: Creates pull requests in your documentation repository

## ⚙️ Setup (5 Minutes)

### Step 1: Create Workflow File

Save the workflow above as `.github/workflows/docs-enhancer.yml` in your code repository.

### Step 2: Add GitHub Secrets

Go to your repository Settings → Secrets and variables → Actions:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `GEMINI_API_KEY` | Your Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey) | `****` |
| `DOCS_REPO_URL` | URL of your documentation repository | `https://github.com/org/docs` |
| `GH_TOKEN` | GitHub Personal Access Token with `repo` + `pull_requests:write` permissions | `****` |

### Step 3: That's It!

Comment `[update-docs]` on any PR to automatically update documentation.

## 📋 Action Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `gemini-api-key` | ✅ | - | Gemini API key for AI analysis |
| `docs-repo-url` | ✅ | - | URL of documentation repository |
| `github-token` | ✅ | - | GitHub token for creating PRs |
| `dry-run` | ❌ | `false` | Preview changes without creating PR |

## 📊 Action Outputs

| Output | Description |
|--------|-------------|
| `status` | Status of the documentation enhancement |
| `modified-files` | JSON array of modified files |
| `pr-created` | Whether a PR was created |

---

**Ready to automate your documentation?** Just add the workflow file, set up secrets, and comment `[update-docs]` on PRs! 🚀
