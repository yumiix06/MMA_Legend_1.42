"""1.5.0 smoke."""
from __future__ import annotations

from mma_legend.models import Fighter
from mma_legend import systems15 as s
from mma_legend import v08
from mma_legend.data import country_by_name


def _p(country="Bulgaria"):
    c = country_by_name(country)
    return Fighter.new_player("T", "X", c, "BJJ")


def test_sa_not_europe():
    f = _p("South Africa")
    f.national_team = True
    f.medals = {"national": {"gold": 1, "silver": 0, "bronze": 0},
                "european": {"gold": 0, "silver": 0, "bronze": 0},
                "world": {"gold": 0, "silver": 0, "bronze": 0}}
    assert v08.europe_eligible(f) is False
    return "SA blocked from Europe"


def test_bg_europe():
    f = _p("Bulgaria")
    f.national_team = True
    f.medals = {"national": {"gold": 1, "silver": 0, "bronze": 0},
                "european": {"gold": 0, "silver": 0, "bronze": 0},
                "world": {"gold": 0, "silver": 0, "bronze": 0}}
    assert v08.europe_eligible(f) is True
    return "BG Europe ok"


def test_opp_label_not_repr():
    f = _p()
    booked = {"opponent": f, "org": "LFA"}
    lab = s.opp_label(booked)
    assert "Fighter(" not in lab
    return lab


def test_belt_ladder():
    f = _p()
    f.bjj_belt = "white"
    f.bjj_stripes = 4
    f.bjj_weeks = 20
    f.style = "BJJ"
    s.tick_belts(f)
    assert f.bjj_belt == "blue"
    return "white -> blue"


def test_loan():
    f = _p()
    f.age = 18
    f.money = 0
    s.take_loan(f, 400)
    assert f.debt == 400 and f.money == 400
    return "loan"


def main():
    for t in (test_sa_not_europe, test_bg_europe, test_opp_label_not_repr, test_belt_ladder, test_loan):
        print("PASS", t())
    print("ALL 1.5 CHECKS OK")


if __name__ == "__main__":
    main()
