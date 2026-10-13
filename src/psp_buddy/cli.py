"""Read-only offline commands. No live transport/control imports or fallbacks."""

import argparse
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import asdict, replace
from pathlib import Path

from .config import RunConfig
from .inspection_io import (
    MAX_INSTRUCTIONS_BYTES,
    load_json_object,
    load_record,
    parse_inspection_profile,
    read_bounded,
)
from .models import Policy
from .policy import parse_policy
from .reader import decode_inspection

LIVE_GATES = (
    'fresh_verified_original_and_portable_backups',
    'authenticated_complete_tactical_observation',
    'unattended_capture_and_recognition',
    'same_slot_save_and_restore',
    'validated_menu_executor_recipes',
    'protected_one_map_acceptance',
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='PSP Buddy read-only offline tooling')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('validate', 'inspect', 'run'):
        command = commands.add_parser(name, help=(
            'disabled: live integration gates pending' if name == 'run' else 'offline read-only'))
        command.add_argument('--config', required=name != 'run',
                             help='Local machine configuration JSON')
        if name == 'inspect':
            command.add_argument('--record', help='Supplied exact-sized binary stat record')
        else:
            command.add_argument('--instructions-file', help='Bounded local policy clauses')
            command.add_argument('--dry-run', action='store_true',
                                 help='Read-only report; run still refuses unmet live gates')
    return parser


def _load_config(path: Path) -> RunConfig:
    values = load_json_object(path)
    for name in ('original_savedata', 'original_states', 'portable_savedata', 'portable_states',
                 'backup_root', 'emulator_path', 'iso_path', 'profile_path'):
        value = values.get(name)
        if isinstance(value, str) and value.strip() and not Path(value).is_absolute():
            values[name] = str(path.absolute().parent / value)
    return RunConfig.from_dict(values)


def _policy(config: RunConfig, path: str | None) -> Policy:
    text = '' if path is None else read_bounded(Path(path), MAX_INSTRUCTIONS_BYTES).decode('utf-8')
    policy = parse_policy(text)
    if (re.search(r'retry\s+at\s+most', text, re.IGNORECASE)
            and policy.max_retries > config.max_retries):
        raise ValueError('policy retries exceed configured safety ceiling')
    return replace(policy, max_retries=min(policy.max_retries, config.max_retries))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == 'run' and args.config is None:
        print(json.dumps({'command': 'run', 'error': 'live capabilities disabled',
                          'autonomous_execution_enabled': False}), file=sys.stderr)
        return 2
    try:
        config = _load_config(Path(args.config))
        profile = parse_inspection_profile(load_json_object(config.profile_path))
        if (profile.game_id, profile.patch_id, profile.emulator_version) != (
            config.game_id, config.patch_id, config.emulator_version,
        ):
            raise ValueError('profile and configuration identity mismatch')
        profile_report = {
            'kind': 'stat_inspection', 'schema_version': 1,
            'provenance': 'user_supplied_profile', 'live_authenticated': False,
            'calibration': 'user_asserted_evidence_references_not_authenticated',
            'unit_label': profile.unit_label, 'record_address': profile.record_address,
            'record_size': profile.record_size,
            'fields': [asdict(field) for field in profile.fields],
        }
        report: dict[str, object] = {
            'command': args.command, 'mode': 'offline_read_only',
            'autonomous_execution_enabled': False,
            'configuration_valid': True, 'profile': profile_report,
            'configuration_validation_scope': 'schema_identity_and_local_save_root_checks',
            'identity': {'game_id': config.game_id, 'patch_id': config.patch_id,
                         'emulator_version': config.emulator_version},
            'live_gates': [{'name': gate, 'passed': False,
                            'reason': 'not_established_by_offline_cli'} for gate in LIVE_GATES],
        }
        if args.command == 'inspect':
            if not args.record:
                raise ValueError('--record required: no live observation fallback')
            inspected = decode_inspection(profile, load_record(Path(args.record), profile),
                                          config.game_id, config.patch_id, config.emulator_version)
            report.update(values=dict(inspected.values), unit_label=inspected.unit_label,
                          provenance='user_supplied_record_and_profile', live_authenticated=False,
                          tactical_snapshot_available=False)
        else:
            report['policy'] = asdict(_policy(config, args.instructions_file))
            report['dry_run'] = True
            report['selected_slot'] = config.slot
            if args.command == 'run':
                report['reason'] = 'live_integration_gates_unmet'
        print(json.dumps(report, sort_keys=True))
        return 2 if args.command == 'run' else 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({'command': args.command, 'error': str(exc),
                          'autonomous_execution_enabled': False}), file=sys.stderr)
        return 2
