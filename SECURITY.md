# Security

## Scope

`vpce` runs on the machine that hosts Visual Paradigm. It starts JVMs with the
product's own classpath, writes to the project file you point it at, and — if
you install the bridge — places a plugin under
`%APPDATA%\VisualParadigm\plugins\com.vpce.bridge`.

Things worth reporting:

- A path where a spec, an XML import or a script can make vpce write outside
  the project file or its backup path.
- A command injection issue in how `java` arguments or `-pluginargs` are built.
- A way for a remote party to reach the MCP server (it is stdio only by
  design, so any such path is a bug).

## Not vulnerabilities

- **Needing a installed, licensed Visual Paradigm.** The tool drives the
  product; it does not activate it.
- **Edition gating.** Commands the installed edition blocks are reported as
  `edition-gated` and are not worked around.
- **The CE watermark on exported images.** That is the product's behaviour.

## Reporting

Open a private security advisory on the repository
(`Security` → `Report a vulnerability`) rather than a public issue. Please
include the version from `python -m vpce status`, the exact command, and the
smallest spec or script that reproduces it.

Expect an initial response within a week.
