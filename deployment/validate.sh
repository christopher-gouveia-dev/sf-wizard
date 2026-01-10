#!/usr/bin/env bash
set -euo pipefail

source scripts/_utils.sh

RUN_ID=""
if [[ "${1:-}" == "--run-id" ]]; then
  RUN_ID="${2:-}"; shift 2
fi
[[ -n "${RUN_ID}" ]] || die "RUN_ID requis."

RUN_DIR="${RUNS_ROOT}/draft/${RUN_ID}"
STATE_FILE="${RUN_DIR}/state.env"
LOG_DIR="${RUN_DIR}/logs"
WAIT_MINUTES="${WAIT_MINUTES:-60}"
TESTLEVEL="${TESTLEVEL:-RunLocalTests}"

state_require "${STATE_FILE}" INIT_DONE
soft_check_org "${TARGET_ALIAS}"

[[ -f "${MANIFEST_PATH}" ]] || die "Manifest introuvable: ${MANIFEST_PATH}"
current_hash="$(hash_file "${MANIFEST_PATH}")"
if [[ "${current_hash}" != "${MANIFEST_HASH}" ]]; then
  die "Manifest modifié depuis init (hash différent). Relance init."
fi

log "🔎 Validation package (dry-run)..."
sf project deploy start -o "${TARGET_ALIAS}" --manifest "${MANIFEST_PATH}"   --test-level "${TESTLEVEL}" --wait "${WAIT_MINUTES}" --dry-run --ignore-warnings   --message "${FEATURE_NAME} | Package" --json   | tee "${LOG_DIR}/validate.package.json"   | json_success_or_die

LABELS_TXT="${LABELS_TXT:-${RUN_DIR}/manifest/customlabels.txt}"
if [[ -s "${LABELS_TXT}" ]]; then
  log "🔎 Validation labels (un par un)..."
  while IFS= read -r label; do
    [[ -z "${label}" ]] && continue
    sf project deploy start -o "${TARGET_ALIAS}" -m "CustomLabel:${label}"       --wait "${WAIT_MINUTES}" --dry-run --ignore-warnings       --message "${FEATURE_NAME} | CustomLabel:${label}" --json       | tee "${LOG_DIR}/validate.label.${label}.json"       | json_success_or_die
  done < "${LABELS_TXT}"
else
  log "ℹ️ Aucun Custom Label à valider."
fi

state_set "${STATE_FILE}" VALIDATE_DONE "1"
log "✅ Validation terminée"
