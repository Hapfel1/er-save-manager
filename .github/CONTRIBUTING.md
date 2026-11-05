# Contributing

Bug reports, feature requests and pull requests are welcome. The full guide,
including the project layout, is in the documentation:
[Contributing](https://elden-ring-save-manager.readthedocs.io/en/main/developer/contributing/).

By taking part you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Questions and help

Use the [Discord server](https://dsc.gg/er-saveman) for questions and help
with the app. Issues are for bugs and feature requests.

## Reporting bugs

Open an issue with the matching form. Attach the save file (zipped) when the
bug involves a save, and the logs:

- `errors.log`, written whenever the app shows an error dialog, in
  `%APPDATA%\ER Save Manager` on Windows and `~/.local/share/er-save-manager`
  on Linux.
- `er_save_manager.log` for save loading problems: on the Settings tab, type
  `STRAWBERRY` to show the Advanced section, tick **Verbose logging to file**,
  load the save again, and take the file from the folder of the save.

Security problems go through the [security policy](SECURITY.md), not issues.

## Pull requests

1. Open an issue first for anything larger than a small fix, so the approach
   can be agreed before work starts.
2. Fork the repository and create a branch from `main`.
3. Set up the environment with [uv](https://github.com/astral-sh/uv):

   ```bash
   uv sync --locked --dev
   uv run python run_gui.py
   ```

4. Before pushing, run:

   ```bash
   uv run ruff check
   uv run ruff format
   uv run pytest
   ```

5. Keep one topic per pull request and describe what changed and why. Add
   screenshots for UI changes.

Save format changes must derive offsets from the parser instead of
hardcoding them, and must keep vanilla (`.sl2`) and Seamless Co-op (`.co2`)
saves working.

## License

The project uses a source-available license, not an open source one. By
submitting a contribution you agree that it is licensed under the
[project license](../LICENSE).
