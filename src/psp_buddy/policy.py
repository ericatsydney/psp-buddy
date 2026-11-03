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
    (r"evade when the foe hit rate is above (\d+)%", "evade_above_hit_percent"),     # M16
    (r"end moves within reach of at most (\d+) foes", "max_foes_in_reach"),          # M16
    (r"strongest weapons above (\d+)%", "strongest_above_percent"),                  # M16 m16-i
    (r"defend when the foe hit rate is at least (\d+)%", "defend_at_hit_percent"),   # M16 m16-i
)
FLAG_CLAUSES = {
    "target non-bosses before bosses": "non_boss_first",
    "use sense then focus before attacking": "spirit_before_attack",     # M11 wording
    "use spirits before attacking": "spirit_before_attack",
    "hold units without focus or sense on turn 1": "hold_unspirited_turn_one",     # M16
    "advance toward foes when none is in reach": "advance_when_no_target",         # M16
    "move damaged units away from foes": "retreat_damaged",                        # M16 m16-i
}
FIXED_CLAUSES = (
    "stop on map clear", "prefer repair then trust then retreat",
    "target damaged enemies before undamaged enemies", "use medium strength weapons otherwise",
)


def parse_policy(text: str) -> Policy:
    """Accept semicolon/newline-separated CLAUSES and FIXED_CLAUSES only."""
    settings: dict[str, int] = {}
    flags: dict[str, bool] = {}
    for raw in re.split(r"[;\n]", text):
        clause = " ".join(raw.lower().strip().rstrip(".").split())
        if not clause or clause in FIXED_CLAUSES:
            continue
        if clause in FLAG_CLAUSES:
            flags[FLAG_CLAUSES[clause]] = True
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
        evade_above_hit_percent=settings.get(
            "evade_above_hit_percent", defaults.evade_above_hit_percent),
        max_foes_in_reach=settings.get("max_foes_in_reach", defaults.max_foes_in_reach),
        strongest_above_percent=settings.get(
            "strongest_above_percent", defaults.strongest_above_percent),
        defend_at_hit_percent=settings.get("defend_at_hit_percent", defaults.defend_at_hit_percent),
        **flags,
    )
