# Reproduce the public examples

Runtime helpers in `scripts/` use Python 3.10+ standard library only.

```sh
python tools/reproduce.py --out work/demo
python -m unittest discover -s tests -v
```

To refresh the tracked example outputs, copy only `stock.*`, `care.*`, `visit.*`, `replay.*` from `work/demo` into `examples/everyday/`. Keep the synthetic-data notice. Do not publish `ledger.demo.json` as a real household example.

## Optional media regeneration

Only `render_showcase.py` requires Pillow (`pip install Pillow`). Supply a locally available CJK font and optional bold font:

```sh
python tools/render_showcase.py --font /path/to/cjk-font.ttf --bold-font /path/to/cjk-bold.ttf
```

It reads the tracked JSON outputs and writes three PNGs plus `workflow.gif`. Original diagrams, a simple cat illustration and actual synthetic output values are composed with Pillow. No stock photos, user photographs, externally generated pet images or bundled fonts are used. The animation is a workflow illustration, **not** an Agent screen recording. These graphics are not part of the runtime requirement.
