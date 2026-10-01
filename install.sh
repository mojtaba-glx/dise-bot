#!/usr/bin/env bash
# Interactive one-command setup for a server with Docker Compose.
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    echo "Docker and the Docker Compose plugin are required."
    echo "Install them from https://docs.docker.com/engine/install/ and rerun this script."
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "Cannot connect to Docker. Start Docker or use an account with Docker access."
    exit 1
fi

if [ ! -e .env ]; then
    echo "First-time setup. Your token will not be shown on screen."
    read -rsp "BotFather token: " bot_token
    echo
    if [[ ! $bot_token =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
        echo "Invalid token format. Get the token from @BotFather and retry."
        exit 1
    fi

    read -rp "Your numeric Telegram user ID for the owner panel (optional): " owner_id
    if [[ -n $owner_id && ( ! $owner_id =~ ^[0-9]+$ || $owner_id == 0 ) ]]; then
        echo "OWNER_USER_ID must be a positive number."
        exit 1
    fi

    umask 077
    cat > .env <<EOF
BOT_TOKEN=$bot_token
OWNER_USER_ID=$owner_id
STATE_DB_PATH=data/activation.sqlite3
LOG_LEVEL=INFO
EOF
    unset bot_token owner_id
    echo "Created .env with private file permissions."
else
    echo "Using the existing .env without changing it."
fi

docker compose up --build -d
docker compose ps
echo "Setup finished. Use ./bot.sh to view logs or manage the bot."
