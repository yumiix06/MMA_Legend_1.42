"""Core data model: the Fighter dataclass.

The original game built every Fighter (player and NPC alike) through one
big constructor that branched on ``is_player`` in a dozen places, and
applied the player's chosen background *after* construction — which meant
background bonuses and starting techniques silently never applied (the
class field they depended on, ``amateur_discipline``, was still ``None``
at ``__init__`` time). Here that generation logic lives in two explicit
factory functions, ``new_player`` and ``new_npc``, so there's no ordering
trap: by the time a player Fighter exists, its discipline is already known.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


from . import constants as C
from . import data

# ---------------------------------------------------------------------
# Country / discipline bonus helpers
# ---------------------------------------------------------------------

_BONUS_STAT_MAP = {
    "kickboxing": "kicks", "kicks": "kicks",
    "wrestling": "grappling", "grappling": "grappling",
    "bjj": "submissions", "submissions": "submissions",
    "judo": "grappling", "sambo": "grappling", "combat sambo": "grappling",
    "muaythai": "striking", "boxing": "striking",
    "taekwondo": "kicks", "kungfu": "striking",
    "discipline": "discipline", "adaptability": "adaptability",
    "fight_iq": "fight_iq", "speed": "speed",
    "durability": "durability", "strength": "strength", "cardio": "cardio",
    "striking": "striking", "ko_power": "ko_power",
}

_BACKGROUND_STAT_BONUS = {
    # discipline -> {stat: delta}, applied once at character creation
    "Boxing": {"striking": 12, "striking_def": 8, "distance_management": 7,
               "kicks": -5, "speed": 5, "fight_iq": 5},
    "Wrestling": {"grappling": 12, "takedown_def": 7, "submission_def": 3,
                  "strength": 5, "cardio": 5},
    "Muay Thai": {"striking": 8, "kicks": 10, "striking_def": 5,
                  "distance_management": 4, "grappling": 3, "durability": 5},
    "Taekwondo": {"kicks": 14, "speed": 8, "distance_management": 8,
                    "striking_def": 4, "striking": 3, "strength": -2},
    "Combat Sambo": {"grappling": 8, "submissions": 5, "submission_def": 6,
              "ground_control": 5, "striking": 8, "kicks": 3},
    "Sambo": {"grappling": 8, "submissions": 5, "submission_def": 6,
              "ground_control": 5, "striking": 8, "kicks": 3},
    "Judo": {"grappling": 10, "takedown_def": 7, "ground_control": 5,
             "submissions": 4, "strength": 4, "fight_iq": 4},
    "BJJ": {"submissions": 12, "submission_def": 10, "ground_control": 8,
            "fight_iq": 5, "grappling": 5},
}

_BOOK_SNAP_KEYS = (
    "name", "nickname", "country", "country_flag", "team", "style", "habit",
    "weight", "walking_weight", "weight_class", "height", "reach", "stance",
    "amateur_record", "pro_record", "pro_debut", "techniques",
    "technique_levels", "striking", "kicks", "grappling", "submissions",
    "takedown_def", "ground_control", "ko_power", "cardio", "strength",
    "speed", "durability", "fight_iq", "striking_def", "submission_def",
    "distance_management", "bjj_belt", "judo_belt", "age", "fid", "is_player",
)


def _pack_booked(bf):
    if not isinstance(bf, dict):
        return None
    out = {k: v for k, v in bf.items() if k not in ("opponent", "opponent_snap")}
    # JSON-safe scalars only
    for k in list(out):
        if isinstance(out[k], (dict, list, str, int, float, bool)) or out[k] is None:
            continue
        out.pop(k, None)
    opp = bf.get("opponent")
    snap = bf.get("opponent_snap") if isinstance(bf.get("opponent_snap"), dict) else None
    if opp is not None and not isinstance(opp, dict):
        snap = {}
        for k in _BOOK_SNAP_KEYS:
            snap[k] = getattr(opp, k, None)
        snap["is_player"] = False
        snap["booked_fight"] = None
    if snap:
        out["opponent_snap"] = snap
    return out


def _unpack_booked(bf):
    if not isinstance(bf, dict):
        return None
    out = dict(bf)
    snap = out.get("opponent_snap")
    if isinstance(snap, dict) and out.get("opponent") is None:
        try:
            out["opponent"] = Fighter.from_dict(snap)
        except Exception:
            out["opponent"] = None
    return out


_PHYSIQUE_STAT_BONUS = {
    "A": {"speed": 8, "cardio": 5, "strength": -5},
    "B": {},
    "C": {"strength": 8, "durability": 5, "speed": -5, "ko_power": 5},
    "D": {"speed": 5, "kicks": 5, "strength": -3},
    "E": {"strength": 10, "durability": 6, "speed": -6, "cardio": -3},
    "F": {"speed": 6, "strength": 3, "cardio": 3, "kicks": -2},
}


def _weight_class_for(weight: int) -> str:
    if weight < 57:
        return "Flyweight"
    if weight < 61:
        return "Bantamweight"
    if weight < 66:
        return "Featherweight"
    if weight < 71:
        return "Lightweight"
    if weight < 77:
        return "Welterweight"
    if weight < 84:
        return "Middleweight"
    if weight < 93:
        return "Light Heavyweight"
    return "Heavyweight"


def _reach_for(height: int, physique: str = "Athletic") -> int:
    """Natural arm span in centimetres, independent enough from height to matter."""
    mod = {"Lean": 3, "Tall": 4, "Stocky": -2, "Heavy-built": -1,
           "Compact": -3, "Athletic": 1}.get(str(physique), 0)
    return max(150, min(218, int(height) + mod + random.randint(-4, 6)))


@dataclass
class Fighter:
    name: str
    country: str
    country_flag: str
    is_player: bool = True

    age: int = 16
    week: int = 1
    last_week_win: bool = False
    fight_cooldown: int = 0

    amateur_record: list = field(default_factory=lambda: [0, 0, 0])
    pro_record: list = field(default_factory=lambda: [0, 0, 0])
    amateur_wins_cap: int = C.AMATEUR_WINS_CAP
    pro_debut: bool = False
    national_team: bool = False

    nutrition: int = 50
    followers: int = 0
    press_hype: int = 0
    weight_cut_health: int = 100
    last_press_conf: int = 0

    # v1.40 performance state. Legacy risk/health fields remain as mirrors for
    # old authored event conditions; the canonical systems live in performance.py.
    doping_risk: int = 0
    doping_health: int = 100
    supplement_active: list = field(default_factory=list)
    supplement_duration: dict = field(default_factory=dict)
    supplement_stack: dict = field(default_factory=dict)
    doping_program: dict = field(default_factory=dict)
    doping_scrutiny: int = 0
    doping_health_burden: int = 0
    doping_sample: dict = field(default_factory=dict)
    doping_violations: int = 0
    doping_history: list = field(default_factory=list)
    contamination_weeks: int = 0
    doping_used: bool = False
    drug_test_weeks: int = 0
    suspension_weeks: int = 0
    doping_fines_paid: int = 0

    # v0.4 fight camp / combat condition
    camp_active: bool = False
    camp_focus: Optional[str] = None
    camp_opponent_style: Optional[str] = None
    camp_weeks_remaining: int = 0
    camp_bonus: int = 0
    camp_technique_xp: int = 0
    camp_bonus_remaining: dict = field(default_factory=dict)
    competition_signup: Optional[str] = None
    competition_week: int = 0
    competition_prep: bool = False
    competition_sport: str = "MMA"
    competition_level: Optional[str] = None
    competition_due_week: int = 0
    # v0.5 story base
    narrative_tags: list = field(default_factory=list)
    active_chains: list = field(default_factory=list)
    story_flags: dict = field(default_factory=dict)
    rivalries: list = field(default_factory=list)
    hangover_weeks: int = 0
    weekly_spend: int = 0
    rival_id: Optional[str] = None
    physique_type: str = "Athletic"
    meal_plan: Optional[str] = None
    injury: dict = field(default_factory=dict)
    # v1.40 education state. school_status/school_grade remain compatibility
    # mirrors for authored events; education_stage is canonical.
    school_status: str = "school"
    school_grade: int = 72
    education_stage: str = "secondary"
    school_attendance: int = 82
    secondary_completed: bool = False
    university_degree: Optional[str] = None
    university_semester: int = 0
    university_semester_weeks: int = 0
    university_credits: int = 0
    university_average: int = 72
    university_attendance: int = 82
    university_scholarship: int = 0
    university_exam_due: bool = False
    university_exam_deadline: int = 0
    academic_probation: bool = False
    university_team: Optional[str] = None
    education_history: list = field(default_factory=list)
    manager: Optional[str] = None
    manager_cut: int = 0
    manager_id: Optional[str] = None  # people.py Person.id — drives negotiation/rapport
    people_rel: dict = field(default_factory=dict)  # person_id -> rapport 0-100
    booker: int = 0
    last_costs: int = 0
    showcase_ready: bool = False
    opponent_read: int = 0
    medals: dict = field(default_factory=lambda: {"national": {"gold": 0, "silver": 0, "bronze": 0}, "european": {"gold": 0, "silver": 0, "bronze": 0}, "world": {"gold": 0, "silver": 0, "bronze": 0}})
    specialty_gym: Optional[str] = None
    specialty_gym_type: Optional[str] = None
    specialty_coach: Optional[str] = None
    specialty_pool: list = field(default_factory=list)
    specialty_gym_dues: int = 0
    specialty_gym_weeks: int = 0
    specialty_gym_tech_xp: int = 0
    specialty_gym_last_learn_week: int = 0
    specialty_gym_event_history: list = field(default_factory=list)
    specialty_gym_auto: bool = True
    bjj_belt: Optional[str] = None
    bjj_stripes: int = 0
    bjj_weeks: int = 0
    bjj_grade_points: int = 0
    judo_belt: Optional[str] = None
    judo_grade_points: int = 0
    judo_weeks: int = 0
    tkd_belt: Optional[str] = None
    tkd_grade_points: int = 0
    tkd_weeks: int = 0
    nogi_nights: int = 0
    last_week_note: str = ""
    week_kind: str = "full"
    coach_tech_week: int = -99
    damage: dict = field(default_factory=lambda: {
        "cuts": 0, "nose": 0, "eyes": 0, "body": 0, "legs": 0, "total": 0
    })
    # v0.4 career/combat history and weight-management state
    natural_weight: float = 70.0
    walking_weight: float = 70.0
    bodyfat: float = 12.0
    cut_fatigue: int = 0
    fight_history: list = field(default_factory=list)
    sport_records: dict = field(default_factory=dict)
    sport_medals: dict = field(default_factory=dict)
    sport_championships: dict = field(default_factory=dict)
    sport_national_teams: dict = field(default_factory=dict)
    sport_experience: dict = field(default_factory=dict)
    active_amateur_sport: str = "MMA"
    coach_personality: str = ""
    coach_offer_week: int = 0
    coach_offer_tech: str = ""
    recent_results: list = field(default_factory=list)
    current_streak: int = 0
    last_fight_stats: dict = field(default_factory=dict)
    performance_rating: float = 0.0
    retired: bool = False
    age_weeks: int = 0

    height: int = 175
    reach: int = 177
    stance: str = "Orthodox"
    weight: int = 70
    weight_class: str = "Lightweight"
    natural_weight_class: str = "Lightweight"
    fight_weight_class: str = "Lightweight"
    size_advantage: int = 0

    promotion_tier: int = 0
    organization: Optional[str] = None
    room: str = ""
    booked_fight: Optional[dict] = None
    # Promotional contract. This was NEVER a declared field, so from_dict()
    # — which filters incoming keys against __dataclass_fields__ — silently
    # dropped it on every load. Every deal a player signed was lost the next
    # time the game loaded, which is why signing appeared not to work at all.
    org_contract: Optional[dict] = None
    debt: int = 0
    # Persistent career-life state. Older builds created these attributes
    # dynamically, which meant from_dict() silently discarded them on reload.
    intl_camp: Optional[str] = None
    intl_camp_weeks: int = 0
    connections: list = field(default_factory=list)
    side_job: Optional[str] = None
    job_shifts: dict = field(default_factory=dict)
    job_reputation: int = 0
    job_history: list = field(default_factory=list)
    timeline: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    # v1.34 UI/QoL state. Declared so quick-training and weekly feedback survive reloads.
    last_training_focus: str = "N"
    last_training_intensity: str = "B"
    last_week_report: list = field(default_factory=list)
    ui_seen_help: list = field(default_factory=list)
    ui_compact: bool = False
    ui_week_report: bool = True
    ui_color: Optional[bool] = None
    ui_tutorial_active: bool = False
    ui_tutorial_step: int = 0
    ui_tutorial_complete: bool = False
    preferred_gameplan: str = "Balanced"
    last_gameplan: dict = field(default_factory=dict)
    last_ledger: dict = field(default_factory=dict)
    injury_history: list = field(default_factory=list)
    mileage: float = 0.0
    rng_seed: int = 0
    booker_decline_week: int = 0
    camp_for_bout: int = 0
    perks: list = field(default_factory=list)
    habit: str = ""
    # v1.38 living-career state. NPC motives are persistent so a prospect,
    # contender or rebuilding veteran keeps a coherent arc across saves.
    career_personality: str = ""
    career_goal: str = ""
    career_goal_week: int = 0
    career_log: list = field(default_factory=list)
    # v1.39 combat-intelligence state. Old saves are reference-only; these
    # defaults intentionally allow clean new careers without migration code.
    camp_preparation: dict = field(default_factory=dict)
    last_fight_adjustments: list = field(default_factory=list)

    # 15 visible fighting attributes
    striking: int = 25
    kicks: int = 20
    grappling: int = 25
    submissions: int = 20
    takedown_def: int = 20
    ground_control: int = 20
    ko_power: int = 20
    cardio: int = 30
    strength: int = 25
    speed: int = 25
    durability: int = 30
    fight_iq: int = 25
    striking_def: int = 22
    submission_def: int = 20
    distance_management: int = 22

    # hidden / mental traits
    confidence: int = 50
    discipline: int = 50
    happiness: int = 60
    mental_toughness: int = 50
    natural_talent: int = 50
    work_ethic: int = 50
    charisma: int = 45
    adaptability: int = 45
    traits: list = field(default_factory=list)

    money: int = 500
    energy: int = 100
    health: int = 100

    reputation: int = 0
    fame: int = 0
    legacy_score: int = 0
    nickname: Optional[str] = None
    nickname_choices: list = field(default_factory=list)

    amateur_discipline: Optional[str] = None
    amateur_aptitudes: dict = field(default_factory=dict)
    amateur_titles: list = field(default_factory=list)
    tournament_wins: int = 0
    fight_details: str = "Round"

    techniques: list = field(default_factory=list)
    technique_levels: dict = field(default_factory=dict)
    technique_usage_count: dict = field(default_factory=dict)

    relationships: dict = field(default_factory=lambda: {
        "partner": 0, "family": 50, "friends": 50, "coach": 50, "rival": 0,
    })
    rival: Optional[str] = None
    teammate: Optional[str] = None
    fid: Optional[str] = None  # stable id, survives autosave trimming/rewrites

    social_cooldowns: dict = field(default_factory=lambda: {
        "socialize": 0, "media": 0, "sidejob": 0, "hobby": 0, "sponsor": 0, "date": 0,
    })
    social_repeat_penalty: dict = field(default_factory=dict)
    sponsors: list = field(default_factory=list)

    coach_boost: Optional[str] = None
    coach_boost_weeks: int = 0
    recovery_bonus_weeks: int = 0  # from Peptides-style supplements

    team: Optional[str] = None
    style: str = "MMA"

    milestones: set = field(default_factory=set)
    active: bool = True
    mood: int = 50

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------
    @classmethod
    def new_player(cls, name: str, physique: str, country_data: dict,
                    discipline: Optional[str], height=None, weight=None) -> "Fighter":
        f = cls(
            name=name, country=country_data["name"], country_flag=country_data["flag"],
            is_player=True, age=16,
            height=int(height) if height else random.randint(165, 188),
            weight=int(weight) if weight else random.randint(57, 93),
            striking=25, kicks=20, grappling=25, submissions=20, takedown_def=20,
            ground_control=20, ko_power=20, cardio=30, strength=25, speed=25,
            durability=30, fight_iq=25, striking_def=22, submission_def=20,
            distance_management=22,
            confidence=50, discipline=50, happiness=60, mental_toughness=50,
            natural_talent=random.randint(40, 70), work_ethic=random.randint(40, 70),
            charisma=random.randint(30, 60), adaptability=random.randint(30, 60),
            money=500, style="MMA",
        )
        f.weight_class = _weight_class_for(f.weight)
        f.natural_weight_class = f.weight_class
        f.fight_weight_class = f.weight_class
        f.natural_weight = float(f.weight)
        f.walking_weight = float(f.weight)
        physique_name = {
            "A": "Lean", "B": "Athletic", "C": "Stocky", "D": "Tall",
            "E": "Heavy-built", "F": "Compact",
        }.get(physique or "B", physique or "Athletic")
        f.physique_type = physique_name
        f.reach = _reach_for(f.height, physique_name)
        f.stance = "Southpaw" if random.random() < 0.12 else "Orthodox"
        f.bodyfat = {"Lean": 9.0, "Athletic": 12.0, "Stocky": 16.0, "Tall": 13.0,
                     "Heavy-built": 20.0, "Compact": 14.0}.get(physique_name, 12.0)
        f.amateur_discipline = discipline
        f._apply_class_body()

        f.fid = "PLAYER"
        try:
            from . import npc as _npc
            f.traits = _npc.traits(f, n=4)
        except Exception:
            f.traits = []
        f._apply_physique(physique)
        f._apply_country_bonus(country_data.get("bonus", {}))
        f._generate_aptitudes()
        f._apply_background_bonus()
        try:
            from .physiology import clamp_stat, PHYSICAL_STATS
            for _s in PHYSICAL_STATS:
                setattr(f, _s, clamp_stat(f, _s, getattr(f, _s)))
        except Exception:
            pass
        f._init_starting_techniques()
        f._update_mood()
        try:
            from . import people as _people
            _people.ensure_gym_coach(f)
        except Exception:
            pass
        return f

    @classmethod
    def new_npc(cls, name: str, country_data: dict, style: Optional[str] = None,
                team: Optional[str] = None, rng=None) -> "Fighter":
        def ri(a, b):
            return random.randint(a, b - 1) if b > a else a
        base = 30 + ri(-10, 21)
        stat_names = C.SKILLS
        values = [max(10, min(90, base + ri(-5, 6))) for _ in stat_names]
        stats = dict(zip(stat_names, values))

        f = cls(
            name=name, country=country_data["name"], country_flag=country_data["flag"],
            is_player=False, age=ri(18, 36),
            height=ri(160, 191), weight=ri(55, 101),
            confidence=ri(40, 71), discipline=ri(40, 71),
            happiness=ri(40, 71), mental_toughness=ri(40, 71),
            natural_talent=ri(40, 71), work_ethic=ri(40, 71),
            charisma=ri(30, 61), adaptability=ri(30, 61),
            money=ri(100, 2001),
            style=style or random.choice(
                ["Boxing", "Wrestling", "BJJ", "Muay Thai", "Combat Sambo", "Judo", "Kickboxing", "Taekwondo", "Balanced"]),
            team=team,
            **stats,
        )
        f.weight_class = _weight_class_for(f.weight)
        f.natural_weight_class = f.weight_class
        f.fight_weight_class = f.weight_class
        f.natural_weight = float(f.weight)
        f.walking_weight = float(f.weight)
        f.bodyfat = float(random.uniform(9.5, 18.0))
        f.reach = _reach_for(f.height, f.physique_type)
        f.stance = "Southpaw" if random.random() < 0.18 else "Orthodox"
        f._apply_class_body()
        f._update_mood()
        return f

    # ------------------------------------------------------------------
    # Creation-time helpers
    # ------------------------------------------------------------------
    def _apply_physique(self, physique: Optional[str]) -> None:
        for stat, delta in _PHYSIQUE_STAT_BONUS.get(physique or "B", {}).items():
            setattr(self, stat, max(0, min(100, getattr(self, stat) + delta)))

    def _apply_class_body(self) -> None:
        # 1.24: one canonical physiology table.  The old class-body table was
        # duplicated in fights.py and could drift from generated opponents.
        from .physiology import apply_class_baseline
        apply_class_baseline(self)

    def _apply_background_bonus(self) -> None:
        for stat, delta in _BACKGROUND_STAT_BONUS.get(self.amateur_discipline or "", {}).items():
            setattr(self, stat, max(0, min(100, getattr(self, stat) + delta)))
        if self.amateur_discipline:
            apt = self.amateur_aptitudes.get(self.amateur_discipline, 50)
            bonus = (apt - 50) // 5
            if self.amateur_discipline in ("Boxing", "Kickboxing", "Muay Thai", "Taekwondo"):
                self.striking += bonus
                self.kicks += bonus // 2
            elif self.amateur_discipline in ("Wrestling", "Sambo", "Combat Sambo", "Judo"):
                self.grappling += bonus
                self.strength += bonus // 2
            elif self.amateur_discipline == "BJJ":
                self.submissions += bonus
                self.ground_control += bonus // 2

    def _apply_country_bonus(self, bonus: dict) -> None:
        for key, value in bonus.items():
            stat = _BONUS_STAT_MAP.get(key.lower())
            if stat and hasattr(self, stat):
                try:
                    from .physiology import gain_stat
                    gain_stat(self, stat, value)
                except Exception:
                    setattr(self, stat, min(100, getattr(self, stat) + value))
            elif key.lower() in ("confidence", "happiness"):
                setattr(self, key.lower(), min(100, getattr(self, key.lower()) + value))

    def _generate_aptitudes(self) -> None:
        for d in ["Boxing", "Kickboxing", "Muay Thai", "Taekwondo", "Wrestling", "BJJ", "Combat Sambo", "Judo", "MMA"]:
            self.amateur_aptitudes[d] = random.randint(40, 70)
        if self.amateur_discipline in self.amateur_aptitudes:
            self.amateur_aptitudes[self.amateur_discipline] += 5

    def _init_starting_techniques(self) -> None:
        for tech in C.DISCIPLINE_STARTING_TECHNIQUES.get(self.amateur_discipline or "", C.BASICS):
            self.technique_levels[tech] = 1
            if tech not in self.techniques:
                self.techniques.append(tech)
        extras = ["Hook", "Teep", "Single Leg", "Knee Slice Pass", "Body Kick", "Clinch Entry"]
        random.shuffle(extras)
        for tech in extras[:2]:
            if tech not in self.techniques:
                self.techniques.append(tech)
                self.technique_levels[tech] = 1

    # ------------------------------------------------------------------
    # Derived state
    # ------------------------------------------------------------------
    def get_total_record(self) -> list:
        return [a + p for a, p in zip(self.amateur_record, self.pro_record)]

    def _update_mood(self) -> int:
        self.mood = int(max(0, min(100,
            self.happiness * 0.35 + self.confidence * 0.25 +
            self.discipline * 0.2 + self.mental_toughness * 0.2)))
        return self.mood

    def sync_techniques(self) -> None:
        # v1.26: broad abilities are real skills, never selectable moves.
        from .techniques import migrate_fighter_concepts, migrate_v131_named_techniques
        migrate_fighter_concepts(self)
        migrate_v131_named_techniques(self)
        for t in list(self.techniques or []):
            if t and t not in self.technique_levels:
                self.technique_levels[t] = 1
        for t in list(self.technique_levels or {}):
            if t and t not in (self.techniques or []):
                self.techniques.append(t)

    def learn_technique(self, tech_name: str) -> bool:
        if not tech_name:
            return False
        if tech_name not in self.techniques:
            self.techniques.append(tech_name)
        if tech_name not in self.technique_levels:
            self.technique_levels[tech_name] = 1
            return True
        return False

    def level_up_technique(self, tech_name: str) -> bool:
        if tech_name in self.technique_levels and self.technique_levels[tech_name] < 5:
            self.technique_levels[tech_name] += 1
            return True
        return False

    def get_technique_bonus(self, tech_name: str) -> int:
        level = self.technique_levels.get(tech_name, 0)
        if level == 0:
            return 0
        return 2 * level if level < 5 else 12

    def rating_vector(self):
        """The visible core skills as a list, in constants.SKILLS order."""
        return [float(getattr(self, s)) for s in C.SKILLS]

    def record_fight(self, opponent: str, result: str, method: str, round_no: int,
                     event: str = "", performance_rating: float = 0.0, stats: Optional[dict] = None,
                     sport: str = "mma", ruleset: str = "") -> None:
        result = result.title()
        entry = {
            "opponent": opponent, "result": result, "method": method or "Decision",
            "round": int(round_no or 0), "event": event,
            "week": int(getattr(self, "week", 0) or 0),
            "performance_rating": round(float(performance_rating), 1),
            "sport": sport or "mma",
            "ruleset": ruleset or sport or "mma",
        }
        if stats:
            entry["stats"] = dict(stats)
        self.fight_history.append(entry)
        try:
            from .timeline import add
            add(self, "%s vs %s (%s)" % (result, opponent, method or "Decision"))
        except (TypeError, ValueError, AttributeError, ImportError):
            pass
        recs = getattr(self, "sport_records", None)
        if not isinstance(recs, dict):
            recs = {}
            self.sport_records = recs
        row = recs.setdefault(sport or "mma", [0, 0, 0])
        if result == "Win":
            row[0] += 1
        elif result == "Loss":
            row[1] += 1
        else:
            row[2] += 1
        self.recent_results.append(result[0] if result in ("Win", "Loss", "Draw") else result)
        self.recent_results = self.recent_results[-5:]
        if result == "Win":
            self.current_streak = self.current_streak + 1 if self.current_streak > 0 else 1
        elif result == "Loss":
            self.current_streak = self.current_streak - 1 if self.current_streak < 0 else -1
        else:
            self.current_streak = 0
        self.performance_rating = round(float(performance_rating), 1)

    def age_modifier(self) -> dict:
        age = self.age
        if age <= 29:
            return {"speed": 1.0, "cardio": 1.0, "durability": 1.0, "fight_iq": 1.0}
        decline = max(0, age - 29)
        return {
            "speed": max(0.72, 1.0 - decline * 0.012),
            "cardio": max(0.78, 1.0 - decline * 0.009),
            "durability": max(0.80, 1.0 - decline * 0.006),
            "fight_iq": min(1.10, 1.0 + min(decline, 10) * 0.006),
        }

    def is_game_over(self) -> bool:
        # Health 0 is "you cannot fight this week", not career death.
        if self.retired:
            return True
        if self.age >= 40:
            return True
        return False

    def end_reason(self) -> str:
        if self.retired:
            return "retired"
        if self.age >= 40:
            return "age 40"
        return ""

    # ------------------------------------------------------------------
    # Weekly tick (player only — NPCs are advanced in bulk by FighterPool)
    # ------------------------------------------------------------------
    def advance_week(self, console=None) -> None:
        self.week += 1
        if int(getattr(self, "camp_for_bout", 0) or 0) > 0:
            self.camp_for_bout = int(self.camp_for_bout) - 1
            self.camp_active = True
            self.energy = max(20, self.energy - 4)
        if getattr(self, "hangover_weeks", 0) > 0:
            self.hangover_weeks -= 1
            self.energy = max(0, self.energy - 8)
            self.weekly_spend = 0
        if self.is_player:
            from . import cut as _cut
            _cut.decay_damage(self)
            _cut.tick_injury(self, console)
            _cut.weekly_costs(self, console)
            try:
                from .education import tick as _education_tick
                _education_tick(self, console)
            except Exception:
                pass
            try:
                from .systems17 import audit_fighter, log_session, ensure
                ensure(self)
                audit_fighter(self)
                note = (self.last_week_note or "").strip()
                log = list((getattr(self, "story_flags", None) or {}).get("session_log") or [])
                prev = log[-1] if log else {}
                # last_week_note used to repeat every week ("fight TKO" x 70).
                if note and not (prev.get("kind") == "week" and prev.get("detail") == note):
                    log_session(self, "week", note)
            except Exception:
                pass
            try:
                from .v08 import tick_bjj_stripes
                tick_bjj_stripes(self, console)
            except Exception:
                pass
            try:
                from .gym_progression import tick as _tick_specialty_gym
                _tick_specialty_gym(self, console)
            except Exception:
                pass
            try:
                from .systems15 import tick_debt, tick_camp, clamp_money
                tick_debt(self, console)
                tick_camp(self, console)
                # clamp_money was orphaned before 1.9 — defined but never
                # called, so the overdraft floor and the automatic
                # cash-shortfall-becomes-debt rule never actually ran.
                clamp_money(self)
            except (TypeError, ValueError, AttributeError, ImportError):
                pass
            try:
                from .contracts import tick as _tick_contract
                _tick_contract(self, console)
            except Exception:
                pass
            try:
                from . import damage as _dmg
                _dmg.tick(self, console)
                _dmg.random_life_injury(self, console)
            except Exception:
                pass
            try:
                from . import dwcs as _dwcs
                if self.pro_debut:
                    _dwcs.tick(self, console)
            except (TypeError, ValueError, AttributeError, ImportError):
                pass
            try:
                from .aging import tick_birthday
                tick_birthday(self, console)
            except (TypeError, ValueError, AttributeError, ImportError):
                pass
            try:
                from .career import tick_coach_offer
                tick_coach_offer(self)
            except Exception:
                pass
            self.relationships["coach"] = min(100, self.relationships.get("coach", 50) + 1)
            if getattr(self, "specialty_gym", None) and not _cut.parents_help(self):
                dues = int(getattr(self, "specialty_gym_dues", 0) or 0)
                if dues <= 0:
                    dues = 35 if self.specialty_gym_type == "bjj" else 30
                self.money = self.money - dues
            try:
                from . import cut as _body
                _body.tick_body(self, console)
            except Exception:
                pass
            try:
                from . import identity as _id
                _id.sync(self)
            except Exception:
                pass
            if getattr(self, "hangover_weeks", 0) > 0 and int(getattr(self, "school_grade", 70)) < 45:
                self.relationships["family"] = max(0, self.relationships.get("family", 50) - 2)
            self.weekly_spend = 0
        if not self.is_player:
            return

        # 1.24: meal plans are persistent weekly regimens, not instant potions.
        try:
            from .physiology import nutrition_week
            nutrition_week(self)
        except Exception:
            pass
        nutrition_mod = (self.nutrition - 50) / 100 * 0.5
        energy_gain = 5 + nutrition_mod * 5
        health_gain = 3 + nutrition_mod * 2
        if self.recovery_bonus_weeks > 0:
            health_gain += 1.5
            self.recovery_bonus_weeks -= 1
        try:
            from .performance import recovery_bonus as _performance_recovery
            _hb, _eb = _performance_recovery(self)
            health_gain += _hb
            energy_gain += _eb
        except Exception:
            pass
        if self.suspension_weeks > 0:
            self.suspension_weeks -= 1
        if self.camp_weeks_remaining > 0:
            self._tick_camp_week(console)
            self.camp_weeks_remaining -= 1
            if self.camp_weeks_remaining == 0:
                self.camp_active = False
                self.camp_bonus = max(2, self.camp_bonus // 2)  # residual sharpness
                if console:
                    console.info("🏕️ Camp complete — residual sharpness remains for the fight.")
                self.camp_bonus_remaining = {}
                # Opponent-specific preparation is the point of the camp and
                # must survive camp completion until the booked bout. Older
                # builds erased the tape read here, so a completed camp could
                # be less useful than an unfinished one.
                if not isinstance(getattr(self, "booked_fight", None), dict):
                    self.camp_opponent_style = None
                    self.opponent_read = 0
                    self.camp_preparation = {}
        self.energy = min(100, self.energy + int(energy_gain))
        self.health = min(100, self.health + int(health_gain))
        mental_bonus = 0
        try:
            from .education import degree_benefit
            mental_bonus = int(degree_benefit(self, "mental_recovery", 0) or 0)
        except Exception:
            pass
        self.happiness = min(100, self.happiness + 1 + mental_bonus)
        self.confidence = min(100, self.confidence + 1 + mental_bonus)
        # v1.40: temporary performance states and anti-doping are owned by
        # performance.py; raw trained attributes are never modified here.
        try:
            from .performance import tick as _performance_tick
            _performance_tick(self, console)
        except Exception:
            pass

        if self.fight_cooldown > 0:
            self.fight_cooldown -= 1
        for key in self.social_cooldowns:
            if self.social_cooldowns[key] > 0:
                self.social_cooldowns[key] -= 1
        if self.coach_boost_weeks > 0:
            self.coach_boost_weeks -= 1
            if self.coach_boost_weeks == 0:
                self.coach_boost = None
        try:
            from .notoriety import decay_week
            decay_week(self)
        except Exception:
            pass
        if self.followers > 15 and self.week % 3 == 0:
            self.followers = max(0, self.followers - max(1, self.followers // 100))
        if self.week % 4 == 0:
            for key in list(self.social_repeat_penalty.keys()):
                self.social_repeat_penalty[key] = max(0, self.social_repeat_penalty[key] - 1)
                if self.social_repeat_penalty[key] == 0:
                    del self.social_repeat_penalty[key]
        if self.last_press_conf > 0:
            self.last_press_conf -= 1
        self._update_mood()
        if self.last_week_win:
            self._check_milestones(console)
        self.last_week_win = False


    def _tick_camp_week(self, console=None) -> None:
        """Apply one week of camp work: partial bonuses + optional camp event."""
        from . import data
        import random as _r

        remaining = getattr(self, "camp_bonus_remaining", {}) or {}
        applied = []
        for stat, left in list(remaining.items()):
            if left <= 0 or not hasattr(self, stat):
                continue
            step = max(1, (left + max(0, self.camp_weeks_remaining - 1)) // max(1, self.camp_weeks_remaining))
            step = min(step, left)
            cur = getattr(self, stat)
            try:
                from .physiology import gain_stat
                actual = gain_stat(self, stat, step)
            except Exception:
                actual = min(step, max(0, 100 - int(cur)))
                setattr(self, stat, min(100, cur + actual))
            remaining[stat] = max(0, left - max(0, actual))
            if actual:
                applied.append(f"{stat}+{actual}")
        self.camp_bonus_remaining = remaining
        # Small fight-night bonus builds each week
        self.camp_bonus = min(12, self.camp_bonus + 1)
        # Actual opponent study becomes more reliable as camp tape accumulates.
        if getattr(self, "camp_opponent_style", None):
            self.opponent_read = min(20, int(getattr(self, "opponent_read", 0) or 0) + 1)
        try:
            from . import combat_intelligence as _ci
            _ci.advance_preparation(self)
        except Exception:
            pass
        # NT members recover better in camp
        if self.national_team:
            self.energy = min(100, self.energy + 4)
            self.health = min(100, self.health + 2)
        else:
            self.energy = max(0, self.energy - 3)

        # Camp event chance
        events = (data.TRAINING_CAMPS or {}).get("events", [])
        chance = 0.45 if self.national_team else 0.32
        if events and _r.random() < chance:
            evt = _r.choice(events)
            if console:
                console.print(f"🏕️ Camp: {evt.get('title', 'Session')}")
                console.print(f"   {evt.get('description', '')}")
            for k, v in (evt.get("effects") or {}).items():
                if k == "technique_xp":
                    self.camp_technique_xp += int(v)
                    # Chance to level a known tech or learn nothing new here
                    if self.technique_levels and _r.random() < 0.5:
                        tech = _r.choice(list(self.technique_levels.keys()))
                        if self.level_up_technique(tech) and console:
                            console.gold(f"   Technique up: {tech} → L{self.technique_levels[tech]}")
                elif k == "opponent_read":
                    self.opponent_read = min(20, self.opponent_read + int(v))
                elif hasattr(self, k):
                    cur = getattr(self, k)
                    if isinstance(cur, (int, float)):
                        if k == "fame":
                            from .notoriety import add_fame
                            add_fame(self, int(v), "training camp event")
                        elif k in ("money", "reputation"):
                            setattr(self, k, max(0, cur + int(v)))
                        else:
                            try:
                                from .physiology import gain_stat
                                if k in C.SKILLS:
                                    gain_stat(self, k, int(v))
                                else:
                                    setattr(self, k, max(0, min(100, cur + int(v))))
                            except Exception:
                                setattr(self, k, max(0, min(100, cur + int(v))))
            if console and applied:
                console.info("   Camp work: " + ", ".join(applied))
        elif console and applied:
            console.info("🏕️ Camp week: " + ", ".join(applied))

    def _apply_aging(self, console=None) -> None:
        if console:
            console.title_line(f"*** {self.name} turns {self.age}! ***")
        if 23 <= self.age <= 29:
            self.fight_iq = min(100, self.fight_iq + 1)
        elif self.age >= 30:
            years = self.age - 29
            speed_loss = 1 if years <= 4 else 2
            cardio_loss = 1 if years <= 6 else 2
            self.speed = max(10, self.speed - speed_loss)
            self.cardio = max(10, self.cardio - cardio_loss)
            if self.age >= 35:
                self.durability = max(10, self.durability - 1)
            self.fight_iq = min(100, self.fight_iq + 1)
            if console:
                console.warn(f"Age modifier: Speed -{speed_loss}, Cardio -{cardio_loss}; Fight IQ +1")
        if self.age >= 40:
            self.retired = True
            self.active = False
            if console:
                console.warn("Retirement age reached. Your active fighting career has ended.")

    def _check_milestones(self, console=None) -> None:
        total = self.get_total_record()
        for w in (5, 10, 20, 30, 50):
            if total[0] >= w and f"wins_{w}" not in self.milestones:
                self.milestones.add(f"wins_{w}")
                self.legacy_score += 5
                from .notoriety import add_fame
                add_fame(self, 3, "career wins milestone")
                if console:
                    console.milestone(f"🏆 MILESTONE: {w} career wins!")
        if self.pro_debut and "pro" not in self.milestones:
            self.milestones.add("pro")
            self.legacy_score += 10
            from .notoriety import add_fame
            add_fame(self, 6, "turned professional")
            if console:
                console.milestone("🏆 MILESTONE: Turned professional!")
        if self.national_team and "national_team" not in self.milestones:
            self.milestones.add("national_team")
            self.legacy_score += 15
            from .notoriety import add_fame
            add_fame(self, 10, "national team selection")
            if console:
                console.milestone("🏆 MILESTONE: Joined the National Team!")

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        skip = {"_last_outcome", "_pending_title"}
        d = {}
        for k, v in self.__dict__.items():
            if k.startswith("_") or k in skip:
                continue
            if k == "booked_fight":
                d[k] = _pack_booked(v)
                continue
            if isinstance(v, set):
                d[k] = list(v)
            else:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Fighter":
        d = dict(d)
        if isinstance(d.get("milestones"), list):
            d["milestones"] = set(d["milestones"])
        if isinstance(d.get("booked_fight"), dict):
            d["booked_fight"] = _unpack_booked(d["booked_fight"])
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        f = cls(**valid)
        if not getattr(f, "traits", None):
            try:
                from . import npc as _npc
                f.traits = _npc.traits(f, n=4)
            except Exception:
                f.traits = list(getattr(f, "traits", None) or [])
        if getattr(f, "bodyfat", None) is None:
            f.bodyfat = 12.0
        return f
