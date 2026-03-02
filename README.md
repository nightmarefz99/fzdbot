# fzdbot

A discord bot that connects to the F-Zero Discord (FZD) database, with MySQL support. It functions as an interface between discord and the database, useful for event scoreboards and statistics gathering from events.

---

## Features

* Slash commands with dynamic autocomplete
* Score tracking in a MySQL database
* Configurable via `.env` file

---

## Setup

### Requirements

* Python on PATH
* [uv](https://docs.astral.sh/uv/) installed: `pipx install uv` or `pip install uv`

This project uses `uv` for dependency management.
From the repository root:

### Clone the repository
```bash
git clone https://github.com/F-Zero-Discord/fzdbot.git
cd fzdbot
```

### Create & activate a virtual env

```bash
uv sync --dev # This creates a venv at ./.venv and installs dependencies there

# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Note you will need to source the virtual environment to activate it and be able to run fzdbot below
Optionally you can add it to your config file (e.g. ~/.bashrc) to automatically activate the virtual environment

```bash
# in ~/.bashrc or ~/.zshrc
cd ~/path/to/fzdbot
source venv/bin/activate
```

---

### Configure environment variables

The `.env.example` file shows how your .env file should be structured. Copy the contents to `.env` and populate the
variables. This file will not be uploaded to the git repo

### Run the bot

```bash
uv run fzdbot
```
