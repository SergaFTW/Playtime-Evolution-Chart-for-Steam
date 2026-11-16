# steam-playtime

**English** · [Español](README.es.md)

See how your Steam play time evolves, game by game. `steam-playtime` reads the session log that the Steam client already keeps on your computer and turns it into an interactive HTML report:

- **Hours per week**, stacked by game
- **Cumulative hours** for your most played games
- **Daily detail** for any game you pick
- **A table** with total hours, number of sessions, average session length, and first and last time played

Steam's own profile only shows a total per game. This shows *when* you played.

Everything runs locally. Nothing is uploaded and no Steam account or API key is needed.

## Requirements

- Python 3.9 or newer ([python.org](https://www.python.org/downloads/)). No other packages.
- The Steam desktop client, with games launched through it at least once.
- An internet connection when you open the report, to load the chart library (Chart.js). The table works offline.

## Quick start

```bash
pip install git+https://github.com/SergaFTW/Playtime-Evolution-Chart-for-Steam.git
steam-playtime
```

Or without installing: download the repository (Code → Download ZIP), unzip it, open a terminal in that folder and run:

```bash
python -m steam_playtime
```

The report is written to `steam_playtime.html` in the current folder and opens in your browser.

## Options

| Option | What it does |
|---|---|
| `-o FILE`, `--output FILE` | Where to write the report (default `steam_playtime.html`) |
| `--steam-dir DIR` | Steam folder, if it isn't found automatically (the one that contains `logs`) |
| `--lang {auto,en,es}` | Report language. `auto` follows your system language |
| `--min-minutes N` | Ignore sessions shorter than N minutes (default 1) |
| `--exclude APPID` | Leave an app out. Repeat it for several |
| `--include-all` | Keep the apps that are left out by default (see below) |
| `--history FILE` | Use a different history file |
| `--no-history` | Only use what Steam's logs hold right now |
| `--csv FILE`, `--json FILE` | Also export every session |
| `--no-open` | Don't open the browser |

Find an AppID in a game's Steam store URL: `store.steampowered.com/app/<AppID>/…`.

## How it works

Every time Steam starts a game it writes a line to `Steam/logs/gameprocess_log.txt`, and another when the process exits:

```text
[2026-06-05 23:42:45] AppID 3224770 adding PID 10280 as a tracked process "...\Game.exe"
[2026-06-06 01:13:25] AppID 3224770 no longer tracking PID 10280, exit code 0
```

`steam-playtime` pairs those lines into sessions:

- Several processes of the same game that overlap (launcher plus game, for example) count once.
- A session that never got an end line, because Steam was closed or crashed while the game was running, is skipped, since its length is unknown.
- Game names come from the `appmanifest_*.acf` files in every Steam library. For games you have uninstalled, the name is taken from the game's install folder.
- **AppID 480 ("Spacewar")** is a public test app that many games launched outside the store use. Those sessions are named after the folder of the executable, when Steam logged it. The rest are grouped as "Spacewar (AppID 480)".
- Left out by default: Steamworks redistributables (228980), Wallpaper Engine (431960, it runs all day) and the EA app's Steam helper (1182480, it would double-count EA games). Use `--include-all` to keep them.

### History

Steam keeps only the current log plus one older rotated file, so it typically holds a few months. Each run saves every session it finds in a history file, so your data keeps growing even after Steam discards old logs. **Run it now and then** (once a month is plenty) to keep a complete record.

| System | History file |
|---|---|
| Windows | `%LOCALAPPDATA%\steam-playtime\history.json` |
| macOS | `~/Library/Application Support/steam-playtime/history.json` |
| Linux | `~/.local/share/steam-playtime/history.json` |

Delete that file to start over.

## Where Steam is looked for

- **Windows**: the Steam path in the registry, then `Program Files (x86)\Steam`.
- **Linux**: `~/.steam/steam`, `~/.local/share/Steam`, Flatpak and Snap installs.
- **macOS**: `~/Library/Application Support/Steam`.

If yours is elsewhere, pass `--steam-dir`.

## Limitations

- History only starts on the first date in your Steam log. Steam doesn't keep a dated record of older play time.
- Only games launched through Steam are counted. Epic, GOG, Xbox and other launchers are not.
- Time is counted while the game process runs, including time it sits idle or minimized.
- It has been tested on Windows. Linux and macOS logs use the same format, but they have had less real-world testing. Reports are welcome.

## Development

```bash
python -m unittest -v
```

The tests use a fake Steam folder in `tests/fixtures`.

## License

[MIT](LICENSE)
