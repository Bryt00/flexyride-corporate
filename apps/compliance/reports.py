"""
Paystack Compliance Evidence Report Generator for FlexyRide Corporate.
Generates an official, verifiable PDF compliance evidence report using ReportLab (Section 11).
"""

import io
from django.utils import timezone
from compliance.models import ComplianceAuditLog

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def generate_compliance_report_pdf(provider, redact=False, buffer=None):
    """
    Builds a professional compliance evidence PDF report for a transport provider.
    Includes operating licence details, Paystack subaccount verification,
    vehicle roadworthiness matrix, and audit trail with optional PII redaction.
    """
    if not HAS_REPORTLAB:
        raise ImportError(
            "The 'reportlab' package is required to generate compliance evidence PDFs. "
            "Please install it in your virtualenv: pip install reportlab"
        )

    if buffer is None:
        buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Brand Colors
    brand_green = colors.HexColor('#8CC63F')
    brand_dark = colors.HexColor('#0A0F1D')
    text_dark = colors.HexColor('#1E293B')
    text_muted = colors.HexColor('#64748B')
    bg_light = colors.HexColor('#F8FAFC')
    border_color = colors.HexColor('#E2E8F0')
    status_green = colors.HexColor('#10B981')
    status_red = colors.HexColor('#EF4444')
    status_amber = colors.HexColor('#F59E0B')

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=brand_dark
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=text_muted
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=brand_dark,
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=text_dark
    )
    body_bold = ParagraphStyle(
        'DocBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    table_cell = ParagraphStyle(
        'TableCell',
        parent=body_style,
        fontSize=8,
        leading=10
    )
    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=body_bold,
        fontSize=8,
        leading=10
    )
    badge_style = ParagraphStyle(
        'Badge',
        parent=body_bold,
        fontSize=8,
        alignment=1
    )

    story = []

    # ================= Header Banner =================
    header_data = [
        [
            Paragraph("<b>FLEXYRIDE CORPORATE</b><br/><font size=7 color='#64748b'>Enterprise Transport Logistics & Compliance Vault</font>", title_style),
            Paragraph(f"<b>COMPLIANCE EVIDENCE REPORT</b><br/><font size=7 color='#64748b'>Report Ref: FRC-COMP-{provider.id:04d}-{timezone.now().strftime('%Y%m%d')}<br/>Generated: {timezone.now().strftime('%Y-%m-%d %H:%M UTC')}</font>", ParagraphStyle('HRight', parent=subtitle_style, alignment=2))
        ]
    ]
    header_table = Table(header_data, colWidths=[280, 260])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=brand_green, spaceBefore=4, spaceAfter=10))

    # ================= Section 1: Provider Compliance Profile =================
    story.append(Paragraph("1. Transport Provider Compliance Profile", section_heading))

    # PII Redaction
    contact_person = "••••••••••••" if redact else provider.contact_person
    phone = "•••• •••• •••" if redact else provider.phone
    email = "••••••••@••••.com" if redact else provider.email
    address = "••••••••••••••••••••" if redact else (provider.address or 'Accra, Ghana')

    overall_status = provider.compliance_status
    status_color = status_green if overall_status == 'VERIFIED' else (status_red if overall_status in ['EXPIRED', 'SUSPENDED'] else status_amber)

    provider_info = [
        [
            Paragraph("<b>Provider / Business Name:</b>", table_cell),
            Paragraph(provider.company_name, table_cell_bold),
            Paragraph("<b>Provider ID:</b>", table_cell),
            Paragraph(f"FRC-PROV-{provider.id:04d}", table_cell_bold)
        ],
        [
            Paragraph("<b>Business Registration #:</b>", table_cell),
            Paragraph(provider.registration_number or "N/A (Pending)", table_cell),
            Paragraph("<b>Overall Compliance Status:</b>", table_cell),
            Paragraph(f"<font color='{status_color.hexval()}'><b>{overall_status}</b></font>", table_cell_bold)
        ],
        [
            Paragraph("<b>Authorised Contact:</b>", table_cell),
            Paragraph(contact_person, table_cell),
            Paragraph("<b>Primary Telephone:</b>", table_cell),
            Paragraph(phone, table_cell)
        ],
        [
            Paragraph("<b>Official Email:</b>", table_cell),
            Paragraph(email, table_cell),
            Paragraph("<b>Operational Base:</b>", table_cell),
            Paragraph(address, table_cell)
        ]
    ]
    t_prov = Table(provider_info, colWidths=[130, 140, 130, 140])
    t_prov.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_light),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_prov)
    story.append(Spacer(1, 10))

    # ================= Section 2: Paystack Subaccount Integration =================
    story.append(Paragraph("2. Paystack Subaccount & Split Payment Verification", section_heading))

    sub_status = "Active & Configured" if provider.paystack_ready else "Pending Setup"
    sub_color = status_green if provider.paystack_ready else status_amber
    acct_masked = provider.masked_account_number if redact else (provider.account_number or 'Unconfigured')

    paystack_info = [
        [
            Paragraph("<b>Paystack Subaccount Code:</b>", table_cell),
            Paragraph(f"<font face='Courier-Bold'>{provider.paystack_subaccount_code or 'ACCT_UNCONFIGURED'}</font>", table_cell),
            Paragraph("<b>Subaccount Status:</b>", table_cell),
            Paragraph(f"<font color='{sub_color.hexval()}'><b>{sub_status}</b></font>", table_cell_bold)
        ],
        [
            Paragraph("<b>Settlement Bank / MoMo:</b>", table_cell),
            Paragraph(provider.settlement_bank_name or provider.settlement_bank or "Not specified", table_cell),
            Paragraph("<b>Settlement Account:</b>", table_cell),
            Paragraph(acct_masked, table_cell)
        ],
        [
            Paragraph("<b>Platform Service Margin:</b>", table_cell),
            Paragraph(f"{provider.percentage_charge or 0}% Split Deduction", table_cell),
            Paragraph("<b>Payment Eligibility:</b>", table_cell),
            Paragraph("Eligible for Direct Split Payouts" if provider.paystack_ready else "Blocked (Setup Required)", table_cell)
        ]
    ]
    t_paystack = Table(paystack_info, colWidths=[130, 140, 130, 140])
    t_paystack.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_light),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_paystack)
    story.append(Spacer(1, 10))

    # ================= Section 3: Commercial Operator Licence =================
    story.append(Paragraph("3. Commercial Vehicle Operator Licence (Provider Level)", section_heading))

    op_lic = provider.operator_license
    if op_lic:
        lic_status_color = status_green if op_lic.is_compliant() else (status_red if op_lic.is_expired else status_amber)
        lic_info = [
            [
                Paragraph("<b>Licence Reference #:</b>", table_cell),
                Paragraph(f"<font face='Courier-Bold'>{op_lic.document_number or 'N/A'}</font>", table_cell),
                Paragraph("<b>Issuing Authority:</b>", table_cell),
                Paragraph(op_lic.issuing_authority or "DVLA / NRSA Ghana", table_cell)
            ],
            [
                Paragraph("<b>Issue Date:</b>", table_cell),
                Paragraph(str(op_lic.issue_date) if op_lic.issue_date else "Not stated", table_cell),
                Paragraph("<b>Expiry Date:</b>", table_cell),
                Paragraph(f"<b>{op_lic.expiry_date}</b>" if op_lic.expiry_date else "Permanent", table_cell)
            ],
            [
                Paragraph("<b>Verification Status:</b>", table_cell),
                Paragraph(f"<font color='{lic_status_color.hexval()}'><b>{op_lic.get_status_display()}</b></font>", table_cell_bold),
                Paragraph("<b>Last Verified:</b>", table_cell),
                Paragraph(f"{op_lic.verified_at.strftime('%Y-%m-%d %H:%M') if op_lic.verified_at else 'Pending Audit'}", table_cell)
            ],
            [
                Paragraph("<b>Reviewing Admin:</b>", table_cell),
                Paragraph(op_lic.verified_by.username if op_lic.verified_by else "System / Unverified", table_cell),
                Paragraph("<b>Audit Notes:</b>", table_cell),
                Paragraph(op_lic.notes or "Document on file in private compliance storage.", table_cell)
            ]
        ]
    else:
        lic_info = [
            [
                Paragraph("<font color='red'><b>NO COMMERCIAL OPERATOR LICENCE ON FILE</b></font><br/>Provider has not submitted a valid Commercial Vehicle Operator Licence. Bookings are automatically blocked.", table_cell),
                Paragraph("", table_cell),
                Paragraph("", table_cell),
                Paragraph("", table_cell)
            ]
        ]
    t_lic = Table(lic_info, colWidths=[130, 140, 130, 140])
    t_lic.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_light),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_lic)
    story.append(Spacer(1, 10))

    # ================= Section 4: Vehicle-Level Compliance Matrix =================
    story.append(Paragraph("4. Linked Commercial Fleet Vehicles Compliance Matrix", section_heading))

    veh_rows = [
        [
            Paragraph("<b>Plate #</b>", table_cell_bold),
            Paragraph("<b>Make / Model</b>", table_cell_bold),
            Paragraph("<b>Category</b>", table_cell_bold),
            Paragraph("<b>Registration Doc</b>", table_cell_bold),
            Paragraph("<b>Roadworthiness Cert</b>", table_cell_bold),
            Paragraph("<b>Roadworthy Expiry</b>", table_cell_bold),
            Paragraph("<b>Status</b>", table_cell_bold)
        ]
    ]

    vehicles = provider.vehicles.all()
    if vehicles.exists():
        for v in vehicles:
            reg_doc = v.registration_document
            rw_doc = v.roadworthiness_document

            reg_text = f"Attached ({reg_doc.get_status_display()})" if reg_doc else "Missing"
            rw_text = f"Attached ({rw_doc.get_status_display()})" if rw_doc else "Missing"
            rw_expiry = str(rw_doc.expiry_date) if (rw_doc and rw_doc.expiry_date) else "--"

            v_comp = v.get_compliance_status_display()
            v_color = status_green if 'Compliant' in v_comp or 'Verified' in v_comp else status_red

            veh_rows.append([
                Paragraph(f"<font face='Courier-Bold'>{v.registration_number}</font>", table_cell),
                Paragraph(f"{v.make} {v.model}", table_cell),
                Paragraph(v.get_category_display(), table_cell),
                Paragraph(reg_text, table_cell),
                Paragraph(rw_text, table_cell),
                Paragraph(rw_expiry, table_cell),
                Paragraph(f"<font color='{v_color.hexval()}'><b>{v_comp}</b></font>", table_cell)
            ])
    else:
        veh_rows.append([
            Paragraph("No commercial vehicles currently registered under this transport provider.", table_cell),
            Paragraph("", table_cell), Paragraph("", table_cell), Paragraph("", table_cell),
            Paragraph("", table_cell), Paragraph("", table_cell), Paragraph("", table_cell)
        ])

    t_veh = Table(veh_rows, colWidths=[65, 85, 75, 80, 85, 80, 70])
    t_veh.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_veh)
    story.append(Spacer(1, 10))

    # ================= Section 5: Recent Audit Trail =================
    story.append(Paragraph("5. Compliance Audit Trail (Recent Activity)", section_heading))

    logs = ComplianceAuditLog.objects.filter(provider=provider).order_by('-created_at')[:5]
    log_rows = [
        [
            Paragraph("<b>Timestamp (UTC)</b>", table_cell_bold),
            Paragraph("<b>Action</b>", table_cell_bold),
            Paragraph("<b>Target Entity</b>", table_cell_bold),
            Paragraph("<b>Actor</b>", table_cell_bold),
            Paragraph("<b>Notes / Verification Reason</b>", table_cell_bold)
        ]
    ]
    if logs.exists():
        for l in logs:
            target_str = l.vehicle.registration_number if l.vehicle else (provider.company_name)
            log_rows.append([
                Paragraph(l.created_at.strftime('%Y-%m-%d %H:%M'), table_cell),
                Paragraph(l.get_action_display(), table_cell_bold),
                Paragraph(target_str, table_cell),
                Paragraph(l.actor.username if l.actor else "System Task", table_cell),
                Paragraph(l.notes or "--", table_cell)
            ])
    else:
        log_rows.append([
            Paragraph("No compliance audit entries recorded yet.", table_cell),
            Paragraph("", table_cell), Paragraph("", table_cell),
            Paragraph("", table_cell), Paragraph("", table_cell)
        ])

    t_log = Table(log_rows, colWidths=[75, 110, 80, 75, 200])
    t_log.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_log)
    story.append(Spacer(1, 15))

    # ================= Certification Sign-off Block =================
    sign_block = [
        [
            Paragraph(
                "<b>COMPLIANCE OFFICER VERIFICATION & SIGN-OFF:</b><br/>"
                "I hereby confirm that all regulatory documents listed above have been collected, cross-checked against DVLA/NRSA guidelines, "
                "and securely archived within the FlexyRide Corporate Compliance Vault. Non-compliant and expired units are automatically barred from dispatch.",
                subtitle_style
            ),
            Paragraph(
                "<b>FLEXYRIDE COMPLIANCE DESK</b><br/>"
                "Verified & Sealed Electronically<br/>"
                f"<font color='#8CC63F'><b>STATUS: {overall_status}</b></font>",
                ParagraphStyle('SignRight', parent=subtitle_style, alignment=2)
            )
        ]
    ]
    t_sign = Table(sign_block, colWidths=[360, 180])
    t_sign.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEABOVE', (0, 0), (-1, -1), 1, brand_green),
    ]))
    story.append(t_sign)

    doc.build(story)
    buffer.seek(0)
    return buffer

