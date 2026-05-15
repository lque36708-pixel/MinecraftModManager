# mmm — Minecraft Mod Manager

`mmm` is a lightweight, dependency-aware CLI tool to manage Minecraft mods from [Modrinth](https://modrinth.com/).

## Features
- **Local Profiles**: Manages mod profiles independently for each project directory.
- **Dependency Resolution**: Automatically and recursively installs all required dependencies.
- **Bulk Installation**: Supports installing mods from command-line arguments or text files.
- **Flexible Search**: Filter by version/loader or disable filters entirely.
- **Lightweight**: Single Python file, no bloat, no API keys required, no background tracking.

## Installation

```bash
git clone https://github.com/yourusername/mmm.git
cd mmm
./install.sh
```

Then restart your terminal or run `source ~/.bashrc`.

### Uninstall

```bash
cd mmm
./uninstall.sh
```

## Usage

### 1. Initialize Profile
Before installing mods in a directory, set your target Minecraft version and loader:

```bash
mmm set-profile 1.21.1 fabric
```

### 2. Search Mods
Search filters use your profile by default, or can be overridden:

```bash
mmm search sodium                                          # uses profile (1.21.1 / fabric)
mmm search sodium --no-filter                               # search all versions/loaders
mmm search sodium --filter-version 1.20.4 --filter-loader forge  # specific filter
```

### 3. Install Mods
- **By Name** (dependencies auto-resolved):
  ```bash
  mmm install sodium, lithium, iris
  ```
  Example: `mmm install indium` automatically downloads **sodium** as a dependency.

- **From File** (one mod slug per line):
  ```bash
  mmm install -f mods.txt
  ```
- **By Search Index**:
  ```bash
  mmm search sodium
  mmm show -i 1
  mmm install -i 1
  ```

### 4. Management
- **List installed mods**:
  ```bash
  mmm ls
  ```
- **Show mod details** (full markdown description):
  ```bash
  mmm show sodium
  mmm show -i 1        # by list/search index
  ```
- **Remove a mod**:
  ```bash
  mmm rm sodium
  ```
- **Autoremove unused dependencies**:
  ```bash
  mmm autoremove
  ```
- **View current profile**:
  ```bash
  mmm profile
  ```

## Commands
| Command | Alias | Description |
| :--- | :--- | :--- |
| `set-profile` | - | Set MC version and loader |
| `search` | - | Search Modrinth for mods |
| `get` | `install` | Install mod(s) |
| `show` | - | Show mod details |
| `list` | `ls` | List installed mods |
| `remove` | `rm` | Remove mod(s) |
| `autoremove` | - | Cleanup orphaned dependencies |
| `profile` | - | View current profile info |

## Requirements
- Python 3.8+
- [rich](https://github.com/Textualize/rich) (installed automatically via `pip install rich`)
