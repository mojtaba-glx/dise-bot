#!/usr/bin/env bash
# Install dise-bot from GitHub on Ubuntu or Debian.
# Run as a regular user: bash <(curl -fsSL https://raw.githubusercontent.com/mojtaba-glx/dise-bot/main/bootstrap.sh)
set -euo pipefail

REPOSITORY=https://github.com/mojtaba-glx/dise-bot.git
INSTALL_DIR=${DISE_BOT_DIR:-"$HOME/dise-bot"}

if (( EUID == 0 )); then
    echo "Run this installer as your regular user, without sudo. It will request sudo only for system packages."
    exit 1
fi

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
    trap 'rm -f "$source_file"' EXIT
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
        echo "Install path exists but is not a Git checkout: $INSTALL_DIR"
        exit 1
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
