#!/usr/bin/env bash
set -euo pipefail

SOURCE_ALIAS="${1:?source alias required}"
IN_MANIFEST="${2:?input manifest required}"
OUT_MANIFEST="${3:?out manifest required}"
LABELS_TXT="${4:?labels txt required}"
BACKUP_DIR="${5:?backup dir required}"

source scripts/_utils.sh

mkdir -p "$(dirname "${OUT_MANIFEST}")" "$(dirname "${LABELS_TXT}")" "${BACKUP_DIR}"

needs_expand=0
if grep -q "<members>\*</members>" "${IN_MANIFEST}"; then
  needs_expand=1
  cp -f "${IN_MANIFEST}" "${BACKUP_DIR}/package.xml.$(date '+%Y%m%d_%H%M%S').bak"
fi

TMP_EXP="${OUT_MANIFEST}.expanded.tmp.$$"

#sf_list_type_members_json_to_file() {
#  local md_type="$1" out_file="$2"
#  rm -f "${out_file}"
#  if ! sf org list metadata -o "${SOURCE_ALIAS}" -m "${md_type}" --json > "${out_file}" 2>/dev/null; then
#    die "sf org list metadata a échoué pour ${md_type}"
#  fi
#  [[ -s "${out_file}" ]] || die "Sortie JSON vide pour ${md_type} (sf org list metadata)"
#}

sf_list_type_members_json_to_file() {
  local md_type="$1" out_file="$2"

  local cmd
  cmd="sf org list metadata -o \"${SOURCE_ALIAS}\" -m \"${md_type}\" --json"

  rm -f "${out_file}"

  # On capture stdout+stderr dans le fichier pour pouvoir diagnostiquer
  if ! bash -lc "${cmd}" > "${out_file}" 2>&1; then
    err "❌ Impossible de lister les membres du type '${md_type}'."
    err "👉 Rejoue cette commande dans ton terminal pour voir l'erreur :"
    err "   ${cmd}"
    err ""
    err "Sortie capturée (debug) :"
    sed -n '1,120p' "${out_file}" >&2 || true
    die "sf org list metadata a échoué pour ${md_type}"
  fi

  # Même si exit code = 0, parfois la sortie n'est pas du JSON exploitable (vide / texte)
  if [[ ! -s "${out_file}" ]]; then
    err "❌ Sortie vide pour '${md_type}'."
    err "👉 Rejoue cette commande :"
    err "   ${cmd}"
    die "Sortie JSON vide pour ${md_type} (sf org list metadata)"
  fi

  # Vérifier que c'est du JSON (et pas un warning/texte)
  if ! python3 - <<'PY' < "${out_file}" >/dev/null 2>&1
import json,sys
json.load(sys.stdin)
PY
  then
    err "❌ Sortie non-JSON pour '${md_type}' (impossible à parser)."
    err "👉 Rejoue cette commande :"
    err "   ${cmd}"
    err ""
    err "Début de sortie capturée (debug) :"
    sed -n '1,120p' "${out_file}" >&2 || true
    die "Sortie non-JSON pour ${md_type}"
  fi
}

#json_to_names() {
#  python3 - <<'PY'
#import json,sys
#j=json.load(sys.stdin)
#for r in (j.get("result") or []):
#    n=r.get("fullName")
#    if n:
#        print(n)
#PY
#}

#json_to_names() {
#  python3 - <<'PY'
#import json,sys
#try:
#    j=json.load(sys.stdin)
#except Exception as e:
#    print(f"ERREUR: JSON invalide: {e}", file=sys.stderr)
#    sys.exit(2)
#
#for r in (j.get("result") or []):
#    n=r.get("fullName")
#    if n:
#        print(n)
#PY
#}

json_file_to_names() {
  local md_type="$1"
  local json_file="$2"

  python3 - "${SOURCE_ALIAS}" "${md_type}" "${json_file}" <<'PY'
import json, sys
from pathlib import Path

source_alias = sys.argv[1]
md_type      = sys.argv[2]
json_path    = Path(sys.argv[3])

cmd = f'sf org list metadata -o "{source_alias}" -m "{md_type}" --json'

try:
    raw = json_path.read_text(encoding="utf-8", errors="replace")
except Exception as e:
    print(f"ERROR: impossible de lire {json_path}: {e}", file=sys.stderr)
    print(f"CMD: {cmd}", file=sys.stderr)
    sys.exit(2)

try:
    j = json.loads(raw)
except Exception as e:
    print(f"ERROR: JSON invalide pour type '{md_type}': {e}", file=sys.stderr)
    print(f"CMD: {cmd}", file=sys.stderr)
    print("OUTPUT (head):", file=sys.stderr)
    for i, line in enumerate(raw.splitlines()[:40], start=1):
        print(f"{i:02d}: {line}", file=sys.stderr)
    sys.exit(2)

for r in (j.get("result") or []):
    n = r.get("fullName")
    if n:
        print(n)
PY
}

if grep -q "<name>CustomLabels</name>" "${IN_MANIFEST}"; then
  log "ℹ️ CustomLabels détecté dans package.xml : ignoré (utilise CustomLabel:* si tu veux tous les labels)."
fi
if [[ "${needs_expand}" -eq 0 ]]; then
  cp -f "${IN_MANIFEST}" "${TMP_EXP}"
else
  # ☣️ todo : a supprimer
  #log "⚠️ Wildcard '*' détecté : expansion interactive…"

  #types_with_star="$(
  #  awk '
  #    /<types>/ {in_types=1; name=""; star=0}
  #    in_types && /<name>/ {gsub(/.*<name>|<\/name>.*/, "", $0); name=$0}
  #    in_types && /<members>\*<\/members>/ {star=1}
  #    /<\/types>/ { if (in_types && star==1 && name!="") print name; in_types=0 }
  #  ' "${IN_MANIFEST}" | sort -u
  #)"
  types_with_star="$(
  awk '
      /<types>/ {in_types=1; name=""; star=0}
      in_types && /<name>/ {
        gsub(/.*<name>|<\/name>.*/, "", $0)
        gsub(/\r/, "", $0)
        name=$0
      }
      in_types && /<members>\*<\/members>/ {star=1}
      /<\/types>/ {
        if (in_types && star==1 && name!="" && name!="CustomLabels") print name
        in_types=0
      }
    ' "${IN_MANIFEST}" | sort -u
  )"

  TMP_DIR="$(dirname "${OUT_MANIFEST}")/tmp_blocks.$$"
  mkdir -p "${TMP_DIR}"

  if [[ -z "${types_with_star//[[:space:]]/}" ]]; then
    # Aucun type à expand (probablement juste CustomLabels ou rien)
    cp -f "${IN_MANIFEST}" "${TMP_EXP}"
  else
    log "⚠️ Wildcard '*' détecté : expansion interactive…"
    # boucle + awk TMP_EXP...
  fi

  for md_type in ${types_with_star}; do
    log ""
    log "➡️ Expansion type: ${md_type}"

    tmp_json="${TMP_DIR}/${md_type}.json"
    sf_list_type_members_json_to_file "${md_type}" "${tmp_json}"
    #names="$(cat "${tmp_json}" | json_to_names | sort)"
    names="$(json_file_to_names "${md_type}" "${tmp_json}" | sort)"
    count="$(printf '%s\n' "${names}" | sed '/^$/d' | wc -l | tr -d ' ')"

    if [[ "${count}" -eq 0 ]]; then
      log "  (0 composant) => type supprimé"
      : > "${TMP_DIR}/${md_type}.block"
      continue
    fi

    selected=""
    if [[ "${count}" -eq 1 ]]; then
      selected="${names}"
      log "  1 composant => auto: ${selected}"
    else
      log "  ${count} composants trouvés."
      if prompt_yn_strict "Inclure TOUS les composants de ${md_type} ?"; then
        selected="${names}"
      else
        while IFS= read -r n; do
          [[ -z "${n}" ]] && continue
          if prompt_yn_strict "Inclure ${md_type}:${n} ?"; then
            selected+="${n}"$'\n'
          fi
        done <<< "${names}"
        selected="$(printf '%s' "${selected}" | sed '/^$/d' || true)"
      fi
    fi

    if [[ -z "${selected}" ]]; then
      log "  Refus global => type supprimé"
      : > "${TMP_DIR}/${md_type}.block"
      continue
    fi

    {
      echo "  <types>"
      while IFS= read -r n; do
        [[ -z "${n}" ]] && continue
        echo "    <members>${n}</members>"
      done <<< "${selected}"
      echo "    <name>${md_type}</name>"
      echo "  </types>"
    } > "${TMP_DIR}/${md_type}.block"
  done

  # ☣️ : remplacer flush_block() pour skip le wildcard sur CustomLabels
  #function flush_block() {
  #  # Règle v1 : CustomLabels interdit -> on drop le bloc complet
  #  if (name == "CustomLabels") {
  #    buf=""; name="";
  #    return;
  #  }
#
  #  if (name != "" && want[name]) {
  #    file=tmpdir "/" name ".block";
  #    while ((getline line < file) > 0) print line;
  #    close(file);
  #  } else {
  #    printf "%s", buf;
  #  }
  #  buf=""; name="";
  #}

  awk -v tmpdir="${TMP_DIR}" -v tws="${types_with_star}" '
    BEGIN {
      n=split(tws, arr, " ");
      for (i=1;i<=n;i++) want[arr[i]]=1;
      in_block=0; buf=""; name="";
    }
    function flush_block() {
      if (name != "" && want[name]) {
        file=tmpdir "/" name ".block";
        while ((getline line < file) > 0) print line;
        close(file);
      } else {
        printf "%s", buf;
      }
      buf=""; name="";
    }
    /<types>/ { in_block=1; buf=$0 "\n"; next }
    in_block==1 {
      buf=buf $0 "\n";
      if ($0 ~ /<name>/) { line=$0; gsub(/.*<name>|<\/name>.*/, "", line); name=line; }
      if ($0 ~ /<\/types>/) { in_block=0; flush_block(); }
      next
    }
    { print }
  ' "${IN_MANIFEST}" > "${TMP_EXP}"

  rm -rf "${TMP_DIR}"
fi

# Retirer CustomLabels du manifest (interdit en v1)
TMP_EXP2="${TMP_EXP}.ncl.$$"
awk '
  BEGIN {in_block=0; name=""; buf=""}
  /<types>/ {in_block=1; buf=$0 "\n"; name=""; next}
  in_block==1 {
    buf=buf $0 "\n";
    if ($0 ~ /<name>/) {
      line=$0; gsub(/.*<name>|<\/name>.*/, "", line);
      name=line; gsub(/\r/, "", name);
    }
    if ($0 ~ /<\/types>/) {
      in_block=0;
      if (name != "CustomLabels") printf "%s", buf;
      buf=""; name="";
    }
    next
  }
  { print }
' "${TMP_EXP}" > "${TMP_EXP2}"
mv -f "${TMP_EXP2}" "${TMP_EXP}"

if grep -q "<members>\*</members>" "${TMP_EXP}"; then
  die "Wildcard '*' restant dans le manifest généré (interdit)."
fi

#labels="$(
#  awk '
#    /<types>/ {in_types=1; name=""; next}
#    in_types && /<name>/ {gsub(/.*<name>|<\/name>.*/, "", $0); name=$0}
#    in_types && (name=="CustomLabel" || name=="CustomLabels") && /<members>/ {
#      line=$0; gsub(/.*<members>|<\/members>.*/, "", line); print line
#    }
#    /<\/types>/ {in_types=0}
#  ' "${TMP_EXP}" | sed '/^$/d'
#)"
labels="$(
  awk '
    /<types>/ {in_types=1; name=""; next}
    in_types && /<name>/ {
      gsub(/.*<name>|<\/name>.*/, "", $0);
      name=$0;
      gsub(/\r/, "", name);
    }
    in_types && name=="CustomLabel" && /<members>/ {
      line=$0;
      gsub(/.*<members>|<\/members>.*/, "", line);
      gsub(/\r/, "", line);
      print line
    }
    /<\/types>/ {in_types=0}
  ' "${TMP_EXP}" | sed '/^$/d'
)"

atomic_write "${LABELS_TXT}" <<<"${labels:-}"

# ☣️ TODO : enlever debug
log "DEBUG labels extracted count: $(wc -l < "${LABELS_TXT}" | tr -d ' ')"
log "DEBUG labels extracted head:"
sed -n '1,20p' "${LABELS_TXT}" || true

awk '
  BEGIN {in_block=0; name=""; buf=""}
  /<types>/ {in_block=1; buf=$0 "\n"; name=""; next}
  in_block==1 {
    buf=buf $0 "\n";
    if ($0 ~ /<name>/) { line=$0; gsub(/.*<name>|<\/name>.*/, "", line); name=line; gsub(/\r/, "", name); }
    if ($0 ~ /<\/types>/) {
      in_block=0;
      if (name != "CustomLabel" && name != "CustomLabels") printf "%s", buf;
      buf=""; name="";
    }
    next
  }
  { print }
' "${TMP_EXP}" > "${OUT_MANIFEST}"

rm -f "${TMP_EXP}"

log "✅ Manifest généré : ${OUT_MANIFEST}"
log "✅ Custom labels listés: ${LABELS_TXT}"
