# Translating ER Save Manager

Translations use the gettext format. Every language lives in
`src/er_save_manager/locales/<code>/LC_MESSAGES/er_save_manager.po`.

## What is translated

Only the interface: buttons, labels, dialogs, tab names, status messages.

Game data is not translated and will not be. Item names, boss names, NPC names,
locations and regions come from the game's own files and are already officially
localized by FromSoftware. Retyping them by hand would produce worse results
than leaving them in English.

Three further groups stay in English for technical reasons:

- Tab names. CustomTkinter's `CTkTabview` uses the tab name as both the label
  and the lookup key, and the names are also used as dictionary keys that
  control which tabs appear per game. Translating them needs the key separated
  from the label first.
- Combobox entries passed as `values=[...]`. These are compared as keys
  elsewhere in the code, so translating one side alone breaks the comparison.
- The `description=` argument of `create_backup()`. It becomes part of the
  backup filename on disk.

## Contributing a translation

1. Install [Poedit](https://poedit.net). It is free and available on Windows,
   macOS and Linux.
2. Fork the repository.
3. If your language already exists, open its `.po` file in Poedit. If it does
   not, open `src/er_save_manager/locales/er_save_manager.pot` in Poedit and
   choose "Create new translation".
4. Translate. Poedit shows which entries are missing or need review.
5. Save. Poedit writes a `.mo` file next to the `.po`; both belong in the
   commit.
6. Open a pull request with the `.po` and `.mo` files.

You do not need Python or any build tools to translate.

### Things to watch for

Placeholders in braces must survive translation exactly as written. The text
around them can move freely:

    msgid  "Loaded {count} characters from {file}"
    msgstr "{count} Charaktere aus {file} geladen"

Entries marked fuzzy mean the English source changed since the translation was
written. Check them and clear the flag once confirmed.

Some entries carry a context note, shown by Poedit above the source string. It
distinguishes identical English words that need different translations, such as
"Save" as a button versus "Save" as a save file.

German is maintained by the project author. Other languages depend entirely on
community contributions.

## Maintainer workflow

Requires the dev dependency group (`uv sync --group dev`).

    uv run scripts/i18n_tool.py extract      rebuild the .pot from source
    uv run scripts/i18n_tool.py init <code>  start a new language
    uv run scripts/i18n_tool.py update       merge .pot into every .po
    uv run scripts/i18n_tool.py compile      build .mo files
    uv run scripts/i18n_tool.py status       per-language coverage

Run `extract` then `update` after changing any English string. `update` marks
altered strings fuzzy so translators are told what to recheck, which is the
main reason this project uses gettext rather than plain JSON files.

`compile` must run before packaging. The build scripts bundle
`src/er_save_manager/locales/` as data, and only `.mo` files are read at
runtime.

## Adding translatable strings to the code

Import the helper and wrap the string at the point it is constructed:

    from er_save_manager.i18n import t

    ctk.CTkLabel(frame, text=t("Backup Manager"))

For interpolation, translate the template and format afterwards, so the
placeholder order stays under the translator's control:

    t("Loaded {count} characters").format(count=n)

Never build a sentence by concatenating translated fragments. Word order
differs between languages and the fragments cannot be reordered.

For counts, use `tn()` so languages with more than two plural forms work:

    tn("{n} backup", "{n} backups", count).format(n=count)

For ambiguous words, use `tc()` with a short context:

    tc("button", "Save")

Do not call `t()` on module-level constants. The catalog is selected during
startup, so anything resolved at import time is frozen to English. Wrap the
string where the widget is built instead.

To find strings that still need wrapping:

    uv run scripts/i18n_lint.py              summary per file
    uv run scripts/i18n_lint.py --detail     every site with line numbers
    uv run scripts/i18n_lint.py --path ui    limit to a subtree
    uv run scripts/i18n_lint.py --exclude X  skip a path substring

To wrap strings in bulk, `scripts/i18n_migrate.py` rewrites the same sites the
lint reports. Review its diff; it cannot tell display text from a lookup key.

    uv run scripts/i18n_migrate.py --path ui/tabs --dry-run
