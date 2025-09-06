#!/bin/bash
# Install shell completions for TASAK

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_color() {
    echo -e "${2}${1}${NC}"
}

# Detect shell
detect_shell() {
    if [ -n "$BASH_VERSION" ]; then
        echo "bash"
    elif [ -n "$ZSH_VERSION" ]; then
        echo "zsh"
    elif [ -n "$FISH_VERSION" ]; then
        echo "fish"
    else
        echo "unknown"
    fi
}

# Install Bash completions
install_bash() {
    print_color "Installing Bash completions..." "$BLUE"

    # Create completion script
    cat > /tmp/tasak-completion.bash << 'EOF'
# TASAK Bash completion
_tasak_complete() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Get available apps from tasak
    if [ "${COMP_CWORD}" -eq 1 ]; then
        # First argument - show apps and built-in commands
        local apps=$(tasak --list-apps 2>/dev/null | grep -E '^\s+' | awk '{print $1}' 2>/dev/null || echo "")
        local builtins="admin --help --version --init --list-apps"
        opts="${apps} ${builtins}"
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi

    # Handle admin subcommands
    if [ "${COMP_WORDS[1]}" = "admin" ] && [ "${COMP_CWORD}" -eq 2 ]; then
        opts="config list status help"
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi

    # Handle --init templates
    if [ "${prev}" = "--init" ]; then
        opts="basic ai-agent team devops"
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
}

complete -F _tasak_complete tasak
EOF

    # Install to user's bash completion directory
    mkdir -p ~/.local/share/bash-completion/completions
    cp /tmp/tasak-completion.bash ~/.local/share/bash-completion/completions/tasak

    # Add to bashrc if not already there
    if ! grep -q "tasak-completion" ~/.bashrc 2>/dev/null; then
        echo "" >> ~/.bashrc
        echo "# TASAK completions" >> ~/.bashrc
        echo "[ -f ~/.local/share/bash-completion/completions/tasak ] && source ~/.local/share/bash-completion/completions/tasak" >> ~/.bashrc
    fi

    print_color "✅ Bash completions installed!" "$GREEN"
    print_color "Reload with: source ~/.bashrc" "$YELLOW"
}

# Install ZSH completions
install_zsh() {
    print_color "Installing ZSH completions..." "$BLUE"

    # Create completion script
    cat > /tmp/_tasak << 'EOF'
#compdef tasak

_tasak() {
    local -a apps builtins

    # Get available apps
    apps=($(tasak --list-apps 2>/dev/null | grep -E '^\s+' | awk '{print $1}' 2>/dev/null))

    # Built-in commands
    builtins=(
        'admin:Administrative commands'
        '--help:Show help message'
        '--version:Show version'
        '--init:Initialize configuration'
        '--list-apps:List available apps'
    )

    # Main completion
    _arguments \
        '1: :->command' \
        '*::arg:->args'

    case $state in
        command)
            _describe 'app' apps
            _describe 'builtin' builtins
            ;;
        args)
            case $words[1] in
                admin)
                    local -a admin_cmds
                    admin_cmds=(
                        'config:Show configuration'
                        'list:List apps'
                        'status:Show status'
                        'help:Show help'
                    )
                    _describe 'admin command' admin_cmds
                    ;;
                --init)
                    local -a templates
                    templates=(
                        'basic:Basic configuration'
                        'ai-agent:AI agent optimized'
                        'team:Team configuration'
                        'devops:DevOps configuration'
                    )
                    _describe 'template' templates
                    ;;
            esac
            ;;
    esac
}

_tasak "$@"
EOF

    # Install to ZSH completions directory
    mkdir -p ~/.zsh/completions
    cp /tmp/_tasak ~/.zsh/completions/_tasak

    # Add to zshrc if not already there
    if ! grep -q "tasak completions" ~/.zshrc 2>/dev/null; then
        echo "" >> ~/.zshrc
        echo "# TASAK completions" >> ~/.zshrc
        echo "fpath=(~/.zsh/completions \$fpath)" >> ~/.zshrc
        echo "autoload -Uz compinit && compinit" >> ~/.zshrc
    fi

    print_color "✅ ZSH completions installed!" "$GREEN"
    print_color "Reload with: source ~/.zshrc" "$YELLOW"
}

# Install Fish completions
install_fish() {
    print_color "Installing Fish completions..." "$BLUE"

    # Create completion script
    cat > /tmp/tasak.fish << 'EOF'
# TASAK Fish completion

function __fish_tasak_apps
    tasak --list-apps 2>/dev/null | grep -E '^\s+' | awk '{print $1}' 2>/dev/null
end

function __fish_tasak_needs_command
    set cmd (commandline -opc)
    if [ (count $cmd) -eq 1 ]
        return 0
    end
    return 1
end

function __fish_tasak_using_command
    set cmd (commandline -opc)
    if [ (count $cmd) -gt 1 ]
        if [ $argv[1] = $cmd[2] ]
            return 0
        end
    end
    return 1
end

# Main commands
complete -f -c tasak -n __fish_tasak_needs_command -a "(__fish_tasak_apps)"
complete -f -c tasak -n __fish_tasak_needs_command -a admin -d "Administrative commands"
complete -f -c tasak -n __fish_tasak_needs_command -l help -d "Show help"
complete -f -c tasak -n __fish_tasak_needs_command -l version -d "Show version"
complete -f -c tasak -n __fish_tasak_needs_command -l init -d "Initialize configuration"
complete -f -c tasak -n __fish_tasak_needs_command -l list-apps -d "List available apps"

# Admin subcommands
complete -f -c tasak -n "__fish_tasak_using_command admin" -a config -d "Show configuration"
complete -f -c tasak -n "__fish_tasak_using_command admin" -a list -d "List apps"
complete -f -c tasak -n "__fish_tasak_using_command admin" -a status -d "Show status"
complete -f -c tasak -n "__fish_tasak_using_command admin" -a help -d "Show help"

# Init templates
complete -f -c tasak -n "__fish_seen_subcommand_from --init" -a basic -d "Basic configuration"
complete -f -c tasak -n "__fish_seen_subcommand_from --init" -a ai-agent -d "AI agent optimized"
complete -f -c tasak -n "__fish_seen_subcommand_from --init" -a team -d "Team configuration"
complete -f -c tasak -n "__fish_seen_subcommand_from --init" -a devops -d "DevOps configuration"
EOF

    # Install to Fish completions directory
    mkdir -p ~/.config/fish/completions
    cp /tmp/tasak.fish ~/.config/fish/completions/tasak.fish

    print_color "✅ Fish completions installed!" "$GREEN"
    print_color "Completions will be available in new Fish sessions" "$YELLOW"
}

# Main installation
main() {
    print_color "🚀 TASAK Shell Completions Installer" "$BLUE"

    SHELL_TYPE=$(detect_shell)

    # Check for specific shell argument
    if [ -n "$1" ]; then
        case "$1" in
            bash)
                install_bash
                ;;
            zsh)
                install_zsh
                ;;
            fish)
                install_fish
                ;;
            all)
                install_bash
                install_zsh
                install_fish
                ;;
            *)
                print_color "Unknown shell: $1" "$RED"
                print_color "Supported: bash, zsh, fish, all" "$YELLOW"
                exit 1
                ;;
        esac
    else
        # Auto-detect and install
        case "$SHELL_TYPE" in
            bash)
                install_bash
                ;;
            zsh)
                install_zsh
                ;;
            fish)
                install_fish
                ;;
            *)
                print_color "Could not detect shell type" "$YELLOW"
                print_color "Please specify: $0 [bash|zsh|fish|all]" "$YELLOW"
                exit 1
                ;;
        esac
    fi

    print_color "" "$NC"
    print_color "Installation complete! 🎉" "$GREEN"
    print_color "Tab completion will be available after reloading your shell" "$YELLOW"
}

main "$@"
