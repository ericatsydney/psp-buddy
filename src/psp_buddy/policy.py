"""Bounded local clauses; unsupported words never silently become policy."""

import re
from dataclasses import replace

from .models import Policy

CLAUSES = (
    (r"heal below (\d+)%", "heal_below_percent"),
    (r"evade below (\d+)%", "evade_below_percent"),
    (r"defend above (\d+)% hit rate", "defend_above_hit_percent"),
    (r"cheap weapons below (\d+)%", "cheap_weapon_below_percent"),
    (r"strongest boss weapons above (\d+)%", "strongest_boss_above_percent"),
    (r"common types have more than (\d+) instances", "common_type_min_count"),
    (r"retry at most (\d+) times", "max_retries"),
)
FIXED_CLAUSES = (
    "stop on map clear", "prefer repair then trust then retreat",
    "target damaged enemies before undamaged enemies", "use medium strength weapons otherwise",
)


def parse_policy(text: str) -> Policy:
    """Accept semicolon/newline-separated CLAUSES and FIXED_CLAUSES only."""
    settings: dict[str, int] = {}
    for raw in re.split(r"[;\n]", text):
        clause = " ".join(raw.lower().strip().rstrip(".").split())
        if not clause or clause in FIXED_CLAUSES:
            continue
        for pattern, field in CLAUSES:
            match = re.fullmatch(pattern, clause)
            if match:
                value = int(match[1])
                upper = 3 if field == "max_retries" else 100
                if not 0 <= value <= upper:
                    raise ValueError(f"unsupported {field} value")
                if field == "common_type_min_count":
                    value += 1
                if field in settings and settings[field] != value:
                    raise ValueError(f"contradictory {field}")
                settings[field] = value
                break
        else:
            raise ValueError(f"unsupported policy clause: {raw}")
    defaults = Policy()
    return replace(
        defaults,
        heal_below_percent=settings.get("heal_below_percent", defaults.heal_below_percent),
        evade_below_percent=settings.get("evade_below_percent", defaults.evade_below_percent),
        defend_above_hit_percent=settings.get(
            "defend_above_hit_percent", defaults.defend_above_hit_percent),
        cheap_weapon_below_percent=settings.get(
            "cheap_weapon_below_percent", defaults.cheap_weapon_below_percent),
        strongest_boss_above_percent=settings.get(
            "strongest_boss_above_percent", defaults.strongest_boss_above_percent),
        common_type_min_count=settings.get("common_type_min_count", defaults.common_type_min_count),
        max_retries=settings.get("max_retries", defaults.max_retries),
    )
