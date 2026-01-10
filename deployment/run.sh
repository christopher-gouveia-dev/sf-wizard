#!/usr/bin/env bash
set -euo pipefail

source scripts/_utils.sh

#RUN_STARTED_AT="$(date '+%Y-%m-%d %H:%M:%S')"
echo "🕒 Run start: $(date '+%Y-%m-%d %H:%M:%S')"

acquire_lock

DRAFT_DIR="${RUNS_ROOT}/draft"
ABANDONED_DIR="${RUNS_ROOT}/abandoned"
SUCCEEDED_DIR="${RUNS_ROOT}/succeeded"

mkdir -p "${DRAFT_DIR}" "${ABANDONED_DIR}" "${SUCCEEDED_DIR}"

mapfile -t drafts < <(find "${DRAFT_DIR}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)

if [[ "${#drafts[@]}" -gt 1 ]]; then
  echo "⚠️ Plusieurs runs détectés dans draft/ :"
  i=1
  for rid in "${drafts[@]}"; do
    echo "  ${i}) ${rid}"
    i=$((i+1))
  done

  read -rp "Choisir un run (numéro) : " sel || true
  if [[ "${sel}" =~ ^[0-9]+$ ]] && (( sel >= 1 && sel <= ${#drafts[@]} )); then
    RUN_ID="${drafts[$((sel-1))]}"
  else
    err "❌ Choix invalide. Relance la task."
    exit 2
  fi

  echo "📦 Classement en abandoned/ :"
  for rid in "${drafts[@]}"; do
    if [[ "${rid}" != "${RUN_ID}" ]]; then
      echo "  - ${rid}"
      mv -f "${DRAFT_DIR}/${rid}" "${ABANDONED_DIR}/${rid}"
    fi
  done

elif [[ "${#drafts[@]}" -eq 1 ]]; then
  RID="${drafts[0]}"
  echo "🧭 Run draft détecté: ${RID}"
  # ☣️ TODO : étendre pour la liste des runs à choisir
  #STATE_FILE="process/runs/draft/${RID}/state.env"
  #if [[ -f "${STATE_FILE}" ]]; then
  #  # shellcheck source=/dev/null
  #  source "${STATE_FILE}"
  #  echo "ℹ️ Draft info:"
  #  echo "  - Source : ${SOURCE_ALIAS:-?}"
  #  echo "  - Cible  : ${TARGET_ALIAS:-?}"
  #  echo "  - Feature: ${FEATURE_NAME:-?}"
  #fi

  if prompt_yn_strict "Continuer ce run ?"; then
    RUN_ID="${RID}"
  else
    echo "📦 Classement en abandoned/ : ${RID}"
    mv -f "${DRAFT_DIR}/${RID}" "${ABANDONED_DIR}/${RID}"
    RUN_ID="$(run_id_new)"
    mkdir -p "${DRAFT_DIR}/${RUN_ID}"
  fi
else
  RUN_ID="$(run_id_new)"
  mkdir -p "${DRAFT_DIR}/${RUN_ID}"
fi

RUN_DIR="${DRAFT_DIR}/${RUN_ID}"
STATE_FILE="${RUN_DIR}/state.env"
LOG_DIR="${RUN_DIR}/logs"
mkdir -p "${LOG_DIR}"

state_set "${STATE_FILE}" RUN_ID "${RUN_ID}"
state_set "${STATE_FILE}" STATUS "IN_PROGRESS"

echo "🧭 RUN_ID=${RUN_ID}"
echo "📁 ${RUN_DIR}"

./scripts/init.sh --run-id "${RUN_ID}" 2>&1 | tee "${LOG_DIR}/init.log"

if prompt_yn "Pause après init ?"; then
  echo "⏸️ Pause."
  exit 0
fi

./scripts/validate.sh --run-id "${RUN_ID}" 2>&1 | tee "${LOG_DIR}/validate.log"

if prompt_yn "Pause après validate ?"; then
  echo "⏸️ Pause."
  exit 0
fi

./scripts/deploy.sh --run-id "${RUN_ID}" 2>&1 | tee "${LOG_DIR}/deploy.log"

echo "✅ Classement en succeeded/ : ${RUN_ID}"
mv -f "${RUN_DIR}" "${SUCCEEDED_DIR}/${RUN_ID}"

echo "✅ Run terminé: ${RUN_ID}"
