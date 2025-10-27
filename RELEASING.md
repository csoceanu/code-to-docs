# Release Process

This document explains how to release new versions of the code-to-docs action.

## Releasing a New Version

When you're ready to release a new version (e.g., v1.2.0):

### 1. Create and push the specific version tag

```bash
git tag v1.2.0
git push origin v1.2.0
```

### 2. Move the major version tag

This ensures users using `@v1` get the latest v1.x.x version:

```bash
git tag -f v1              # Move v1 tag to point to v1.2.0
git push -f origin v1      # Force push the moved tag
```

### 3. Update the README (if needed)

If the example in README.md references a specific version, consider whether it needs updating.

## Version Numbering

Follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR** (v2.0.0): Breaking changes
- **MINOR** (v1.2.0): New features, backward compatible
- **PATCH** (v1.1.1): Bug fixes, backward compatible

## Complete Example

```bash
# Release v1.2.0
git tag v1.2.0
git push origin v1.2.0

# Move v1 to v1.2.0
git tag -f v1
git push -f origin v1

echo "✅ Released v1.2.0 and updated v1 tag"
```

## Verification

After releasing, verify users can access it:

```bash
# Check tags
git ls-remote --tags origin | grep v1

# Should see both:
# refs/tags/v1.2.0
# refs/tags/v1
```

Users can now use:
- `csoceanu/code-to-docs@v1` (gets v1.2.0)
- `csoceanu/code-to-docs@v1.2.0` (pinned to v1.2.0)

