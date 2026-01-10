#!/usr/bin/env python3
from __future__ import annotations

import argparse
import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import shutil
import sys
import xml.etree.ElementTree as ET

SF_NS = 'http://soap.sforce.com/2006/04/metadata'
NS = {'m': SF_NS}

# Profile section -> entry element -> key field element
# (pour filtrer une section, on retire les entries dont la key n'est pas autorisée)
SECTION_KEY_MAP: Dict[str, Tuple[str, str]] = {
    'objectpermissions': ('objectPermissions', 'object'),
    'fieldpermissions': ('fieldPermissions', 'field'),
    'tabvisibilities': ('tabVisibilities', 'tab'),
    'classaccesses': ('classAccesses', 'apexClass'),
    'pageaccesses': ('pageAccesses', 'apexPage'),
    'recordtypevisibilities': ('recordTypeVisibilities', 'recordType'),
    'applicationvisibilities': ('applicationVisibilities', 'application'),
    # Ajoute ici si tu veux filtrer d'autres sections à clé.
}

@dataclass
class PruneConfig:
    drop_unlisted_sections: bool
    keep_tags: Set[str]
    section_enabled: Dict[str, bool]
    filter_rules: Dict[str, str]
    objects_from_manifest: bool

def parse_ini(path: Path) -> PruneConfig:
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding='utf-8')

    drop_unlisted = cfg.getboolean('core', 'drop_unlisted_sections', fallback=False)
    keep_tags_raw = cfg.get('core', 'keep_tags', fallback='custom,userLicense,description')
    # ☣️ TODO : A voir si ça plante
    keep_tags = {t.strip() for t in keep_tags_raw.split(',') if t.strip()}

    section_enabled = {}
    if cfg.has_section('sections'):
        for k, v in cfg.items('sections'):
            #print(f'Valeur de {k} : {v.strip().lower()}')
            section_enabled[k] = v.strip().lower() == 'true'
            #print(f'section_enabled[k] : {section_enabled[k]}')

    filter_rules = {}
    if cfg.has_section('filters'):
        for k, v in cfg.items('filters'):
            filter_rules[k] = v.strip()

    objects_from_manifest = cfg.getboolean('filters', 'objects_from_manifest', fallback=True)

    return PruneConfig(
        drop_unlisted_sections=drop_unlisted,
        keep_tags=keep_tags,
        section_enabled=section_enabled,
        filter_rules=filter_rules,
        objects_from_manifest=objects_from_manifest,
    )

# TODO : à supprimer, ne sert à rien, si ?
def _local(tag: str) -> str:
    # '{ns}name' -> 'name'
    return tag.split('}', 1)[1] if '}' in tag else tag

def parse_package_xml(package_path: Path) -> Dict[str, Set[str]]:
    tree = ET.parse(package_path)
    root = tree.getroot()

    def endswith(el: ET.Element, name: str) -> bool:
        return _local(el.tag) == name

    out: Dict[str, Set[str]] = {}
    for types_el in root:
        if not endswith(types_el, 'types'):
            continue

        md_type = None
        members: List[str] = []
        for child in list(types_el):
            if endswith(child, 'name'):
                md_type = (child.text or '').strip()
            elif endswith(child, 'members'):
                members.append((child.text or '').strip())

        if not md_type:
            continue

        s = out.setdefault(md_type, set())
        for m in members:
            if not m:
                continue
            # on ignore '*' : wildcard non exploitable pour filtrage propre
            if m == '*':
                continue
            s.add(m)

    return out

def read_list_file(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    lines = []
    for raw in path.read_text(encoding='utf-8').splitlines():
        x = raw.strip()
        if not x or x.startswith('#'):
            continue
        lines.append(x)
    return set(lines)

def union_sources(spec: str, manifest: Dict[str, Set[str]]) -> Set[str]:
    # spec: 'union:a+b+c' où chaque partie est une spec standard
    _, rest = spec.split(':', 1)
    parts = [p.strip() for p in rest.split('+') if p.strip()]
    allowed: Set[str] = set()
    for p in parts:
        allowed |= resolve_source(p, manifest)
    return allowed

def resolve_source(spec: str, manifest: Dict[str, Set[str]]) -> Set[str]:
    # spec patterns:
    #   keep_all / keep_none
    #   manifest:CustomObject
    #   file:path/to/list.txt
    #   union:...
    #   objects_from_manifest (pseudo-source)
    if spec == 'keep_all':
        # spécial: géré ailleurs
        return set(['__KEEP_ALL__'])
    if spec == 'keep_none':
        return set()
    if spec.startswith('union:'):
        return union_sources(spec, manifest)
    if spec == 'objects_from_manifest':
        return manifest.get('CustomObject', set())

    if ':' not in spec:
        # fallback: rien
        return set()

    mode, arg = spec.split(':', 1)
    mode = mode.strip()
    arg = arg.strip()

    if mode == 'manifest':
        return set(manifest.get(arg, set()))
    if mode == 'file':
        return read_list_file(Path(arg))

    return set()

def ensure_backup(file_path: Path) -> None:
    bak = file_path.with_suffix(file_path.suffix + '.bak')
    if not bak.exists():
        shutil.copy2(file_path, bak)

def prune_profile(
    profile_path: Path,
    cfg: PruneConfig,
    manifest: Dict[str, Set[str]],
) -> None:
    ensure_backup(profile_path)

    tree = ET.parse(profile_path)
    root = tree.getroot()

    # Collect all section names present
    present_sections = [_local(ch.tag) for ch in list(root)]

    # 1) Drop sections disabled
    for ch in list(root):
        name = _local(ch.tag)
        name = name.lower()
        # keep_tags are leaf-ish, but we still allow them even if sections says false
        if name in cfg.keep_tags:
            #print(f'On gardee (kep_tags) {name}')
            continue

        if name in cfg.section_enabled:
            if not cfg.section_enabled[name]:
                #print(f'On supprime (section false) {name}')
                root.remove(ch)
        else:
            if cfg.drop_unlisted_sections:
                #print(f'On supprime (unlisted) {name}')
                root.remove(ch)

    # 2) Filtering per section (only for enabled + key-mapped sections)
    for section, rule in cfg.filter_rules.items():
        # Only filter sections that exist and are enabled
        if cfg.section_enabled.get(section, True) is False:
            continue

        if section not in SECTION_KEY_MAP:
            continue

        entry_tag, key_tag = SECTION_KEY_MAP[section]

        allowed = resolve_source(rule, manifest)

        # Special: keep_all marker
        if '__KEEP_ALL__' in allowed:
            continue

        # Special: for fieldpermissions, allow union with objects_from_manifest if configured
        # BUT this is already possible via union:manifest:CustomField+objects_from_manifest
        # Here we add an extra safety: if rule is manifest:CustomField and objects_from_manifest=true, we include objects.
        if section == 'fieldpermissions' and cfg.objects_from_manifest and rule.startswith('manifest:CustomField'):
            allowed |= manifest.get('CustomObject', set())

        # Filter entries
        for entry in list(root.findall(f'm:{entry_tag}', NS)):
            key_el = entry.find(f'm:{key_tag}', NS)
            key_val = (key_el.text or '').strip() if key_el is not None else ''

            if not key_val:
                root.remove(entry)
                continue

            # fieldPermissions: allow either exact field match OR object match (Obj__c.*)
            #if section == 'fieldpermissions':
            if entry_tag == 'fieldPermissions':
                if key_val in allowed:
                    continue
                obj = key_val.split('.', 1)[0]
                if obj in allowed:
                    continue
                root.remove(entry)
                continue

            # other sections: exact match only
            if key_val not in allowed:
                root.remove(entry)

    # Write back (preserve namespace)
    ET.register_namespace('', SF_NS)
    tree.write(profile_path, encoding='UTF-8', xml_declaration=True)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--package', required=True, help='Path to manifest/package.xml')
    ap.add_argument('--profiles-dir', required=True, help='Directory containing *.profile-meta.xml')
    ap.add_argument('--config', required=True, help='Path to profile-prune.ini')
    ap.add_argument('--no-backup', action='store_true', help='Do not create .bak backups')
    args = ap.parse_args()

    package_path = Path(args.package)
    profiles_dir = Path(args.profiles_dir)
    config_path = Path(args.config)

    if not package_path.exists():
        print(f'ERROR: package.xml not found: {package_path}', file=sys.stderr)
        return 2
    if not profiles_dir.exists():
        print(f'INFO: profiles dir not found: {profiles_dir} (nothing to prune)')
        return 0
    if not config_path.exists():
        print(f'ERROR: config not found: {config_path}', file=sys.stderr)
        return 2

    cfg = parse_ini(config_path)
    manifest = parse_package_xml(package_path) 

    # Backup behavior: script currently always backs up, but allow disabling by removing .bak creation
    if args.no_backup:
        # monkey patch: overwrite ensure_backup
        globals()['ensure_backup'] = lambda _: None  # noqa: E731

    files = sorted(profiles_dir.glob('*.profile-meta.xml'))
    if not files:
        print('INFO: no profile files found.')
        return 0

    print(f'INFO: pruning {len(files)} profile(s) using {config_path}')
    for f in files:
        print(f' - {f.name}')
        prune_profile(f, cfg, manifest)

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
