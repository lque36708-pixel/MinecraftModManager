# 3m — Minecraft Mod Manager

`3m` (or `mmm`) is a lightweight, dependency-aware CLI tool to manage Minecraft mods from [Modrinth](https://modrinth.com/).

## Features
- **Local Profiles**: Manages mod profiles independently for each project directory.
- **Dependency Resolution**: Automatically and recursively installs all required dependencies.
- **Bulk Installation**: Supports installing mods from command-line arguments or text files.
- **Lightweight**: Single Python file, no bloat, no API keys required, no background tracking.

## Installation

```bash
git clone https://github.com/yourusername/3m.git
cd 3m
./install.sh
```

Then restart your terminal or run `source ~/.bashrc`.

### Uninstall

```bash
cd 3m
./uninstall.sh
```

## Usage

### 1. Initialize Profile
Before installing mods in a directory, set your target Minecraft version and loader:

```bash
3m set-profile 1.21.1 fabric
```

### 2. Install Mods
- **By Name**:
  ```bash
  3m install sodium, lithium, iris
  ```
- **From File** (one mod name per line):
  ```bash
  3m install -f mods.txt
  ```
- **By Search Index**:
  ```bash
  3m search sodium
  3m show -i 1
  3m install -i 1
  ```

### 3. Management
- **List installed mods**:
  ```bash
  3m ls
  ```
- **Show mod details**:
  ```bash
  3m show sodium
  ```
- **Remove a mod**:
  ```bash
  3m rm sodium
  ```
- **Autoremove unused dependencies**:
  ```bash
  3m autoremove
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
