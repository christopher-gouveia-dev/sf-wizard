#!/usr/bin/env bash
set -euo pipefail

source scripts/_utils.sh

./scripts/check_prereqs.sh >/dev/null

RUN_ID=""
if [[ "${1:-}" == "--run-id" ]]; then
  RUN_ID="${2:-}"; shift 2
fi
[[ -n "${RUN_ID}" ]] || die "RUN_ID requis."

RUN_DIR="${RUNS_ROOT}/draft/${RUN_ID}"
STATE_FILE="${RUN_DIR}/state.env"
LOG_DIR="${RUN_DIR}/logs"
BACKUP_DIR="${RUN_DIR}/backups"
MANIFEST_USER="manifest/package.xml"
WAIT_MINUTES="${WAIT_MINUTES:-60}"

mkdir -p "${LOG_DIR}" "${BACKUP_DIR}" "${RUN_DIR}/manifest" "${RUN_DIR}/plan"

state_set "${STATE_FILE}" STATUS "IN_PROGRESS"
[[ -f "${MANIFEST_USER}" ]] || die "Manifest manquant: ${MANIFEST_USER}"

state_load "${STATE_FILE}" || true

if [[ -z "${SOURCE_ALIAS:-}" ]]; then read -rp "Alias ORG SOURCE : " SOURCE_ALIAS; fi
if [[ -z "${TARGET_ALIAS:-}" ]]; then read -rp "Alias ORG CIBLE  : " TARGET_ALIAS; fi
if [[ -z "${FEATURE_NAME:-}" ]]; then read -rp "Nom feature / ticket : " FEATURE_NAME; fi
echo ""

[[ -n "${SOURCE_ALIAS}" && -n "${TARGET_ALIAS}" && -n "${FEATURE_NAME}" ]] || die "Valeurs obligatoires manquantes."

soft_check_org "${SOURCE_ALIAS}"
soft_check_org "${TARGET_ALIAS}"

MANIFEST_GEN="${RUN_DIR}/manifest/package.generated.xml"
LABELS_TXT="${RUN_DIR}/manifest/customlabels.txt"

./scripts/generate_manifest.sh "${SOURCE_ALIAS}" "${MANIFEST_USER}" "${MANIFEST_GEN}" "${LABELS_TXT}" "${BACKUP_DIR}"

MANIFEST_HASH="$(hash_file "${MANIFEST_GEN}")"

state_set "${STATE_FILE}" RUN_ID "${RUN_ID}"
state_set "${STATE_FILE}" SOURCE_ALIAS "${SOURCE_ALIAS}"
state_set "${STATE_FILE}" TARGET_ALIAS "${TARGET_ALIAS}"
state_set "${STATE_FILE}" FEATURE_NAME "${FEATURE_NAME}"
state_set "${STATE_FILE}" MANIFEST_PATH "${MANIFEST_GEN}"
state_set "${STATE_FILE}" MANIFEST_HASH "${MANIFEST_HASH}"
state_set "${STATE_FILE}" LABELS_TXT "${LABELS_TXT}"

PLAN_TXT="${RUN_DIR}/plan/components_to_deploy.txt"
{
  echo "Package manifest: ${MANIFEST_GEN}"
  echo ""
  if [[ -s "${LABELS_TXT}" ]]; then
    echo "Custom Labels (deployed individually):"
    sed 's/^/CustomLabel: /' "${LABELS_TXT}"
  else
    echo "Custom Labels: (none)"
  fi
} | atomic_write "${PLAN_TXT}"

log "🧾 Plan généré: ${PLAN_TXT}"

log "⬇️ Retrieve package depuis SOURCE (${SOURCE_ALIAS})..."
#sf project retrieve start -o "${SOURCE_ALIAS}" --manifest "${MANIFEST_GEN}" --wait "${WAIT_MINUTES}"
OUT_PACK_JSON="${LOG_DIR}/retrieve.package.source.json"
run_sf_json_to_file "${OUT_PACK_JSON}" sf project retrieve start -o "${SOURCE_ALIAS}" --manifest "${MANIFEST_GEN}" --wait "${WAIT_MINUTES}" --json \
  || die "Retrieve package SOURCE a échoué (voir ${OUT_PACK_JSON})"
sf_json_status_or_die "${OUT_PACK_JSON}" || die "Retrieve package SOURCE KO (voir ${OUT_PACK_JSON})"


if grep -q "<name>Profile</name>" "${MANIFEST_GEN}" && [[ -d "force-app/main/default/profiles" ]]; then
  log "🧹 Prune Profiles..."
  python3 scripts/prune_profiles.py     --package "${MANIFEST_GEN}"     --profiles-dir "force-app/main/default/profiles"     --config "config/profile-prune.ini"
else
  log "ℹ️ Pas de Profile => prune ignoré."
fi

# Prepare CustomLabels local file safely for later per-label deploy:
# - baseline from TARGET (all labels)
# - override each requested label from SOURCE into baseline (merge by fullName)
if [[ -s "${LABELS_TXT}" ]]; then
  log "⬇️ Retrieve TOUS les Custom Labels depuis CIBLE (${TARGET_ALIAS}) (baseline)..."
  sf project retrieve start -o "${TARGET_ALIAS}" -m CustomLabels --wait "${WAIT_MINUTES}" --json \
    | tee "${LOG_DIR}/retrieve.labels.target.json" \
    | json_success_or_die || true
  
  BASE_DIR="force-app/main/default/labels"
  BASE_FILE="${BASE_DIR}/CustomLabels.labels-meta.xml"

  if [[ ! -f "${BASE_FILE}" ]]; then
    log "ℹ️ Aucun CustomLabels récupéré depuis la cible (Nothing retrieved). Création d'une baseline vide."
    mkdir -p "${BASE_DIR}"
    cat > "${BASE_FILE}" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<CustomLabels xmlns="http://soap.sforce.com/2006/04/metadata">
</CustomLabels>
XML
  fi

  cp -f "${BASE_FILE}" "${RUN_DIR}/backups/CustomLabels.baseline.xml"

  log "⬇️ Override labels depuis SOURCE (${SOURCE_ALIAS}) (merge dans baseline)..."
  
  MERGED_TXT="${RUN_DIR}/manifest/customlabels.merged.tmp"
  : > "${MERGED_TXT}"

  while IFS= read -r label; do
    [[ -z "${label}" ]] && continue

    sf project retrieve start -o "${SOURCE_ALIAS}" -m "CustomLabel:${label}" --wait "${WAIT_MINUTES}" --json \
      | tee "${LOG_DIR}/retrieve.label.${label}.json" \
      | json_success_or_die || continue

    SRC_FILE="force-app/main/default/labels/CustomLabels.labels-meta.xml"
    if [[ ! -f "${SRC_FILE}" ]]; then
      log "⚠️ Label non récupéré depuis la source (peut-être managed / non récupérable): ${label}"
      continue
    fi

    TMP_SRC="${RUN_DIR}/backups/CustomLabels.source.${label}.xml"
    cp -f "${SRC_FILE}" "${TMP_SRC}"

    # Restore baseline then merge one label
    cp -f "${RUN_DIR}/backups/CustomLabels.baseline.xml" "${BASE_FILE}"

    python3 - <<PY
import sys, xml.etree.ElementTree as ET
from pathlib import Path
base_path = Path("${BASE_FILE}")
src_path  = Path("${TMP_SRC}")
label_name = "${label}"
NSURI = "http://soap.sforce.com/2006/04/metadata"
NS = {"md": NSURI}

def parse(p: Path):
    t=ET.parse(p)
    return t, t.getroot()

bt, br = parse(base_path)
st, sr = parse(src_path)

def find_label(root, name):
    # handle namespace or not
    if root.tag.startswith("{"):
        for el in root.findall("md:labels", NS):
            if el.findtext("md:fullName", default="", namespaces=NS) == name:
                return el
    else:
        for el in root.findall("labels"):
            if (el.findtext("fullName") or "") == name:
                return el
    return None

src_el = find_label(sr, label_name)
if src_el is None:
    print(f"❌ Label {label_name} introuvable dans le fichier source récupéré.", file=sys.stderr)
    sys.exit(2)

# Remove existing label in baseline if present
if br.tag.startswith("{"):
    base_labels = br.findall("md:labels", NS)
    def get_fn(e): return e.findtext("md:fullName", default="", namespaces=NS)
else:
    base_labels = br.findall("labels")
    def get_fn(e): return e.findtext("fullName") or ""

for el in list(base_labels):
    if get_fn(el) == label_name:
        br.remove(el)

br.append(src_el)
bt.write(base_path, encoding="UTF-8", xml_declaration=True)
PY

    # Update baseline for next iteration
    cp -f "${BASE_FILE}" "${RUN_DIR}/backups/CustomLabels.baseline.xml"
    log "  ✔ ${label}"
    echo "${label}" >> "${MERGED_TXT}"
  done < "${LABELS_TXT}"

  # Ne garder que les labels réellement préparés (récupérés + mergés)
  sort -u "${MERGED_TXT}" | atomic_write "${LABELS_TXT}"
  rm -f "${MERGED_TXT}"

  log "✅ Custom labels réellement préparés: $(wc -l < "${LABELS_TXT}" | tr -d ' ')"
else
  log "ℹ️ Pas de Custom Labels à préparer."
fi

PLAN_TXT="${RUN_DIR}/plan/components_to_deploy.txt"
{
  echo "Package manifest: ${MANIFEST_GEN}"
  echo ""
  if [[ -s "${LABELS_TXT}" ]]; then
    echo "Custom Labels (deployed individually):"
    sed 's/^/CustomLabel: /' "${LABELS_TXT}"
  else
    echo "Custom Labels: (none)"
  fi
} | atomic_write "${PLAN_TXT}"

log "🧾 Plan final généré: ${PLAN_TXT}"

state_set "${STATE_FILE}" INIT_DONE "1"
log "✅ Init terminé"
