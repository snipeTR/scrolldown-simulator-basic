# Scrolldown Simulator Basic

A tiny Windows tool for mouse wheels that don't spin freely. Press a hotkey and it scrolls the window under your mouse cursor like a flicked free-spinning wheel: very fast at first, then slowing down smoothly until it stops.

## Download

Get `ScrolldownSimulatorBasic.exe` from [Releases](../../releases). No installation needed.

## Usage

1. Run the program and leave its window open (you can minimize it).
2. Put the mouse cursor over the page you want to scroll.
3. Press the hotkey (default **Ctrl+Shift+L**). Scrolling starts when you release the keys.
4. Press the hotkey again while it is scrolling to stop.

Settings:

- **Starting speed** (0-100): how fast the scroll starts.
- **Stop after** (seconds): when the scroll comes to a stop.
- **Change hotkey**: lists the key combinations that no other program has taken; double-click one to use it.

Settings are saved to `settings.json` next to the program.

## Notes

- The free-hotkey list only detects global hotkeys. A shortcut that works only inside one program (for example inside your editor) can still show up as free.
- Windows doesn't let normal programs send input to windows running as administrator, so those don't scroll.
- Windows Defender sometimes flags PyInstaller-built `.exe` files by mistake. You can run the Python script instead.

## Run from source

Requires Python 3 on Windows. It uses only the standard library.

```
pythonw scrolldown_simulator_basic.py
```

The `.exe` is built by GitHub Actions with PyInstaller (see `.github/workflows/build.yml`). Pushing a `v*` tag publishes a release.
