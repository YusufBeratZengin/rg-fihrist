# Contributing

Thanks for taking a look. This project is small on purpose: standard library
only, no build step, no network in tests.

## Before you open a pull request

```console
$ python -m venv .venv
$ . .venv/bin/activate            # Windows: .venv\Scripts\activate
$ pip install -e ".[dev]"
$ bash scripts/check.sh
```

`scripts/check.sh` must exit 0. It runs, in order: secret scan, `ruff check`,
`ruff format --check`, `mypy`, `pytest --cov` (coverage floor 85%) and a CLI
smoke test. Please do not lower the coverage floor to make a change pass — add a
test instead.

## What a good change looks like

- **A bug fix comes with a regression test that fails before the fix.** Say so in
  the pull request: which test was red, which line made it green.
- **No network in tests.** Inject `getir_fn`/`sleep_fn`/`saat_fn` into
  `Indirici` (see `tests/test_indir.py`) or reuse the recorded pages in
  `tests/fixtures/`.
- **Fixtures are recordings, not inventions.** If the site layout changes, record
  a new page, keep the source URL and the date in `tests/fixtures/README.md`, and
  strip anything unrelated to the index (scripts, analytics, user data).
- **Keep the politeness policy intact.** Nothing may lower the 2-second floor,
  drop the `User-Agent`, or skip robots.txt by default.
- **Docs stay in sync.** User-visible behaviour belongs in `README.md` and
  `README.tr.md`; changes belong in `CHANGELOG.md` under the newest version
  heading. If the change alters an example output, update that example too.

## Style

- Python 3.10+, type hints on every function, `ruff` (line length 100) and
  `mypy` clean.
- Code identifiers and log messages are ASCII (Turkish characters are fine in
  data and in documentation).
- Prefer a clear error over a silently empty result: that is why `YapiHatasi`
  exists.

## Reporting bugs

Open an issue with the command you ran, the exit code, and the stderr output.
Do not paste page content that contains personal data; a date plus the exit code
is usually enough to reproduce.
