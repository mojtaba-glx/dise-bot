# dise bot · 🎲 ᎠᏆᏟᎬ

**Version 1.2.1**

A small, modular Telegram bot with an English interface and the original
`ᎠᏆᏟᎬ` button lettering. Red returns `-1` through `-10`; green returns
`+1` through `+10`. The duplicated values in the original code are intentional
and are preserved exactly. The Defense menu adds Light, Heavy, Super, God, and
Gold defense calculations with positive rolls from +1 to +9.

```text
🎲 ᎠᏆᏟᎬ 🎲

Choose your color. Roll your number.

🔴 Red: -1 to -10
🟢 Green: +1 to +10

[ 🛡️ ᎠᎬᎰᎬᏁᏚᎬ ][ ✨ ᎪᏴᏞᏆᎢᎩ ]
[ 🎲🔴 ᎠᏆᏟᎬ 🔴🎲 ]
[ 🎲🟢 ᎠᏆᏟᎬ 🟢🎲 ]

Example replies: -3   +8
```

The lettering uses the exact Unicode characters from the original code.
Telegram controls its fonts and keyboard layout; appearance can vary by client.
Help text uses regular English for readability.

## One-command server installation

On Ubuntu or Debian, run this command from any directory, using your regular
user or a root shell:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/mojtaba-glx/dise-bot/main/bootstrap.sh)
```

The script installs Git, Docker Engine, and the Docker Compose plugin if needed,
clones the repository to `~/dise-bot`, then privately prompts for the BotFather
token and optionally your numeric Telegram owner ID. It asks for your sudo
password only when system packages need installation as a regular user. A root
shell installs into `/root/dise-bot` without sudo. Run the same command to
update an existing clean checkout. The bot's `.env` and saved data are retained;
the token is requested only on first setup. `curl` is needed to fetch the script.
To use another location, set `DISE_BOT_DIR` before the command.

If `~/dise-bot` already contains an older non-Git bot with a Docker Compose
file, set `DISE_BOT_REPLACE_EXISTING=1` on the install command to replace it.
The installer stops the old Compose service, temporarily moves its files aside,
and removes those files after the new installation succeeds. If installation
fails, it restores the old files. It does not delete Docker volumes, so saved
bot state remains available. The new installation asks for a BotFather token.
An old bot started outside Docker Compose must be stopped separately before
replacement.

If you already cloned the repository and have Docker Compose, run:

```bash
cd dise-bot
./install.sh
```

The installer asks privately for a token from [@BotFather](https://t.me/BotFather)
and optionally your numeric Telegram owner ID. It creates `.env` only when that
file does not already exist, starts the bot in Docker, and leaves all existing
settings untouched. Use `./bot.sh` afterward for status, logs, restart, and stop.
The in-repository `install.sh` expects Docker Compose to be installed. See the
[Docker installation guide](https://docs.docker.com/engine/install/) for other
Linux distributions. Container setup does not verify that your server can reach
Telegram; outbound HTTPS to `api.telegram.org` is required. Check logs with
`cd ~/dise-bot && ./bot.sh` if the bot does not respond.

For a manual Python setup, use Python 3.11 or newer. Python 3.12 is the default
development version.

```bash
cd dise-bot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install "telethon==1.45.0"
python -m pip install --no-deps .
[ -e .env ] || cp .env.example .env
chmod 600 .env
```

On Windows, activate with `.venv\Scripts\Activate.ps1` in PowerShell, and copy
`.env.example` to `.env` only if `.env` does not already exist. The `chmod`
command is only needed on Unix systems.

Edit `.env` and set `BOT_TOKEN` to the token supplied by BotFather. Then run:

```bash
dise-bot --check
dise-bot
```

`--check` validates local settings and token format only. It does not contact
Telegram or prove that the token is valid. `python -m dise_bot` is an alternative
entry point. Use Ctrl+C to stop.

Open your bot in Telegram and send `/start`. The bot uses long polling, so a
public URL and incoming server ports are unnecessary. Outbound HTTPS access to
`api.telegram.org` is required. Keep the process running for the bot to stay online.

If you use [uv](https://docs.astral.sh/uv/), the equivalent setup is:

```bash
uv sync --locked
uv pip install "telethon==1.45.0"
[ -e .env ] || cp .env.example .env
# Edit .env before continuing.
uv run dise-bot --check
uv run dise-bot
```

## Commands and behavior

| Command | Action |
| --- | --- |
| `/start` | Show the welcome message and persistent keyboard |
| `/red` | Roll the red dice |
| `/green` | Roll the green dice |
| `/defense` | Open the defense menu |
| `/defense light 3` | Calculate a tier for an explicit +1 to +9 roll |
| `/on` | Enable dice for yourself in the current group |
| `/off` | Disable dice for yourself in the current group |
| `/status` | Show your own ON/OFF state in the current group |
| `/version` | Show the running bot version |
| `/help` | Show the rules and exact odds |
| `/id` | Show your numeric Telegram user ID |
| `/panel` | Open the owner/admin menu in a private chat |
| `/ban <ID>` / `/unban <ID>` | Block or restore a user's access to this bot |
| `/admin <ID>` / `/unadmin <ID>` | Owner only: grant or remove bot admin access |
| `/reply add <text> \| <answer>` | Save an automatic response in the current group |
| `/reply remove <text>` / `/reply list` | Remove or list this group's automatic responses |
| `/join add @channelname` | Owner/admin: add a public required channel |
| `/join add -100... [invite]` | Owner/admin: add a private required channel |
| `/join remove <chat_id>` | Owner/admin: remove one required channel |
| `/join on` / `/join off` | Owner/admin: toggle required membership globally |
| `/join status` / `/join list` | Owner/admin: show status and all configured channels |
| `/tag` | Owner/admin: reply to a group message and mention every current member by numeric Telegram ID |

- Both original dice button labels are unchanged, including spaces and emoji.
- Results stay minimal: a sign and a number, such as `-3` or `+8`.
- Every dice button press or roll command generates one independent result.
- There is no score, balance, or stored roll history. SQLite stores group
  activation choices, bot moderation roles, bans, automatic replies, and the
  optional required channel.
- There is no per-user cooldown or spam rejection. Rapid clicks are accepted.
  Up to 32 updates can be processed concurrently; the HTTP pool has 64 connections.
  Results from overlapping requests may arrive in a different order.
- The Help button has been removed; `/help` remains available as a command.
- The ABLITY button opens its own screen with Back. Ability actions can be added
  to that screen when their rules are specified.
- The Defense menu also holds Absolute and Reflect (one random signed value
  per tap each) and Cursed Aura (one random value per tap, costing 10 energy).
- Unrelated private text receives a menu hint. Unrelated group text and unknown
  commands are ignored.
- In groups, `/red@YourBotUsername` and `/green@YourBotUsername` work with privacy
  mode enabled. For reliable handling of plain keyboard messages from all group
  members, adjust the bot's group privacy setting through BotFather.
- Old pending updates are discarded on startup so offline clicks are not replayed.
- Run one polling instance per bot token.

### Group tag command

Reply to a message in a group and send `/tag`. Only the configured owner and bot admins can use it.
Before tagging, the bot opens an MTProto connection with its own bot token and fetches the current
participant list directly from Telegram. It then sends real `text_mention` entities tied to each
numeric Telegram user ID, so usernames and online status are not required.

Members are tagged three at a time. Between each three-member batch the bot sends a separate
continuation message and pauses briefly before continuing. Bots and deleted accounts are skipped.

Full member enumeration is not available through the ordinary Bot API. To enable the MTProto sync,
create an API application at `my.telegram.org` and set both values below in `.env`:

```env
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=0123456789abcdef0123456789abcdef
```

The bot itself must be an administrator in the target group. If these two values are missing or
the full member list cannot be fetched, `/tag` stops with an error instead of tagging only the
partial locally observed member list.

### Group activation

Group dice are off for each member until that member sends `/on` in the group.
Activation controls are command-only: use `/on`, `/off`, and `/status`. The group keyboard contains no ON, OFF, or STATUS buttons. `/off` removes only that member’s custom keyboard and keeps the other members unchanged. While off, `/start`, Defense, Ability, and status checks do not restore the keyboard. Sending `/on` restores the full personal keyboard for that member. `/off` stops red, green,
ranked defense, cursed aura, absolute, and reflect rolls from that user in that
group; it does not change any other member's choice or that user's choice in
another group. No roll is generated and no reply is sent for a disabled user's
roll. Opening a menu or reading help still works. Private-chat dice remain
available regardless of these group switches.

Both switches reply with a short status message and the requested creator credit:
`بات ساخته شده توسط @Anthony_0088`. Repeating a switch is safe. Choices are
stored in SQLite and survive a bot restart. The default location is
`data/activation.sqlite3`; set `STATE_DB_PATH` to change it. Do not delete this
file if you want to keep group choices.

### Owner panel and group auto replies

Telegram does not provide a bot owner's user ID through its token. To activate
the owner panel, send `/id` to the bot in a private chat, put the number it returns
in `.env` as `OWNER_USER_ID=123456789` (using your own number), and restart the
bot. If `OWNER_USER_ID` is empty, the management panel stays disabled. Keep your
existing `.env` and token; add only this line. The owner sees a Panel button on
the private keyboard and can also use `/panel`.

The owner can ban/unban users and grant/remove bot admin roles. Bot admins can
ban/unban users and manage automatic replies, but cannot change admin roles.
The panel asks for a numeric user ID; alternatively, send `/ban`, `/unban`,
`/admin`, or `/unadmin` as a reply to someone's message in a group. A ban stops
that person's interaction with this bot in every chat. It does not remove the
person from a Telegram group. The owner cannot be banned, and an admin must lose
the admin role before being banned.

To make the bot respond to a Persian phrase, send these commands **in the group**:

```text
/reply add سلام | سلام! خوش اومدی
/reply list
/reply remove سلام
```

Each trigger matches an entire message, ignoring extra whitespace and treating
Persian/Arabic variants of ی and ک alike. Replies are specific to each group and
survive restarts. Only the owner or a bot admin can change them. Commands remain
Latin because Telegram slash commands use Latin letters; the trigger and answer
can be Persian. For ordinary group messages to reach the bot, disable its group
Privacy Mode in BotFather and re-add it to the group, or make it a group admin.
See [Telegram's Privacy Mode documentation](https://core.telegram.org/bots/features#privacy-mode).

### Required membership

Required membership now supports multiple Telegram channels or supergroups at the same time.
Open the private admin panel and choose **Required membership / عضویت اجباری**. The panel includes
buttons for ON, OFF, adding a channel, removing a channel, listing channels, and returning to the
main admin panel.

The same controls remain available as commands:

```text
/join add @channelname
/join add -1001234567890
/join add -1001234567890 https://t.me/+invitecode
/join remove -1001234567890
/join list
/join on
/join off
/join status
```

The bot must be an administrator in every required channel. Public channels use their public link.
For private channels, the bot can create an invite link when it has invite permission, or an existing
`https://t.me/+...` invite link can be supplied.

When required membership is ON, a user must belong to **every configured channel** before normal bot
features work. The join prompt contains one button per required channel plus **Check membership**.
Membership is checked live with Telegram and cached briefly for performance. Turning membership OFF
keeps the channel list saved. Turning it back ON revalidates every configured channel and the bot's
admin access before enforcing the requirement.

Owner/admin management commands and admin-panel buttons remain accessible even when the manager is not
a member, so the configuration cannot lock administrators out of the control panel. Normal game use,
including `/start` and dice actions, is still subject to the membership rule for admins as well; this
makes it possible to test the rule with an admin account.

Existing single-channel databases are migrated automatically to the multi-channel format. The migrated
channel is preserved and can later be removed normally without reappearing after a restart.

### Bilingual admin panel

Admin reply-keyboard buttons are routed through one deterministic private-admin handler. This prevents
Settings, language, and required-membership buttons from being swallowed by overlapping handlers.


The private admin experience supports **English and Persian** independently for each owner/admin.
Open **Settings / تنظیمات** and choose **🇬🇧 English** or **🇮🇷 فارسی**. The preference is stored in
SQLite and survives restarts. Panel buttons, moderation responses, automatic-reply management, and
required-membership management follow that admin's selected language without changing ordinary users'
language or another admin's preference.


## Exact probabilities

| Color | Magnitude | Chance per number |
| --- | --- | --- |
| Red | 1, 2, 3, 4 | 2/14 ≈ 14.29% |
| Red | 5, 6, 7, 8, 9, 10 | 1/14 ≈ 7.14% |
| Green | 1, 2, 3, 4, 5, 6 | 1/14 ≈ 7.14% |
| Green | 7, 8, 9, 10 | 2/14 ≈ 14.29% |

The sign is applied after choosing a magnitude. `secrets.choice` selects an
entry from the original 14-entry pool using the operating system's random source.
Duplicates remain in the pool; no normalization or deduplication is performed.
These probabilities apply to each independent roll and do not guarantee a
particular distribution in a short session.

## Ranked defense

Tap Defense, then a tier to generate a positive roll and calculate its defense.
All nine defense rolls are equally likely. This is separate from the original
red/green dice, whose weighted 1–10 pools remain unchanged.

Each tap randomly shows either the calculated value or a negative percentage:
-25, -50, -75, or -100. The magnitude is random and independent. An explicit
`/defense <tier> <roll>` always shows the calculated value for the given roll.

| Roll | Light | Heavy | Super | God | Gold |
| --- | --- | --- | --- | --- | --- |
| +1 | 10 | 15 | 20 | 25 | 30 |
| +2 | 15 | 20 | 25 | 30 | 35 |
| +3 | 20 | 25 | 30 | 35 | 40 |
| +4 | 25 | 30 | 35 | 40 | 45 |
| +5 | 30 | 35 | 40 | 45 | 50 |
| +6 | 35 | 40 | 45 | 50 | 55 |
| +7 | 40 | 45 | 50 | 55 | 60 |
| +8 | 45 | 50 | 55 | 60 | 65 |
| +9 | 50 | 55 | 60 | 65 | 70 |

The formula is `base + 5 * (roll - 1)`. The maximum roll is +9; explicit rolls
outside +1…+9 are rejected. Silver is not a tier. Back returns to the main menu.
Each result is independent; there is no hidden accumulator or shared player state.
Use `/defense gold +9` when the roll has already been determined outside the bot.

The menu text also shows the coverage percentages `25% · 50% · 75% · 100%`.
They are copy only: no button, roll, calculation, or stored state is attached
to them. Their rules are not defined yet.

### Absolute

Tap Absolute to receive one random signed label from 0, 15, 25, 35, or 40.
A positive value replies `+ ♾️ ᎪᏴᏚᎾᏞᏌᎢᎬ`, a negative value replies
`- ♾️ ᎪᏴᏚᎾᏞᏌᎢᎬ`, and zero replies with the plain label and no sign.
Each result is independent; there is no hidden accumulator or shared player state.

### Reflect

Tap Reflect to receive one random signed label from 0, 15, 25, 35, or 40,
exactly like Absolute. A positive value replies `+ 🪞 ᎡᎬᎰᏞᎬᏟᎢ`,
a negative value replies `- 🪞 ᎡᎬᎰᏞᎬᏟᎢ`, and zero replies with the plain
label and no sign. Each result is independent; there is no hidden accumulator
or shared player state.

### Cursed Aura

Tap Cursed Aura to receive one random value from 0, 15, 25, 35, or 40.
Every tap costs 10 energy, shown together with the value. Each result is
independent; there is no hidden accumulator or shared player state.

### Rules awaiting clarification

Random Def and energy calculations are not active yet. Their rules
need to be settled before buttons or computed results are exposed to players:

- Random Def needs an exact dice sequence and a rule for turning its signed total
  into defense. It will belong inside the Defense menu.
- Ordinary defense energy needs a clear reference amount and rules for all
  coverage intervals, including values between the listed percentages.
- Absolute defense uses attack energy, which is a separate input from attack
  damage. Reflection behavior depends on personal power rules not supplied here.

The supplied basic-attack table is available as a tested service function:
10, 10, 20, 20, 30, 30, 30, 35, 35 for rolls +1 through +9. It is not exposed
as an additional menu item or silently used as an energy cost.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `BOT_TOKEN` | Required | Your bot token |
| `STATE_DB_PATH` | `data/activation.sqlite3` | SQLite file for switches, roles, bans, and replies |
| `OWNER_USER_ID` | Empty | Numeric Telegram user ID with full management access |
| `TELEGRAM_API_ID` | Empty | API ID from my.telegram.org; required for full `/tag` sync |
| `TELEGRAM_API_HASH` | Empty | API hash from my.telegram.org; required for full `/tag` sync |
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR, or CRITICAL |

Environment variables override `.env`. By default, `.env` is read from the current
working directory. To use another path:

```bash
dise-bot --env-file /path/to/bot.env
```

Old `COOLDOWN_SECONDS` entries are ignored. Existing `.env` files do not need to
be replaced, and their token is preserved when updating the project.

The token is excluded from settings representations and redacted from console
logs, including tracebacks. HTTP and Telegram debug payload logging is disabled.
The project ignores `.env` in Git and excludes it from Docker builds.

Telegram's API limits still apply. The outgoing API limiter may queue replies
without rejecting user clicks. Rate-limit rejections can be retried once.
Uncertain network failures do not reroll or replay results, since Telegram might
already have received the message. The bot cannot guarantee message delivery
during an outage or an exhausted API retry.

## Project layout

```text
dise-bot/
├── src/dise_bot/
│   ├── __init__.py
│   ├── __main__.py          # python -m dise_bot
│   ├── app.py               # Application wiring and CLI
│   ├── config.py            # Validated environment configuration
│   ├── logging_config.py    # Token-safe console logging
│   ├── keyboards.py         # Persistent dice keyboard
│   ├── messages.py          # English copy and original button labels
│   ├── handlers/            # Commands, dice, defense, management, errors
│   └── services/            # Dice, defense, activation, management, and join state
├── tests/                   # Offline service and Telegram integration tests
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── compose.yaml
├── install.sh               # First-time interactive Docker installation
├── bot.sh                  # English terminal menu: start/restart/stop on a server
├── pyproject.toml
├── requirements.txt         # Locked runtime dependencies with hashes
├── uv.lock                  # Full dependency lock, including development tools
└── README.md
```

## Development

```bash
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Tests do not need a real token or Telegram connection. They cover the exact
weighted distributions, result signs and boundaries, keyboard and command
routing through a mocked Telegram transport, concurrent rapid clicks, every
ranked defense table entry, configuration, and safe error logging. Live delivery
requires a real token and a manual `/start`, dice, and defense smoke test.

After intentionally changing dependencies, regenerate both lock files:

```bash
uv lock
uv export --locked --no-dev --no-emit-project --format requirements-txt -o requirements.txt
```

## Docker

Create and configure `.env` first, then:

```bash
docker compose up --build -d
docker compose logs -f
docker compose down
```

If your installation provides the standalone `docker-compose` command, use that
in place of `docker compose`.

The container runs as an unprivileged user, uses the locked runtime dependencies,
and reads the token from its environment. The named `bot_state` volume stores
group activation choices across container restarts. No ports are needed.
Stop any local polling process before starting the container with the same token.

## Server menu

On the server, `./bot.sh` opens an English terminal menu for the container:

```text
===== dise-bot manager =====
1) Start bot
2) Restart bot
3) Stop bot
4) Status
5) Logs (live)
0) Exit
```

Start builds the image if needed and launches the bot in the background;
Restart restarts the running container; Stop stops it; Status shows the
container state; Logs follows the live log (Ctrl+C returns to the menu).
The menu needs Docker with Compose and a configured `.env` file.

## Design choices

Defense and ABLITY share the first row, above the red and green dice. Inside Defense,
Cursed Aura sits above all, Light/Heavy and Super/God share rows, followed by
Gold/Absolute sharing a row, then Reflect and Back. Colored symbols and matching
Unicode lettering distinguish the tiers.
Dice results remain short; defense results show the selected tier, roll, and
either the calculated value or a random percent together.

Built with [python-telegram-bot](https://docs.python-telegram-bot.org/en/stable/).
