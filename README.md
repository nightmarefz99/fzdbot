# fzdbot
A discord bot that connects to the F-Zero Discord (FZD) database, with MySQL support. It functions as an interface between discord and the database, useful for event scoreboards and statistics gathering from events.

---

## Features

* Slash commands with dynamic autocomplete
* Score tracking in a MySQL database
* Configurable via `.env` file

---

## Installation

### 1️⃣ Clone the repository

```bash
git clone https://github.com/nightmarefz99/fzdbot.git
cd fzdbot
```

---

### 2️⃣ Set up a Python virtual environment (recommended)

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

Note after creating you only need to run the 2nd line to activate it (source venv/bin/activate or venv\Scripts\activate)
Optionally you can add it to your config file (e.g. ~/.bashrc) to automatically activate the virtual environment

```bash
# in ~/.bashrc or ~/.zshrc
cd ~/path/to/fzdbot
source venv/bin/activate
```

---

### 3️⃣ Install dependencies

```bash
pip install -e .
```

* `-e` = editable mode; allows live changes without reinstalling.
* This installs all dependencies listed in `pyproject.toml`.

---

### 4️⃣ Configure environment variables

Create `.env` file with your credentials:

```env
DISCORD_TOKEN=your_discord_bot_token_here
SERVER_ID=id_of_server_where_bot_runs
# Database connection
DB_HOST=localhost
DB_PORT=3306
DB_USER=mydbuser
DB_PASSWORD=supersecretpassword
DB_NAME=mydatabase
```

---

### 5️⃣ Run the bot

**Option 1 – entry point command:**

```bash
fzdbot
```

**Option 2 – module style:**

```bash
python -m fzdbot.bot
```


