# Fixture generator

`build_fixtures.py` rebuilds every fixture folder in `tests/` from `source/` (the `SPEC.md`, `RESOURCES.md` and `PLAN.md` of `ok/`). It writes `ok/` with `Plan-Labels.json` and `Decision-Classes.json`, then makes each `fail-*` / `warn-*` folder as a copy of `ok/` with one defect, and recomputes the label hashes last (except in `warn-W-STALE-LABELS`).

```
python build_fixtures.py            # writes into tests/ (the folder above this one)
python build_fixtures.py <out-dir>  # writes somewhere else, e.g. to compare
python ../run_tests.py
```

To change a fixture, edit `source/` or the variant functions in `build_fixtures.py`, never the generated folders, and update `../EXPECTED.md`. The generator deletes and rewrites the folders it owns. Standard library only.
