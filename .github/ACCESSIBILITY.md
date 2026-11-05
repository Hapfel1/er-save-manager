# Accessibility

The goal is for the save manager to be usable by everyone who plays the
supported games. The app is built with CustomTkinter, which limits what it
can offer to assistive technology. This page lists what works, what does
not, and how to report a barrier.

## Supported environments

- Windows 10 and 11 (release executable)
- Linux desktops (AppImage), including Steam Deck in desktop mode
- Running from source on Windows or Linux with Python 3.13

## What the app supports

- **UI scale:** Settings offers Auto and 100% to 300%. Text and controls
  scale together.
- **Themes:** Dark (default) and Bright.
- **Keyboard in dialogs:** Escape closes many dialogs and Return confirms
  many input dialogs.
- **Confirmation before changes:** every write is backed up first, and
  unapplied edits are confirmed before switching character, game or save.

## Known limitations

- **Screen readers:** CustomTkinter draws its controls itself and does not
  expose them to Windows UI Automation or Linux AT-SPI. Screen readers such
  as NVDA, JAWS, Narrator or Orca cannot read buttons, tabs or lists.
- **Keyboard navigation:** Tab moves only between text fields. Buttons, tabs,
  checkboxes and lists need a mouse, touchpad or touchscreen.
- **High contrast:** the app does not follow the operating system's high
  contrast mode. Bright theme is the closest option.
- **Color:** not every view has been checked for information shown by
  color alone.

## Reporting a barrier

Open a [bug report](https://github.com/Hapfel1/er-save-manager/issues/new/choose)
and start the title with "Accessibility:", or ask on the
[Discord server](https://dsc.gg/er-saveman). Describe what you tried to do,
which assistive technology or setting you use, and where it failed.
