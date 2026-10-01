#!/usr/bin/env bash
# English terminal menu to manage the dise-bot container on a server.
# Requires Docker with the Compose plugin (or standalone docker-compose).
#
# Usage: ./bot.sh

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is not installed. Install it first: https://docs.docker.com/engine/install/"
    exit 1
fi

if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
    echo "WARNING: using legacy docker-compose v1, which is deprecated and fails"
    echo "with newer Docker engines (e.g. KeyError: 'ContainerConfig')."
    echo "Install the v2 plugin instead: sudo apt-get install -y docker-compose-plugin"
else
    echo "Docker Compose is not available (need 'docker compose' or 'docker-compose')."
    exit 1
fi

need_env() {
    if [ ! -f .env ]; then
        echo "Missing .env file. Copy it first:"
        echo "  cp .env.example .env"
        echo "Then set BOT_TOKEN inside .env and run this menu again."
        return 1
    fi
    return 0
}

do_start() {
    need_env || return
    # shellcheck disable=SC2086
    $COMPOSE up --build -d
    echo "--- status ---"
    # shellcheck disable=SC2086
    $COMPOSE ps
}

do_restart() {
    need_env || return
    # shellcheck disable=SC2086
    $COMPOSE restart
    echo "--- status ---"
    # shellcheck disable=SC2086
    $COMPOSE ps
}

do_stop() {
    # shellcheck disable=SC2086
    $COMPOSE stop
}

do_status() {
    # shellcheck disable=SC2086
    $COMPOSE ps
}

do_logs() {
    echo "Showing logs (Ctrl+C to go back to the menu)..."
    # shellcheck disable=SC2086
    $COMPOSE logs -f --tail=100
}

while true; do
    echo ""
    echo "===== dise-bot manager ====="
    echo "1) Start bot"
    echo "2) Restart bot"
    echo "3) Stop bot"
    echo "4) Status"
    echo "5) Logs (live)"
    echo "0) Exit"
    read -rp "Choose an option: " choice
    case "$choice" in
        1) do_start ;;
        2) do_restart ;;
        3) do_stop ;;
        4) do_status ;;
        5) do_logs ;;
        0) echo "Bye."; exit 0 ;;
        *) echo "Invalid option: $choice" ;;
    esac
done
