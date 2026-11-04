# Security policy

## Supported versions

Only the latest released minor version receives fixes.

## Reporting a vulnerability

Please report privately, not in a public issue:

- GitHub: *Security* tab → *Report a vulnerability* on the repository.

Include the version, the command or API call, and what you observed. You can
expect an initial reply within a week. Please give a fix a reasonable window
before publishing details.

## Scope

This tool fetches a public web page and writes JSON/RSS files. It has no server
component, no credentials, no telemetry and no runtime dependencies, so the most
interesting failure modes are:

- a malformed or hostile page causing a crash or unbounded memory use,
- an argument that makes the tool write outside the requested output paths,
- anything that would silently weaken the 2-second request floor or the
  robots.txt check.

Report those with a minimal reproducer (a short HTML snippet is ideal).
