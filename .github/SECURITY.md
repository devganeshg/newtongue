# Security Policy

VoxDub runs entirely on your own machine and doesn't handle authentication, payments, or
other people's data, but if you find a genuine security issue (e.g. something that lets a
malicious video or subtitle file execute code, or an unsafe use of a subprocess/temp file),
please report it privately rather than opening a public issue.

## Reporting a vulnerability

Use GitHub's private reporting flow: go to the
[Security tab](https://github.com/devganeshg/voxdub/security) →
**Report a vulnerability**. This opens a private draft advisory visible only to you and the
maintainers, so details aren't public before a fix ships.

Please include:

- The version/commit you're on
- Steps to reproduce (a minimal video/subtitle file if relevant)
- What you'd expect to happen vs. what actually happens

## Supported versions

VoxDub doesn't yet maintain multiple release branches — security fixes are made against the
latest release. Please make sure you're on the newest version before reporting.
