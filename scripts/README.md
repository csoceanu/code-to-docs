# Scripts Directory

This directory contains the main scripts for the code-to-docs GitHub Action.

## Files

### `suggest_docs.py`
Main script that:
- Analyzes code changes using git diff
- Uses Gemini AI to identify relevant documentation files
- Generates updated documentation content
- Posts review comments on PRs (review mode)
- Creates PRs in documentation repository (update mode)

**Usage:**
```bash
python suggest_docs.py [--dry-run]
```

**Modes:**
- `[review-docs]` - Posts suggestions as PR comment
- `[update-docs]` - Posts suggestions + creates PR

### `security_utils.py`
Security utilities module that provides:
- **`sanitize_output()`** - Removes sensitive tokens from text
- **`run_command_safe()`** - Safe subprocess execution with sanitization
- **`validate_file_path()`** - Prevents path traversal attacks
- **`setup_git_credentials()`** - Secure git credential helper setup
- **`validate_docs_file_extension()`** - Checks file extensions
- **`validate_docs_subfolder()`** - Validates subfolder paths

**Security Features:**
- Prevents token leakage in error messages
- Validates all file paths before operations
- Sanitizes all subprocess output
- Uses git credential helper (no tokens in URLs)

## Architecture

```
suggest_docs.py
├── Imports security_utils
├── Core Functions:
│   ├── get_diff() - Extract PR changes
│   ├── get_commit_info() - Get PR metadata
│   ├── setup_docs_environment() - Setup docs repo
│   ├── ask_gemini_for_relevant_files() - AI file selection
│   ├── ask_gemini_for_updated_content() - AI content generation
│   ├── post_review_comment() - Post PR comments
│   └── push_and_open_pr() - Create docs PR
└── Uses security_utils for all sensitive operations

security_utils.py
└── Pure security functions (no dependencies on main script)
```

## Environment Variables

Required:
- `GEMINI_API_KEY` - Gemini AI API key
- `DOCS_REPO_URL` - Documentation repository URL
- `GH_TOKEN` - GitHub Personal Access Token

Optional:
- `PR_NUMBER` - Pull request number
- `PR_BASE` - Base branch for comparison
- `DOCS_SUBFOLDER` - Docs subfolder in same repo
- `COMMENT_BODY` - Comment text (to detect commands)

## Security

All security-sensitive operations use functions from `security_utils.py`:

1. **Token Protection**: All tokens sanitized in output
2. **Path Validation**: All file paths validated before access
3. **Subprocess Safety**: All commands use safe wrapper
4. **Git Credentials**: Uses credential helper (not URL)

See `SECURITY_IMPROVEMENTS.md` for detailed security documentation.

## Testing

### Test Review Mode:
```bash
export COMMENT_BODY="[review-docs]"
export GEMINI_API_KEY="your-key"
export DOCS_REPO_URL="https://github.com/org/docs"
export GH_TOKEN="your-token"
export PR_NUMBER="123"

python suggest_docs.py
```

### Test Update Mode:
```bash
export COMMENT_BODY="[update-docs]"
# ... same as above

python suggest_docs.py
```

### Test Security:
```python
# Import security utilities
from security_utils import validate_file_path, sanitize_output

# Test path validation
assert validate_file_path("docs/guide.adoc") == True
assert validate_file_path("../../etc/passwd") == False

# Test sanitization
output = "Token: ghp_123456789"
assert "ghp_" not in sanitize_output(output)
assert "***TOKEN***" in sanitize_output(output)
```

## Development

### Adding New Security Features:
1. Add function to `security_utils.py`
2. Add docstring with examples
3. Import in `suggest_docs.py`
4. Use in appropriate places

### Code Style:
- Type hints where helpful
- Docstrings for all public functions
- Security checks before operations
- Sanitize all error output

## Dependencies

Python packages:
- `google-genai` - Gemini AI SDK
- Standard library: `os`, `subprocess`, `argparse`, `pathlib`

System requirements:
- `git` - Version control operations
- `gh` - GitHub CLI (for PR operations)

See `Dockerfile` for complete setup.

