# Windows Security & Version Files

This directory contains Windows-specific security and version information files for the ER Save Manager executable.

## Files

### `app.manifest`
Windows application manifest that defines:
- **Windows 10/11 Compatibility**: Declares support for Windows 10 and 11
- **DPI Awareness**: Ensures proper scaling on high-DPI displays
- **Execution Level**: Runs with user privileges (non-admin)
- **Security Settings**: Standard Windows security configuration

This file is embedded in the Windows executable during the build process.

### `version.txt`
Plain text version metadata (version, product, company, description) updated by `scripts/bump_version.py` for easy viewing and tooling. This replaces the old binary RC approach entirely.

## Version Synchronization

Version numbers in both files are automatically updated when releasing new versions via the GitHub Actions workflow:

1. **Release Trigger**: Merge to `main` or manual `workflow_dispatch`
2. **Version Planning**: `scripts/bump_version.py` is called with the new version
3. **File Updates**: 
   - `pyproject.toml` version updated
   - `resources/version.rc` version fields updated
   - Both files committed to release branch

### Manual Version Update

To manually bump the version during development:

```bash
uv run scripts/bump_version.py 1.2.3
```

This updates:
- `pyproject.toml`: Version = "1.2.3"
- `resources/version.txt`: Version metadata updated to 1.2.3.0
- `resources/app.manifest`: AssemblyIdentity version = 1.2.3.0

## Security Considerations

- **Manifest**: Non-admin execution level prevents accidental privilege escalation
- **DPI Awareness**: Prevents blurry rendering which could obscure security prompts
- **Version Info**: Allows Windows Defender and security tools to validate the executable

## Build Integration

These files are automatically included in Windows builds via `build-windows.py`:
- Manifest is embedded in the executable by cx_Freeze
- Version txt file contents are used for executable metadata
- Icon file is set during executable creation

No additional configuration is required during builds.
