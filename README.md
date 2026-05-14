# 3m — Minecraft Mod Manager

`3m` (or `mmm`) is a lightweight, dependency-aware CLI tool to manage Minecraft mods from [Modrinth](https://modrinth.com/).

## Features
- **Local Profiles**: Manages mod profiles independently for each project directory.
- **Dependency Resolution**: Automatically and recursively installs all required dependencies.
- **Bulk Installation**: Supports installing mods from command-line arguments or text files (`requirements.txt` style).
- **Lightweight**: No bloat, no API keys required, no background tracking.
- **Clean Architecture**: Modular Python package structure.

## Installation

### From Debian Package (.deb)
The recommended way to install `3m` is via the provided Debian package, which sets up a dedicated virtual environment for the application.

1. Download the latest `.deb` file.
2. Install using `apt`:
   ```bash
   sudo apt install ./3m_0.1.0_all.deb
   ```

## Usage

### 1. Initialize Profile
Before installing mods in a directory, set your target Minecraft version and loader (e.g., `fabric`, `forge`, `quilt`, `neoforge`):
```bash
mmm set-profile 1.21.1 fabric
```

### 2. Install Mods
- **By Name**:
  ```bash
  mmm install sodium, lithium, iris
  ```
- **From File** (e.g., `mods.txt` with one mod slug per line):
  ```bash
  mmm install -f mods.txt
  ```
- **By Search Index**:
  ```bash
  mmm search sodium
  mmm install -i 1
  ```

### 3. Management
- **List installed mods**:
  ```bash
  mmm ls
  ```
- **Remove a mod**:
  ```bash
  mmm rm sodium
  ```
- **Autoremove unused dependencies**:
  ```bash
  mmm autoremove
  ```

## Commands
| Command | Alias | Description |
| :--- | :--- | :--- |
| `set-profile` | - | Set MC version and loader |
| `search` | - | Search Modrinth for mods |
| `install` | `get` | Install mod(s) |
| `show` | - | Show mod details |
| `ls` | `list` | List installed mods |
| `rm` | `remove` | Remove mod(s) |
| `autoremove` | - | Cleanup orphaned dependencies |
| `profile` | - | View current profile info |

---
*Built with ❤️ for Minecraft enthusiasts.*
