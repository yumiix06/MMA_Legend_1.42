"""Technique definitions and v1.26 concept migration.

A technique is a discrete action a fighter can drill and attempt in a fight.
Broad abilities (defence, distance control, pressure) belong on the fighter's
skill sheet instead.  Keeping that distinction here prevents data, coaches and
the fight engine from quietly drifting back to concept-shaped move buttons.
"""
from __future__ import annotations

from typing import Iterable


# Old technique labels which represented broad abilities rather than moves.
# Values are the real skill which inherits that development on old saves.
CONCEPT_SKILLS: dict[str, str] = {
    "Boxing Defense": "striking_def",
    "Kickboxing Defense": "striking_def",
    "Sambo Defense": "submission_def",
    "Sambo Throw": "grappling",
    "Sambo Sub": "submissions",
    "Judo Takedown": "grappling",
    "Judo Submission": "submissions",
    "Guard Pass": "ground_control",
    "Sweep": "grappling",
    "BJJ Escape": "submission_def",
    "Butterfly Guard": "ground_control",
    "Distance Management": "distance_management",
    "Cage Cutoff": "distance_management",
    "Pressure Walking": "distance_management",
}

# Specific defensive mechanics remain learnable techniques, but are reactions
# rather than attack buttons. Their level gives a small bonus to the relevant
# real defensive skill during resolution.
REACTION_TECHNIQUES: dict[str, str] = {
    "Philly Shell": "striking_def",
    "Shoulder Roll": "striking_def",
    "Leg Kick Check": "striking_def",
    "Long Guard": "striking_def",
    "Frame and Post": "striking_def",
    "Peel the Hands": "submission_def",
    "Switch Stance": "distance_management",
}

_ACTION_EXACT = {
    "Jab": ("jab", "head"), "Body Jab": ("jab", "body"),
    "Cross": ("cross", "head"), "Counter Punch": ("cross", "head"),
    "Combination": ("cross", "head"), "Hook": ("hook", "head"),
    "Lead Hook": ("hook", "head"), "Check Hook": ("hook", "head"),
    "Overhand Right": ("hook", "head"), "Uppercut": ("uppercut", "head"),
    "Uppercut Through Guard": ("uppercut", "head"), "Liver Shot": ("liver", "body"),
    "Double Leg": ("double_leg", ""), "Blast Double": ("double_leg", ""),
    "Single Leg": ("single_leg", ""), "Sweep Single": ("single_leg", ""),
    "High Crotch": ("single_leg", ""), "Re-shot": ("single_leg", ""),
    "Ankle Pick": ("single_leg", ""), "Sprawl": ("sprawl", ""),
    "Front Headlock": ("snap_down", ""), "Front Headlock Snap": ("snap_down", ""),
    "Sprawl to Front Headlock": ("snap_down", ""),
    "Inside Trip": ("trip", ""), "Knee Tap": ("trip", ""),
    "Ouchi Gari": ("trip", ""), "Osoto Gari": ("throw", ""),
    "Uchi Mata": ("throw", ""), "Fireman's Carry": ("throw", ""),
    "Sumi Gaeshi": ("throw", ""), "Belt-Grip O-Goshi": ("throw", ""),
    "Seoi Nage": ("throw", ""), "Tai Otoshi": ("throw", ""),
    "Harai Goshi": ("throw", ""), "Sasae Tsurikomi Ashi": ("trip", ""),
    "Hip Toss to Mount": ("throw", ""), "Sacrifice Throw Pin": ("throw", ""),
    "Body Lock Pass": ("guard_pass", ""),
    "Knee Slice Pass": ("guard_pass", ""), "Long Step Pass": ("guard_pass", ""),
    "Stack Pass": ("guard_pass", ""), "Toreando Pass": ("guard_pass", ""),
    "Butterfly Sweep": ("sweep", ""), "Scissor Sweep": ("sweep", ""),
    "Tripod Sweep": ("sweep", ""), "Elbow-Knee Escape": ("escape", ""),
    "Back Take": ("take_back", ""), "Arm Drag to Back": ("take_back", ""),
    "Body Lock to Back": ("take_back", ""), "Mat Return": ("take_back", ""),
    "Rear Naked Choke": ("rear_naked", ""), "Armbar": ("armbar", ""),
    "Triangle Choke": ("triangle", ""), "Kimura": ("kimura", ""),
    "Guillotine": ("guillotine", ""), "Anaconda Choke": ("anaconda", ""),
    "Darce Choke": ("anaconda", ""), "Heel Hook": ("heel_hook", ""),
    "Inside Heel Hook": ("heel_hook", ""), "Outside Heel Hook": ("heel_hook", ""),
    "Kneebar": ("kneebar", ""), "Rolling Kneebar": ("kneebar", ""),
    "Rolling Kneebar Entry": ("kneebar", ""), "Straight Ankle Lock": ("kneebar", ""),
    "Achilles Lock": ("kneebar", ""), "Juji Gatame": ("armbar", ""),
    "Kesa Gatame": ("ride", ""),
    "North-South Choke": ("north_south_choke", ""),
    "Leg Kick": ("low_kick", "leg"), "Calf Kick": ("low_kick", "leg"),
    "Low Calf Kick": ("low_kick", "leg"), "Low Kick Accumulation": ("low_kick", "leg"),
    "Body Kick": ("body_kick", "body"), "Roundhouse Kick": ("body_kick", "body"),
    "Head Kick": ("head_kick", "head"), "Question Mark Kick": ("head_kick", "head"),
    "Axe Kick": ("head_kick", "head"), "Spin Kick": ("head_kick", "head"),
    "Teep": ("teep", "body"), "Teep Kick": ("teep", "body"),
    "Teep to Body": ("teep", "body"), "Front Kick": ("teep", "body"),
    "Clinch": ("clinch_entry", ""), "Muay Thai Clinch": ("clinch_entry", ""),
    "Cage Wrestling": ("clinch_entry", ""), "Elbow": ("dirty_box", "head"),
    "Spinning Elbow": ("dirty_box", "head"), "Clinched Elbow": ("dirty_box", "head"),
    "Elbow Spike": ("dirty_box", "head"), "Knee": ("knee_body", "body"),
    "Wall Knee": ("knee_body", "body"), "Knee to Head Clinch": ("dirty_box", "head"),
    "Elbow From Mount": ("gnp", "head"), "Ground Hammerfist": ("gnp", "head"),
    "Ground Elbow": ("gnp", "head"), "Feint Entry": ("jab", "head"),
    "Level Change Strike": ("double_leg", ""), "Fence Stall Break": ("break", ""),
}


def technique_metadata(name: str) -> dict:
    """Structured combat meaning for one learnable technique."""
    if name in REACTION_TECHNIQUES:
        return {"action_id": None, "role": "reaction", "target": "",
                "skill": REACTION_TECHNIQUES[name], "kind": "defense"}
    action, target = _ACTION_EXACT.get(name, (None, ""))
    if action is None:
        low = name.lower()
        if any(x in low for x in ("arm triangle", "wristlock", "omoplata", "calf slicer", "suloev")):
            action = "kimura"
        elif any(x in low for x in ("berimbolo", "kiss of the dragon", "truck")):
            action = "take_back"
        elif any(x in low for x in ("wrist ride", "ride flatten", "wrist control")):
            action = "ride"
        elif "kick" in low:
            action, target = "body_kick", "body"
        elif "strike" in low or "punch" in low:
            action, target = "cross", "head"
        elif "submission" in low or low.endswith(" sub") or "leg lock" in low:
            action = "kneebar"
        elif "takedown" in low or "throw" in low:
            action = "double_leg"
        elif "guard" in low:
            action = "sweep"
        else:
            action = "scramble"
    kind = "submission" if action in {
        "rear_naked", "armbar", "triangle", "kimura", "guillotine", "anaconda",
        "heel_hook", "kneebar", "north_south_choke",
    } else "strike" if target else "grappling"
    return {"action_id": action, "role": "action", "target": target, "kind": kind}


def is_concept(name: str) -> bool:
    return str(name or "").strip().lower() in {
        label.lower() for label in CONCEPT_SKILLS
    }


def playable_rows(rows: Iterable[dict]) -> list[dict]:
    """Return only discrete moves and repair prerequisites removed with concepts."""
    concepts = {name.lower() for name in CONCEPT_SKILLS}
    out: list[dict] = []
    for source in rows:
        name = str(source.get("name") or "").strip()
        if not name or name.lower() in concepts:
            continue
        row = dict(source)
        if str(row.get("prerequisite") or "").lower() in concepts:
            row["prerequisite"] = None
        row.update(technique_metadata(name))
        out.append(row)
    return out


def migrate_fighter_concepts(fighter) -> dict[str, int]:
    """Remove legacy concepts and convert their level to modest skill XP once.

    The conversion deliberately awards one skill point per two technique
    levels (minimum one) rather than copying a 1-5 move rank directly.  Old
    saves keep some value without gaining a large combat advantage.
    """
    flags = getattr(fighter, "story_flags", None)
    if flags is None:
        fighter.story_flags = {}
        flags = fighter.story_flags
    marker = "v126_concepts_migrated"
    if flags.get(marker):
        return {}

    techs = list(getattr(fighter, "techniques", None) or [])
    levels = dict(getattr(fighter, "technique_levels", None) or {})
    lookup = {name.lower(): (name, skill) for name, skill in CONCEPT_SKILLS.items()}
    gains: dict[str, int] = {}
    kept: list[str] = []

    for name in techs:
        hit = lookup.get(str(name).strip().lower())
        if not hit:
            kept.append(name)
            continue
        canonical, skill = hit
        level = max(1, int(levels.get(name, levels.get(canonical, 1)) or 1))
        gains[skill] = gains.get(skill, 0) + max(1, (level + 1) // 2)

    # Catch concepts present only in the level dictionary.
    for name, level in list(levels.items()):
        hit = lookup.get(str(name).strip().lower())
        if not hit:
            continue
        _canonical, skill = hit
        if not any(str(x).strip().lower() == str(name).strip().lower() for x in techs):
            gains[skill] = gains.get(skill, 0) + max(1, (int(level or 1) + 1) // 2)
        levels.pop(name, None)

    fighter.techniques = kept
    fighter.technique_levels = levels
    for skill, amount in gains.items():
        current = int(getattr(fighter, skill, 20) or 20)
        setattr(fighter, skill, min(100, current + amount))
    flags[marker] = True
    if gains:
        flags["v126_concept_skill_gains"] = dict(gains)
    return gains



V131_CONCEPT_REPLACEMENTS: dict[str, str | None] = {
    "Sambo Throw": "Ouchi Gari",
    "Sambo Sub": "Straight Ankle Lock",
    "Sambo Defense": None,
    "Judo Takedown": "Ouchi Gari",
    "Judo Submission": "Juji Gatame",
    "Guard Pass": "Knee Slice Pass",
    "Sweep": "Scissor Sweep",
    "BJJ Escape": "Elbow-Knee Escape",
    "Butterfly Guard": "Butterfly Sweep",
}

def migrate_v131_named_techniques(fighter) -> dict[str, str]:
    """Replace broad legacy technique labels with actual named moves once.

    This has its own marker because many 1.30 saves already carry the older
    v1.26 migration marker; those saves still need the new cleanup.
    """
    flags = getattr(fighter, "story_flags", None)
    if not isinstance(flags, dict):
        fighter.story_flags = {}; flags = fighter.story_flags
    marker = "v131_named_techniques_migrated"
    if flags.get(marker):
        return {}
    techs = list(getattr(fighter, "techniques", None) or [])
    levels = dict(getattr(fighter, "technique_levels", None) or {})
    mapping = {k.lower(): (k, v) for k, v in V131_CONCEPT_REPLACEMENTS.items()}
    changed = {}
    out=[]
    for name in techs:
        hit=mapping.get(str(name).strip().lower())
        if not hit:
            if name not in out: out.append(name)
            continue
        old,new=hit; lvl=max(1,int(levels.pop(name, levels.pop(old,1)) or 1))
        if new:
            if new not in out: out.append(new)
            levels[new]=max(int(levels.get(new,0) or 0),lvl)
            changed[old]=new
        else:
            skill=CONCEPT_SKILLS.get(old)
            if skill:
                setattr(fighter,skill,min(100,int(getattr(fighter,skill,20) or 20)+max(1,(lvl+1)//2)))
            changed[old]="skill"
    # concepts can also live only in levels
    for key in list(levels):
        hit=mapping.get(str(key).strip().lower())
        if not hit: continue
        old,new=hit; lvl=max(1,int(levels.pop(key,1) or 1))
        if new:
            if new not in out: out.append(new)
            levels[new]=max(int(levels.get(new,0) or 0),lvl)
            changed[old]=new
    fighter.techniques=out
    fighter.technique_levels=levels
    flags[marker]=True
    if changed: flags["v131_named_technique_changes"]=dict(changed)
    return changed

def reaction_bonus(fighter, skill: str) -> float:
    """Small 0.0-0.045 combat bonus from specific learned reactions."""
    levels = getattr(fighter, "technique_levels", None) or {}
    total = 0
    for name, linked in REACTION_TECHNIQUES.items():
        if linked == skill:
            total += max(0, min(5, int(levels.get(name, 0) or 0)))
    return min(0.045, total * 0.009)
