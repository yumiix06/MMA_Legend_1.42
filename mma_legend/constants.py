"""Static game constants: weight classes, promotion tiers, skill lists."""

GAME_VERSION = "1.42.0"

WEIGHT_CLASSES = [
    "Flyweight", "Bantamweight", "Featherweight", "Lightweight",
    "Welterweight", "Middleweight", "Light Heavyweight", "Heavyweight",
]

WEIGHT_RANGES_KG = {
    "Flyweight": (52, 57),
    "Bantamweight": (57, 61),
    "Featherweight": (61, 66),
    "Lightweight": (66, 71),
    "Welterweight": (71, 77),
    "Middleweight": (77, 84),
    "Light Heavyweight": (84, 93),
    "Heavyweight": (93, 120),
}

PROMOTION_TIERS = [
    "Amateur (Local)", "National Amateur", "European Amateur", "IMMAF World",
    "Pro (Local)", "Regional FC", "National MMA", "European Championship",
    "Bellator", "ONE", "PFL", "Rizin", "UFC", "UFC Championship",
]

# The 15 visible fighting attributes, in canonical display order. 1.26 splits
# broad defensive/tactical competence out of named move collection.
SKILLS = [
    "striking", "kicks", "grappling", "submissions",
    "ground_control", "ko_power", "striking_def", "takedown_def",
    "submission_def", "distance_management", "cardio", "strength",
    "speed", "durability", "fight_iq",
]

SKILL_LABELS = {
    "striking": "Striking", "kicks": "Kicks", "grappling": "Grappling",
    "submissions": "Submissions", "ground_control": "Ground Control",
    "ko_power": "KO Power", "striking_def": "Striking Def.",
    "takedown_def": "Takedown Def.", "submission_def": "Submission Def.",
    "distance_management": "Distance Mgmt.",
    "cardio": "Cardio", "strength": "Strength", "speed": "Speed",
    "durability": "Durability", "fight_iq": "Fight IQ",
}

# Relative importance of each skill in the fight-rating formula (must line
# up 1:1 with SKILLS above).
SKILL_WEIGHTS = [1.25, 1.05, 1.15, 1.05, 1.0, 1.30, 1.15, 1.0,
                 1.05, 1.10, 1.20, 1.0, 1.10, 1.20, 1.35]

DISCIPLINES = ["Boxing", "Wrestling", "Muay Thai", "Combat Sambo", "BJJ", "Judo", "Taekwondo"]

BASICS = ["Jab", "Cross", "Low Kick", "Sprawl", "Double Leg"]

DISCIPLINE_STARTING_TECHNIQUES = {
    "Boxing": BASICS + ["Hook", "Uppercut", "Rear Slip"],
    "Wrestling": BASICS + ["Single Leg", "Clinch Entry", "Stand Up"],
    "Muay Thai": BASICS + ["Teep", "Body Kick", "Long Guard"],
    "Kickboxing": BASICS + ["Body Kick", "Hook"],
    "Taekwondo": ["Jab", "Cross", "Teep", "Side Kick", "Roundhouse to Body", "Roundhouse to Head"],
    "Sambo": BASICS + ["Ouchi Gari", "Straight Ankle Lock"],
    "Combat Sambo": BASICS + ["Ouchi Gari", "Straight Ankle Lock"],
    "Judo": BASICS + ["Ouchi Gari", "Uchi Mata", "Knee Slice Pass"],
    "BJJ": BASICS + ["Knee Slice Pass", "Scissor Sweep", "Rear Naked Choke", "Elbow-Knee Escape"],
    "": list(BASICS),
}

DISCIPLINE_TRAINING_FOCUS = {
    "Boxing": ["striking", "striking_def", "distance_management", "speed", "fight_iq", "ko_power"],
    "Kickboxing": ["striking", "kicks", "striking_def", "distance_management", "speed", "cardio"],
    "Muay Thai": ["striking", "kicks", "striking_def", "grappling", "durability"],
    "Taekwondo": ["kicks", "speed", "distance_management", "striking_def", "cardio", "fight_iq"],
    "Wrestling": ["grappling", "takedown_def", "submission_def", "strength", "cardio"],
    "BJJ": ["submissions", "submission_def", "ground_control", "fight_iq", "adaptability"],
    "Sambo": ["grappling", "submissions", "submission_def", "strength", "ground_control", "striking"],
    "Combat Sambo": ["grappling", "submissions", "submission_def", "strength", "ground_control", "striking"],
    "Judo": ["grappling", "takedown_def", "ground_control", "strength", "fight_iq"],
    "MMA": SKILLS,
}

AMATEUR_WINS_CAP = 30

TRAINING_FOCUS_MAP = {
    # key: (primary_stat, primary_gain, (secondary_stat, secondary_gain) | None)
    "A": ("striking", 3, ("speed", 1)),
    "B": ("kicks", 3, ("speed", 1)),
    "C": ("grappling", 3, ("strength", 1)),
    "D": ("submissions", 3, ("fight_iq", 1)),
    "E": ("takedown_def", 3, ("grappling", 1)),
    "F": ("ground_control", 3, ("grappling", 1)),
    "G": ("cardio", 4, ("durability", 1)),
    "H": ("strength", 3, ("ko_power", 1)),
    "I": ("speed", 3, ("cardio", 1)),
    "J": ("fight_iq", 4, ("adaptability", 1)),
    "K": ("striking_def", 3, ("distance_management", 1)),
    "L": ("submission_def", 3, ("grappling", 1)),
    "M": ("distance_management", 3, ("fight_iq", 1)),
}

SUPPLEMENTS_DB = {
    "legal": [
        {"name": "Creatine", "cost": 50, "effect": {"strength": 3, "ko_power": 2}, "duration": 4, "risk": 0},
        {"name": "Protein", "cost": 40, "effect": {"strength": 2, "cardio": 2}, "duration": 4, "risk": 0},
        {"name": "Pre-Workout", "cost": 30, "effect": {"speed": 3, "energy": 10}, "duration": 2, "risk": 0},
        {"name": "CBD", "cost": 60, "effect": {"health": 5, "happiness": 5}, "duration": 4, "risk": 0},
        {"name": "Multivitamin", "cost": 25, "effect": {"health": 3, "nutrition": 5}, "duration": 4, "risk": 0},
    ],
    "gray_area": [
        {"name": "TRT (Prescription)", "cost": 200, "effect": {"strength": 5, "cardio": 5},
         "duration": 6, "risk": 15, "suspicious": True},
        {"name": "SARMs", "cost": 300, "effect": {"strength": 8, "speed": 5},
         "duration": 6, "risk": 25, "suspicious": True},
        {"name": "Diuretics", "cost": 150, "effect": {"weight_cut_health": 20},
         "duration": 2, "risk": 20, "suspicious": True},
    ],
    "illegal": [
        {"name": "Anabolic Steroids", "cost": 500,
         "effect": {"strength": 12, "ko_power": 10, "cardio": 5}, "duration": 8, "risk": 50, "suspicious": True},
        {"name": "EPO", "cost": 600, "effect": {"cardio": 15, "speed": 5},
         "duration": 8, "risk": 45, "suspicious": True},
        {"name": "HGH", "cost": 800, "effect": {"strength": 10, "durability": 10, "speed": 5},
         "duration": 8, "risk": 55, "suspicious": True},
        {"name": "Peptides", "cost": 400, "effect": {"health": 10, "recovery": 10},
         "duration": 6, "risk": 35, "suspicious": True},
    ],
}

SOCIAL_ACTIONS = {
    # key: (label, energy_cost, cooldown_weeks)
    "socialize": ("Socialize (friends/family)", 10, 3),
    "media": ("Media Appearance (money + fame)", 15, 2),
    "sidejob": ("Side Job (earn cash)", 20, 4),
    "hobby": ("Hobby (relax)", 5, 2),
    "sponsor": ("Sponsor Obligation", 25, 3),
    "date": ("Date Night", 10, 3),
}
