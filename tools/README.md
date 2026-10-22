# tools

Diagnostics and measurement. Everything here talks to a real Visual Paradigm
installation and works on a temp copy of the project you pass in — none of them
write to your source project.

```bash
python tools/<script>.py <any-project.vpp>
```

| Script | Purpose | Output |
|---|---|---|
| `coverage.py` | Four probes: diagram types, element types, command gating, end-to-end render. Rewrites `COVERAGE.md`. | `coverage.json`, `COVERAGE.md` |
| `find_shapes.py` | Round-robin search for an element type that actually renders per diagram type. | prints a `WINNERS` dict |
| `probe_shape_types.py` | Fixed matrix of diagram × element, to check a specific pairing. | printed table |
| `probe_crc.py` | Documents why `CRCCardDiagram` and `EAProcessStepDiagram` render empty. | printed table |
| `probe_ctor_paths.py` | Shows which element types need `createChild()` instead of `create()`. | raw bridge output |
| `dump_model_types.py` | Regenerate `vpce/core/model_types.json` (1455 names) from `IModelElementFactory`. | JSON |
| `dump_diagram_types.py` | Regenerate `vpce/core/diagram_types.json` (106 names) from `IDiagramTypeConstants`. | JSON |
| `classdump.py` | Minimal `.class` parser — `javap` is not available (the bundled JRE ships `jdk.compiler` without `jdk.zipfs`). | constant pool + methods |
| `bench.py` | Time one bridge call: JVM start, VP bootstrap, project open, statement run. | printed table |
| `regen_doc.py` | Rewrite `COVERAGE.md` from an existing `coverage.json` without re-probing. | `COVERAGE.md` |

## When to re-run

- After a Visual Paradigm upgrade: `dump_model_types.py`, `dump_diagram_types.py`,
  then `coverage.py --render`.
- Before a release: `coverage.py <project> --render`, commit both artefacts.
- When a diagram type renders empty: `find_shapes.py`, then update
  `vpce/core/profiles.py` or `NODE_OVERRIDE` in `coverage.py` with the result.

`coverage.py` takes about seven minutes end to end because 28 command classes
each start a JVM; `--only elements|diagrams|commands|render` runs one probe and
merges into the existing `coverage.json`.
