"""Career timeline and fight-ledger presentation.

The ledger is authoritative in ``fight_history``.  This module is a paged,
filtered view over it plus non-fight career milestones.
"""
from __future__ import annotations


def add(fighter, text: str, year: int | None = None) -> None:
    y = year
    if y is None:
        y = ((max(1, int(getattr(fighter, "week", 1) or 1)) - 1) // 52) + 1
    log = list(getattr(fighter, "timeline", None) or [])
    log.append({
        "year": y,
        "week": int(getattr(fighter, "week", 0) or 0),
        "text": text,
        "phase": "pro" if bool(getattr(fighter, "pro_debut", False)) else "amateur",
        "amateur_record": list(getattr(fighter, "amateur_record", None) or [0, 0, 0]),
        "pro_record": list(getattr(fighter, "pro_record", None) or [0, 0, 0]),
    })
    fighter.timeline = log[-160:]


def _result_code(row: dict) -> int:
    r = str(row.get("result") or "Draw").lower()
    if r.startswith("w"): return 0
    if r.startswith("l"): return 1
    return 2


def _is_pro(row: dict) -> bool:
    try:
        from .record import is_pro_row
        return bool(is_pro_row(row))
    except Exception:
        return bool(row.get("pro"))


def _sport_name(row: dict) -> str:
    name = str(row.get("sport_name") or row.get("sport") or "MMA")
    aliases = {"mma":"MMA", "combat_sambo":"Combat Sambo", "grappling":"BJJ / No-Gi",
               "boxing":"Boxing", "kickboxing":"Kickboxing", "taekwondo":"Taekwondo", "wrestling":"Wrestling", "judo":"Judo"}
    return aliases.get(name.lower(), name.replace("_", " ").title())


def _stats_line(stats: dict) -> str:
    st = dict(stats or {})
    if not st: return ""
    bits=[]
    sl=int(st.get("strikes_landed",0) or 0); sa=int(st.get("strikes_attempted",0) or 0)
    td=int(st.get("takedowns_landed",0) or 0); ta=int(st.get("takedowns_attempted",0) or 0)
    kd=int(st.get("knockdowns",0) or 0); ctrl=int(st.get("control_sec",0) or 0); sub=int(st.get("submission_attempts",0) or 0)
    if sa: bits.append("str %s/%s"%(sl,sa))
    if ta: bits.append("TD %s/%s"%(td,ta))
    if kd: bits.append("KD %s"%kd)
    if ctrl: bits.append("ctrl %s:%02d"%(ctrl//60,ctrl%60))
    if sub: bits.append("sub %s"%sub)
    return " · ".join(bits)


def _fight_lines(row: dict) -> list[str]:
    week=row.get("week") or "?"; result=str(row.get("result") or "Draw")
    method=str(row.get("method") or "Decision"); event=str(row.get("event") or _sport_name(row))
    rnd=int(row.get("round",0) or 0)
    line="W%s · %s"%(week,event)
    detail="%s vs %s · %s%s"%(result,row.get("opponent","Opponent"),method,(" R%s"%rnd if rnd else ""))
    extras=[]
    perf=float(row.get("performance_rating",0.0) or 0.0)
    if perf>0: extras.append("rating %.1f"%perf)
    stats=_stats_line(row.get("stats") or {})
    if stats: extras.append(stats)
    return [line,detail] + ([" · ".join(extras)] if extras else [])


def _milestones(fighter) -> list[dict]:
    cleaned=[]
    for row in list(getattr(fighter,"timeline",None) or []):
        text=str(row.get("text") or "")
        if " vs " in text and any(text.startswith(x) for x in ("Win","Loss","Draw")):
            continue
        cleaned.append(row)
    return cleaned


def _render_page(console, rows: list[dict], *, title: str, page: int, page_size: int=10) -> tuple[int,int]:
    pages=max(1,(len(rows)+page_size-1)//page_size)
    page=max(0,min(page,pages-1))
    console.section("%s · PAGE %s/%s"%(title,page+1,pages))
    chunk=rows[page*page_size:(page+1)*page_size]
    if not chunk:
        console.print("  No entries.")
    for row in reversed(chunk):
        lines=_fight_lines(row)
        console.print("  "+lines[0])
        console.print("    "+lines[1])
        if len(lines)>2: console.print("    "+lines[2],style="dim")
    return page,pages


def render(console, fighter) -> None:
    history=list(getattr(fighter,"fight_history",None) or [])
    amateur=[r for r in history if not _is_pro(r)]
    pro=[r for r in history if _is_pro(r)]
    console.header("TIMELINE", "Amateur and professional careers stay separate")
    ar=list(getattr(fighter,"amateur_record",None) or [0,0,0]); pr=list(getattr(fighter,"pro_record",None) or [0,0,0])
    console.print("  Amateur %s-%s-%s · Pro %s-%s-%s"%(*ar,*pr))
    # Fast overview first: never dump the whole career on entry.
    console.section("AMATEUR CAREER")
    if not amateur: console.print("  No amateur fights recorded.")
    for row in reversed(amateur[-5:]):
        lines=_fight_lines(row); console.print("  "+lines[0]); console.print("    "+lines[1]);
        if len(lines)>2: console.print("    "+lines[2],style="dim")
    console.section("PROFESSIONAL CAREER")
    if not pro: console.print("  No professional fights recorded.")
    for row in reversed(pro[-5:]):
        lines=_fight_lines(row); console.print("  "+lines[0]); console.print("    "+lines[1]);
        if len(lines)>2: console.print("    "+lines[2],style="dim")
    ms=_milestones(fighter)
    if ms:
        console.section("CAREER MILESTONES")
        for row in reversed(ms[-6:]): console.print("  W%s · %s"%(row.get("week","?"),row.get("text","")))
    console.print("\n  F) Browse / filter full history   X) Back")
    first=(console.ask("Timeline > ") or "X").strip().upper()
    if first != "F": return

    mode="ALL"; page=0
    while True:
        console.header("HISTORY BROWSER", "Filter and page through the full ledger")
        if mode=="AMATEUR": rows=amateur; title="AMATEUR"
        elif mode=="PRO": rows=pro; title="PROFESSIONAL"
        else: rows=history; title="ALL FIGHTS"
        if mode=="MILESTONES":
            rows_ms=ms; pages=max(1,(len(rows_ms)+11)//12); page=max(0,min(page,pages-1))
            console.section("MILESTONES · PAGE %s/%s"%(page+1,pages))
            chunk=rows_ms[page*12:(page+1)*12]
            if not chunk: console.print("  No milestones recorded.")
            for r in reversed(chunk): console.print("  W%s · %s"%(r.get("week","?"),r.get("text","")))
        else:
            page,pages=_render_page(console,rows,title=title,page=page)
        console.print("\n  A) All  B) Amateur  C) Pro  D) Milestones")
        nav=[]
        if page>0: nav.append("P prev")
        if page+1<pages: nav.append("N next")
        nav.append("X back")
        console.print("  " + " · ".join(nav))
        ch=(console.ask("History > ") or "X").strip().upper()
        if ch in ("X","0",""): return
        if ch in ("A","B","C","D"):
            mode={"A":"ALL","B":"AMATEUR","C":"PRO","D":"MILESTONES"}[ch]; page=0
        elif ch=="N" and page+1<pages: page+=1
        elif ch=="P" and page>0: page-=1
        else: console.warn("Invalid.")
