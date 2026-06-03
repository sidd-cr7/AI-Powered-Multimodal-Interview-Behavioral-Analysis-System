import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF
from reportlab.graphics.charts.barcharts import VerticalBarChart
from backend.models.report import SessionReport


# ── Colour palette ────────────────────────────────────────────────────────────
C_PRIMARY   = colors.HexColor("#1a1a2e")
C_ACCENT    = colors.HexColor("#457b9d")
C_GREEN     = colors.HexColor("#2d6a4f")
C_ORANGE    = colors.HexColor("#fd7e14")
C_RED       = colors.HexColor("#dc3545")
C_LIGHT     = colors.HexColor("#f8f9fa")
C_BORDER    = colors.HexColor("#dee2e6")
C_TEXT      = colors.HexColor("#212529")
C_MUTED     = colors.HexColor("#6c757d")


def _score_color(score: int) -> colors.Color:
    if score >= 80: return C_GREEN
    if score >= 60: return C_ACCENT
    if score >= 40: return C_ORANGE
    return C_RED


def _styles():
    base = getSampleStyleSheet()
    return {
        "title":    ParagraphStyle("title",    fontSize=22, textColor=C_PRIMARY,  spaceAfter=4,  fontName="Helvetica-Bold"),
        "subtitle": ParagraphStyle("subtitle", fontSize=11, textColor=C_MUTED,    spaceAfter=16, fontName="Helvetica"),
        "h2":       ParagraphStyle("h2",       fontSize=13, textColor=C_PRIMARY,  spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold"),
        "h3":       ParagraphStyle("h3",       fontSize=11, textColor=C_ACCENT,   spaceBefore=8,  spaceAfter=4, fontName="Helvetica-Bold"),
        "body":     ParagraphStyle("body",     fontSize=9,  textColor=C_TEXT,     spaceAfter=4,  fontName="Helvetica",    leading=14),
        "small":    ParagraphStyle("small",    fontSize=8,  textColor=C_MUTED,    spaceAfter=2,  fontName="Helvetica"),
        "bullet":   ParagraphStyle("bullet",   fontSize=9,  textColor=C_TEXT,     spaceAfter=3,  fontName="Helvetica", leftIndent=12, leading=13),
    }


def _score_bar(label: str, score: int, width: float = 12 * cm) -> Drawing:
    h = 22
    d = Drawing(width, h)
    bar_w = (score / 100) * (width - 90)
    d.add(Rect(80, 4, width - 90, h - 8, fillColor=C_LIGHT, strokeColor=C_BORDER, strokeWidth=0.5))
    d.add(Rect(80, 4, max(bar_w, 0), h - 8, fillColor=_score_color(score), strokeColor=None))
    d.add(String(0,  7, label,         fontSize=8, fillColor=C_TEXT))
    d.add(String(width - 5, 7, f"{score}", fontSize=8, fillColor=_score_color(score), textAnchor="end"))
    return d


def _radar_chart(metrics: dict) -> Drawing:
    keys   = ["Overall", "Comm.", "Eye Contact", "Voice", "Presence", "Readiness"]
    values = [
        metrics.overall_score,
        metrics.communication_score,
        round(metrics.eye_contact_percentage),
        metrics.voice_confidence_score,
        metrics.professional_presence_score,
        metrics.interview_readiness_score,
    ]
    w, h = 14 * cm, 6 * cm
    d    = Drawing(w, h)
    bc   = VerticalBarChart()
    bc.x, bc.y, bc.width, bc.height = 30, 20, w - 40, h - 30
    bc.data = [values]
    bc.bars[0].fillColor = C_ACCENT
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 100
    bc.valueAxis.valueStep = 20
    bc.categoryAxis.categoryNames = keys
    bc.categoryAxis.labels.fontSize = 7
    bc.categoryAxis.labels.angle = 0
    d.add(bc)
    return d


def generate_pdf(report: SessionReport) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
    )
    S   = _styles()
    m   = report.metrics
    els = []

    # ── Cover ─────────────────────────────────────────────────────────────────
    els += [
        Paragraph("AI Interview Assessment Report", S["title"]),
        Paragraph(
            f"Role: {report.role.replace('_',' ').title()}  |  "
            f"Session: {report.session_id}  |  "
            f"{report.timestamp.strftime('%d %b %Y, %H:%M UTC')}",
            S["subtitle"],
        ),
        HRFlowable(width="100%", color=C_PRIMARY, thickness=2),
        Spacer(1, 10),
    ]

    # ── Overall scores row ────────────────────────────────────────────────────
    def score_cell(label, val):
        col = _score_color(val)
        return [
            Paragraph(f"<font color='#{col.hexval()[2:]}' size='18'><b>{val}</b></font>", S["body"]),
            Paragraph(f"<font size='7' color='#6c757d'>{label}</font>", S["body"]),
        ]

    score_table = Table(
        [
            [score_cell("Overall", m.overall_score),
             score_cell("Communication", m.communication_score),
             score_cell("Eye Contact", round(m.eye_contact_percentage)),
             score_cell("Voice", m.voice_confidence_score),
             score_cell("Readiness", m.interview_readiness_score)],
        ],
        colWidths=[3.4*cm]*5,
    )
    score_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), C_LIGHT),
        ("BOX",         (0,0), (-1,-1), 0.5, C_BORDER),
        ("INNERGRID",   (0,0), (-1,-1), 0.5, C_BORDER),
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",  (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
    ]))
    els += [score_table, Spacer(1, 12)]

    # ── Executive summary ─────────────────────────────────────────────────────
    els += [
        Paragraph("Executive Summary", S["h2"]),
        Paragraph(report.executive_summary, S["body"]),
        Spacer(1, 6),
        Paragraph(f"<b>Rating:</b> {m.rating}  |  <b>Readiness:</b> {m.readiness_level}  |  <b>Response Quality:</b> {m.response_quality_score}/100", S["body"]),
        Spacer(1, 10),
    ]

    # ── Score bars ────────────────────────────────────────────────────────────
    els.append(Paragraph("Performance Breakdown", S["h2"]))
    bar_metrics = [
        ("Overall Score",          m.overall_score),
        ("Engagement",             m.engagement_score),
        ("Professionalism",        m.professionalism_score),
        ("Communication",          m.communication_score),
        ("Voice Confidence",       m.voice_confidence_score),
        ("Eye Contact",            round(m.eye_contact_percentage)),
        ("Attention",              m.attention_score),
        ("Posture",                m.posture_score),
        ("Professional Presence",  m.professional_presence_score),
        ("Interview Readiness",    m.interview_readiness_score),
    ]
    for label, val in bar_metrics:
        els.append(_score_bar(label, val))
    els.append(Spacer(1, 10))

    # ── Communication ─────────────────────────────────────────────────────────
    els.append(Paragraph("Communication Analysis", S["h2"]))
    comm_data = [
        ["Metric", "Value", "Benchmark"],
        ["Speaking Rate",     f"{m.speaking_rate_wpm:.0f} WPM", "120–170 WPM"],
        ["Vocabulary Diversity", f"{m.vocabulary_diversity:.2f}", "> 0.65"],
        ["Filler Words",     str(m.filler_word_count),  "< 5"],
        ["Filler Rate",      f"{m.filler_rate:.1f}%",    "< 2%"],
        ["Clarity Score",    str(m.clarity_score),       "> 75"],
        ["Fluency Score",    str(m.fluency_score),        "> 75"],
    ]
    comm_table = Table(comm_data, colWidths=[6*cm, 4*cm, 5*cm])
    comm_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_PRIMARY),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_LIGHT, colors.white]),
        ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
    ]))
    els += [comm_table, Spacer(1, 10)]

    # ── Strengths ─────────────────────────────────────────────────────────────
    els.append(Paragraph("Identified Strengths", S["h2"]))
    for s in report.strengths:
        els.append(Paragraph(f"✓  {s}", S["bullet"]))
    els.append(Spacer(1, 8))

    # ── Improvements ─────────────────────────────────────────────────────────
    els.append(Paragraph("Areas for Improvement", S["h2"]))
    for imp in report.improvements:
        els.append(Paragraph(f"•  {imp}", S["bullet"]))
    els.append(Spacer(1, 8))

    # ── Coaching plan ─────────────────────────────────────────────────────────
    els.append(Paragraph("Personalised Coaching Plan", S["h2"]))
    for item in report.coaching_plan[:6]:
        els.append(KeepTogether([
            Paragraph(f"<b>{item.get('priority','')}.  {item.get('area','')}</b> "
                      f"<font color='#6c757d'>({item.get('timeframe','')})</font>", S["h3"]),
            Paragraph(item.get("action", ""), S["body"]),
            Paragraph(f"<i>Expected impact: {item.get('expected_impact','')}</i>", S["small"]),
            Spacer(1, 4),
        ]))

    # ── HR perspective ────────────────────────────────────────────────────────
    els += [
        Paragraph("HR Perspective", S["h2"]),
        Paragraph(f'<i>"{report.hr_perspective}"</i>', S["body"]),
        Spacer(1, 8),
    ]

    # ── Transcript snippet ────────────────────────────────────────────────────
    if report.transcript:
        snippet = report.transcript[:400] + ("…" if len(report.transcript) > 400 else "")
        els += [
            Paragraph("Transcript (excerpt)", S["h2"]),
            Paragraph(snippet, S["small"]),
            Spacer(1, 8),
        ]

    # ── Footer note ───────────────────────────────────────────────────────────
    els += [
        HRFlowable(width="100%", color=C_BORDER, thickness=0.5),
        Paragraph(
            "Generated by AI-Powered Multimodal Interview Behavioral Analysis System  •  "
            f"Session {report.session_id}",
            S["small"],
        ),
    ]

    doc.build(els)
    return buf.getvalue()
