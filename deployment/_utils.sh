#!/usr/bin/env bash
set -euo pipefail

PROCESS_DIR='process'
RUNS_ROOT="${PROCESS_DIR}/runs"
LOCK_DIR="${PROCESS_DIR}/lock"

log() { printf '%s\n' "$*"; }
err() { printf '%s\n' "$*" >&2; }
die() { err "❌ $*"; exit 1; }

atomic_write() {
  local dest="$1"
  local tmp="${dest}.tmp.$$"
  mkdir -p "$(dirname "${dest}")"
  cat > "${tmp}"
  mv -f "${tmp}" "${dest}"
}

# ---------- Prompts ----------
prompt_yn() {
  local msg="$1" ans
  while true; do
    read -rp "${msg} [Y/N] : " ans || true
    case "${ans,,}" in
      y|yes) return 0 ;;
      n|no)  return 1 ;;
      *) echo "Réponds Y/N (insensible à la casse)." ;;
    esac
  done
}

prompt_yn_strict() {
  local msg="$1" ans
  read -rp "${msg} [Y/N] : " ans || true
  case "${ans,,}" in
    y|yes) return 0 ;;
    n|no)  return 1 ;;
    *)
      err "❌ Entrée invalide. Relance la task pour recommencer."
      exit 2
      ;;
  esac
}

# ---------- Lock (1 run à la fois) ----------
acquire_lock() {
  mkdir -p "${PROCESS_DIR}"
  if mkdir "${LOCK_DIR}" 2>/dev/null; then
    echo "$$" > "${LOCK_DIR}/pid"
    trap 'release_lock' EXIT INT TERM
    return 0
  fi

  # lock existe : check PID
  local pid=''
  [[ -f "${LOCK_DIR}/pid" ]] && pid="$(cat "${LOCK_DIR}/pid" || true)"

  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    die "Un run est déjà en cours (PID ${pid})."
  fi

  # lock stale
  rm -rf "${LOCK_DIR}"
  mkdir "${LOCK_DIR}" || die "Impossible de prendre le lock."
  echo "$$" > "${LOCK_DIR}/pid"
  trap 'release_lock' EXIT INT TERM
}

release_lock() {
  [[ -d "${LOCK_DIR}" ]] && rm -rf "${LOCK_DIR}" || true
}

# ---------- RUN_ID ----------
run_id_new() {
  echo "$(date '+%Y%m%d_%H%M%S')_$$_$RANDOM"
}

# ---------- State ----------
state_load() {
  local state_file="$1"
  [[ -f "${state_file}" ]] || return 1
  # shellcheck source=/dev/null
  source "${state_file}"
}

state_set() {
  local state_file="$1" key="$2" val="$3"
  mkdir -p "$(dirname "${state_file}")"
  if [[ -f "${state_file}" ]]; then
    if grep -qE "^${key}=" "${state_file}"; then
      sed -i.bak "s|^${key}=.*|${key}=\"${val//\"/\\\"}\"|g" "${state_file}"
      rm -f "${state_file}.bak"
    else
      printf '%s="%s"\n' "${key}" "${val//\"/\\\"}" >> "${state_file}"
    fi
  else
    atomic_write "${state_file}" <<EOF
${key}="${val//\"/\\\"}"
EOF
  fi
}

state_require() {
  local state_file="$1" key="$2"
  state_load "${state_file}" || die "State manquant: ${state_file}"
  [[ -n "${!key:-}" ]] || die "State invalide: ${key} absent."
}

# ---------- Checks ----------
soft_check_org() {
  local alias="$1"
  sf org display -o "${alias}" >/dev/null 2>&1 || die "Alias/session SF invalide pour '${alias}'. Re-login ou corrige l’alias."
}

hash_file() {
  local f="$1"
  sha256sum "${f}" | awk '{print $1}'
}

# ---------- Régler les réponses des commandes SF -------------
run_sf_json_to_file() {
  local out_file="$1"; shift
  rm -f "${out_file}"

  # IMPORTANT : capture stdout+stderr pour comprendre un éventuel output non JSON
  if ! "$@" > "${out_file}" 2>&1; then
    err "❌ Commande SF en échec : $*"
    err "↳ Output (head):"
    sed -n '1,120p' "${out_file}" >&2 || true
    return 1
  fi

  if [[ ! -s "${out_file}" ]]; then
    err "❌ Sortie SF vide : $*"
    return 2
  fi

  return 0
}

sf_json_status_or_die() {
  local json_file="$1"
  python3 - <<'PY' "${json_file}"
import json,sys
p=sys.argv[1]
raw=open(p,'r',encoding='utf-8',errors='replace').read()
try:
    j=json.loads(raw)
except Exception as e:
    print(f"ERROR: sortie non-JSON: {e}", file=sys.stderr)
    print("OUTPUT(head):", file=sys.stderr)
    for i,line in enumerate(raw.splitlines()[:40],1):
        print(f"{i:02d}: {line}", file=sys.stderr)
    sys.exit(2)

status=j.get("status")
# SF CLI met souvent status=0 si OK
if status not in (0, "0"):
    print(f"ERROR: status={status}", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
PY
}

json_success_or_die() {
  python3 - <<'PY'
import json,sys
try:
    j=json.load(sys.stdin)
except Exception as e:
    print(f"❌ JSON invalide: {e}", file=sys.stderr)
    sys.exit(2)

success = None
if isinstance(j, dict):
    if 'success' in j:
        success = j.get('success')
    elif isinstance(j.get('result'), dict) and 'success' in j['result']:
        success = j['result'].get('success')

if success is True:
    sys.exit(0)

print("❌ Déploiement/validation non réussie (success != true).", file=sys.stderr)
sys.exit(1)
PY
}
