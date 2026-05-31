"""
Communication Score Formula
───────────────────────────
Base score:          100 points

Speaking rate score  (max 40 pts)
  Ideal range: 120–170 WPM → full 40 pts
  Outside range: linear decay, floored at 0

Filler penalty       (max -30 pts)
  filler_rate 0%   →  0 penalty
  filler_rate 10%+ → -30 penalty (linear)

Confidence bonus     (max +20 pts)
  confidence_language_score mapped 0–100 → 0–20 pts
  Scores below 50 become a penalty instead

Final score clamped to [0, 100].
"""


def _speaking_rate_score(wpm: float) -> float:
    IDEAL_LOW, IDEAL_HIGH = 120.0, 170.0
    MAX_SCORE = 40.0

    if IDEAL_LOW <= wpm <= IDEAL_HIGH:
        return MAX_SCORE

    if wpm < IDEAL_LOW:
        # Too slow — decay from 120 down to 60 WPM
        ratio = max(0.0, (wpm - 60.0) / (IDEAL_LOW - 60.0))
    else:
        # Too fast — decay from 170 up to 240 WPM
        ratio = max(0.0, (240.0 - wpm) / (240.0 - IDEAL_HIGH))

    return round(ratio * MAX_SCORE, 2)


def _filler_penalty(filler_rate: float) -> float:
    MAX_PENALTY = 30.0
    penalty = min(filler_rate / 10.0, 1.0) * MAX_PENALTY
    return round(penalty, 2)


def _confidence_adjustment(confidence_score: float) -> float:
    """Maps 0–100 confidence score to -10 … +20 adjustment."""
    # 50 = neutral (0 adjustment), 100 = +20, 0 = -10
    adjustment = ((confidence_score - 50.0) / 50.0) * 20.0
    return round(max(-10.0, min(20.0, adjustment)), 2)


def analyze(
    speaking_rate_wpm: float,
    filler_rate: float,
    confidence_language_score: float,
) -> dict:
    rate_score        = _speaking_rate_score(speaking_rate_wpm)
    filler_pen        = _filler_penalty(filler_rate)
    confidence_adj    = _confidence_adjustment(confidence_language_score)

    # Base 40 pts from speaking rate + up to 30 pts from low fillers + confidence adj
    raw = rate_score + (30.0 - filler_pen) + (10.0 + confidence_adj)
    communication_score = round(max(0.0, min(100.0, raw)), 1)

    return {
        "communication_score": communication_score,
        "speaking_rate_score": rate_score,
        "filler_penalty": filler_pen,
        "confidence_bonus": confidence_adj,
    }
