#!/usr/bin/env bash
set -euo pipefail

# --- helpers ---
log() { echo "[sf-wizard] $*"; }
warn() { echo "[sf-wizard][WARN] $*" >&2; }
die() { echo "[sf-wizard][ERROR] $*" >&2; exit 1; }
usage() {
  cat <<EOF
Usage: ./run.sh [options]

Options:
  --no-docker     App is not launched with Docker
  --no-sync       SF auth in host is not copied to ./data
  -d, --detached  Launch Docker in detached mode
  -h, --help      Display help
EOF
}
need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Commande not found: $1"; }

NO_DOCKER=false
NO_SYNC=false
DETACHED=false

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-docker) NO_DOCKER=true; shift ;;
    --no-sync) NO_SYNC=true; shift ;;
    -d|--detached) DETACHED=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ "${NO_DOCKER}" == "true" && "${NO_SYNC}" == "true" ]]; then
  echo "[sf-wizard][ERROR] --no-docker et --no-sync together have no effect. Nothing to do." >&2
  exit 2
fi

HOST_HOME_WIN="${USERPROFILE:-}"
if [[ -z "${HOST_HOME_WIN}" ]]; then
  die "USERPROFILE is empty. Launch the script from Git Bash on Windows."
fi

# Convert C:\Users\X -> /c/Users/X (format MSYS)
HOST_HOME_POSIX="$(cygpath -u "${HOST_HOME_WIN}")"

PROJECT_DIR="$(pwd)"
DATA_DIR="${PROJECT_DIR}/data"
SFCLI_HOME="${DATA_DIR}/sfcli-home"
TARGET_HOME="${SFCLI_HOME}"
TARGET_SFDX_TMP_DIR="${TARGET_HOME}/.sfdx/tmp"

HOST_SFDX_DIR="${HOST_HOME_POSIX}/.sfdx"

mkdir -p "${TARGET_HOME}"

merge_alias_json() {
    local src="$1"   # host alias.json
    local dst="$2"   # app alias.json (target)
    local conflicts="$3"

    mkdir -p "$(dirname "$dst")"

    # If src doesn't exist, exit
    [[ -f "$src" ]] || return 0
    
    # If dst doesn't exist, simple copy
    if [[ ! -f "$dst" && -f "$src" ]]; then
        cp "$src" "$dst"
        return 0
    fi

    if command -v jq >/dev/null 2>&1; then
        # Merge: dst wins in case of conflict (app wins)
        # conflicts: alias where src != dst
        #jq -s '
        #def conflicts(a;b):
        #    (a as $A | b as $B |
        #    ($A|keys_unsorted + $B|keys_unsorted | unique) as $K |
        #    [ $K[] | select(($A[.] != null) and ($B[.] != null) and ($A[.] != $B[.])) ] );
#
        #.[0] as $SRC
        #| .[1] as $DST
        #| {
        #    merged: ($SRC + $DST),
        #    conflicts: (conflicts($SRC; $DST))
        #    }
        #' "$src" "$dst" > "${dst}.tmp"
        jq -s '
            def obj(x): (x // {}) | if type=="object" then . else {} end;

            .[0] as $SRC
            | .[1] as $DST
            | (obj($SRC.orgs)) as $SRC_ORGS
            | (obj($DST.orgs)) as $DST_ORGS
            | ($SRC_ORGS + $DST_ORGS) as $MERGED_ORGS
            | (
                ($SRC_ORGS|keys_unsorted) + ($DST_ORGS|keys_unsorted)
                | unique
                | map(select(($SRC_ORGS[.] != null) and ($DST_ORGS[.] != null) and ($SRC_ORGS[.] != $DST_ORGS[.])))
            ) as $CONFLICT_KEYS
            | {
                merged: { orgs: $MERGED_ORGS },
                conflicts: $CONFLICT_KEYS
            }
        ' "$src" "$dst" > "${dst}.tmp"

        mv "${dst}.tmp" "${dst}"

        # Extract readable conflicts
        jq '.conflicts' "$dst" > "$conflicts" || true

        # Write final merged
        jq '.merged' "$dst" > "${dst}.tmp"
        mv "${dst}.tmp" "$dst"    
    else
        warn "jq not found. No merge of alias.json between host and app."
        if [[ -f "$src" && -f "$dst" ]]; then
            warn "alias.json exists in host and in app. App version is chosen."
            cp "$src" "${dst}.host.bak.$(date +%s)" || true
        else
            cp -n "$src" "$dst" || true
        fi
    fi
}

sync_from_host() {
    if [[ -d "${HOST_SFDX_DIR}" ]]; then
        log "Bootstrap from ${HOST_SFDX_DIR} -> ${TARGET_HOME}/.sfdx"
        # Copy in app temp folder everything in host SFDX folder
        mkdir -p "${TARGET_SFDX_TMP_DIR}"
        cp -R "${HOST_SFDX_DIR}/." "${TARGET_SFDX_TMP_DIR}" || true
        # Exclude some files
        rm -f "${TARGET_SFDX_TMP_DIR}/alias.json" || true
        rm -f "${TARGET_SFDX_TMP_DIR}/config.json" || true
        # Copy every file from temp folder to app .sfdx folder (if the file doesn't exist)
        cp -R -n "${TARGET_SFDX_TMP_DIR}" "${TARGET_HOME}/.sfdx" || true
        rm -f "${TARGET_SFDX_TMP_DIR}" || true
        # Merge alias.json, copy or ignore
        merge_alias_json "${HOST_HOME_POSIX}/.sfdx/alias.json" "${TARGET_HOME}/.sfdx/alias.json" "${DATA_DIR}/alias.conflicts.sfdx.json"
    else
        warn "No host folder found: ${HOST_SFDX_DIR}"
    fi
}

if [[ "${NO_SYNC}" == "false" ]]; then
    log "Bootstrap SF CLI auth from host"
    sync_from_host
fi

if [[ "${NO_DOCKER}" == "false" ]]; then
    need_cmd docker
    log "Starting Docker compose"

    if [[ "${DETACHED}" == "true" ]]; then
        docker compose up -d --build
    else
        docker compose up --build
    fi
fi
