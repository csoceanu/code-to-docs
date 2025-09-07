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
        uses: your-username/upstream-docs-enhancer@v1
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

## 🔧 Advanced Configuration

### Dry Run Mode

Test without creating actual PRs:

```yaml
- name: Update Documentation (Dry Run)
  uses: your-username/upstream-docs-enhancer@v1
  with:
    gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
    docs-repo-url: ${{ secrets.DOCS_REPO_URL }}
    github-token: ${{ secrets.GH_TOKEN }}
    dry-run: 'true'
```

### Multiple Trigger Phrases

Support different trigger phrases:

```yaml
jobs:
  update-docs:
    if: |
      github.event.issue.pull_request && 
      (contains(github.event.comment.body, '[update-docs]') ||
       contains(github.event.comment.body, '[docs]') ||
       contains(github.event.comment.body, '/update-docs'))
```

### Auto-trigger on PR Events

Automatically run on PR creation/updates:

```yaml
name: Auto-Update Documentation

on:
  issue_comment:
    types: [created]
  pull_request:
    types: [opened, synchronize]

jobs:
  update-docs:
    if: |
      (github.event_name == 'pull_request') ||
      (github.event.issue.pull_request && 
       contains(github.event.comment.body, '[update-docs]'))
```

## 🛡️ Security & Permissions

### GitHub Token Requirements

Your GitHub Personal Access Token needs these permissions:
- ✅ `repo` - Full control of private repositories
- ✅ `pull_requests:write` - Create and update pull requests

### Security Best Practices

- ❌ **Never commit API keys** to repositories
- ✅ **Use GitHub Secrets** for all sensitive data
- ✅ **Rotate tokens regularly** for security
- ✅ **Use least-privilege access** on tokens
- ✅ **Review generated PRs** before merging

## 🎉 Usage Examples

### Basic Team Workflow

1. 👩‍💻 Developer creates PR with new API endpoints
2. 🔍 Reviewer comments `[update-docs]` on the PR
3. 🤖 Action analyzes changes and updates API documentation
4. 📝 New PR appears in docs repository with suggested updates
5. ✅ Team reviews and merges documentation changes

### Enterprise Workflow

```yaml
name: Documentation Pipeline

on:
  pull_request:
    types: [opened, synchronize]
    branches: [main, develop]

jobs:
  analyze-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          
      - name: Check Documentation Impact
        uses: your-username/upstream-docs-enhancer@v1
        with:
          gemini-api-key: ${{ secrets.GEMINI_API_KEY }}
          docs-repo-url: ${{ secrets.DOCS_REPO_URL }}
          github-token: ${{ secrets.GH_TOKEN }}
          dry-run: 'true'
        id: docs-check
        
      - name: Comment PR with Documentation Impact
        if: steps.docs-check.outputs.modified-files != '[]'
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '📚 **Documentation Impact Detected**\n\nThis PR may require documentation updates. Comment `[update-docs]` to generate documentation changes automatically.'
            });
```

## 🔍 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| "No changes detected" | Ensure you're running from a repository with actual code changes |
| "Failed to clone docs repository" | Check `DOCS_REPO_URL` format and token permissions |
| "Gemini API error" | Verify `GEMINI_API_KEY` and check API quota limits |
| "No documentation files found" | Ensure docs repository contains `.adoc` files |

### Debug Information

The action provides detailed logging. Check the Actions tab in your repository for:
- ✅ Environment variable setup
- ✅ Git diff analysis  
- ✅ AI file selection process
- ✅ Documentation generation steps
- ✅ PR creation details

### Getting Help

- 📖 [Setup Guide](examples/SETUP-GUIDE.md)
- 🐛 [Report Issues](https://github.com/your-username/upstream-docs-enhancer/issues)  
- 💬 [Ask Questions](https://github.com/your-username/upstream-docs-enhancer/discussions)

## 🎯 Requirements

**Your Setup:**
- ✅ Code repository (where you develop)
- ✅ Documentation repository (with `.adoc` files)
- ✅ Gemini API key from Google AI Studio
- ✅ GitHub Personal Access Token

**Action Requirements:**
- ✅ Runs on `ubuntu-latest`
- ✅ Requires internet access (for Gemini API)
- ✅ Needs git access to both repositories
- ✅ Uses Docker container for consistent environment

## 📈 Benefits

| Benefit | Description |
|---------|-------------|
| **Zero Installation** | No dependencies to install or manage locally |
| **Team Collaboration** | Anyone can trigger documentation updates |  
| **Consistent Environment** | Same Docker environment every time |
| **Always Up-to-Date** | Uses latest version with `@v1` tag |
| **Audit Trail** | All actions logged in GitHub Actions |
| **Secure** | API keys stored as encrypted GitHub secrets |

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Ready to automate your documentation?** Just add the workflow file, set up secrets, and comment `[update-docs]` on PRs! 🚀
