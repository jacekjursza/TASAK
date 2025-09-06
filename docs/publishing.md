# Publishing TASAK to PyPI

## Prerequisites

1. **PyPI Account**: Create accounts at:
   - [PyPI](https://pypi.org/account/register/) - Main repository
   - [TestPyPI](https://test.pypi.org/account/register/) - Testing repository

2. **API Tokens**: Generate tokens for secure publishing:
   - PyPI: Account Settings → API tokens → Add API token
   - TestPyPI: Same process on test.pypi.org

3. **Configure Tokens**: Save in `~/.pypirc`:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE

[testpypi]
username = __token__
password = pypi-YOUR_TEST_TOKEN_HERE
```

## Quick Publish

### 1. Test Release (Recommended First)
```bash
# Dry run - just check everything
python scripts/publish.py --check

# Publish to TestPyPI
python scripts/publish.py --test

# Install and test from TestPyPI
pip install -i https://test.pypi.org/simple/ tasak==VERSION
```

### 2. Production Release
```bash
# Full release to PyPI
python scripts/publish.py

# This will:
# ✓ Check version is newer than PyPI
# ✓ Run all tests
# ✓ Run code quality checks
# ✓ Build distribution packages
# ✓ Upload to PyPI
# ✓ Create and push git tag
```

## Manual Publishing Process

If you prefer manual control:

### 1. Update Version
Edit `pyproject.toml`:
```toml
[project]
version = "0.2.0"  # Increment from current
```

### 2. Run Quality Checks
```bash
# Run tests
pytest -q

# Check code quality
ruff check .
ruff format --check .
```

### 3. Build Package
```bash
# Clean old builds
rm -rf dist/ build/ *.egg-info

# Build distributions
python -m build
```

### 4. Upload to PyPI
```bash
# Test first
python -m twine upload --repository testpypi dist/*

# Then production
python -m twine upload dist/*
```

### 5. Create Git Tag
```bash
git tag -a v0.2.0 -m "Release 0.2.0"
git push origin v0.2.0
```

## Script Options

The `scripts/publish.py` script supports:

- `--test` - Publish to TestPyPI instead of PyPI
- `--check` - Run all checks without publishing
- `--skip-tests` - Skip test suite (not recommended)
- `--skip-tag` - Don't create git tag

## Version Management

Follow semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking API changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

## Troubleshooting

### "Version already exists"
You must increment the version in `pyproject.toml`. PyPI doesn't allow overwriting.

### "Invalid credentials"
Check your `~/.pypirc` file has correct API tokens (start with `pypi-`).

### "Package name taken"
The name "tasak" is reserved. For forks, choose a different name in `pyproject.toml`.

### TestPyPI Dependencies
TestPyPI doesn't mirror all packages. Some dependencies might fail to install.

## Post-Release Checklist

After successful release:

- [ ] Verify installation: `pip install tasak==VERSION`
- [ ] Test basic functionality: `tasak --help`
- [ ] Update GitHub release notes
- [ ] Announce in discussions/social media
- [ ] Update documentation if needed

## Automation with GitHub Actions

For CI/CD, add `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install build twine
          pip install -e .

      - name: Build package
        run: python -m build

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: python -m twine upload dist/*
```

Remember to add `PYPI_API_TOKEN` to repository secrets!
