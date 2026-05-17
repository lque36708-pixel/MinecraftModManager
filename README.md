# mmm — Minecraft Mod Manager

`mmm` is a lightweight, dependency-aware CLI tool to manage Minecraft mods from [Modrinth](https://modrinth.com/). It downloads, tracks, and resolves dependencies automatically — no launcher, no GUI, no bloat.

Each project directory keeps its own `profile.json` (version/loader) and `metadata.json` (installed mods), so you can manage multiple modpacks independently.

## Features

- **Automatic Dependency Resolution** — Required dependencies are downloaded recursively; optional deps are skipped.
- **Per-Directory Profiles** — Set a different version/loader for each modpack folder.
- **Bulk Installation** — Install multiple mods at once via comma-separated names, search indexes, or `.txt` files.
- **Smart Search** — Filter by Minecraft version and mod loader, or disable filters to search everything.
- **Dependency-Aware Removal** — Warns if other mods depend on what you're removing.
- **Autoremove Orphans** — Clean up unused dependencies in one command.
- **SHA-512 Verification** — Every download is checksum-verified automatically.
- **No Login Required** — No API key, no account, no background services. Just `mmm` and a terminal.
- **Rich Terminal UI** — Colorful, structured output via the [rich](https://github.com/Textualize/rich) library.

## Requirements

- **Python 3.8+**
- **pip** (Python package installer)
- **rich** — installed automatically during setup

## Installation

### Linux / macOS

```bash
git clone https://github.com/lque36708-pixel/MinecraftModManager.git
cd MinecraftModManager
./install.sh
source ~/.bashrc
```

The install script adds an alias to `~/.bashrc`:

```bash
alias mmm="python3 /path/to/MinecraftModManager/mmm.py"
```

If you use **zsh**, add the alias to `~/.zshrc` manually after cloning:

```bash
echo 'alias mmm="python3 /path/to/MinecraftModManager/mmm.py"' >> ~/.zshrc
source ~/.zshrc
```

### Windows (PowerShell)

1. Install Python 3.8+ from [python.org](https://python.org) — ensure **Add to PATH** is checked.
2. Clone the repository:
   ```powershell
   git clone https://github.com/lque36708-pixel/MinecraftModManager.git
   cd MinecraftModManager
   ```
3. Install the dependency:
   ```powershell
   pip install rich
   ```
4. Add a function to your PowerShell profile for convenience:
   ```powershell
   function mmm { python "$env:USERPROFILE\MinecraftModManager\mmm.py" @args }
   ```
   Or just run `python mmm.py` directly in the repo folder.

### Verify Installation

```bash
mmm --help
```

You should see the mmm logo, a list of commands, and usage notes.

### Updating

```bash
cd MinecraftModManager
git pull
```

That's it — no build step, no reinstall needed.

## Quick Start

```bash
# 1. Go to your mods folder
cd ~/minecraft/mods

# 2. Set your Minecraft version and loader
mmm set-profile 1.21.1 fabric

# 3. Install mods (dependencies resolved automatically)
mmm get sodium, lithium, iris

# 4. See what's installed
mmm list

# 5. Remove a mod (warns if other mods depend on it)
mmm remove sodium

# 6. Clean up orphaned dependencies
mmm autoremove
```

## Usage

### `set-profile <mc_version> <loader>`

Set the Minecraft version and mod loader for the current directory.

```bash
mmm set-profile 1.21.1 fabric
mmm set-profile 1.20.4 forge
mmm set-profile 1.21 neoforge
```

Loaders: `fabric`, `forge`, `quilt`, `neoforge`

This creates a `profile.json` file in the current directory. Every command that needs a profile (search, get, show, list, remove, autoremove) will check for this file and warn you if it's missing.

### `search <query> [options]`

Search Modrinth for mods matching your query. Results are numbered and can be referenced by index in `get`, `show`, or `remove`.

```bash
mmm search sodium                              # uses profile version/loader
mmm search "performance" -n 15                 # show 15 results instead of 10
mmm search sodium --no-filter                  # ignore profile, search all
mmm search sodium --filter-version 1.20.4      # override version filter
mmm search sodium --filter-loader forge        # override loader filter
```

Flags:
- `-n <count>` — Number of results (default: 10)
- `--no-filter` — Don't filter by profile version/loader
- `--filter-version <version>` — Override the version filter
- `--filter-loader <loader>` — Override the loader filter

### `get <name> [options]`

Install one or more mods to the current directory. Required dependencies are resolved and downloaded automatically.

```bash
mmm get sodium                                  # single mod by slug
mmm get sodium, lithium, iris                   # multiple mods (comma-separated)
mmm get -i 1                                    # install search result #1
mmm get -i 1,3,5                                # install search results #1, 3, 5
mmm get -f mods.txt                             # read mod names from a file
mmm get immediately fast, sodium                # "immediately fast" is one mod name
```

File format (`-f`):
```
sodium
lithium
iris
immediately fast
```

Alias: `mmm install` (same as `mmm get`)

### `show <name> | -i <index>`

Display full details about a mod: version, file size, dependencies, checksums, and the full Markdown description.

```bash
mmm show sodium                                 # by slug name
mmm show -i 1                                   # by search/list index
```

### `list`

Show all tracked mods in the current directory, including file sizes and the dependency graph.

```bash
mmm list
mmm ls                                          # alias
```

### `remove <name> | -i <index> | -a`

Remove installed mods. Warns if any other mod depends on the one being removed.

```bash
mmm remove sodium                               # by name
mmm remove -i 1                                 # by search/list index
mmm remove sodium, lithium                      # multiple
mmm remove -a                                   # remove everything (nuclear)
```

Alias: `mmm rm` (same as `mmm remove`)

### `autoremove`

Find and remove dependencies that are no longer required by any installed mod.

```bash
mmm autoremove
```

### `profile`

Display the current profile settings (Minecraft version, loader) and the cache directory information.

```bash
mmm profile
```

## Workflows

### Build a Performance Modpack

```bash
cd ~/minecraft/mods
mmm set-profile 1.21.1 fabric
mmm get sodium, lithium, iris, immediately fast
mmm get ferritecore, entityculling, modernfix, krypton
mmm get sodium-extra
mmm list                                     # verify everything installed
```

### Explore and Install from Search

```bash
mmm search "chunk loading"
mmm show -i 1
mmm get -i 1
```

### Bulk Install from a List

```bash
# mods.txt:
# sodium
# lithium
# iris
# ferritecore
mmm get -f mods.txt
```

## How It Works

### File Structure

```
your-mods-folder/
├── profile.json          # Minecraft version, loader (created by set-profile)
├── metadata.json         # Tracked mods, versions, checksums
├── sodium-0.6.0+mc1.21.jar
├── fabric-api-0.102.0+mc1.21.jar
└── ...
```

### Dependency Resolution

When you run `mmm get sodium`, it:
1. Queries Modrinth for the best version matching your profile.
2. Downloads the `.jar` file to the current directory.
3. Reads the mod's dependencies from Modrinth's API.
4. Recursively downloads any **required** dependencies (optional deps are skipped).
5. Records all installed files in `metadata.json`.

### Removal Safety

When you run `mmm remove sodium`, it checks `metadata.json` to see if any other installed mods list sodium as a dependency. If so, it warns you before proceeding.

## Troubleshooting

### "No profile set in this directory"

You're in a folder that doesn't have a `profile.json`. Either:

```bash
# Option A — Set a profile in the current folder
mmm set-profile 1.21.1 fabric

# Option B — Move to your mods folder and try again
cd ~/minecraft/mods
mmm list
```

### Mod not found in search

- Try `--no-filter` to search without version/loader restrictions.
- Make sure the mod name is correct (it uses Modrinth slugs).
- Some mods may only be on CurseForge — mmm only supports Modrinth.

### Rate limiting

Modrinth's API allows 300 requests per minute. This is more than enough for normal use.

## Uninstall

### Linux / macOS

```bash
cd MinecraftModManager
./uninstall.sh
```

Remove the cloned folder if you no longer need it:

```bash
rm -rf MinecraftModManager
```

### Windows

1. Remove the function from your PowerShell profile.
2. Delete the cloned folder.
3. Optionally remove `rich`:
   ```powershell
   pip uninstall rich
   ```

## Commands Reference

| Command | Alias | Description |
|---------|-------|-------------|
| `set-profile <ver> <loader>` | — | Set MC version and loader for this directory |
| `search <query>` | — | Search Modrinth for mods |
| `get <name>` | `install` | Install mod(s) with dependency resolution |
| `show <name>` | — | Show detailed mod info |
| `list` | `ls` | List installed mods |
| `remove <name>` | `rm` | Remove mod(s) |
| `autoremove` | — | Clean up orphaned dependencies |
| `profile` | — | View current profile |

## Notes

- Mods always install to the **current working directory**, not to a system location.
- Only **required** dependencies are auto-installed; optional deps are skipped.
- Commas separate multiple mod names: `mmm get sodium, lithium, iris`
- Spaces are part of the mod name: `mmm get immediately fast` installs "Immediately Fast"
- Every download is verified against its SHA-512 hash.
- Profile and metadata are stored as plain JSON — easy to edit or back up.
- No login, no API key, no telemetry, no background processes.
