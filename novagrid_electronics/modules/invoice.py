"""
NovaGrid Electronics - PDF Invoice Generator
Builds a clean, single-page GST tax invoice for a completed order using
reportlab (a pure-Python PDF writer — no external binaries needed).
Called right after checkout so the shopper can download a real invoice
with invoice number, customer name, itemized products, GST, discount,
payment method and a date/time stamp.
"""

import io
import json
import datetime as dt

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

PURPLE = colors.HexColor("#5B2E9E")
EMERALD = colors.HexColor("#12B886")
CORAL = colors.HexColor("#FF6F91")
GOLD = colors.HexColor("#B8873F")
MUTED = colors.HexColor("#6B6478")
INK = colors.HexColor("#241B3D")


def _fmt_inr(amount):
    amount = float(amount or 0)
    s = f"{amount:,.2f}"
    return f"Rs. {s}"


def _plain_text(s):
    """Strip emoji/non-ASCII glyphs (e.g. the payment-method icons used in
    the UI radio buttons) — reportlab's default font can't render them and
    would otherwise print as a black square box."""
    if not s:
        return ""
    return " ".join(ch for ch in s if ord(ch) < 128).strip()


def build_invoice_pdf(order):
    """Returns PDF bytes for the given Order record. `order.items_json` is
    the same structure checkout_cart() writes: a list of
    {product_id, name, quantity, price} dicts — no schema changes needed."""
    buf = io.BytesIO()
    invoice_number = f"INV-{order.order_number}"
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=22 * mm, rightMargin=22 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title=f"Invoice {invoice_number}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], textColor=INK,
                                  fontSize=22, spaceAfter=0)
    tagline_style = ParagraphStyle("Tagline", parent=styles["Normal"], textColor=PURPLE,
                                    fontSize=10, spaceAfter=0)
    label_style = ParagraphStyle("Label", parent=styles["Normal"], textColor=MUTED, fontSize=9)
    value_style = ParagraphStyle("Value", parent=styles["Normal"], textColor=INK, fontSize=11,
                                  leading=14)
    section_style = ParagraphStyle("Section", parent=styles["Heading3"], textColor=INK,
                                    fontSize=12, spaceBefore=14, spaceAfter=6)

    story = []
    story.append(Paragraph("NOVAGRID <font color='#5B2E9E'>ELECTRONICS</font>", title_style))
    story.append(Paragraph("Premium Retail. Intelligently Connected.", tagline_style))
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=1.2, color=PURPLE))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("TAX INVOICE", section_style))
    now = dt.datetime.utcnow()
    meta_table = Table(
        [
            [Paragraph("Invoice Number", label_style), Paragraph("Order Number", label_style),
             Paragraph("Date &amp; Time", label_style)],
            [Paragraph(f"<b>{invoice_number}</b>", value_style),
             Paragraph(order.order_number, value_style),
             Paragraph(order.created_at.strftime("%d %b %Y, %I:%M %p") + " UTC", value_style)],
        ],
        colWidths=[55 * mm, 55 * mm, 60 * mm],
    )
    meta_table.setStyle(TableStyle([
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph(f"Billed To: <b>{_plain_text(order.customer_name) or 'Guest Customer'}</b>",
                            label_style))
    if order.customer_phone:
        story.append(Paragraph(f"Mobile: <b>{_plain_text(order.customer_phone)}</b>", label_style))
    if order.customer_email:
        story.append(Paragraph(f"Email: <b>{_plain_text(order.customer_email)}</b>", label_style))
    if order.shipping_address:
        story.append(Paragraph(f"Shipping Address: {_plain_text(order.shipping_address)}", label_style))
    story.append(Paragraph(f"Payment Method: <b>{_plain_text(order.payment_method) or '-'}</b>",
                            label_style))
    story.append(Paragraph(f"Status: <b>{order.status}</b>", label_style))
    if order.estimated_delivery:
        story.append(Paragraph(
            f"Estimated Delivery: <b>{order.estimated_delivery.strftime('%d %b %Y')}</b>",
            label_style))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Order Items", section_style))
    try:
        items = json.loads(order.items_json or "[]")
    except (ValueError, TypeError):
        items = []

    header = ["#", "Item", "Qty", "Unit Price", "Amount"]
    rows = [header]
    for i, it in enumerate(items, start=1):
        qty = it.get("quantity", 1)
        price = it.get("price", 0)
        rows.append([
            str(i), it.get("name", "Item"), str(qty),
            _fmt_inr(price), _fmt_inr(price * qty),
        ])

    items_table = Table(rows, colWidths=[10 * mm, 78 * mm, 15 * mm, 33 * mm, 34 * mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F2FB")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E4DFF2")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6 * mm))

    summary_rows = [["", "Subtotal", _fmt_inr(order.subtotal_amount)]]
    if order.coupon_code:
        summary_rows.append(["", f"Coupon Discount ({order.coupon_code})",
                              f"- {_fmt_inr(order.discount_amount)}"])
    elif order.discount_amount:
        summary_rows.append(["", "Discount", f"- {_fmt_inr(order.discount_amount)}"])
    summary_rows.append(["", "GST (18%)", _fmt_inr(order.gst_amount)])
    summary_rows.append(["", "Final Total", _fmt_inr(order.total_amount)])

    summary_table = Table(summary_rows, colWidths=[78 * mm, 50 * mm, 42 * mm])
    style_cmds = [
        ("FONTSIZE", (1, 0), (-1, -1), 10.5),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TEXTCOLOR", (1, 0), (-1, -1), MUTED),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    last_row = len(summary_rows) - 1
    style_cmds += [
        ("FONTSIZE", (1, last_row), (-1, last_row), 13),
        ("FONTNAME", (1, last_row), (-1, last_row), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, last_row), (-1, last_row), EMERALD),
        ("LINEABOVE", (1, last_row), (-1, last_row), 1, INK),
        ("TOPPADDING", (0, last_row), (-1, last_row), 8),
    ]
    summary_table.setStyle(TableStyle(style_cmds))
    story.append(summary_table)
    story.append(Spacer(1, 12 * mm))

    story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#E4DFF2")))
    story.append(Spacer(1, 3 * mm))
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"], textColor=MUTED,
                                   fontSize=8.5, alignment=TA_CENTER)
    story.append(Paragraph(
        "This is a system-generated tax invoice for a demo transaction and does not represent "
        "a real payment. NovaGrid Electronics — support@novagridelectronics.example — "
        "1800-NOVAGRID (Toll-Free) — Bengaluru, India. GSTIN: 29NVGELEC1Z5.",
        footer_style,
    ))
    story.append(Paragraph(
        f"Generated on {now.strftime('%d %b %Y, %I:%M %p')} UTC", footer_style))

    doc.build(story)
    return buf.getvalue()
