# Security Policy

## Supported versions

Only the latest release receives security fixes. Builds from the
[Releases](https://github.com/Hapfel1/er-save-manager/releases) page and the
[Nexus Mods page](https://www.nexusmods.com/eldenring/mods/9271) are the only
official downloads.

| Version        | Supported |
| -------------- | --------- |
| Latest release | Yes       |
| Older releases | No        |

## Reporting a vulnerability

Report vulnerabilities privately through GitHub:
[Report a vulnerability](https://github.com/Hapfel1/er-save-manager/security/advisories/new)
(Security tab, "Report a vulnerability"). Do not open a public issue,
pull request or Discord post for a security problem.

Include:

- The affected version and platform (Windows, Linux AppImage, Steam Deck)
- What an attacker can do and the steps to reproduce it
- A proof of concept file if one is needed, for example a crafted save file

Fixes ship in a release, and the advisory is published once that release
is out. Reporters are credited in the advisory unless they ask not to be.

## Scope

In scope:

- Crashes, code execution or file writes outside the save folder caused by
  opening a crafted save file
- The community character and preset browsers (downloaded data, share codes)
- The update check and the Troubleshooter add-on download
- The release builds, including the AppImage signature

Out of scope:

- Online bans or anti-cheat flags caused by edited saves. These are game
  behaviour, not vulnerabilities in this tool.
- Vulnerabilities in the games themselves
- Unofficial builds or re-uploads from other sites
