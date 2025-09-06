# PyPI Publishing Setup

## Overview
This repository is configured to automatically publish to PyPI when a new GitHub release is created.

## Setup Instructions

### 1. Configure PyPI Trusted Publisher (Recommended)

This workflow uses PyPI's trusted publisher feature (OIDC), which is more secure than API tokens.

1. Go to https://pypi.org/manage/account/publishing/
2. Add a new trusted publisher with these settings:
   - **Repository owner**: `okhan` (your GitHub username)
   - **Repository name**: `tasak`
   - **Workflow name**: `publish.yml`
   - **Environment**: `pypi`

3. For Test PyPI (optional):
   - Go to https://test.pypi.org/manage/account/publishing/
   - Add the same repository with environment: `test-pypi`

### 2. Configure GitHub Repository

1. Go to your repository Settings → Environments
2. Create two environments:
   - `pypi` - for production releases
   - `test-pypi` - for test releases (optional)

3. Optionally add protection rules:
   - Required reviewers
   - Deployment branches (e.g., only from `main`)

## Usage

### Automatic Publishing (Production)

1. Create a new release on GitHub:
   ```bash
   gh release create v0.1.0 --title "Release v0.1.0" --notes "Release notes here"
   ```

2. The workflow will automatically:
   - Build the package
   - Check it with twine
   - Publish to PyPI

### Manual Testing (Test PyPI)

1. Manually trigger the workflow:
   ```bash
   gh workflow run publish.yml
   ```

2. Or use GitHub UI:
   - Go to Actions → Publish to PyPI
   - Click "Run workflow"
   - This publishes to Test PyPI only

## Workflow Features

- **Trusted Publisher**: Uses OIDC authentication (no API tokens needed)
- **Build Verification**: Checks package with `twine check` before publishing
- **Artifact Storage**: Keeps built packages as GitHub artifacts
- **Test PyPI Support**: Can publish to Test PyPI for testing
- **Manual Trigger**: Workflow can be manually triggered for testing

## Troubleshooting

1. **Permission Denied**: Ensure trusted publisher is configured on PyPI
2. **Environment Not Found**: Create environments in GitHub repository settings
3. **Build Fails**: Check that `pyproject.toml` is properly configured

## Version Management

Before creating a release, update the version in `pyproject.toml`:
```toml
[project]
version = "0.1.0"
```

Then create a matching Git tag:
```bash
git tag v0.1.0
git push origin v0.1.0
```
