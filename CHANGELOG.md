# Changelog

All notable changes to TASAK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Fixed
- Nothing yet

## [0.1.1] - 2025-01-06

### Fixed
- **App listing format** - Added app type information in parentheses to list output
- **Test expectations** - Updated tests to match actual output messages
- **Error flow tests** - Fixed incorrect test assertion for app not enabled error

## [0.1.0] - 2025-01-06

### Added
- **Multi-platform binary builds** - Automated binary generation for Linux, Windows, and macOS (Intel + Apple Silicon)
- **GitHub Actions workflows** - Automated PyPI publishing and binary builds on release
- **Python plugins support** - Dynamic plugin discovery and integration system
- **Admin commands** - New `tasak admin` subcommand for administrative tasks
- **Custom CLI creation** - `tasak admin create_command` for generating custom CLI tools
- **PyPI publishing infrastructure** - Complete setup for package distribution
- **MCP E2E testing** - Comprehensive end-to-end test suite for MCP servers
- **MIT License** - Open source licensing
- **Comprehensive documentation** - Extended docs for setup, usage, and development
- **Shell completions** - Support for bash/zsh/fish autocompletion
- **Interactive MCP mode** - Enhanced interactive experience for MCP applications

### Changed
- **Improved cross-platform compatibility** - Better Windows/Unix support with proper path handling
- **Enhanced documentation structure** - Reorganized docs/ directory with better navigation
- **Better error messages** - More helpful error messages with suggestions
- **Cleaner README** - Removed promotional content, focused on practical information

### Fixed
- **Cross-platform path handling** - Fixed issues with Windows vs Unix path separators
- **MCP interactive tests** - Fixed failing interactive mode tests
- **Mock configurations** - Corrected test mock setups
- **Create command compatibility** - Fixed cross-platform issues in create_command

## [0.0.1] - 2024-12-20

### Added
- Initial release of TASAK
- Basic `cmd` and `mcp` application types
- Hierarchical configuration system
- MCP client implementation
- OAuth 2.1 authentication support
- Basic CLI interface

[Unreleased]: https://github.com/jacekjursza/tasak/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jacekjursza/tasak/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/jacekjursza/tasak/releases/tag/v0.0.1
