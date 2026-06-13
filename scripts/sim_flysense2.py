"""Numeric sanity simulation of the FlySense 2.0 engine math in index.html.

Transcribes the update rules (not a substitute for the live code) to verify:
 - an NBA 12-0 run reaches on fire and an established run cools slower
 - a soccer goal lingers much longer than an NBA basket
 - hysteresis stops label chatter at the on-fire boundary
 - cricket: T20 10/over -> on fire (mom 70); ODI 6/over -> on fire; 8/over T20 warm-run
"""

MOM_GAIN = 70
PERSIST_FULL = 300
PERSIST_MAX = 1.8
STATE_FACTOR = {"onfire": 1.3, "warming": 0.8}
BANDS = [("onfire", 70, 64), ("onrun", 45, 40), ("warming", 20, 16)]


def tier(mom, prev):
    for i, (t, enter, exit_) in enumerate(BANDS):
        held = prev and [b[0] for b in BANDS].index(prev) <= i if prev in [b[0] for b in BANDS] else False
        if mom >= (exit_ if held else enter):
            return t
    return ""


def halflife(base, run_start, t_now, tr):
    pn = min((t_now - run_start) / PERSIST_FULL, 1) if run_start is not None else 0
    return base * (1 + (PERSIST_MAX - 1) * pn) * STATE_FACTOR.get(tr, 1)


def simulate(label, base_hl, big_play, events, poll=60, total=900):
    """events: dict t -> points scored at that poll time."""
    mom, run_start, tr, ember = 0.0, None, "", 0.0
    log = []
    for t in range(0, total + 1, poll):
        hl = halflife(base_hl, run_start, t, tr)
        decay = 0.5 ** (poll / hl) if t > 0 else 1
        delta = events.get(t, 0)
        boost = 1 + 0.3 * (ember / 100)
        mom = max(0, min(100, mom * decay + min(delta / big_play, 1.6) * MOM_GAIN * boost))
        if delta == 0 and mom < 5:
            mom = max(0, mom - poll * 0.05)
        ember = max(ember * 0.5 ** (poll / 300), mom)
        tr = tier(mom, tr)
        run_start = (run_start if run_start is not None else t) if mom >= 20 else (None if mom < 16 else run_start)
        log.append((t, round(mom, 1), tr))
    print(f"\n{label}")
    for t, m, tr_ in log:
        if t % 120 == 0 or events.get(t):
            print(f"  t={t:>4}s mom={m:>5} tier={tr_ or '-'}")
    return log


# NBA: 12-0 run across two polls, then silence.
nba = simulate("NBA 12-0 run then silence (halflife 40s)", 40, 6, {60: 6, 120: 6})
assert any(tr_ == "onfire" for _, _, tr_ in nba), "NBA run should reach on fire"
after = [m for t, m, _ in nba if t == 300][0]
print(f"  -> mom 3 min after run: {after}")

# Soccer: one goal, watch it linger (halflife 90s).
soc = simulate("Soccer goal then silence (halflife 90s)", 90, 1, {60: 1}, total=600)
m_at = {t: m for t, m, _ in soc}
print(f"  -> goal mom at +60s {m_at[120]}, +180s {m_at[240]}, +300s {m_at[360]}")
assert m_at[240] > 20, "soccer goal should still be warm 3 min later"

# Hysteresis: oscillate around the on-fire boundary.
print("\nHysteresis at the on-fire boundary")
tr_ = ""
for mom in [71, 67, 65, 64.5, 63, 62, 71]:
    t2 = tier(mom, tr_)
    print(f"  mom={mom:>5} -> {t2 or '-'} (was {tr_ or '-'})")
    tr_ = t2

# Cricket: rr -> momentum mapping.
print("\nCricket run-rate mapping (mom = rr/fireRR*70)")
for fmt, fire in (("T20", 10), ("ODI", 6)):
    for rr in (4, 6, 8, 10, 12):
        mom = max(0, min(100, rr / fire * 70))
        print(f"  {fmt} rr={rr:>2}/over -> mom={mom:5.1f} tier={tier(mom, '') or '-'}")

print("\nAll assertions passed.")
