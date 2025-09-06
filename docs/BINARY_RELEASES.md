# Binary Releases

TASAK provides pre-built binaries for multiple platforms, automatically built and attached to each GitHub release.

## Supported Platforms

| Platform | Binary Name | Architecture |
|----------|------------|--------------|
| Linux | `tasak-linux-x64` | x86_64 |
| Windows | `tasak-windows-x64.exe` | x86_64 |
| macOS (Apple Silicon) | `tasak-macos-x64` | ARM64 |
| macOS (Intel) | `tasak-macos-intel` | x86_64 |
| macOS (Universal) | `tasak-macos-universal` | ARM64 + x86_64 |

## Installation from Binary

### Linux
```bash
# Download the latest release
wget https://github.com/jacekjursza/tasak/releases/latest/download/tasak-linux-x64

# Make executable
chmod +x tasak-linux-x64

# Move to PATH (optional)
sudo mv tasak-linux-x64 /usr/local/bin/tasak

# Verify installation
tasak --version
```

### macOS
```bash
# Download the appropriate binary
# For Apple Silicon (M1/M2/M3):
curl -L -o tasak https://github.com/jacekjursza/tasak/releases/latest/download/tasak-macos-x64

# For Intel Macs:
curl -L -o tasak https://github.com/jacekjursza/tasak/releases/latest/download/tasak-macos-intel

# Or Universal (works on both):
curl -L -o tasak https://github.com/jacekjursza/tasak/releases/latest/download/tasak-macos-universal

# Make executable
chmod +x tasak

# Remove quarantine attribute (macOS security)
xattr -d com.apple.quarantine tasak

# Move to PATH (optional)
sudo mv tasak /usr/local/bin/

# Verify installation
tasak --version
```

### Windows
```powershell
# Download using PowerShell
Invoke-WebRequest -Uri "https://github.com/jacekjursza/tasak/releases/latest/download/tasak-windows-x64.exe" -OutFile "tasak.exe"

# Or using curl (Windows 10+)
curl -L -o tasak.exe https://github.com/jacekjursza/tasak/releases/latest/download/tasak-windows-x64.exe

# Add to PATH (optional) - run as Administrator
Move-Item tasak.exe "C:\Program Files\tasak\tasak.exe"
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\tasak", [EnvironmentVariableTarget]::Machine)

# Verify installation
tasak --version
```

## Verifying Downloads

Each binary comes with a SHA256 checksum file. To verify:

### Linux/macOS
```bash
# Download both binary and checksum
wget https://github.com/jacekjursza/tasak/releases/latest/download/tasak-linux-x64
wget https://github.com/jacekjursza/tasak/releases/latest/download/tasak-linux-x64.sha256

# Verify
sha256sum -c tasak-linux-x64.sha256
```

### Windows (PowerShell)
```powershell
# Download both files
Invoke-WebRequest -Uri "https://github.com/jacekjursza/tasak/releases/latest/download/tasak-windows-x64.exe" -OutFile "tasak.exe"
Invoke-WebRequest -Uri "https://github.com/jacekjursza/tasak/releases/latest/download/tasak-windows-x64.exe.sha256" -OutFile "tasak.exe.sha256"

# Calculate hash
$hash = (Get-FileHash -Path "tasak.exe" -Algorithm SHA256).Hash
$expected = (Get-Content "tasak.exe.sha256" -Raw).Split(' ')[0]

# Verify
if ($hash -eq $expected) {
    Write-Host "Verification successful!" -ForegroundColor Green
} else {
    Write-Host "Verification failed!" -ForegroundColor Red
}
```

## Build Process

Binaries are automatically built using GitHub Actions when a new release is created. The build process:

1. Triggers on release publication
2. Builds on native runners for each platform
3. Uses PyInstaller to create standalone executables
4. Generates SHA256 checksums
5. Attaches binaries and checksums to the release

## Building from Source

If you prefer to build your own binary:

```bash
# Clone the repository
git clone https://github.com/jacekjursza/tasak.git
cd tasak

# Install dependencies
pip install -e .
pip install pyinstaller

# Build using the spec file
pyinstaller tasak.spec

# Or build manually
pyinstaller --onefile \
  --name tasak \
  --add-data "README.md:." \
  --hidden-import tasak \
  --collect-all tasak \
  tasak/main.py

# Binary will be in dist/tasak
```

## Troubleshooting

### macOS: "Cannot be opened because the developer cannot be verified"
```bash
xattr -d com.apple.quarantine tasak
```

### Linux: "Permission denied"
```bash
chmod +x tasak-linux-x64
```

### Windows: Security warning
Right-click the file → Properties → Check "Unblock" → Apply

### Missing dependencies
The binaries are standalone and include all dependencies. If you encounter issues, try:
- Re-downloading the binary
- Verifying the checksum
- Building from source
