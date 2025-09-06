# Development Workflow

## Branch Strategy

### Primary Branches
- **`main`** - Production-ready code, protected branch
- **`devel`** - Active development branch, all new work happens here

### Development Rules

1. **All new development on `devel` branch**
   - Switch to `devel` immediately when starting work
   - Create feature branches from `devel` if needed
   - Never commit directly to `main` unless explicitly requested

2. **Merging to `main`**
   - Only merge `devel` → `main` when explicitly requested by user
   - User must explicitly say: "merge to main", "push to main", or similar
   - No automatic or assumed merges

3. **Post-merge to `main` Checklist**
   When merging to main, always:
   - [ ] Bump version in `pyproject.toml`
   - [ ] Update `CHANGELOG.md`:
     - Move items from [Unreleased] to new version section
     - Add release date
     - Create comparison link
   - [ ] Create git tag: `git tag v0.x.x`
   - [ ] Push tag: `git push origin v0.x.x`
   - [ ] Create GitHub release (triggers PyPI publish)
   - [ ] Verify PyPI deployment succeeded
   - [ ] Verify binary builds completed

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

## Commit Conventions

Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `style:` Code style (formatting, missing semicolons, etc.)
- `refactor:` Code change that neither fixes a bug nor adds a feature
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

## Testing Requirements

Before merging to main:
1. All tests must pass: `pytest`
2. Pre-commit hooks must pass: `pre-commit run --all-files`
3. Manual testing of new features
4. Cross-platform verification (if applicable)

## Release Process

1. **Prepare Release** (on `devel`):
   ```bash
   # Update version in pyproject.toml
   # Update CHANGELOG.md
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore: prepare release v0.x.x"
   ```

2. **Merge to Main**:
   ```bash
   git checkout main
   git merge devel
   git push origin main
   ```

3. **Create Release**:
   ```bash
   git tag v0.x.x
   git push origin v0.x.x
   gh release create v0.x.x --title "Release v0.x.x" --notes "See CHANGELOG.md"
   ```

4. **Post-Release**:
   ```bash
   git checkout devel
   git merge main  # Sync devel with main
   ```

## Emergency Hotfixes

Only for critical bugs in production:
1. Create hotfix branch from `main`
2. Fix the issue
3. Merge to both `main` and `devel`
4. Follow post-merge checklist

## Claude/AI Assistant Instructions

When working with Claude or other AI assistants:
1. Always work on `devel` branch unless fixing documentation
2. Wait for explicit merge request before touching `main`
3. Remind about version bump and changelog when merge is requested
4. Run tests before committing significant changes
