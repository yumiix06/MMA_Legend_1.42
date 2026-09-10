"""FighterPool: large amateur + pro roster, UFC rankings, weekly AI careers."""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Optional


from . import constants as C
from . import data
from .models import Fighter


_FIRST = [
    "James","John","Alex","Marco","Ivan","Yuri","Omar","Luis","Carlos","Diego",
    "Mateo","Noah","Liam","Ethan","Ryan","Sean","Connor","Patrick","Andre","Pierre",
    "Jean","Luca","Matteo","Giovanni","Hiro","Kenji","Takeshi","Min","Joon","Dae",
    "Wei","Chen","Kai","Rafael","Thiago","Bruno","Paulo","Miguel","Jorge","Pedro",
    "Ahmed","Youssef","Karim","Nassim","Tariq","Dmitri","Sergei","Pavel","Nikita","Oleg",
    "Adam","Kamil","Piotr","Jakub","Tomas","Marek","Lukas","Jan","Erik","Sven",
    "Oliver","William","George","Harry","Jack","Daniel","Samuel","Nathan","Leo","Max",
    "Enzo","Hugo","Antoine","Gabriel","Nicolas","Victor","Igor","Roman","Anton","Boris",
    "Khalid","Hassan","Amir","Farid","Sami","Rashid","Isa","Arman","Arash","Reza",
    "Santiago","Emiliano","Joao","Felipe","Gustavo","Henrique","Caio","Murilo","Demian","Gilbert",
]
_LAST = [
    "Silva","Santos","Oliveira","Pereira","Almeida","Costa","Ferreira","Souza","Lima","Rocha",
    "Garcia","Martinez","Rodriguez","Hernandez","Lopez","Gonzalez","Perez","Sanchez","Ramirez","Torres",
    "Smith","Johnson","Williams","Brown","Jones","Miller","Davis","Wilson","Anderson","Thomas",
    "Murphy","Kelly","Walsh","OBrien","Byrne","Ryan","Quinn","Doyle","Kennedy","Gallagher",
    "Ivanov","Petrov","Sokolov","Popov","Volkov","Morozov","Novikov","Fedorov","Mikhailov","Orlov",
    "Kim","Park","Lee","Choi","Jung","Han","Kang","Cho","Yoon","Shin",
    "Tanaka","Sato","Suzuki","Takahashi","Watanabe","Ito","Yamamoto","Nakamura","Kobayashi","Kato",
    "Wang","Li","Zhang","Liu","Chen","Yang","Huang","Zhao","Wu","Zhou",
    "Muller","Schmidt","Fischer","Weber","Wagner","Becker","Hoffmann","Schafer","Koch","Bauer",
    "Dubois","Lefevre","Moreau","Laurent","Simon","Michel","Garcia","Bernard","Petit","Robert",
    "Nowak","Kowalski","Wisniewski","Wojcik","Kaminski","Lewandowski","Zielinski","Szymanski","Wozniak","Dabrowski",
    "Andersson","Johansson","Karlsson","Nilsson","Eriksson","Larsson","Olsson","Persson","Svensson","Gustafsson",
    "Rossi","Russo","Ferrari","Esposito","Bianchi","Romano","Colombo","Ricci","Marino","Greco",
    "Adebayo","Okoye","Mensah","Diallo","Traore","Kamara","Ndiaye","Bello","Okafor","Abebe",
]


_FIRST += [
    "Arnar","Bjorn","Einar","Hrafn","Kristjan","Nikolai","Stoyan","Veselin","Dimitar","Kaloyan",
    "Gheorghe","Vasile","Mihai","Cristian","Ionut","Laszlo","Zoltan","Gabor","Attila","Balazs",
    "Nikos","Dimitris","Kostas","Yannis","Stefanos","Tiago","Rui","Nuno","Goncalo","Vitor",
    "Lukas","Stefan","Matthias","Andreas","Florian","Tomasz","Wojciech","Bartosz","Filip","Jakub",
    "Luka","Marko","Stefan","Nemanja","Aleksandar","Giorgi","Levan","Irakli","Tigran","Arman",
    "Sergio","Alvaro","Ricardo","Eduardo","Manuel","Francisco","Pablo","Hector","Raul","Ivan",
    "Oskars","Rihards","Mairis","Edgars","Arturs","Aivaras","Mantas","Tadas","Deividas","Karolis",
    "Emre","Can","Burak","Yusuf","Cem","Farhad","Javad","Saeed","Navid","Pouya",
    "Kwame","Kofi","Ibrahim","Moussa","Abdoulaye","Chinedu","Emeka","Tunde","Sibusiso","Thabo",
    "Mateo","Tomas","Joaquin","Agustin","Nicolas","Facundo","Lautaro","Bautista","Thiago","Gael",
]
_LAST += [
    "Gudmundsson","Sigurdsson","Benediktsson","Magnusson","Kristjansson","Ivanov","Petrov","Dimitrov","Nikolov","Georgiev",
    "Popescu","Ionescu","Stanescu","Dumitru","Radu","Nagy","Toth","Kovacs","Szabo","Horvath",
    "Papadopoulos","Nikolaidis","Georgiou","Dimitriou","Ioannou","Silva","Fernandes","Costa","Pereira","Oliveira",
    "Gruber","Huber","Wagner","Steiner","Lehner","Novak","Horvat","Kovac","Jovanovic","Petrovic",
    "Beridze","Kvaratskhelia","Maisuradze","Sargsyan","Hakobyan","Petrosyan","Grigoryan","Mkrtchyan","Vardanyan","Karapetyan",
    "Almeida","Carvalho","Mendes","Ribeiro","Gomes","Nunes","Teixeira","Moreira","Pinto","Rocha",
    "Bergmann","Fuchs","Bauer","Moser","Eder","Nowak","Kowalski","Wisniewski","Kaminski","Zielinski",
    "Yilmaz","Kaya","Demir","Sahin","Celik","Mohammadi","Hosseini","Ahmadi","Karimi","Rahimi",
    "Mensah","Owusu","Boateng","Traore","Diallo","Okeke","Okafor","Adeyemi","Ndlovu","Dlamini",
    "Romero","Suarez","Vargas","Castillo","Navarro","Reyes","Aguilar","Molina","Castro","Ortiz",
]

_STYLES = ["Boxing", "Wrestling", "BJJ", "Muay Thai", "Combat Sambo", "Judo", "Kickboxing", "Taekwondo", "Balanced"]
_TEAMS = [
    "Team Alpha", "Legion MMA", "Dagestan Elite", "Team Europe", "Free Agent",
    "Alliance MMA", "City Gym", "National Centre", "Tiger Muay Thai", "AKA",
]

# Names are generated from nationality-linked pools first, then fall back to
# the large global catalog. This keeps a Bulgarian roster Bulgarian-looking
# without pretending every culture has only one naming convention.
_NAME_GROUPS = {
    "bulgarian": (("Georgi","Dimitar","Kaloyan","Stoyan","Nikolay","Yordan","Bozhidar","Radoslav"),
                  ("Ivanov","Petrov","Dimitrov","Nikolov","Georgiev","Stoyanov","Kolev","Vasilev")),
    "balkan": (("Luka","Marko","Nemanja","Aleksandar","Nikola","Stefan","Filip","Dario"),
               ("Jovanovic","Petrovic","Nikolic","Markovic","Kovacevic","Horvat","Kovacic","Stojanovic")),
    "romanian": (("Andrei","Mihai","Vlad","Cristian","Ionut","Radu","Sorin","Alexandru"),
                 ("Popescu","Ionescu","Dumitru","Stanescu","Radu","Marinescu","Stoica","Munteanu")),
    "greek": (("Nikos","Dimitris","Kostas","Yannis","Stefanos","Giorgos","Andreas","Manolis"),
              ("Papadopoulos","Nikolaidis","Georgiou","Dimitriou","Ioannou","Pappas","Vlachos","Kostas")),
    "slavic": (("Dmitri","Sergei","Pavel","Nikita","Oleg","Mikhail","Andrei","Viktor"),
               ("Volkov","Sokolov","Morozov","Fedorov","Orlov","Kuznetsov","Smirnov","Pavlov")),
    "polish": (("Kamil","Piotr","Jakub","Tomasz","Marek","Wojciech","Bartosz","Mateusz"),
               ("Nowak","Kowalski","Wisniewski","Wojcik","Kaminski","Lewandowski","Zielinski","Dabrowski")),
    "caucasus": (("Giorgi","Levan","Irakli","Tigran","Arman","Narek","Davit","Vazgen"),
                 ("Beridze","Maisuradze","Sargsyan","Hakobyan","Petrosyan","Grigoryan","Vardanyan","Karapetyan")),
    "central_asia": (("Bekzat","Alisher","Timur","Azamat","Daniyar","Rustam","Bakhodir","Nursultan"),
                     ("Akhmedov","Karimov","Tursunov","Yuldashev","Nurgaliyev","Sadykov","Bekov","Ismailov")),
    "iranian": (("Reza","Farhad","Javad","Saeed","Navid","Pouya","Amir","Arash"),
                ("Mohammadi","Hosseini","Ahmadi","Karimi","Rahimi","Jafari","Kazemi","Rostami")),
    "turkish": (("Emre","Can","Burak","Yusuf","Cem","Kerem","Mert","Ozan"),
                ("Yilmaz","Kaya","Demir","Sahin","Celik","Aydin","Arslan","Koc")),
    "arabic": (("Ahmed","Youssef","Karim","Nassim","Tariq","Khalid","Hassan","Rashid"),
               ("Mansour","Haddad","Nasser","Saleh","Khalil","Hamdan","Farouk","Rahman")),
    "brazilian": (("Rafael","Thiago","Bruno","Paulo","Joao","Felipe","Caio","Murilo"),
                  ("Silva","Santos","Oliveira","Pereira","Almeida","Costa","Ferreira","Souza")),
    "hispanic": (("Santiago","Mateo","Diego","Carlos","Miguel","Jorge","Emiliano","Lautaro"),
                 ("Garcia","Martinez","Rodriguez","Hernandez","Lopez","Gonzalez","Ramirez","Torres")),
    "anglo": (("James","Liam","Ethan","Ryan","Sean","Connor","Daniel","Nathan"),
              ("Smith","Johnson","Williams","Brown","Miller","Davis","Wilson","Anderson")),
    "french": (("Pierre","Jean","Antoine","Gabriel","Nicolas","Hugo","Bastien","Remy"),
               ("Dubois","Lefevre","Moreau","Laurent","Bernard","Petit","Robert","Girard")),
    "germanic": (("Lukas","Stefan","Matthias","Andreas","Florian","Erik","Jonas","Felix"),
                 ("Muller","Schmidt","Fischer","Weber","Wagner","Becker","Hoffmann","Bauer")),
    "italian": (("Luca","Matteo","Giovanni","Marco","Enzo","Alessio","Davide","Simone"),
                ("Rossi","Russo","Ferrari","Esposito","Bianchi","Romano","Ricci","Greco")),
    "nordic": (("Erik","Sven","Bjorn","Arnar","Einar","Hrafn","Oskar","Mikkel"),
               ("Andersson","Johansson","Karlsson","Eriksson","Larsson","Gustafsson","Sigurdsson","Magnusson")),
    "japanese": (("Hiro","Kenji","Takeshi","Daichi","Riku","Yuto","Kenta","Naoki"),
                 ("Tanaka","Sato","Suzuki","Takahashi","Watanabe","Yamamoto","Nakamura","Kobayashi")),
    "korean": (("Min","Joon","Dae","Hyun","Jiho","Seung","Tae","Dong"),
               ("Kim","Park","Lee","Choi","Jung","Kang","Yoon","Shin")),
    "chinese": (("Wei","Chen","Kai","Jian","Hao","Jun","Lei","Tao"),
                ("Wang","Li","Zhang","Liu","Chen","Yang","Huang","Zhao")),
    "southeast_asia": (("Somchai","Anan","Niran","Arif","Bima","Rizky","Paolo","Miguel"),
                       ("Srisai","Kittisak","Pratama","Saputra","Santoso","Reyes","Santos","Cruz")),
    "african": (("Kwame","Kofi","Ibrahim","Moussa","Chinedu","Emeka","Tunde","Thabo"),
                ("Mensah","Owusu","Traore","Diallo","Okeke","Okafor","Adeyemi","Ndlovu")),
}
_COUNTRY_NAME_GROUP = {
    "Bulgaria":"bulgarian", "Serbia":"balkan", "Croatia":"balkan",
    "Romania":"romanian", "Hungary":"polish", "Greece":"greek",
    "Russia":"slavic", "Ukraine":"slavic", "Belarus":"slavic",
    "Poland":"polish", "Czech Republic":"polish",
    "Georgia":"caucasus", "Armenia":"caucasus",
    "Kazakhstan":"central_asia", "Uzbekistan":"central_asia", "Mongolia":"central_asia",
    "Iran":"iranian", "Turkey":"turkish", "Egypt":"arabic", "Morocco":"arabic",
    "Brazil":"brazilian", "Portugal":"brazilian",
    "Mexico":"hispanic", "Spain":"hispanic", "Cuba":"hispanic", "Colombia":"hispanic",
    "Argentina":"hispanic", "Peru":"hispanic", "Chile":"hispanic", "Venezuela":"hispanic",
    "USA":"anglo", "Canada":"anglo", "UK":"anglo", "Ireland":"anglo",
    "Australia":"anglo", "New Zealand":"anglo",
    "France":"french", "Germany":"germanic", "Austria":"germanic", "Netherlands":"germanic",
    "Italy":"italian", "Sweden":"nordic", "Norway":"nordic", "Denmark":"nordic",
    "Finland":"nordic", "Iceland":"nordic",
    "Japan":"japanese", "South Korea":"korean", "China":"chinese",
    "Thailand":"southeast_asia", "Philippines":"southeast_asia", "Indonesia":"southeast_asia",
    "India":"central_asia", "Nigeria":"african", "Ghana":"african", "Senegal":"african",
    "Cameroon":"african", "South Africa":"african",
}
_PRO_ORGS_SECONDARY = ["PFL", "Bellator", "BRAVE CF", "KSW", "Cage Warriors",
                       "Balkan Combat", "LFA", "Road FC", "ARES FC"]
_EUROPE = {"UK", "Ireland", "France", "Germany", "Netherlands", "Sweden", "Poland",
           "Italy", "Spain", "Ukraine", "Norway", "Czech Republic", "Georgia", "Armenia",
           "Serbia", "Croatia", "Finland", "Denmark", "Iceland", "Bulgaria", "Romania",
           "Hungary", "Greece", "Portugal", "Austria"}


def _ri(a, b):
    """Inclusive random int, safe if a==b."""
    a, b = int(a), int(b)
    if b < a:
        a, b = b, a
    return random.randint(a, b)


def season_week(career_week: int) -> int:
    """Season week 1–52 from absolute career week."""
    return ((max(1, career_week) - 1) % 52) + 1


def career_year(career_week: int) -> int:
    return ((max(1, career_week) - 1) // 52) + 1


class FighterPool:
    def __init__(self, rng=None):
        self.fighters: list[Fighter] = []
        self.rankings: dict[str, list[Fighter]] = defaultdict(list)  # UFC WC only
        self.p4p: list[Fighter] = []
        self.champions: dict[str, Fighter] = {}
        self.news: list[str] = []
        # Fighters who retired and took a role in the sport (coach/manager/promoter)
        self.retired_staff: list = []
        self.next_id = 1000
        self.rng = rng
        self.week = 0  # world clock (tracks with player roughly)
        self.belts: dict = {}  # "Org|WC" -> {"name","fid"}
        self.events: list[dict] = []
        self.event_history: list[dict] = []
        self.title_history: list[dict] = []
        self.hall_of_fame: list[dict] = []
        self.matchup_history: dict[str, dict] = {}
        # Persistent lifetime counts enforce the hard trilogy ceiling even after
        # recent rematch memory is pruned for save/runtime size.
        self.matchup_lifetime: dict[str, int] = {}
        self.next_event_id: int = 1
        # Per-promotion numbered/Fight Night series counters. Optional in v17
        # saves; old worlds derive them lazily from existing cards.
        self.event_counters: dict[str, dict[str, int]] = {}

    # ------------------------------------------------------------------
    def get_by_id(self, fid: Optional[str]) -> Optional[Fighter]:
        """Stable lookup by fid — survives renames, unlike name matching."""
        if not fid:
            return None
        for f in self.fighters:
            if getattr(f, "fid", None) == fid:
                return f
        return None

    def protected_ids(self, player=None) -> set:
        """Fids that must never be dropped by autosave trimming: champions,
        current top-ranked contenders, and the player's rival."""
        ids: set = set()
        for champ in self.champions.values():
            if champ is not None and getattr(champ, "fid", None) and getattr(champ, "is_player", False) is False:
                ids.add(champ.fid)
        for ranked in self.rankings.values():
            for f in ranked[:5]:
                if getattr(f, "fid", None) and not getattr(f, "is_player", False):
                    ids.add(f.fid)
        if player is not None:
            rid = getattr(player, "rival_id", None)
            if rid:
                ids.add(rid)
            # Keep a real division around the player so title boards survive trim.
            org = getattr(player, "organization", None)
            wc = getattr(player, "weight_class", None)
            n = 0
            for f in self.fighters:
                if n >= 10:
                    break
                if getattr(f, "is_player", False):
                    continue
                if org and getattr(f, "organization", None) != org:
                    continue
                if wc and getattr(f, "weight_class", None) != wc:
                    continue
                fid = getattr(f, "fid", None)
                if fid:
                    ids.add(fid)
                    n += 1
        for info in (getattr(self, "belts", None) or {}).values():
            if isinstance(info, dict) and info.get("fid"):
                ids.add(info["fid"])
        return ids

    # ------------------------------------------------------------------
    def generate_world(self, n_amateurs: int = 840, n_pros: int = 560) -> None:
        """Build feeder amateurs + pros; concentrate elite in UFC."""
        self.fighters.clear()
        self.retired_staff = list(getattr(self, "retired_staff", None) or [])
        used_names: set[str] = set()
        # Balanced weight classes
        for i in range(n_amateurs):
            wc = C.WEIGHT_CLASSES[i % len(C.WEIGHT_CLASSES)]
            self.fighters.append(self._make_npc(used_names, wc, pro=False))
        for i in range(n_pros):
            wc = C.WEIGHT_CLASSES[i % len(C.WEIGHT_CLASSES)]
            self.fighters.append(self._make_npc(used_names, wc, pro=True))
        self._assign_ufc_elite()
        self._balance_initial_orgs()
        self.update_rankings()
        from . import promotion_events
        promotion_events.maintain(self)

    def seed_missing(self, n_amateurs: int = 840, n_pros: int = 560) -> None:
        """Add NPCs until the world is full without deleting saved fids."""
        used = {f.name for f in self.fighters}
        n_am = sum(1 for f in self.fighters if not getattr(f, "pro_debut", False))
        n_pr = sum(1 for f in self.fighters if getattr(f, "pro_debut", False))
        while n_am < n_amateurs:
            wc = C.WEIGHT_CLASSES[n_am % len(C.WEIGHT_CLASSES)]
            self.fighters.append(self._make_npc(used, wc, pro=False))
            n_am += 1
        while n_pr < n_pros:
            wc = C.WEIGHT_CLASSES[n_pr % len(C.WEIGHT_CLASSES)]
            self.fighters.append(self._make_npc(used, wc, pro=True))
            n_pr += 1
        self.update_rankings()

    def generate_fighters(self, count: int = 80) -> None:
        """Back-compat entry used by app — prefer full world."""
        if count >= 200:
            self.generate_world(400, 250)
        else:
            self.generate_world(max(count, 100), max(count // 2, 80))

    def _unique_name(self, used: set[str], country: str = "") -> tuple:
        # Prefer original opponent templates once, then compose unique names
        opp_meta = None
        if data.OPPONENTS:
            unused = [m for m in data.OPPONENTS
                      if ("%s %s" % (m.get("firstName"), m.get("lastName"))) not in used
                      and (not country or m.get("country") == country)]
            if unused and random.random() < 0.35:
                opp_meta = random.choice(unused)
                name = "%s %s" % (opp_meta.get("firstName"), opp_meta.get("lastName"))
                return name, opp_meta
        group = _NAME_GROUPS.get(_COUNTRY_NAME_GROUP.get(country, ""))
        for _ in range(400):
            if group:
                name = "%s %s" % (random.choice(group[0]), random.choice(group[1]))
            else:
                name = "%s %s" % (random.choice(_FIRST), random.choice(_LAST))
            if name not in used:
                return name, None
        # Long careers can exhaust an eight-by-eight regional combination
        # pool. Keep the nationality-linked identity with a middle initial
        # instead of degrading late-generation athletes to "Fighter 2451".
        if group:
            for first in group[0]:
                for initial in "ABCDEFGH":
                    for last in group[1]:
                        name = "%s %s. %s" % (first, initial, last)
                        if name not in used:
                            return name, None
        name = "Fighter %s" % self.next_id
        self.next_id += 1
        return name, None

    def _make_npc(self, used: set[str], wc: str, pro: bool) -> Fighter:
        country_data = random.choice(data.COUNTRIES) if data.COUNTRIES else {"name": "USA", "flag": "🇺🇸", "bonus": {}}
        name, meta = self._unique_name(used, country_data.get("name", ""))
        used.add(name)
        if meta and meta.get("country"):
            cd = data.country_by_name(meta["country"])
            if cd:
                country_data = cd
        style = (meta or {}).get("style") or random.choice(_STYLES)
        team = (meta or {}).get("team") or random.choice(_TEAMS)
        f = Fighter.new_npc(name, country_data, style=style, team=team, rng=self.rng)
        f.fid = "npc_%s" % self.next_id
        self.next_id += 1
        low, high = C.WEIGHT_RANGES_KG.get(wc, (60, 80))
        f.weight = _ri(low, high)
        f.weight_class = wc
        f.natural_weight_class = wc
        f.fight_weight_class = wc
        # Scale weight and walking weight are different things. Most fighters
        # live a few percent above the number they make on the scale.
        _walk_mult = random.uniform(1.02, 1.06) if wc != "Heavyweight" else random.uniform(1.01, 1.04)
        f.natural_weight = min(128.0, float(f.weight) * _walk_mult)
        f.walking_weight = max(float(f.weight), f.natural_weight + random.uniform(-0.5, 0.8))
        f.age = _ri(18, 33 if pro else 27)

        if pro:
            self._seed_pro_career(f)
        else:
            self._seed_amateur_career(f)

        all_techs = [t["name"] for t in data.TECHNIQUES_DB] or ["Jab"]
        n_tech = min(len(all_techs), random.randint(2, 6 if pro else 4))
        for tech in random.sample(all_techs, n_tech):
            f.technique_levels[tech] = random.randint(1, 4 if pro else 2)
            f.techniques.append(tech)

        archetype = data.archetype_by_name((meta or {}).get("archetype"))
        _apply_archetype(f, archetype)
        try:
            from . import nicknames
            nicknames.assign_npc(f, self)
        except Exception:
            pass
        try:
            from . import living_careers
            living_careers.ensure(f)
            living_careers.update_goal(f, self, self.week)
        except Exception:
            pass
        return f

    def _seed_amateur_career(self, f: Fighter) -> None:
        wins = _ri(0, 13)
        losses = _ri(0, max(0, wins // 2))
        style_sport = {
            "BJJ": "BJJ / No-Gi", "Boxing": "Boxing", "Kickboxing": "Kickboxing",
            "Muay Thai": "Kickboxing", "Taekwondo": "Taekwondo", "Wrestling": "Wrestling", "Judo": "Judo",
            "Combat Sambo": "Combat Sambo",
        }.get(getattr(f, "style", ""), "MMA")
        sport = style_sport if style_sport != "MMA" and random.random() < 0.58 else "MMA"
        f.active_amateur_sport = sport
        f.story_flags = dict(getattr(f, "story_flags", None) or {})
        f.story_flags["compete_in"] = sport
        # A substantial minority of specialists build a lifetime in their own
        # sport. Others may cross over after a real amateur base, preserving a
        # healthy MMA prospect pipeline across a twenty-year career.
        f.story_flags["mma_transition"] = bool(sport == "MMA" or random.random() < 0.55)
        f.amateur_record = [wins, losses, _ri(0, 1)] if sport == "MMA" else [0, 0, 0]
        from . import amateur_sports as _sports
        _sports.ensure(f)
        if sport != "MMA":
            key = _sports.key_for(sport)
            f.sport_records[key] = [wins, losses, _ri(0, 1)]
            f.sport_experience[key] = wins * 8 + losses * 3
        f.pro_record = [0, 0, 0]
        f.pro_debut = False
        f.promotion_tier = 0 if wins < 5 else (1 if wins < 10 else 2)
        f.organization = None
        f.reputation = wins * 2 + losses
        f.fame = max(0, wins - 2)
        # Skill band for amateurs
        target = 28 + wins * 1.8 + random.uniform(-4, 6)
        self._set_skills_toward(f, target, spread=10)

    def _seed_pro_career(self, f: Fighter) -> None:
        # Quality tiers: gate / solid / contender
        roll = random.random()
        if roll < 0.45:
            wins = _ri(2, 9)
            losses = _ri(1, 5)
            target = 38 + wins * 1.2
            org = random.choice(_PRO_ORGS_SECONDARY)
            tier = 4
        elif roll < 0.80:
            wins = _ri(8, 17)
            losses = _ri(1, 6)
            target = 48 + wins * 0.9
            org = random.choice(["Bellator", "PFL", "BRAVE CF", "KSW", "UFC"])
            tier = 8 if org == "UFC" else 6
        else:
            wins = _ri(12, 27)
            losses = _ri(0, 4)
            target = 58 + wins * 0.7
            org = "UFC"
            tier = 11
        f.pro_debut = True
        f.amateur_record = [_ri(3, 11), _ri(0, 3), 0]
        f.pro_record = [wins, losses, _ri(0, 1)]
        f.organization = org
        f.promotion_tier = tier
        try:
            from . import identity as _id
            f.room = _id.band_for(org, "regional")
        except Exception:
            f.room = "regional"
        f.reputation = wins * 4
        f.fame = wins * 3
        self._set_skills_toward(f, target, spread=8)

    def _set_skills_toward(self, f: Fighter, target: float, spread: float = 8) -> None:
        from .physiology import target_stat_for_class, clamp_stat
        for s in C.SKILLS:
            val = target_stat_for_class(f.weight_class, s, target) + random.uniform(-spread, spread)
            setattr(f, s, int(max(12, clamp_stat(f, s, round(val)))))

    def _assign_ufc_elite(self) -> None:
        """Ensure each WC has a strong UFC ranked core."""
        pros = [f for f in self.fighters if f.pro_debut and f.active]
        by_wc: dict[str, list[Fighter]] = defaultdict(list)
        for f in pros:
            by_wc[f.weight_class].append(f)
        for wc, roster in by_wc.items():
            roster.sort(key=self._power, reverse=True)
            # Top ~15 in division lean UFC with real records
            for i, f in enumerate(roster[:15]):
                f.organization = "UFC"
                f.promotion_tier = max(f.promotion_tier, 10)
                # Guarantee non-tomato records for ranked
                if f.pro_record[0] < 8:
                    f.pro_record[0] = _ri(8, 21)
                if f.pro_record[1] > f.pro_record[0] // 2:
                    f.pro_record[1] = _ri(0, max(0, f.pro_record[0] // 3))
                boost = 8 - i * 0.4
                from .physiology import gain_stat
                for s in C.SKILLS:
                    gain_stat(f, s, int(boost))
            # Champ = best
            if roster:
                champ = roster[0]
                champ.pro_record[0] = max(champ.pro_record[0], 15)
                champ.fame = max(champ.fame, 60)

    def _balance_initial_orgs(self) -> None:
        """Guarantee viable opening divisions without inventing extra bouts.

        Random organization seeding could leave a regional weight class with
        only two fighters. Those two then fought each other repeatedly before
        normal career movement had time to repair the division.
        """
        from . import orgs as _orgs
        pros = [f for f in self.fighters if f.active and f.pro_debut]
        counts = defaultdict(int)
        for f in pros:
            counts[(f.organization, f.weight_class)] += 1

        def floor(org: str) -> int:
            return 15 if org == "UFC" else 6 if org in ("PFL", "Bellator") else 4

        for target in _orgs.ORGS:
            for wc in C.WEIGHT_CLASSES:
                while counts[(target, wc)] < floor(target):
                    donors = [f for f in pros if f.weight_class == wc
                              and f.organization != target
                              and counts[(f.organization, wc)] > floor(f.organization)]
                    if not donors:
                        break
                    # Move the least established surplus fighter; seeded UFC
                    # contenders and champions therefore remain in place.
                    fighter = min(donors, key=self._power)
                    old = fighter.organization
                    fighter.organization = target
                    fighter.promotion_tier = int(_orgs.ORGS[target]["tier"])
                    try:
                        from . import identity as _id
                        fighter.room = _id.band_for(target, "regional")
                    except Exception:
                        fighter.room = "regional"
                    counts[(old, wc)] -= 1
                    counts[(target, wc)] += 1

    @staticmethod
    def _power(f: Fighter) -> float:
        try:
            vec = f.rating_vector(); skill = (sum(vec)/len(vec)) if vec else 40.0
        except Exception:
            skill = 40.0
        rec = f.pro_record if f.pro_debut else f.amateur_record
        return skill + rec[0] * 1.5 - rec[1] * 1.2 + f.fame * 0.05

    # ------------------------------------------------------------------
    def _rank_score(self, f: Fighter) -> float:
        """Promotion ranking score driven by résumé, not hidden ratings.

        1.23 let raw skill/fame dominate this board.  A 0-2 prospect from the
        supplied playtest could therefore sit #1 above winning fighters, and
        story/title logic trusted that rank.  Skill is now only a small
        tiebreaker; professional results, recent form and activity do the work.
        """
        idle = max(0, int(getattr(f, "idle_weeks", 0) or 0))
        rec = f.pro_record if f.pro_debut else f.amateur_record
        w = int((rec or [0, 0, 0])[0] or 0)
        l = int((rec or [0, 0, 0])[1] or 0)
        d = int((rec or [0, 0, 0])[2] or 0)
        bouts = max(1, w + l + d)
        win_rate = w / bouts

        recent = list(getattr(f, "recent_results", None) or [])[-5:]
        recent_score = 0.0
        streak = 0
        for x in recent:
            sx = str(x).upper()
            recent_score += 2.0 if sx.startswith("W") else (-1.8 if sx.startswith("L") else 0.2)
        for x in reversed(recent):
            sx = str(x).upper()
            if sx.startswith("W"):
                streak += 1
            elif sx.startswith("L"):
                streak -= 1
            else:
                break

        # Actual results are the large terms.  Fame and underlying ability may
        # break close ties, but cannot manufacture a contender résumé.
        try:
            vec = f.rating_vector()
            skill = (sum(vec) / len(vec)) if vec else 40.0
        except Exception:
            skill = 40.0
        fame = max(0, int(getattr(f, "fame", 0) or 0))
        activity_penalty = min(12.0, idle * 0.12)
        return (
            w * 6.0 - l * 4.0 + d * 0.5
            + win_rate * 6.0
            + recent_score
            + streak * 1.2
            + skill * 0.08
            + min(4.0, fame * 0.015)
            - activity_penalty
        )

    def update_rankings(self) -> None:
        """UFC divisions: champion is C (not #1). Then ranked 1-15. P4P is separate."""
        self.rankings = defaultdict(list)
        ufc = [
            f for f in self.fighters
            if f.active and f.pro_debut and (f.organization or "") == "UFC"
        ]
        pl = getattr(self, "_player", None)
        if pl and pl.pro_debut and (pl.organization or "") == "UFC" and pl not in ufc:
            ufc.append(pl)

        def _ufc_bouts(f):
            from . import identity as _identity
            return len(_identity.promotion_history(f, "UFC"))

        # Apply the player's minimum-resume gate consistently to divisional
        # and pound-for-pound boards.  The junior patch filtered only the
        # first board, so an unranked debutant could still appear in P4P.
        ranked_ufc = [f for f in ufc if f is not pl or _ufc_bouts(f) >= 3]
        by_wc = defaultdict(list)
        for f in ranked_ufc:
            # A one-fight UFC signee is on the roster, not in the top 15.
            by_wc[f.weight_class].append(f)
        new_champs = {}
        old = getattr(self, "champions", None) or {}
        for wc, roster in by_wc.items():
            roster.sort(key=self._rank_score, reverse=True)
            champ = self.belt_holder("UFC", wc)
            if champ not in roster:
                champ = old.get(wc)
            if champ not in roster:
                champ = roster[0] if roster else None
            new_champs[wc] = champ
            numbered = [f for f in roster if f is not champ][:15]
            self.rankings[wc] = numbered
        self.champions = new_champs
        self.p4p = sorted(ranked_ufc, key=self._rank_score, reverse=True)[:15]

        # Per-promotion boards. A Balkan 4-0 is #something at home, not UFC #4.
        from . import identity as _id
        self.org_rankings = defaultdict(lambda: defaultdict(list))
        self.org_champs = {}
        everyone = list(self.fighters)
        if pl is not None and pl not in everyone:
            everyone.append(pl)
        buckets = defaultdict(lambda: defaultdict(list))
        if pl is not None:
            pflags = getattr(pl, "story_flags", None)
            if isinstance(pflags, dict):
                pflags["org_rank"] = None
                # Always rebuild UFC rank. Otherwise a rank from an old save or
                # previous refresh can survive even when this pass excludes a
                # new signee for having fewer than three UFC bouts.
                pflags["ufc_rank"] = None
                pflags["org_board"] = None
        for f in everyone:
            if not getattr(f, "active", True) or not getattr(f, "pro_debut", False):
                continue
            org = _id.canonical_org(f)
            if not org:
                continue
            if f is pl and org == "UFC" and _ufc_bouts(f) < 3:
                continue
            buckets[org][getattr(f, "weight_class", "") or "Lightweight"].append(f)
        # Build full boards first so belt repair can preserve a legitimate
        # champion even when that fighter is no longer the score leader.
        full_boards = defaultdict(lambda: defaultdict(list))
        for org, by_wc in buckets.items():
            for wc, roster in by_wc.items():
                roster.sort(key=self._rank_score, reverse=True)
                full_boards[org][wc] = roster
        self.org_rankings = full_boards
        self._sync_belts(pl)

        numbered_boards = defaultdict(lambda: defaultdict(list))
        for org, by_wc in full_boards.items():
            for wc, roster in by_wc.items():
                champ = self.belt_holder(org, wc)
                if champ is not None:
                    self.org_champs[(org, wc)] = champ
                numbered = [f for f in roster if f is not champ][:15]
                numbered_boards[org][wc] = numbered
                for i, f in enumerate(numbered, start=1):
                    flags = getattr(f, "story_flags", None)
                    if not isinstance(flags, dict):
                        f.story_flags = {}
                        flags = f.story_flags
                    flags["org_rank"] = i
                    flags["org_board"] = org
                    if org == "UFC":
                        flags["ufc_rank"] = i
        self.org_rankings = numbered_boards
        self.champions = {
            wc: holder for wc in C.WEIGHT_CLASSES
            if (holder := self.belt_holder("UFC", wc)) is not None
        }

    def simulate_week(self) -> None:
        self.week += 1
        self._advance_npcs()
        if self.week % 8 == 0:
            self._intake_new_blood()
        try:
            from . import ai
            extra = ai.tick_npcs(self, limit=90)
            extra += ai.tick_promos(self)
            try:
                from . import living_careers
                extra += living_careers.tick_world(self)
            except Exception:
                pass
            for line in extra:
                self.news.append(line)
            if len(self.news) > 16:
                self.news = self.news[-16:]
        except Exception:
            pass
        self._climb_npcs()
        from . import promotion_events
        promotion_events.maintain(self)
        # Withdrawal/replacement logic used to exist as a dead helper. Run it
        # before event resolution so scheduled NPC cards can actually react to
        # injuries and short-notice opportunities without stalling divisions.
        self.news.extend(promotion_events.process_world_withdrawals(self))
        self.news.extend(promotion_events.resolve_due(self))
        pl = getattr(self, "_player", None)
        if pl is not None:
            note = promotion_events.process_player_withdrawal(self, pl)
            if note:
                self.news.append(note)
        self._maybe_promote_amateurs()
        self._run_amateur_championships()
        self.update_rankings()
        promotion_events.repair_titles(self)
        self.news = self.news[-16:]

    def _advance_npcs(self) -> None:
        for f in self.fighters:
            if not f.active:
                continue
            f.idle_weeks = int(getattr(f, "idle_weeks", 0) or 0) + 1
            f.age_weeks += 1
            if f.age_weeks >= 52:
                f.age_weeks = 0
                f.age += 1
                if f.age >= 30:
                    f.speed = max(10, f.speed - (1 if f.age < 35 else 2))
                    f.cardio = max(10, f.cardio - 1)
                    if f.age >= 35:
                        f.durability = max(10, f.durability - 1)
                f.fight_iq = min(100, f.fight_iq + (1 if f.age < 40 else 0))
                if f.age >= 40:
                    f.retired = True
                    f.active = False
            # --- career arc: improve young, peak, then decline -------------
            # A 21-year-old prospect should be visibly getting better and a
            # 36-year-old visibly getting worse, rather than every NPC in the
            # world drifting randomly around their starting numbers.
            if random.random() < 0.14:
                s = random.choice(C.SKILLS)
                if f.age <= 24:
                    delta = random.choice([0, 1, 1, 2])
                elif f.age <= 30:
                    delta = random.choice([-1, 0, 1, 1])
                elif f.age <= 34:
                    delta = random.choice([-1, 0, 0, 1])
                else:
                    delta = random.choice([-2, -1, -1, 0])
                work = int(getattr(f, "work_ethic", 50) or 50)
                if work >= 70 and delta < 0 and random.random() < 0.4:
                    delta += 1
                from .physiology import clamp_stat
                setattr(f, s, max(12, clamp_stat(f, s, getattr(f, s) + delta)))

            # --- injuries and layoffs --------------------------------------
            if getattr(f, "npc_injury_weeks", 0) > 0:
                f.npc_injury_weeks -= 1
            elif random.random() < 0.004:
                f.npc_injury_weeks = random.randint(4, 20)
                if random.random() < 0.10:
                    self.news.append("%s is out with an injury." % f.name)

            # --- retirement, and what they do next -------------------------
            retire = False
            if f.age >= 40:
                retire = True
            elif f.age >= 34 and int(getattr(f, "idle_weeks", 0) or 0) > 90:
                retire = True
            elif f.age >= 36 and random.random() < 0.004:
                retire = True
            else:
                recent = list(getattr(f, "recent_results", None) or [])[-5:]
                if len(recent) >= 5 and all(str(x).upper().startswith("L") for x in recent):
                    if random.random() < 0.03:
                        retire = True
            if retire:
                f.retired = True
                f.active = False
                wins = int((getattr(f, "pro_record", [0, 0, 0]) or [0, 0, 0])[0])
                if wins < 8 and random.random() < 0.55:
                    f.role = "gone"
                else:
                    self._retire_into_role(f)


    def _intake_new_blood(self) -> None:
        """New kids walk into gyms every year.

        Without this the amateur pool drains as fighters turn pro or retire,
        and an amateur player eventually has nobody left to fight.
        """
        amateurs = sum(1 for f in self.fighters if f.active and not f.pro_debut)
        # Preserve the expanded seven-sport ecosystem instead of letting the
        # 840-fighter starting pool decay to the old smaller-world target.
        target = 840
        if amateurs >= target:
            return
        used = {f.name for f in self.fighters}
        for _ in range(min(22, target - amateurs)):
            wc = random.choice(C.WEIGHT_CLASSES)
            kid = self._make_npc(used, wc, pro=False)
            kid.age = random.randint(17, 21)
            kid.amateur_record = [0, 0, 0]
            try:
                from . import amateur_sports as _sports
                _sports.ensure(kid)
                key = _sports.key_for(kid.active_amateur_sport)
                kid.sport_records[key] = [0, 0, 0]
                kid.sport_experience[key] = 0
            except Exception:
                pass
            self.fighters.append(kid)

    def _retire_into_role(self, f) -> None:
        """A retiring fighter does not vanish — they take a role in the sport.

        Uses the shared NPC role map, so the same fighter record becomes a
        coach, manager or promoter rather than being deleted from the world.
        """
        try:
            from . import npc as _npc
        except Exception:
            return
        wins = int((getattr(f, "pro_record", [0, 0, 0]) or [0, 0, 0])[0])
        comp = _npc.competencies(f)
        options = []
        if comp.get("technical", 0) >= 55:
            options += ["coach"] * 3
        if comp.get("negotiation", 0) >= 60 or comp.get("politics", 0) >= 60:
            options += ["manager"] * 2
        if wins >= 12 and comp.get("politics", 0) >= 65:
            options.append("promoter")
        options.append("coach")
        role = random.choice(options)
        f.role = role
        self.retired_staff.append(f)
        try:
            from . import legacy
            inducted = legacy.maybe_induct(self, f)
            if inducted:
                self.news.append("%s is inducted into the Hall of Fame (%s)." % (f.name, inducted.get("tier")))
        except Exception:
            pass
        if wins >= 8 or random.random() < 0.15:
            self.news.append("%s retires and moves into %sing." % (
                f.name, role if role != "manager" else "manage"))

    def _title_log(self, org: str, wc: str, action: str, fighter=None,
                   previous=None, opponent=None) -> None:
        history = list(getattr(self, "title_history", None) or [])

        # Long-career record books must not depend on the capped recent lineage
        # list. Bootstrap a fighter-local lifetime title ledger the first time
        # we touch them, then update it transactionally with every title event.
        if fighter is not None:
            flags = getattr(fighter, "story_flags", None)
            if not isinstance(flags, dict):
                fighter.story_flags = {}
                flags = fighter.story_flags
            stats = flags.get("career_title_stats")
            if not isinstance(stats, dict):
                fid = getattr(fighter, "fid", None)
                prior = [h for h in history if h.get("fighter_id") == fid]
                prior_wins = [h for h in prior if h.get("action") in ("won", "inaugural")]
                prior_defs = [h for h in prior if h.get("action") == "defended"]
                stats = {
                    "title_wins": len(prior_wins),
                    "defenses": len(prior_defs),
                    "ufc_title_wins": sum(h.get("org") == "UFC" for h in prior_wins),
                    "ufc_defenses": sum(h.get("org") == "UFC" for h in prior_defs),
                    "championships": sorted({
                        str(h.get("org") or "") + "|" + str(h.get("weight_class") or "")
                        for h in prior_wins if h.get("org") and h.get("weight_class")
                    }),
                }
            stats = dict(stats)
            if action in ("won", "inaugural"):
                stats["title_wins"] = int(stats.get("title_wins", 0) or 0) + 1
                if org == "UFC":
                    stats["ufc_title_wins"] = int(stats.get("ufc_title_wins", 0) or 0) + 1
                champs = set(stats.get("championships") or [])
                champs.add(str(org) + "|" + str(wc))
                stats["championships"] = sorted(champs)
            elif action == "defended":
                stats["defenses"] = int(stats.get("defenses", 0) or 0) + 1
                if org == "UFC":
                    stats["ufc_defenses"] = int(stats.get("ufc_defenses", 0) or 0) + 1
            flags["career_title_stats"] = stats

        history.append({"week": int(getattr(self, "week", 0) or 0),
                        "org": org, "weight_class": wc, "action": action,
                        "fighter_id": getattr(fighter, "fid", None),
                        "fighter": getattr(fighter, "name", None),
                        "fighter_age": getattr(fighter, "age", None),
                        "fighter_record": list(getattr(fighter, "pro_record", None) or []) if fighter is not None else [],
                        "previous_id": getattr(previous, "fid", None),
                        "previous": getattr(previous, "name", None),
                        "opponent_id": getattr(opponent, "fid", None),
                        "opponent": getattr(opponent, "name", None)})
        # This is now explicitly the recent lineage feed. Lifetime totals live
        # on the fighter and therefore survive this UI/history cap.
        self.title_history = history[-2000:]

    def _sync_belts(self, player=None) -> None:
        """Champion of each named-org class. Persist on pool.belts."""
        from . import identity as _id
        from . import orgs as _orgs
        belts = dict(getattr(self, "belts", None) or {})
        boards = getattr(self, "org_rankings", None) or {}
        living = set()
        for org in _orgs.ORGS:
            by_wc = boards.get(org) if hasattr(boards, "get") else None
            if not by_wc:
                continue
            items = by_wc.items() if hasattr(by_wc, "items") else []
            for wc, roster in items:
                if not roster:
                    continue
                key = _id.belt_key(org, wc)
                living.add(key)
                cur = belts.get(key) if isinstance(belts.get(key), dict) else None
                holder = None
                previous = None
                if cur and cur.get("fid"):
                    holder = self.get_by_id(cur["fid"])
                    if holder is None and player is not None and getattr(player, "fid", None) == cur.get("fid"):
                        holder = player
                    previous = holder
                    if holder is not None:
                        live_org = _id.canonical_org(holder) or getattr(holder, "organization", "")
                        multi_classes = set((getattr(holder, "story_flags", None) or {}).get("double_champ_classes") or [])
                        same_class = getattr(holder, "weight_class", "") == wc or wc in multi_classes or bool(cur.get("multi_division"))
                        if not getattr(holder, "active", True) or not same_class:
                            holder = None
                        elif live_org != org:
                            # Free-agent champ may keep the last strap
                            keep_fa = (
                                player is not None and holder is player
                                and not _id.canonical_org(holder)
                                and not str(getattr(holder, "organization", "") or "").strip()
                            )
                            if not keep_fa:
                                holder = None
                if holder is None:
                    taken = {info.get("fid") for k2, info in belts.items()
                             if k2 != key and isinstance(info, dict) and str(k2).startswith(org + "|")}
                    pick = next((f for f in roster if getattr(f, "fid", None) not in taken
                                 and getattr(f, "weight_class", "") == wc), None)
                    holder = pick or roster[0]
                    belts[key] = {"name": holder.name, "fid": getattr(holder, "fid", None),
                                  "org": org, "wc": wc,
                                  "won_week": int(getattr(self, "week", 0) or 0), "defenses": 0}
                    if previous is not None:
                        self._title_log(org, wc, "vacated", fighter=previous)
                    self._title_log(org, wc, "inaugural", fighter=holder, previous=previous)
                    if previous is not None:
                        old_flags = getattr(previous, "story_flags", None)
                        if isinstance(old_flags, dict) and old_flags.get("org_belt") == org:
                            old_flags["org_belt"] = None
                flags = getattr(holder, "story_flags", None)
                if isinstance(flags, dict):
                    flags["org_belt"] = org
                    flags["org_rank"] = 1
        clean = {}
        for k, v in belts.items():
            if k in living:
                clean[k] = v
                continue
            if player is not None and isinstance(v, dict) and v.get("fid") == getattr(player, "fid", None):
                clean[k] = v
        self.belts = clean
        if player is not None:
            pflags = getattr(player, "story_flags", None)
            if isinstance(pflags, dict):
                mine = [k for k, v in self.belts.items()
                        if isinstance(v, dict) and v.get("fid") == getattr(player, "fid", None)]
                pflags["org_belt"] = mine[0].split("|")[0] if mine else None

    def award_belt(self, org: str, wc: str, winner, reason: str = "title fight", defeated=None) -> None:
        from . import identity as _id
        if not org or not wc or winner is None:
            return
        key = _id.belt_key(org, wc)
        self.belts = dict(getattr(self, "belts", None) or {})
        old = self.belt_holder(org, wc)
        if old is winner:
            return
        if old is not None:
            old_flags = getattr(old, "story_flags", None)
            if isinstance(old_flags, dict) and old_flags.get("org_belt") == org:
                old_flags["org_belt"] = None
        self.belts[key] = {"name": winner.name, "fid": getattr(winner, "fid", None),
                           "org": org, "wc": wc,
                           "won_week": int(getattr(self, "week", 0) or 0), "defenses": 0}
        flags = getattr(winner, "story_flags", None)
        if not isinstance(flags, dict):
            winner.story_flags = {}
            flags = winner.story_flags
        flags["org_belt"] = org
        self._title_log(org, wc, "won", fighter=winner, previous=old or defeated,
                        opponent=defeated or old)
        if org == "UFC":
            self.champions[wc] = winner
        try:
            from . import legacy
            legacy.on_belt_awarded(self, org, wc, winner)
        except Exception:
            pass
        self.news.append("%s is the new %s %s champion." % (winner.name, org, wc))

    def record_title_defense(self, org: str, wc: str, champion, challenger=None) -> None:
        from . import identity as _id
        key = _id.belt_key(org, wc)
        info = (getattr(self, "belts", None) or {}).get(key)
        if not isinstance(info, dict) or info.get("fid") != getattr(champion, "fid", None):
            return
        info["defenses"] = int(info.get("defenses", 0) or 0) + 1
        info["last_defense_week"] = int(getattr(self, "week", 0) or 0)
        self._title_log(org, wc, "defended", fighter=champion, opponent=challenger)
        self.news.append("%s defends the %s %s title." % (champion.name, org, wc))

    def belt_holder(self, org: str, wc: str):
        from . import identity as _id
        info = (getattr(self, "belts", None) or {}).get(_id.belt_key(org, wc))
        if not isinstance(info, dict):
            return None
        fid = info.get("fid")
        player = getattr(self, "_player", None)
        if player is not None and getattr(player, "fid", None) == fid:
            return player
        return self.get_by_id(fid)

    def _climb_npcs(self) -> None:
        """Monthly merit transfers keep every promotion/division populated.

        The old linear ladder moved almost everyone toward Bellator and never
        admitted a new UFC fighter. After twenty years PFL was empty and UFC
        had only 18 active fighters. Floors now create vacancies-driven moves,
        including earned UFC recruitment, without stripping feeder rosters.
        """
        if self.week % 4:
            return
        from . import identity as _id
        from . import orgs as _orgs

        def floor(org: str) -> int:
            return 12 if org == "UFC" else 7 if org in ("PFL", "Bellator") else 5

        roster = [f for f in self.fighters if f.active and f.pro_debut
                  and not getattr(f, "is_player", False) and _id.canonical_org(f)]
        counts = defaultdict(int)
        for f in roster:
            counts[(_id.canonical_org(f), f.weight_class)] += 1
        needs = []
        for org in _orgs.ORGS:
            for wc in C.WEIGHT_CLASSES:
                gap = floor(org) - counts[(org, wc)]
                if gap > 0:
                    needs.append((0 if org == "UFC" else 1, -gap, org, wc))
        needs.sort()
        moved = 0
        for _, _, target, wc in needs:
            if moved >= 5:
                break
            target_tier = int((_orgs.ORGS.get(target) or {}).get("tier", 5))
            candidates = []
            for f in roster:
                cur = _id.canonical_org(f)
                if f.weight_class != wc or cur == target or cur == "UFC":
                    continue
                # Regional champions are exactly the sort of proven talent
                # UFC recruits. Moving one vacates that feeder belt cleanly;
                # ordinary lateral/up-tier balancing still leaves champions.
                if self.belt_holder(cur, wc) is f and target != "UFC":
                    continue
                if counts[(cur, wc)] <= floor(cur):
                    continue
                wins, losses = int(f.pro_record[0]), int(f.pro_record[1])
                cur_tier = int((_orgs.ORGS.get(cur) or {}).get("tier", 4))
                # Same-tier transfers are legitimate roster balancing. The
                # old >= comparison trapped talent in one regional promotion
                # while another could run a division with only two fighters.
                if cur_tier > target_tier and target != "UFC":
                    continue
                if target == "UFC" and (wins < 6 or wins < losses
                                         or int(getattr(f, "current_streak", 0) or 0) < 1):
                    continue
                candidates.append(f)
            if not candidates:
                continue
            try:
                from . import living_careers as _living
                f = max(candidates, key=lambda who: (
                    self._rank_score(who) + _living.transfer_priority(who, target, _id.canonical_org(who), self),
                    int(getattr(who, "current_streak", 0) or 0)))
            except Exception:
                f = max(candidates, key=lambda who: (self._rank_score(who),
                                                     int(getattr(who, "current_streak", 0) or 0)))
            old = _id.canonical_org(f)
            f.organization = target
            f.room = _id.band_for(target, "regional")
            f.promotion_tier = target_tier
            f.idle_weeks = min(int(getattr(f, "idle_weeks", 0) or 0), 8)
            counts[(old, wc)] -= 1
            counts[(target, wc)] += 1
            moved += 1
            try:
                from . import living_careers as _living
                _living.update_goal(f, self, self.week)
                motive = str(getattr(f, "career_goal", "rank_climb") or "rank_climb").replace("_", " ")
            except Exception:
                motive = "career move"
            self.news.append("%s signs with %s after a strong run in %s (%s)." % (f.name, target, old, motive))

        # A hard trilogy ceiling needs real roster churn. First refresh title
        # challenger pools that have been completely exhausted, then resolve
        # ordinary long-idle traps.
        self._refresh_title_challengers(limit=2)
        self._refresh_stale_rosters(limit=3)

    def _refresh_title_challengers(self, limit: int = 2) -> int:
        """Swap in fresh challengers when a champion has completed every trilogy.

        The lifetime trilogy ceiling is a sporting rule, not a reason to freeze
        a championship. Once a healthy champion is overdue and every local
        contender has already met them three times, exchange one saturated
        non-champion with a comparable promotion's fresh fighter. This keeps
        roster sizes stable and preserves promotion identity better than
        generating a disposable opponent.
        """
        if self.week % 4:
            return 0
        from . import identity as _id
        from . import orgs as _orgs
        from .promotion_events import _meeting_count

        open_ids = set()
        for ev in getattr(self, "events", None) or []:
            if ev.get("status") != "scheduled":
                continue
            for bout in ev.get("bouts", []) or []:
                if bout.get("status") == "scheduled":
                    open_ids.update(x for x in (bout.get("red_id"), bout.get("blue_id")) if x)

        active = [f for f in self.fighters if f.active and f.pro_debut
                  and not getattr(f, "is_player", False) and _id.canonical_org(f)]
        swaps = 0
        for key, info in list((getattr(self, "belts", None) or {}).items()):
            if swaps >= max(0, int(limit)) or not isinstance(info, dict):
                break
            org = str(info.get("org") or (str(key).split("|", 1)[0] if "|" in str(key) else ""))
            wc = str(info.get("wc") or (str(key).split("|", 1)[1] if "|" in str(key) else ""))
            champ = self.belt_holder(org, wc)
            if champ is None or not champ.active or getattr(champ, "npc_injury_weeks", 0) or champ.fid in open_ids:
                continue
            last = int(info.get("last_defense_week", info.get("won_week", self.week)) or self.week)
            if self.week - last < 40:
                continue
            peers = [f for f in active if _id.canonical_org(f) == org and f.weight_class == wc
                     and f is not champ and f.fid not in open_ids and not getattr(f, "npc_injury_weeks", 0)]
            if any(_meeting_count(self, champ.fid, f.fid) < 3 for f in peers):
                continue
            if not peers:
                continue

            org_tier = int((_orgs.ORGS.get(org) or {}).get("tier", 5))
            candidates = []
            for f in active:
                other = _id.canonical_org(f)
                if (f is champ or not other or other == org or other == "UFC" and org != "UFC"
                        or f.weight_class != wc or f.fid in open_ids
                        or getattr(f, "npc_injury_weeks", 0)
                        or self.belt_holder(other, wc) is f):
                    continue
                other_tier = int((_orgs.ORGS.get(other) or {}).get("tier", 5))
                if abs(other_tier - org_tier) > 2:
                    continue
                if _meeting_count(self, champ.fid, f.fid) >= 3:
                    continue
                candidates.append(f)
            if not candidates:
                continue

            newcomer = max(candidates, key=lambda f: (
                self._rank_score(f),
                int(getattr(f, "current_streak", 0) or 0),
                -int(getattr(f, "idle_weeks", 0) or 0),
            ))
            old_org = _id.canonical_org(newcomer)
            # Export the least useful saturated local fighter, preferring a
            # healthy non-booked athlete who has already completed the trilogy.
            outbound = min(peers, key=lambda f: (
                self._rank_score(f),
                -int(getattr(f, "idle_weeks", 0) or 0),
            ))
            newcomer.organization, outbound.organization = org, old_org
            newcomer.room = _id.band_for(org, "regional")
            outbound.room = _id.band_for(old_org, "regional")
            newcomer.promotion_tier = int((_orgs.ORGS.get(org) or {}).get("tier", newcomer.promotion_tier))
            outbound.promotion_tier = int((_orgs.ORGS.get(old_org) or {}).get("tier", outbound.promotion_tier))
            newcomer.idle_weeks = min(int(getattr(newcomer, "idle_weeks", 0) or 0), 8)
            outbound.idle_weeks = min(int(getattr(outbound, "idle_weeks", 0) or 0), 12)
            swaps += 1
            self.news.append("%s signs %s as a fresh %s challenger; %s moves to %s." % (
                org, newcomer.name, wc, outbound.name, old_org))
        return swaps

    def _refresh_stale_rosters(self, limit: int = 3) -> int:
        if self.week % 4:
            return 0
        from . import identity as _id
        from . import orgs as _orgs
        from .promotion_events import _pair_key, _meeting_count

        open_ids = set()
        for ev in getattr(self, "events", None) or []:
            if ev.get("status") != "scheduled":
                continue
            for bout in ev.get("bouts", []) or []:
                if bout.get("status") == "scheduled":
                    open_ids.update(x for x in (bout.get("red_id"), bout.get("blue_id")) if x)

        active = [f for f in self.fighters if f.active and f.pro_debut
                  and not getattr(f, "is_player", False) and _id.canonical_org(f)]

        def is_champ(f) -> bool:
            org = _id.canonical_org(f)
            return bool(org and self.belt_holder(org, f.weight_class) is f)

        def roster(org, wc):
            return [f for f in active if _id.canonical_org(f) == org and f.weight_class == wc]

        def has_fresh_peer(f, org):
            for peer in roster(org, f.weight_class):
                if peer is f or is_champ(peer) or peer.fid in open_ids or getattr(peer, "npc_injury_weeks", 0):
                    continue
                count = _meeting_count(self, f.fid, peer.fid)
                if count < 3:
                    return True
            return False

        stuck = sorted((f for f in active
                        if int(getattr(f, "idle_weeks", 0) or 0) >= 80
                        and f.fid not in open_ids and not is_champ(f)
                        and not getattr(f, "npc_injury_weeks", 0)),
                       key=lambda f: int(getattr(f, "idle_weeks", 0) or 0), reverse=True)
        swaps = 0
        used = set()
        for f in stuck:
            if swaps >= max(0, int(limit)) or f.fid in used:
                break
            cur = _id.canonical_org(f)
            if has_fresh_peer(f, cur):
                continue
            cur_tier = int((_orgs.ORGS.get(cur) or {}).get("tier", 5))
            candidates = []
            for g in active:
                other = _id.canonical_org(g)
                if (g is f or g.fid in used or g.fid in open_ids or other == cur or other == "UFC"
                        or cur == "UFC" or g.weight_class != f.weight_class or is_champ(g)
                        or getattr(g, "npc_injury_weeks", 0)):
                    continue
                other_tier = int((_orgs.ORGS.get(other) or {}).get("tier", 5))
                if abs(other_tier - cur_tier) > 2:
                    continue
                # Both athletes need at least one genuinely fresh matchup after
                # the exchange; otherwise the swap merely moves the trap.
                other_peers = [x for x in roster(other, f.weight_class) if x is not g and not is_champ(x)]
                cur_peers = [x for x in roster(cur, f.weight_class) if x is not f and not is_champ(x)]
                fresh_for_f = any(_meeting_count(self, f.fid, x.fid) < 3 for x in other_peers)
                fresh_for_g = any(_meeting_count(self, g.fid, x.fid) < 3 for x in cur_peers)
                if fresh_for_f and fresh_for_g:
                    candidates.append(g)
            if not candidates:
                continue
            g = min(candidates, key=lambda x: (abs(int(getattr(x, "idle_weeks", 0) or 0) - int(getattr(f, "idle_weeks", 0) or 0)),
                                                abs(self._rank_score(x) - self._rank_score(f))))
            other = _id.canonical_org(g)
            f.organization, g.organization = other, cur
            f.room = _id.band_for(other, "regional"); g.room = _id.band_for(cur, "regional")
            f.promotion_tier = int((_orgs.ORGS.get(other) or {}).get("tier", f.promotion_tier))
            g.promotion_tier = int((_orgs.ORGS.get(cur) or {}).get("tier", g.promotion_tier))
            f.idle_weeks = min(int(getattr(f, "idle_weeks", 0) or 0), 12)
            g.idle_weeks = min(int(getattr(g, "idle_weeks", 0) or 0), 12)
            used.update((f.fid, g.fid)); swaps += 1
            self.news.append("%s and %s change promotions as both divisions refresh their matchups." % (f.name, g.name))
        return swaps

    def _simulate_pro_fights(self) -> None:
        """One small card per org slice with an intent tag (1.2)."""
        tags = ("protect_streak", "rematch", "title_eliminator", "prospect_showcase", "short_notice")
        by_org = {}
        for f in self.fighters:
            if not (f.pro_debut and f.active):
                continue
            try:
                from . import identity as _id
                org = _id.canonical_org(f) or ""
            except Exception:
                org = f.organization or ""
            if not org:
                continue
            by_org.setdefault(org, []).append(f)
        made = 0
        orgs = list(by_org.keys())
        random.shuffle(orgs)
        for org in orgs:
            if made >= 4:
                break
            roster = [f for f in by_org[org] if getattr(f, "weight_class", None)]
            if len(roster) < 2:
                continue
            hungry = [f for f in roster if getattr(f, "npc_wants_fight", False)]
            wc = random.choice(list({f.weight_class for f in roster}))
            same = [f for f in roster if f.weight_class == wc]
            if len(same) < 2:
                same = roster
            pool = hungry if len(hungry) >= 2 else same
            if len(pool) < 2:
                pool = roster
            champ = self.belt_holder(org, wc) if hasattr(self, "belt_holder") else None
            if champ is None and org == "UFC":
                champ = self.champions.get(wc)
            board = same
            if hasattr(self, "get_org_top"):
                board = self.get_org_top(org, wc, 8) or same
            f1 = f2 = None
            if champ is not None and champ in same and random.random() < 0.45:
                chall = next((f for f in board if f is not champ and f in same), None)
                if chall is None:
                    chall = next((f for f in same if f is not champ), None)
                if chall is not None:
                    f1, f2 = champ, chall
            if f1 is None:
                f1, f2 = random.sample(pool[:12] if len(pool) > 12 else pool, 2)
            f1.npc_wants_fight = False
            f2.npc_wants_fight = False
            try:
                from . import ai
                tag = ai.promo_intent(org, same, wc, champ)
            except Exception:
                tag = random.choice(tags)
            if champ in (f1, f2):
                tag = "title"
            f1.idle_weeks = 0
            f2.idle_weeks = 0
            winner, loser, draw = self.simulate_ai_fight(f1, f2)
            if champ in (f1, f2) and not draw and loser is champ:
                if org == "UFC":
                    self.champions[wc] = winner
                self.award_belt(org, wc, winner)
                tag = "title"
            if draw:
                f1.pro_record[2] += 1
                f2.pro_record[2] += 1
                self.news.append("%s [%s]: %s vs %s ends a draw (%s)." % (org, tag, f1.name, f2.name, wc))
            else:
                winner.pro_record[0] += 1
                loser.pro_record[1] += 1
                self.news.append("%s [%s]: %s def. %s (%s)." % (org, tag, winner.name, loser.name, wc))
            made += 1
            if len(self.news) > 12:
                self.news.pop(0)

    def _maybe_promote_amateurs(self) -> None:
        """Advance seven amateur ecosystems; only MMA crossovers turn pro."""
        from . import amateur_sports as _sports
        amateurs = [f for f in self.fighters if f.active and not f.pro_debut]
        active_pros = sum(1 for f in self.fighters if f.active and f.pro_debut)
        pro_target = 620
        random.shuffle(amateurs)
        eligible = []
        for f in amateurs:
            _sports.ensure(f)
            sport = f.active_amateur_sport
            key = _sports.key_for(sport)
            if sport != "MMA":
                # Dedicated athletes remain useful, developing opponents even
                # when they never enter an MMA cage.
                if random.random() < 0.065:
                    row = f.sport_records[key]
                    rating = sum(f.rating_vector()) / max(1, len(f.rating_vector()))
                    win = random.random() < max(0.42, min(0.70, 0.52 + (rating - 45) / 180))
                    row[0 if win else 1] += 1
                    f.sport_experience[key] += 8 if win else 3
                    f.idle_weeks = 0
                side_bouts = sum(f.sport_records[key])
                transition = bool((f.story_flags or {}).get("mma_transition", False))
                if transition and f.age >= 20 and side_bouts >= 8 and random.random() < 0.004:
                    f.active_amateur_sport = "MMA"
                    f.story_flags["compete_in"] = "MMA"
                    self.news.append("%s crosses over from %s to amateur MMA." % (f.name, sport))
                continue

            # MMA amateurs need activity before a professional contract. This
            # also lets zero-bout new intake build a résumé instead of freezing.
            if random.random() < 0.075:
                win = random.random() < 0.58
                f.amateur_record[0 if win else 1] += 1
                f.sport_records["mma"] = list(f.amateur_record)
                f.idle_weeks = 0
            wins = f.amateur_record[0]
            bouts = sum(f.amateur_record)
            if wins >= 4 and bouts >= 6 and f.age >= 19:
                eligible.append(f)

        # Replace retirements with qualified prospects. The old 2.5% roll let
        # active pros fall from 560 to 373 over twenty years and eventually
        # reduced UFC to its champions plus only a few challengers.
        slots = min(3, max(0, pro_target - active_pros))
        eligible.sort(key=lambda f: (
            int(f.amateur_record[0]) - int(f.amateur_record[1]),
            int(f.amateur_record[0]),
            int(f.sport_experience.get("mma", 0) or 0),
            sum(f.rating_vector()) / max(1, len(f.rating_vector())),
        ), reverse=True)
        from . import orgs as _orgs
        from . import identity as _id
        pro_counts = defaultdict(int)
        for pro in self.fighters:
            if pro.active and pro.pro_debut and _id.canonical_org(pro):
                pro_counts[(_id.canonical_org(pro), pro.weight_class)] += 1
        entry_orgs = [org for org in _orgs.ORGS if org not in ("UFC", "PFL", "Bellator")]
        for f in eligible[:slots]:
            f.pro_debut = True
            f.pro_record = [0, 0, 0]
            home = _orgs.home_org(getattr(f, "country", "") or "")
            # Prefer a hometown debut, but use legitimate international
            # scouting when that division is full and another regional needs
            # bodies. This keeps every promoter's card ecosystem functional.
            if pro_counts[(home, f.weight_class)] < 5:
                f.organization = home
            else:
                f.organization = min(
                    entry_orgs,
                    key=lambda org: (pro_counts[(org, f.weight_class)],
                                     0 if org == home else 1),
                )
            pro_counts[(f.organization, f.weight_class)] += 1
            f.promotion_tier = int(_orgs.ORGS[f.organization]["tier"])
            f.room = _id.band_for(f.organization, "local")
            from .notoriety import add_fame
            add_fame(f, max(0, 5 - int(getattr(f, "fame", 0) or 0)), "turned professional")
            for s in C.SKILLS:
                from .physiology import gain_stat
                gain_stat(f, s, 2)
            self.news.append(f"{f.name} ({f.country}) has turned professional.")

    def _run_amateur_championships(self) -> None:
        """Resolve NPC national/continental/world/Olympic amateur ecosystems.

        Uses the same v1.30 calendar and continental routing as the player.
        Small-country regional qualifiers are intentionally a player/calendar
        presentation concern; NPC national fields are already country scoped.
        """
        from . import amateur_sports as sports
        from .systems15 import continent as _continent
        sw = season_week(self.week)
        cy = career_year(self.week)
        if sw not in (12, 22, 30, 38, 40):
            return
        level = ("national" if sw in (12, 38) else "continental" if sw == 22
                 else "world" if sw == 30 else "olympic")
        if level == "olympic" and cy % 4:
            return

        athletes = [f for f in self.fighters if f.active and not f.pro_debut]
        for fighter in athletes:
            sports.ensure(fighter)

        def score(f, sport):
            key = sports.key_for(sport)
            pair = sports.SPORT_INFO.get(sport, ("fight_iq", "cardio"))
            return (int(getattr(f, pair[0], 40) or 40)
                    + int(getattr(f, pair[1], 40) or 40)
                    + int(getattr(f, "fight_iq", 40) or 40) * 0.35
                    + int(f.sport_experience.get(key, 0) or 0) * 0.05
                    + random.uniform(-10, 10))

        def podium(field, sport, level_name, label=None):
            if len(field) < 2:
                return
            key = sports.key_for(sport)
            ranked = sorted(field, key=lambda f: score(f, sport), reverse=True)[:3]
            for colour, f in zip(("gold", "silver", "bronze"), ranked):
                f.sport_championships[key][level_name][colour] += 1
                f.sport_medals[key][colour] += 1
                f.sport_experience[key] += {"gold": 20, "silver": 10, "bronze": 6}[colour]
                if level_name == "national" and colour in ("gold", "silver"):
                    f.sport_national_teams[key] = True
                    if sport == "MMA":
                        f.national_team = True
            if level_name in ("continental", "world", "olympic"):
                self.news.append("%s wins %s %s gold for %s." % (
                    ranked[0].name, sport, label or level_name, ranked[0].country))

        for sport in sports.SPORT_KEYS:
            if level == "olympic" and sport not in sports.OLYMPIC_SPORTS:
                continue
            key = sports.key_for(sport)
            field = [f for f in athletes if f.active_amateur_sport == sport]
            if level == "national":
                countries = defaultdict(list)
                for f in field:
                    countries[f.country].append(f)
                for country_field in countries.values():
                    podium(country_field, sport, level)
                continue
            field = [f for f in field if f.sport_national_teams.get(key)]
            if level == "continental":
                regions = defaultdict(list)
                for f in field:
                    regions[_continent(f.country)].append(f)
                for region, region_field in regions.items():
                    label = sports.CONTINENTAL_NAMES.get(region, "Continental Championships")
                    podium(region_field, sport, "continental", label=label)
                continue
            if level == "world":
                field = [f for f in field if sum(f.sport_championships[key]["continental"].values())
                         or f.sport_championships[key]["national"]["gold"]]
            elif level == "olympic":
                field = [f for f in field if int(f.sport_experience.get(key, 0) or 0) >= 360
                         and (sum(f.sport_championships[key]["world"].values())
                              or f.sport_championships[key]["continental"]["gold"])]
            podium(field, sport, level, label=("Olympic Games" if level == "olympic" else "World Championships"))

    @staticmethod
    def simulate_ai_fight(f1: Fighter, f2: Fighter) -> tuple:
        idx = [C.SKILLS.index(s) for s in (
            "striking", "grappling", "submissions", "cardio", "strength", "speed", "durability", "fight_iq"
        )]
        r1, r2 = f1.rating_vector(), f2.rating_vector()
        v1 = (sum(r1[i] for i in idx)/len(idx) if idx else 40) + random.randint(-8, 8) + f1.current_streak * 0.5
        v2 = (sum(r2[i] for i in idx)/len(idx) if idx else 40) + random.randint(-8, 8) + f2.current_streak * 0.5
        if abs(v1 - v2) < 2.0 and random.random() < 0.22:
            return f1, f2, True
        return (f1, f2, False) if v1 > v2 else (f2, f1, False)

    def get_ranked_opponents(self, weight_class: str, exclude: Optional[Fighter] = None, limit: int = 10) -> list:
        roster = list(self.rankings.get(weight_class, []))
        if exclude:
            roster = [f for f in roster if f is not exclude and f.name != getattr(exclude, "name", None)]
        return roster[:limit]

    def get_top_10(self, weight_class: str) -> list:
        return self.rankings.get(weight_class, [])[:10]

    def get_org_top(self, org: str, weight_class: str, limit: int = 10) -> list:
        boards = getattr(self, "org_rankings", None) or {}
        row = boards.get(org) if isinstance(boards, dict) else None
        if row is None:
            return []
        if hasattr(row, "get"):
            return list(row.get(weight_class, []) or [])[:limit]
        return []

    def attach_player(self, player) -> None:
        """Keep the player on the UFC board when signed."""
        self._player = player

    def get_p4p(self, limit: int = 15) -> list:
        return self.p4p[:limit]

    def fighters_from_country(self, country: str, weight_class: Optional[str] = None, amateur: bool = True) -> list:
        out = []
        for f in self.fighters:
            if not f.active:
                continue
            if f.country != country:
                continue
            if amateur and f.pro_debut:
                continue
            if not amateur and not f.pro_debut:
                continue
            if weight_class and f.weight_class != weight_class:
                continue
            out.append(f)
        return out


def _apply_archetype(fighter: Fighter, archetype: Optional[dict]) -> None:
    if not archetype:
        return
    fighter.archetype = archetype.get("name") or getattr(fighter, "archetype", None)
    modifiers = archetype.get("modifiers", {})
    from .physiology import clamp_stat
    if "all" in modifiers:
        mod = modifiers["all"]
        for attr in C.SKILLS:
            setattr(fighter, attr, min(90, clamp_stat(fighter, attr, int(getattr(fighter, attr) * mod))))
        return
    for stat, mod in modifiers.items():
        if hasattr(fighter, stat):
            setattr(fighter, stat, min(90, clamp_stat(fighter, stat, int(getattr(fighter, stat) * mod))))
