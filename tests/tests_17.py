"""1.7 checks."""
from mma_legend.models import Fighter
from mma_legend.engine import positions as P
from mma_legend import systems17 as s17


def _f():
    f = Fighter(name="T", country="Croatia", country_flag="HR", is_player=True)
    f.week = 20
    f.age = 18
    f.school_status = "school"
    f.amateur_record = [7, 4, 0]
    return f


def test_positions():
    assert "rear_naked" in P.legal_actions("back")
    assert "rear_naked" not in P.legal_actions("stand")
    # apply_transition now reports whether top/bottom roles swapped.
    pos, swapped = P.apply_transition("stand", "double_leg")
    assert pos == "closed_guard", pos
    assert swapped is False
    # Only the fighter holding the back may choke; the one underneath escapes.
    assert "rear_naked" in P.legal_actions("back", role="top")
    assert "rear_naked" not in P.legal_actions("back", role="bottom")
    # A sweep is a reversal.
    _, swept = P.apply_transition("mount", "sweep")
    assert swept is True
    return "pos ok (roles + transitions)"


def test_grad_and_audit():
    f = _f()
    f.school_grade = 70
    f.school_attendance = 80
    assert s17.graduate(f) == "graduated"
    assert f.secondary_completed is True
    assert f.education_stage == "gap"
    assert f.school_status == "none"
    notes = s17.audit_fighter(f)
    return "audit %s" % notes


def test_contract():
    f = _f()
    f.org_contract = {"org": "KSW", "fights_left": 3}
    assert s17.contract_locked(f, "UFC") is True
    assert s17.contract_locked(f, "KSW") is False
    return "contract"


def main():
    for t in (test_positions, test_grad_and_audit, test_contract):
        print("PASS", t())
    print("ALL 1.7 OK")


if __name__ == "__main__":
    main()
