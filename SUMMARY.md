# SF Wizard — Summary

## What we decided

- **Local-first** tool: fast, powerful, and safe for enterprise workflows.
- **Docker-first** distribution, but also runnable **without Docker**.
- **Minimal dependencies** (avoid unnecessary libraries).
- **SF CLI** is the execution backbone (query/deploy/automation).
- UI is **English only**.
- Store **recent org selections** locally (do not depend on SF CLI ordering).

## v0.1.0 scope

**Goal:** a working, testable vertical slice for the Query feature.

Included:
- Monorepo layout (`apps/api`, `apps/web`, `docker`, `data`)
- FastAPI backend:
  - list orgs via `sf org list --json`
  - store/retrieve active org + recents in `data/`
  - run SOQL queries via `sf data query --json`
  - run model + logs + SSE events endpoint
- Vue 3 frontend:
  - header navigation (Query / Deploy)
  - org badge + org picker
  - SOQL editor + run
  - Results table + Logs tab
  - Copy Excel (TSV)
- Docker Compose + Dockerfiles
- Run without Docker instructions

Not included (by design):
- Bulk API mode
- WHERE IN Builder modal (planned next)
- Deployment automation (page is a placeholder in v0.1.0)

## Next versions plan

### v0.1.1 — WHERE IN Builder
- Modal to paste values (Excel/CSV-like)
- Chunking + “execute all chunks” with aggregation
- Better stats (chunks, duration, row count)

### v0.1.2 — Deploy page skeleton
- Parse and analyze `package.xml`
- Detect monolithic metadata (Custom Labels / Translations)
- Create a “deployment plan” (retrieve/merge/deploy steps) + logs

### v0.1.3+ — Deploy actions
- Baseline retrieve (source/target)
- Merge for Custom Labels / Translations
- Validate/deploy runs
- Permission trimming (“pruning”) integration

## Longer-term
- Resume runs
- Chrome extension UI + local agent bridge
- CI/CD-friendly export/import of run plans

## v0.1.0.2

1️⃣ Architecture & runtime

  - ✅ Mode Docker-first validé
  - Ajout de la variable :
    ○ SF_WIZARD_RUNTIME=docker (compose)
    ○ SF_WIZARD_RUNTIME=native (.env)
  - Objectif clair :
  → le backend sait dans quel contexte il tourne, le front pourra adapter l’UX (ex : login web désactivé en Docker).

2️⃣ SF CLI isolé et maîtrisé

  - ✅ SF CLI version pinnée (@salesforce/cli@2.115.15)
  - ✅ Toutes les commandes SF CLI exécutées uniquement via runner.py
  - ✅ Forçage du HOME au runtime subprocess :
    ○ HOME=/data/sfcli-home
  - 👉 Résultat :
    ○ aucune dépendance au .sf/.sfdx du poste utilisateur
    ○ isolation complète des sessions SF CLI
    ○ comportement déterministe Docker / native

3️⃣ Persistance et sécurité du state

  - ✅ Volume Docker ./data:/data
  - ✅ Écriture atomique des fichiers JSON (write_json_atomic)
  - États séparés :
    ○ data/sfcli-home/ → vérité SF CLI
    ○ data/state/query.json → état UI Query
  - 🔒 Pas de fuite de tokens dans les logs applicatifs

4️⃣ Login Salesforce (mode B)

  - ❌ sf org login web non supporté en Docker (confirmé)
  - ✅ Login via SFDX Auth URL fonctionnel :
    ○ endpoint POST /api/query/login/sfdx-url
    ○ écriture correcte dans /data/sfcli-home/.sfdx
  - ⚠️ Découverte importante :
    ○ un sf org login ... lancé manuellement dans le container n’utilise pas le même HOME que l’API
→ seul le login via l’API (ou avec HOME=/data/sfcli-home) est valable

5️⃣ API Orgs : diagnostic clair

  - /api/orgs fonctionne techniquement
  - La normalisation est correcte
  - ❗ État actuel connu : sf_list_orgs() ne voit pas encore les orgs car : il n’utilise pas le même HOME que le sf manuel ou n’appelle pas run_sf() correctement

👉 Bug identifié, non bloquant, clairement isolé pour la prochaine itération

6️⃣ Ce qui est prêt pour le front

  - Backend stable
  - Flux de login Docker clair et assumé
  - États séparés (orgs / query)
  - APIs en place pour :
    ○ lister les orgs (quand le bug sera corrigé)
    ○ gérer l’org active pour Query
    ○ lancer des queries SOQL

La suite logique est :
  - corriger sf_list_orgs() dans un nouveau cycle
  - puis attaquer le front sereinement