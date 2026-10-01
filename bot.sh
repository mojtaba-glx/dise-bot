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

if ! docker compose version >/dev/null 2>&1; then
    echo "The Docker Compose plugin is required."
    exit 1
fi

if docker info >/dev/null 2>&1; then
    compose=(docker compose)
elif command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    compose=(sudo docker compose)
else
    echo "Cannot connect to Docker. Start Docker and check your account's Docker access."
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
    "${compose[@]}" up --build -d
    echo "--- status ---"
    "${compose[@]}" ps
}

do_restart() {
    need_env || return
    "${compose[@]}" restart
    echo "--- status ---"
    "${compose[@]}" ps
}

do_stop() {
    "${compose[@]}" stop
}

do_status() {
    "${compose[@]}" ps
}

do_logs() {
    echo "Showing logs (Ctrl+C to go back to the menu)..."
    "${compose[@]}" logs -f --tail=100
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
