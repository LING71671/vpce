# Contributing

## What this project is

`vpce` drives a local Visual Paradigm installation headlessly: it reads and
writes `.vpp` projects, creates model elements and diagrams, and renders
images. It does not redistribute, patch or relicense anything from Visual
Paradigm — it calls the command classes and the Open API that ship with the
product.

## Layering is a hard rule

```
cli / mcp_server  ->  service  ->  ports  ->  adapters  ->  core
```

- `core/` must stay pure: standard library only, no `subprocess`, no
  `os.environ`, no file writes. It is the part that can be unit tested without
  Visual Paradigm installed.
- `adapters/` is the only layer that starts processes or touches `%APPDATA%`.
- Transports (`cli.py`, `mcp_server.py`) contain no business logic.

If a change needs a new external capability, add a method to a port and
implement it in an adapter. Do not import `adapters` from `service`.

## Development setup

```bash
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e .

python -m unittest discover -s tests -p "test_core.py" -v   # no VP needed
```

Building the Open API bridge (needs a local Visual Paradigm install):

```bash
python java/bridge/build.py
python -m vpce bridge --install
```

The build step unpacks `lib/openapi.jar` into `java/bridge/build/api` first:
the JDK bundled with Visual Paradigm ships `jdk.compiler` but not `jdk.zipfs`,
so `javac -cp something.jar` fails with "no file system provider handles file".
More of these are in [`docs/GOTCHAS.md`](docs/GOTCHAS.md).

## Tests

| Command | Needs VP | What it covers |
|---|---|---|
| `python -m unittest discover -s tests -p "test_core.py"` | no | spec, layout, statements, XML model/builder |
| `python tests/manual/test_e2e.py <any.vpp>` | yes | XML channel + Open API + spec drawing, ~1 min |
| `python tests/mcp_smoke.py <any.vpp>` | yes | MCP handshake, tool list, read tools |

Integration tests copy the project you pass in and never write to it.

## Changing the API surface

Anything that changes a tool name, argument, CLI flag or spec field must be
reflected in `docs/API.md` in the same commit. `COVERAGE.md` is generated —
run `python tools/coverage.py <any.vpp> --render` instead of editing it.

## Commit messages

Conventional-ish, one line summary in the imperative, then a short body if the
"why" is not obvious. Keep unrelated changes out of the same commit.

## Reporting bugs

Include the output of `python -m vpce status --probe`, the Visual Paradigm
build number, and the spec or command that failed. A PNG that came out wrong is
usually more informative than the error text.
