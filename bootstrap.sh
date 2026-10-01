#!/usr/bin/env bash
# Install dise-bot from GitHub on Ubuntu or Debian.
# Run from a regular-user or root shell.
set -euo pipefail

REPOSITORY=https://github.com/mojtaba-glx/dise-bot.git
INSTALL_DIR=${DISE_BOT_DIR:-"$HOME/dise-bot"}
source_file=
replacement_backup=

cleanup() {
    result=$?
    if [[ -n $source_file ]]; then
        rm -f -- "$source_file"
    fi
    if [[ -n $replacement_backup ]]; then
        if (( result == 0 )); then
            rm -rf -- "$replacement_backup"
            echo "Removed the old bot files after the new installation completed."
        else
            rm -rf -- "$INSTALL_DIR"
            mv -- "$replacement_backup" "$INSTALL_DIR"
            echo "Installation failed; restored the old bot files at $INSTALL_DIR." >&2
            echo "The old Compose service was stopped. Restart it manually if needed." >&2
        fi
    fi
    exit "$result"
}
trap cleanup EXIT

if [[ ! -f /etc/os-release ]]; then
    echo "Only Ubuntu and Debian are supported by the automatic prerequisite installer."
    exit 1
fi
# shellcheck source=/dev/null
source /etc/os-release
case "$ID" in
    ubuntu|debian) distribution=$ID ;;
    *) echo "Automatic installation supports Ubuntu and Debian only (found: $ID)."; exit 1 ;;
esac

as_root() {
    if (( EUID == 0 )); then
        "$@"
        return
    fi
    if ! command -v sudo >/dev/null 2>&1; then
        echo "sudo is required to install system packages."
        exit 1
    fi
    sudo "$@"
}

if ! command -v git >/dev/null 2>&1; then
    echo "Installing Git..."
    as_root apt-get update
    as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y git ca-certificates
fi

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    echo "Installing Docker Engine and the Compose plugin from Docker's official apt repository..."
    for package in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
        if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q '^install ok installed$'; then
            echo "Existing package $package conflicts with Docker's official packages."
            echo "Resolve the conflict using https://docs.docker.com/engine/install/$distribution/ and rerun."
            exit 1
        fi
    done
    as_root apt-get update
    as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl
    as_root install -m 0755 -d /etc/apt/keyrings
    as_root curl -fsSL "https://download.docker.com/linux/$distribution/gpg" -o /etc/apt/keyrings/docker.asc
    as_root chmod a+r /etc/apt/keyrings/docker.asc

    architecture=$(dpkg --print-architecture)
    codename=${UBUNTU_CODENAME:-$VERSION_CODENAME}
    source_file=$(mktemp)
    cat > "$source_file" <<EOF
Types: deb
URIs: https://download.docker.com/linux/$distribution
Suites: $codename
Components: stable
Architectures: $architecture
Signed-By: /etc/apt/keyrings/docker.asc
EOF
    as_root install -m 0644 "$source_file" /etc/apt/sources.list.d/docker.sources
    as_root apt-get update
    as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    as_root systemctl enable --now docker
fi

if [[ -e "$INSTALL_DIR" ]]; then
    if [[ ! -d "$INSTALL_DIR/.git" ]]; then
        if [[ ${DISE_BOT_REPLACE_EXISTING:-0} != 1 ]]; then
            echo "Install path exists but is not a Git checkout: $INSTALL_DIR"
            echo "To replace the old bot, set DISE_BOT_REPLACE_EXISTING=1 when running this installer."
            exit 1
        fi
        if [[ -L $INSTALL_DIR || $(basename -- "$INSTALL_DIR") != dise-bot ]]; then
            echo "For safety, automatic replacement requires a real directory named dise-bot."
            exit 1
        fi
        if [[ ! -f "$INSTALL_DIR/compose.yaml" && ! -f "$INSTALL_DIR/compose.yml" && ! -f "$INSTALL_DIR/docker-compose.yaml" && ! -f "$INSTALL_DIR/docker-compose.yml" ]]; then
            echo "Cannot identify how the old bot runs: no Docker Compose file exists in $INSTALL_DIR."
            echo "Stop the old bot manually before replacing its files."
            exit 1
        fi
        echo "Stopping the old bot's Docker Compose service..."
        if docker info >/dev/null 2>&1; then
            (cd -- "$INSTALL_DIR" && docker compose down)
        else
            (cd -- "$INSTALL_DIR" && as_root docker compose down)
        fi
        candidate_backup=$(mktemp -d "${INSTALL_DIR}.backup.XXXXXX")
        rmdir -- "$candidate_backup"
        mv -- "$INSTALL_DIR" "$candidate_backup"
        replacement_backup=$candidate_backup
        git clone --branch main --single-branch "$REPOSITORY" "$INSTALL_DIR"
        bash "$INSTALL_DIR/install.sh"
        exit 0
    fi
    remote=$(git -C "$INSTALL_DIR" remote get-url origin)
    case "$remote" in
        "$REPOSITORY"|https://github.com/mojtaba-glx/dise-bot|git@github.com:mojtaba-glx/dise-bot.git) ;;
        *) echo "Install path has a different Git origin: $INSTALL_DIR"; exit 1 ;;
    esac
    if [[ $(git -C "$INSTALL_DIR" branch --show-current) != main ]]; then
        echo "Existing checkout must be on the main branch: $INSTALL_DIR"
        exit 1
    fi
    if [[ -n $(git -C "$INSTALL_DIR" status --porcelain --untracked-files=no) ]]; then
        echo "Existing checkout has local changes. Commit or stash them before updating: $INSTALL_DIR"
        exit 1
    fi
    git -C "$INSTALL_DIR" fetch origin main
    git -C "$INSTALL_DIR" merge --ff-only origin/main
else
    mkdir -p -- "$(dirname -- "$INSTALL_DIR")"
    git clone --branch main --single-branch "$REPOSITORY" "$INSTALL_DIR"
fi

bash "$INSTALL_DIR/install.sh"
