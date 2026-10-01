#!/usr/bin/env bash
# Interactive setup from an existing checkout.
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    echo "Docker and the Docker Compose plugin are required."
    echo "Install them from https://docs.docker.com/engine/install/ and rerun this script."
    exit 1
fi

docker_command=(docker)
if ! docker info >/dev/null 2>&1; then
    if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
        docker_command=(sudo docker)
    else
        echo "Cannot connect to Docker. Start Docker and check your account's Docker access."
        exit 1
    fi
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
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
STATE_DB_PATH=data/activation.sqlite3
LOG_LEVEL=INFO
EOF
    unset bot_token owner_id
    echo "Created .env with private file permissions."
else
    echo "Using the existing .env without changing existing values."
    if ! grep -q '^TELEGRAM_API_ID=' .env; then
        printf '\nTELEGRAM_API_ID=\n' >> .env
    fi
    if ! grep -q '^TELEGRAM_API_HASH=' .env; then
        printf 'TELEGRAM_API_HASH=\n' >> .env
    fi
fi

"${docker_command[@]}" compose up --build -d
"${docker_command[@]}" compose ps
echo "Container setup finished. Telegram connectivity and token validity have not been verified."
echo "Use ./bot.sh in this directory to inspect status and logs."
