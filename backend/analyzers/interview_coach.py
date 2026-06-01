"""
AI Interview Coach — transforms platform analytics into a professional coaching report.

Every recommendation is traceable to a specific metric.
LLM enhancement is optional — falls back to rule-based if no provider is configured.
"""

import logging
from analyzers.llm_provider import get_provider

log = logging.getLogger("interview_coach")

# ── Role-specific coaching context ────────────────────────────────────────────
ROLE_CONTEXT: dict[str, dict] = {
    "software_engineer": {
        "label":    "Software Engineer",
        "keywords": ["built", "implemented", "designed", "optimized", "deployed", "architected"],
        "tips":     [
            "Use the STAR method to structure technical problem-solving answers.",
            "Quantify impact: 'reduced latency by 40%' beats 'improved performance'.",
            "Demonstrate system design thinking — mention trade-offs and scalability.",
        ],
    },
    "ai_ml_engineer": {
        "label":    "AI/ML Engineer",
        "keywords": ["trained", "fine-tuned", "evaluated", "deployed", "modelled", "experimented"],
        "tips":     [
            "Explain model selection rationale, not just results.",
            "Discuss data pipeline, feature engineering, and evaluation metrics.",
            "Show awareness of production ML challenges: drift, latency, monitoring.",
        ],
    },
    "data_scientist": {
        "label":    "Data Scientist",
        "keywords": ["analysed", "modelled", "visualised", "predicted", "clustered", "validated"],
        "tips":     [
            "Lead with business impact before technical methodology.",
            "Mention statistical rigour — confidence intervals, A/B testing, p-values.",
            "Show stakeholder communication skills alongside technical depth.",
        ],
    },
    "product_manager": {
        "label":    "Product Manager",
        "keywords": ["launched", "prioritised", "roadmap", "stakeholders", "metrics", "shipped"],
        "tips":     [
            "Frame every answer around user impact and business outcomes.",
            "Demonstrate cross-functional collaboration and influence without authority.",
            "Use data to justify product decisions — show analytical thinking.",
        ],
    },
    "business_analyst": {
        "label":    "Business Analyst",
        "keywords": ["analysed", "documented", "requirements", "stakeholders", "process", "improved"],
        "tips":     [
            "Highlight requirements gathering and stakeholder management experience.",
            "Demonstrate ability to translate business needs into technical specifications.",
            "Show proficiency with data analysis tools and process improvement frameworks.",
        ],
    },
}


# ── Metric helpers ────────────────────────────────────────────────────────────

def _band(score: float, excellent: float = 80, good: float = 65, fair: float = 50) -> str:
    if score >= excellent: return "excellent"
    if score >= good:      return "good"
    if score >= fair:      return "fair"
    return "poor"


def _wpm_label(wpm: float) -> str:
    if wpm == 0:          return "no speech detected"
    if wpm < 100:         return f"too slow ({wpm:.0f} WPM)"
    if wpm <= 120:        return f"slightly slow ({wpm:.0f} WPM)"
    if wpm <= 170:        return f"ideal ({wpm:.0f} WPM)"
    if wpm <= 200:        return f"slightly fast ({wpm:.0f} WPM)"
    return f"too fast ({wpm:.0f} WPM)"


# ── Response quality scoring ──────────────────────────────────────────────────

def _response_quality(
    word_count:           int,
    sentence_count:       int,
    vocabulary_diversity: float,
    filler_rate:          float,
    confidence_score:     int,
    avg_words_per_sentence: float,
) -> tuple[int, str]:
    """Score answer structure, clarity, conciseness, and professional language."""

    # Structure: reasonable sentence length (10–25 words ideal)
    if 10 <= avg_words_per_sentence <= 25:
        structure = 100
    elif avg_words_per_sentence < 5:
        structure = 40
    else:
        structure = max(0, 100 - abs(avg_words_per_sentence - 17) * 3)

    # Clarity: low filler + high vocab diversity
    clarity = max(0, min(100, round(
        (1 - filler_rate / 20) * 50 + vocabulary_diversity * 50
    )))

    # Conciseness: penalise very short or very long answers
    if word_count == 0:
        conciseness = 0
    elif word_count < 20:
        conciseness = 40
    elif word_count <= 300:
        conciseness = 100
    else:
        conciseness = max(40, 100 - (word_count - 300) // 10)

    # Professional language: confidence score proxy
    professionalism = confidence_score

    score = round(
        structure      * 0.25 +
        clarity        * 0.30 +
        conciseness    * 0.20 +
        professionalism * 0.25
    )
    score = min(100, max(0, score))

    if score >= 85:   label = "Excellent"
    elif score >= 70: label = "Good"
    elif score >= 50: label = "Average"
    else:             label = "Needs Improvement"

    return score, label


# ── Detailed strengths ────────────────────────────────────────────────────────

def _build_strengths(d: dict) -> list[dict]:
    strengths = []

    eye  = d.get("eye_contact_percentage", 0)
    wpm  = d.get("speaking_rate_wpm", 0)
    fil  = d.get("filler_rate", 0)
    voc  = d.get("vocabulary_diversity", 0)
    conf = d.get("confidence_language_score", 0)
    comm = d.get("communication_score", 0)
    vc   = d.get("voice_confidence_score", 0)
    post = d.get("posture_score", 0)
    attn = d.get("attention_score", 0)
    pres = d.get("professional_presence_score", 0)
    overall = d.get("overall_score", 0)

    if eye >= 70:
        strengths.append({
            "title":       "Strong Eye Contact",
            "description": f"Maintained eye contact for {eye:.0f}% of the interview — well above the 70% benchmark for confident candidates.",
            "metric":      f"eye_contact_percentage: {eye:.1f}%",
        })
    if 120 <= wpm <= 170:
        strengths.append({
            "title":       "Ideal Speaking Pace",
            "description": f"Spoke at {wpm:.0f} WPM — within the optimal 120–170 WPM range that maximises listener comprehension.",
            "metric":      f"speaking_rate_wpm: {wpm:.1f}",
        })
    if fil <= 2:
        strengths.append({
            "title":       "Clean, Filler-Free Speech",
            "description": f"Only {d.get('filler_word_count', 0)} filler words detected ({fil:.1f}% rate) — speech was clear and direct.",
            "metric":      f"filler_rate: {fil:.1f}%",
        })
    if voc >= 0.65:
        strengths.append({
            "title":       "Rich Vocabulary",
            "description": f"Vocabulary diversity score of {voc:.2f} indicates varied, professional word choice that avoids repetition.",
            "metric":      f"vocabulary_diversity: {voc:.3f}",
        })
    if conf >= 70:
        strengths.append({
            "title":       "Confident Language",
            "description": f"Confidence language score of {conf} — used {d.get('confident_phrases', 0)} action-oriented phrases with minimal hedging.",
            "metric":      f"confidence_language_score: {conf}",
        })
    if comm >= 80:
        strengths.append({
            "title":       "Strong Communication",
            "description": f"Communication score of {comm} reflects effective pacing, vocabulary, and language confidence combined.",
            "metric":      f"communication_score: {comm}",
        })
    if vc >= 75:
        strengths.append({
            "title":       "Vocal Confidence",
            "description": f"Voice confidence score of {vc} — stable volume and minimal hesitation projected authority.",
            "metric":      f"voice_confidence_score: {vc}",
        })
    if post >= 75:
        strengths.append({
            "title":       "Professional Posture",
            "description": f"Posture score of {post} — maintained stable, upright positioning throughout with only {d.get('leaning_events', 0)} leaning events.",
            "metric":      f"posture_score: {post}",
        })
    if attn >= 75:
        strengths.append({
            "title":       "Sustained Attention",
            "description": f"Attention score of {attn} — consistent focus with only {d.get('gaze_shifts', 0)} gaze shifts detected.",
            "metric":      f"attention_score: {attn}",
        })
    if pres >= 80:
        strengths.append({
            "title":       "Outstanding Professional Presence",
            "description": f"Professional presence score of {pres} — composure, visibility, and engagement were all strong.",
            "metric":      f"professional_presence_score: {pres}",
        })

    if not strengths:
        strengths.append({
            "title":       "Interview Completed",
            "description": "Completed the full interview session — a solid foundation to build on with targeted practice.",
            "metric":      f"overall_score: {overall}",
        })

    return strengths


# ── Detailed improvements ─────────────────────────────────────────────────────

def _build_improvements(d: dict) -> list[dict]:
    improvements = []

    eye     = d.get("eye_contact_percentage", 0)
    wpm     = d.get("speaking_rate_wpm", 0)
    fil_n   = d.get("filler_word_count", 0)
    fil_r   = d.get("filler_rate", 0)
    voc     = d.get("vocabulary_diversity", 0)
    conf    = d.get("confidence_language_score", 0)
    comm    = d.get("communication_score", 0)
    vc      = d.get("voice_confidence_score")
    pauses  = d.get("pause_count", 0)
    avg_p   = d.get("average_pause_seconds", 0)
    post    = d.get("posture_score")
    attn    = d.get("attention_score")
    rest    = d.get("restlessness_score")

    if eye < 70:
        improvements.append({
            "title":       "Improve Eye Contact",
            "description": f"Eye contact was {eye:.0f}% — below the 70% benchmark. Inconsistent gaze reduces perceived confidence.",
            "metric":      f"eye_contact_percentage: {eye:.1f}%",
            "priority":    1 if eye < 50 else 2,
        })
    if wpm > 170 or (0 < wpm < 120):
        improvements.append({
            "title":       "Adjust Speaking Pace",
            "description": f"Speaking pace was {_wpm_label(wpm)}. Target 120–170 WPM for optimal clarity and engagement.",
            "metric":      f"speaking_rate_wpm: {wpm:.1f}",
            "priority":    2,
        })
    if fil_n > 0:
        improvements.append({
            "title":       "Reduce Filler Words",
            "description": f"{fil_n} filler words detected ({fil_r:.1f}% rate). Common fillers like 'um', 'uh', and 'like' undermine professional delivery.",
            "metric":      f"filler_word_count: {fil_n}, filler_rate: {fil_r:.1f}%",
            "priority":    1 if fil_r > 5 else 2,
        })
    if voc < 0.55:
        improvements.append({
            "title":       "Expand Vocabulary",
            "description": f"Vocabulary diversity of {voc:.2f} indicates repetitive word choice. Varied language signals stronger communication skills.",
            "metric":      f"vocabulary_diversity: {voc:.3f}",
            "priority":    3,
        })
    if conf < 70:
        improvements.append({
            "title":       "Use More Confident Language",
            "description": f"Confidence language score of {conf} — {d.get('uncertain_phrases', 0)} uncertain phrases detected. Replace 'I think' and 'maybe' with direct statements.",
            "metric":      f"confidence_language_score: {conf}",
            "priority":    1 if conf < 50 else 2,
        })
    if vc is not None and vc < 65:
        improvements.append({
            "title":       "Strengthen Vocal Delivery",
            "description": f"Voice confidence score of {vc} — {pauses} pauses detected (avg {avg_p:.1f}s). Work on reducing hesitation and projecting with a steady tone.",
            "metric":      f"voice_confidence_score: {vc}, pause_count: {pauses}",
            "priority":    2,
        })
    if post is not None and post < 65:
        improvements.append({
            "title":       "Improve Posture Stability",
            "description": f"Posture score of {post} — {d.get('leaning_events', 0)} leaning events detected. Sit upright and minimise body movement.",
            "metric":      f"posture_score: {post}",
            "priority":    3,
        })
    if attn is not None and attn < 65:
        improvements.append({
            "title":       "Maintain Consistent Attention",
            "description": f"Attention score of {attn} with {d.get('gaze_shifts', 0)} gaze shifts. Reduce looking away — it signals distraction to interviewers.",
            "metric":      f"attention_score: {attn}",
            "priority":    2,
        })
    if rest is not None and rest < 55:
        improvements.append({
            "title":       "Reduce Restless Movement",
            "description": f"Restlessness score of {rest} — frequent head and gaze shifts detected. Stillness projects calm confidence.",
            "metric":      f"restlessness_score: {rest}",
            "priority":    3,
        })

    improvements.sort(key=lambda x: x.get("priority", 9))
    return improvements


# ── Coaching plan ─────────────────────────────────────────────────────────────

def _build_coaching_plan(improvements: list[dict], d: dict, role: str) -> list[dict]:
    plan = []
    priority = 1

    for imp in improvements[:5]:  # top 5 improvements become plan items
        title = imp["title"]

        if "Filler" in title:
            plan.append({
                "priority":        priority,
                "area":            "Speech Clarity",
                "action":          "Record yourself answering 3 mock questions daily. Count filler words per answer and track weekly reduction.",
                "expected_impact": "Reduce filler rate below 2% within 2 weeks of consistent practice.",
                "timeframe":       "2 weeks",
            })
        elif "Eye Contact" in title:
            plan.append({
                "priority":        priority,
                "area":            "Non-Verbal Communication",
                "action":          "Place a sticky note at eye level near your webcam. Practice maintaining gaze for 5-second intervals during mock answers.",
                "expected_impact": "Increase eye contact percentage above 75% within 1 week.",
                "timeframe":       "1 week",
            })
        elif "Pace" in title or "Speaking" in title:
            plan.append({
                "priority":        priority,
                "area":            "Delivery Pace",
                "action":          "Use a metronome app set to 140 BPM as a pacing guide. Read aloud for 10 minutes daily at that rhythm.",
                "expected_impact": "Achieve consistent 130–160 WPM delivery within 10 days.",
                "timeframe":       "10 days",
            })
        elif "Confident Language" in title:
            plan.append({
                "priority":        priority,
                "area":            "Language Confidence",
                "action":          "Rewrite your top 5 interview answers replacing all hedging phrases with action verbs. Rehearse until natural.",
                "expected_impact": "Increase confidence language score above 75 within 1 week.",
                "timeframe":       "1 week",
            })
        elif "Vocal" in title:
            plan.append({
                "priority":        priority,
                "area":            "Vocal Delivery",
                "action":          "Practice 'power pausing' — replace filler sounds with 1-second silent pauses. Record and review daily.",
                "expected_impact": "Reduce hesitation count by 50% and improve voice confidence score within 2 weeks.",
                "timeframe":       "2 weeks",
            })
        elif "Posture" in title:
            plan.append({
                "priority":        priority,
                "area":            "Physical Presence",
                "action":          "Set up your interview space with a chair that supports upright posture. Practice mock interviews standing first, then seated.",
                "expected_impact": "Achieve posture score above 75 within 1 week.",
                "timeframe":       "1 week",
            })
        elif "Vocabulary" in title:
            plan.append({
                "priority":        priority,
                "area":            "Language Quality",
                "action":          "Read one industry article daily and note 5 new professional terms. Incorporate them into mock answers.",
                "expected_impact": "Increase vocabulary diversity above 0.65 within 3 weeks.",
                "timeframe":       "3 weeks",
            })
        else:
            plan.append({
                "priority":        priority,
                "area":            imp["title"],
                "action":          f"Focus on improving {imp['title'].lower()} through targeted mock interview practice.",
                "expected_impact": "Measurable improvement within 2 weeks of consistent practice.",
                "timeframe":       "2 weeks",
            })

        priority += 1

    # Add role-specific tip
    role_data = ROLE_CONTEXT.get(role, ROLE_CONTEXT["software_engineer"])
    plan.append({
        "priority":        priority,
        "area":            f"{role_data['label']} Interview Preparation",
        "action":          role_data["tips"][0],
        "expected_impact": "Stronger, more targeted answers aligned with interviewer expectations for this role.",
        "timeframe":       "Ongoing",
    })

    # Universal final item
    plan.append({
        "priority":        priority + 1,
        "area":            "Mock Interview Practice",
        "action":          "Complete 3 full mock interviews using this platform before your target interview date.",
        "expected_impact": "Consolidate all improvements and build interview confidence through repetition.",
        "timeframe":       "Before interview",
    })

    return plan


# ── HR perspective ────────────────────────────────────────────────────────────

def _hr_perspective(d: dict, role: str, llm_provider) -> str:
    overall  = d.get("overall_score", 0)
    comm     = d.get("communication_score", 0)
    eye      = d.get("eye_contact_percentage", 0)
    conf     = d.get("confidence_language_score", 0)
    fil_n    = d.get("filler_word_count", 0)
    pres     = d.get("professional_presence_score", 0)
    role_label = ROLE_CONTEXT.get(role, ROLE_CONTEXT["software_engineer"])["label"]

    # Try LLM first
    prompt = f"""You are a senior technical recruiter evaluating a {role_label} candidate.
Write a 3-sentence professional assessment based on these metrics:
- Overall Score: {overall}/100
- Communication Score: {comm}/100
- Eye Contact: {eye:.0f}%
- Confidence Language Score: {conf}/100
- Filler Words: {fil_n}
- Professional Presence: {pres}/100

Be specific, professional, and constructive. Do not use bullet points."""

    llm_text = llm_provider.complete(prompt, max_tokens=200)
    if llm_text:
        return llm_text

    # Rule-based fallback
    parts = []
    if overall >= 80:
        parts.append(f"This {role_label} candidate demonstrated a strong overall interview performance with a score of {overall}/100.")
    elif overall >= 65:
        parts.append(f"This {role_label} candidate showed solid foundational interview skills with an overall score of {overall}/100, with clear areas for development.")
    else:
        parts.append(f"This {role_label} candidate's interview performance requires improvement, scoring {overall}/100 overall.")

    if comm >= 75:
        parts.append("Communication was clear, well-paced, and professional throughout the session.")
    else:
        parts.append("Communication clarity and confidence would benefit from further development before proceeding to final rounds.")

    if eye >= 70 and conf >= 70:
        parts.append("The candidate projected confidence through consistent eye contact and assertive language — a positive indicator for client-facing or collaborative roles.")
    elif fil_n > 5:
        parts.append(f"Filler word usage ({fil_n} instances) and inconsistent delivery detracted from an otherwise competent presentation.")
    else:
        parts.append("With targeted preparation, this candidate has the potential to perform strongly in a formal interview setting.")

    return " ".join(parts)


# ── Executive summary ─────────────────────────────────────────────────────────

def _executive_summary(d: dict, role: str, readiness_score: int, readiness_level: str, llm_provider) -> str:
    overall  = d.get("overall_score", 0)
    comm     = d.get("communication_score", 0)
    eye      = d.get("eye_contact_percentage", 0)
    wpm      = d.get("speaking_rate_wpm", 0)
    role_label = ROLE_CONTEXT.get(role, ROLE_CONTEXT["software_engineer"])["label"]

    prompt = f"""Write a 2-sentence executive summary for an AI interview assessment report.
Candidate role: {role_label}
Overall Score: {overall}/100, Communication: {comm}/100, Eye Contact: {eye:.0f}%, Speaking Rate: {wpm:.0f} WPM
Interview Readiness: {readiness_level} ({readiness_score}/100)
Be concise and professional."""

    llm_text = llm_provider.complete(prompt, max_tokens=150)
    if llm_text:
        return llm_text

    # Rule-based fallback
    return (
        f"This {role_label} candidate achieved an overall interview score of {overall}/100 "
        f"with a readiness level of '{readiness_level}' ({readiness_score}/100). "
        f"Key highlights include a communication score of {comm}/100 and {eye:.0f}% eye contact, "
        f"with speaking pace at {_wpm_label(wpm)}."
    )


# ── Candidate profile ─────────────────────────────────────────────────────────

def _candidate_profile(d: dict) -> str:
    overall  = d.get("overall_score", 0)
    comm     = d.get("communication_score", 0)
    conf     = d.get("confidence_language_score", 0)
    eye      = d.get("eye_contact_percentage", 0)
    pres     = d.get("professional_presence_score", 0)

    comm_band = _band(comm)
    conf_band = _band(conf)
    eye_band  = _band(eye)

    if comm_band == "excellent" and conf_band in ("excellent", "good"):
        profile = "Articulate Communicator"
    elif eye_band == "excellent" and pres >= 75:
        profile = "Confident Presenter"
    elif comm_band in ("fair", "poor") and conf_band in ("fair", "poor"):
        profile = "Developing Communicator"
    elif overall >= 75:
        profile = "Well-Rounded Candidate"
    else:
        profile = "Emerging Candidate"

    descriptions = {
        "Articulate Communicator": "Demonstrates strong verbal communication with confident, structured responses.",
        "Confident Presenter":     "Projects strong professional presence with consistent eye contact and composure.",
        "Developing Communicator": "Shows potential but needs focused work on communication clarity and confidence.",
        "Well-Rounded Candidate":  "Performs consistently across multiple interview dimensions.",
        "Emerging Candidate":      "Early-stage interview skills with clear development opportunities.",
    }

    return f"{profile} — {descriptions[profile]}"


# ── Readiness score ───────────────────────────────────────────────────────────

def _readiness(d: dict) -> tuple[int, str]:
    overall  = d.get("overall_score", 0)
    comm     = d.get("communication_score", 0)
    conf     = d.get("confidence_language_score", 0)
    eye      = d.get("eye_contact_percentage", 0)
    vc       = d.get("voice_confidence_score", 50)
    pres     = d.get("professional_presence_score", 50)

    score = min(100, max(0, round(
        overall * 0.35 +
        comm    * 0.20 +
        conf    * 0.15 +
        eye     * 0.15 +
        vc      * 0.08 +
        pres    * 0.07
    )))

    if score >= 88:   level = "Outstanding"
    elif score >= 78: level = "Ready"
    elif score >= 65: level = "Needs Practice"
    else:             level = "Requires Improvement"

    return score, level


# ── Master coaching report ────────────────────────────────────────────────────

def generate_report(data: dict, role: str = "software_engineer") -> dict:
    """
    Generate a complete AI coaching report from platform analytics.

    Args:
        data: Merged dict of all analyzer outputs.
        role: Target role key (software_engineer, ai_ml_engineer, etc.)
    """
    role = role.lower().replace(" ", "_")
    if role not in ROLE_CONTEXT:
        role = "software_engineer"

    llm = get_provider()

    readiness_score, readiness_level = _readiness(data)

    rq_score, rq_label = _response_quality(
        word_count            = data.get("word_count", 0),
        sentence_count        = data.get("sentence_count", 1),
        vocabulary_diversity  = data.get("vocabulary_diversity", 0),
        filler_rate           = data.get("filler_rate", 0),
        confidence_score      = data.get("confidence_language_score", 50),
        avg_words_per_sentence = data.get("average_words_per_sentence", 15),
    )

    strengths   = _build_strengths(data)
    improvements = _build_improvements(data)
    plan        = _build_coaching_plan(improvements, data, role)
    hr          = _hr_perspective(data, role, llm)
    summary     = _executive_summary(data, role, readiness_score, readiness_level, llm)
    profile     = _candidate_profile(data)

    role_data = ROLE_CONTEXT[role]

    return {
        "executive_summary":    summary,
        "candidate_profile":    profile,
        "overall_assessment":   f"Overall Score: {data.get('overall_score', 0)}/100 — {data.get('rating', 'N/A')}",
        "strengths":            strengths,
        "improvements":         improvements,
        "coaching_plan":        plan,
        "response_quality": {
            "response_quality_score": rq_score,
            "response_quality_level": rq_label,
        },
        "interview_readiness": {
            "interview_readiness_score": readiness_score,
            "readiness_level":           readiness_level,
        },
        "hr_perspective":       hr,
        "role_coaching": {
            "role":  role_data["label"],
            "tips":  role_data["tips"],
        },
        "llm_enhanced": bool(os.environ.get("LLM_PROVIDER", "") not in ("", "rule_based")),
    }


import os
