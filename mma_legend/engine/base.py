from __future__ import annotations


class Ruleset:
    name = "base"
    sport = "mma"
    periods = 3
    ticks_per_period = 8
    amateur = True
    grappling_only = False
    legal_tags_blocked = ()
    allowed_actions = None
    blocked_actions = frozenset()
    period_seconds = 300

    def label_period(self, n: int) -> str:
        return "ROUND %s/%s" % (n, self.periods)

    def allows(self, action: dict) -> bool:
        tags = action.get("tags") or []
        if self.amateur and "pro_only" in tags:
            return False
        if self.grappling_only and action.get("kind") in ("strike", "kick"):
            return False
        return True

    def allows_action(self, action_id: str) -> bool:
        """Single action-ID gate consumed by menus, AI and resolution."""
        if self.allowed_actions is not None and action_id not in self.allowed_actions:
            return False
        if action_id in self.blocked_actions:
            return False
        return True
