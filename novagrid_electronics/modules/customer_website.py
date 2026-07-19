"""
NovaGrid Electronics - Customer Website Panel
Premium Nykaa + Apple + Reliance Digital + Croma inspired storefront:
white / soft lavender / purple / coral pink / emerald / soft gold design
system, glassmorphism cards, full-width hero slider, hover-reveal offer
panels, Quick View modal, wishlist, compare, recently viewed,
recommendations, reviews, trust badges, a 4-step single-confirmation
checkout with coupon codes and GST, and a full order celebration
(confetti + balloons + crackers + sound + congratulations popup).
Renders in the LEFT panel of the permanent 50/50 split. Reads live data
from the shared SQLite database so any admin change appears here on the
next rerun/refresh.
"""

import datetime as dt
import difflib
import html
import random
import re

import streamlit as st
import streamlit.components.v1 as components

from database.db_setup import get_session, Advertisement, TodaysDeal, VideoAd, Product, Review, Order
from modules.utils import (
    get_all_products, get_product, get_discount_rules, get_active_deal,
    add_to_cart, remove_from_cart, get_cart_items, checkout_cart,
    fmt_inr, image_data_uri, asset_abs_path, star_string, get_brands,
    get_wishlist_product_ids, toggle_wishlist, get_wishlist_items,
    record_product_view, get_recently_viewed, get_recommended_products,
    get_reviews, add_review, rating_breakdown,
    estimate_delivery_for_pincode, emi_options,
    get_compare_product_ids, toggle_compare, validate_coupon,
    get_active_coupons,
)
from modules.effects import (
    play_add_to_cart_sound, checkout_celebration, play_notification_sound,
    limited_stock_warning, out_of_stock_popup, flash_message,
    flash_sale_alert, todays_deal_popup, congratulations_popup,
)
from database.seed_data import GALLERY_LABELS
from modules.invoice import build_invoice_pdf

PAYMENT_METHODS = ["📱 UPI", "💳 Credit Card", "💳 Debit Card", "👛 Wallet",
                    "🏦 Net Banking", "💵 Cash on Delivery"]

CATEGORIES = ["All", "Smartphones", "Laptops", "Audio", "Televisions",
              "Wearables", "Home Appliances", "Gaming", "Cameras"]

CATEGORY_ICONS = {
    "Smartphones": "📱", "Laptops": "💻", "Audio": "🎧", "Televisions": "📺",
    "Wearables": "⌚", "Home Appliances": "🏠", "Gaming": "🎮", "Cameras": "📷",
}


# --------------------------------------------------------------------------- #
# SESSION STATE
# --------------------------------------------------------------------------- #
def _init_session_state():
    defaults = {
        "cart_session_id": "customer_demo_session",
        "selected_product_id": None,
        "highlight_product_id": None,
        "sound_enabled": True,
        "theme_mode": "light",
        "quickview_product_id": None,
        "gallery_index": {},
        "shown_alerts": False,
        "last_order": None,
        "checkout_step": "shipping",
        "checkout_shipping": {"name": "", "phone": "", "email": "", "address": "", "pincode": ""},
        "checkout_coupon_code": "",
        "checkout_coupon_discount": 0.0,
        "checkout_coupon_error": None,
        "newsletter_subscribed": False,
        "chatbot_open": False,
        "chat_history": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# --------------------------------------------------------------------------- #
# CSS THEME (white / soft lavender / purple / coral pink / emerald / gold)
# --------------------------------------------------------------------------- #
def _inject_customer_css():
    dark = st.session_state.get("theme_mode") == "dark"

    if dark:
        bg = "#150F24"; surface = "#1E1533"; card = "rgba(255,255,255,0.05)"
        text = "#F3EFFB"; subtext = "#B9AFD1"; border = "rgba(255,255,255,0.10)"
    else:
        bg = "#FAF8FC"; surface = "#FFFFFF"; card = "rgba(255,255,255,0.78)"
        text = "#2A1B4D"; subtext = "#6B6478"; border = "rgba(91,46,158,0.10)"

    ink = "#2A1B4D"
    purple = "#5B2E9E"
    purple_bright = "#7C4DFF"
    lavender = "#E8E1F7"
    coral = "#FF6F91"
    emerald = "#12B886"
    gold = "#B8873F"

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800;900&family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif;
            -webkit-font-smoothing: antialiased;
            letter-spacing: -0.01em;
        }}

        .novagrid-scope {{ color:{text}; }}

        @keyframes fadeInUp {{
            from {{ opacity:0; transform: translateY(10px); }}
            to {{ opacity:1; transform: translateY(0); }}
        }}
        .novagrid-scope .block-container, .novagrid-fade {{
            animation: fadeInUp 0.45s cubic-bezier(.22,1,.36,1) both;
        }}

        /* ---------------- Premium button system ---------------- */
        .stButton > button {{
            border-radius: 980px !important;
            font-weight: 600 !important;
            letter-spacing: -0.01em;
            transition: transform 0.16s cubic-bezier(.22,1,.36,1), box-shadow 0.16s ease, opacity 0.16s ease !important;
            border: 1px solid {border} !important;
        }}
        .stButton > button:hover {{
            transform: translateY(-1px) scale(1.012);
            box-shadow: 0 8px 20px rgba(91,46,158,0.16);
        }}
        .stButton > button:active {{ transform: translateY(0) scale(0.985); }}
        .stButton > button[kind="primary"] {{
            background: linear-gradient(180deg,{purple},#43227A) !important;
            border: none !important;
            box-shadow: 0 6px 16px rgba(91,46,158,0.32);
        }}
        .stButton > button[kind="primary"]:hover {{
            box-shadow: 0 10px 24px rgba(91,46,158,0.42);
        }}

        /* ---------------- Tabs ---------------- */
        .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 12px 12px 0 0; font-weight: 600; font-size: 13.5px;
        }}
        .stTabs [aria-selected="true"] {{ color:{purple} !important; }}

        /* ---------------- Main navigation (st.radio styled as tabs) ----------------
           The primary Home/Cart/Wishlist/... navigation is a real st.radio bound to
           session_state rather than st.tabs, specifically so that clicking the navbar
           cart/wishlist pills can switch the active section purely in Python (setting
           session_state before the widget is created) — no injected JS, no iframe
           timing race, so it can never silently fail to "wire up" the way a JS click
           bridge can in some browsers. */
        .st-key-ng_main_nav div[role="radiogroup"] {{
            gap: 4px; flex-wrap: wrap; row-gap: 6px;
            border-bottom: 2px solid {border}; margin-bottom: 10px; padding-bottom: 2px;
        }}
        .st-key-ng_main_nav label[data-testid="stRadioOption"] {{
            border-radius: 12px 12px 0 0 !important; padding: 8px 14px !important;
            font-weight: 600 !important; font-size: 13.5px !important; margin: 0 !important;
            background: transparent !important; cursor: pointer !important;
        }}
        .st-key-ng_main_nav label[data-testid="stRadioOption"][data-selected="true"] {{
            color: {purple} !important; background: rgba(124,77,255,0.08) !important;
        }}
        /* Hide the round radio-dot indicator so this reads as a tab strip */
        .st-key-ng_main_nav label[data-testid="stRadioOption"] > div > div > div:first-child {{
            display: none !important;
        }}

        /* ---------------- Inputs ---------------- */
        .stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"] > div {{
            border-radius: 12px !important;
        }}

        /* ---------------- Offer ticker ---------------- */
        .offer-ticker {{
            background: linear-gradient(90deg,{ink},{purple});
            color: white; padding: 9px 0; border-radius: 12px; margin-bottom: 14px;
            overflow: hidden; white-space: nowrap; font-weight: 600; font-size:13px;
        }}
        .offer-ticker span {{
            display: inline-block; padding-left: 100%;
            animation: ticker 20s linear infinite;
        }}
        @keyframes ticker {{ 0% {{ transform: translate(0,0); }} 100% {{ transform: translate(-100%,0); }} }}

        /* ---------------- Glass product card ---------------- */
        .glass-card {{
            background: {card};
            backdrop-filter: blur(12px);
            border: 1px solid {border};
            border-radius: 20px; padding: 14px; margin-bottom: 18px;
            transition: transform 0.28s cubic-bezier(.2,.8,.2,1), box-shadow 0.28s ease, border-color 0.3s ease;
            position: relative; overflow:hidden;
        }}
        .glass-card:hover {{
            transform: translateY(-6px);
            box-shadow: 0 18px 38px rgba(91,46,158,0.18);
            border-color: {purple_bright}55;
        }}
        .glass-card.pulse {{ animation: pulseGlow 0.6s ease; }}
        .glass-card.spotlight {{ border: 2px solid {purple_bright}; box-shadow: 0 0 0 6px {purple_bright}22; }}
        @keyframes pulseGlow {{
            0% {{ box-shadow: 0 0 0 0 {purple_bright}66; }}
            70% {{ box-shadow: 0 0 0 14px {purple_bright}00; }}
            100% {{ box-shadow: 0 0 0 0 {purple_bright}00; }}
        }}

        .zoom-frame {{
            overflow:hidden; border-radius:16px; margin-bottom:8px; position:relative;
            aspect-ratio: 1 / 1; background:{surface};
        }}
        .zoom-frame img {{
            width:100%; height:100%; object-fit:cover; display:block;
            transition: transform 0.6s cubic-bezier(.22,1,.36,1);
            border-radius:16px;
        }}
        .zoom-frame:hover img {{ transform: scale(1.08); }}
        .video-chip {{
            position:absolute; top:10px; right:10px; z-index:5;
            background:rgba(42,27,77,0.75); backdrop-filter: blur(6px); color:white;
            font-size:10.5px; font-weight:700; padding:4px 10px; border-radius:999px;
            letter-spacing:0.2px; pointer-events:none;
        }}
        /* ---------------- Hover-reveal offer panel (offers / qty discounts /
           cashback / warranty / video preview note) ---------------- */
        .zoom-frame .hover-overlay {{
            position:absolute; left:0; right:0; bottom:0; padding:10px 12px;
            background: linear-gradient(0deg, rgba(42,27,77,0.90), rgba(42,27,77,0));
            color:white; opacity:0; transform: translateY(8px);
            transition: opacity 0.3s ease, transform 0.3s ease; pointer-events:none;
            font-size:11px; font-weight:600; line-height:1.5;
        }}
        .zoom-frame:hover .hover-overlay {{ opacity:1; transform: translateY(0); }}
        .hover-overlay .ho-title {{ font-weight:800; font-size:12.5px; margin-bottom:3px; }}
        .hover-overlay .ho-line {{ display:block; }}

        /* ---------------- Flash / crazy retail announcement ticker ---------------- */
        @keyframes blinkAlert {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.55; }} }}
        .flash-announce {{
            background: repeating-linear-gradient(135deg,{coral},{coral} 12px,#E14F72 12px,#E14F72 24px);
            color:white; border-radius:12px; padding:10px 16px; margin-bottom:12px;
            font-weight:800; font-size:13px; text-align:center;
            animation: blinkAlert 1.3s ease-in-out infinite;
            box-shadow: 0 8px 20px rgba(255,111,145,0.35);
        }}

        /* ---------------- CRM chatbot widget ---------------- */
        .chat-bubble {{
            background:{card}; border:1px solid {border}; border-radius:12px;
            padding:10px 12px; margin-bottom:8px; font-size:13px; color:{text};
        }}
        .rating-badge {{
            display:inline-flex; align-items:center; gap:6px; background:{lavender}55;
            border:1px solid {purple_bright}66; color:{purple}; border-radius:10px;
            padding:6px 12px; font-weight:800; font-size:12.5px; margin:4px 0;
        }}

        .product-title {{ font-weight: 700; font-size: 15px; margin: 6px 0 2px 0; color: {text}; }}
        .product-brand {{ font-size: 11px; color:{subtext}; font-weight:600; text-transform:uppercase; letter-spacing:0.4px;}}
        .product-price {{ font-size: 19px; font-weight: 900; color: {ink}; }}
        .product-mrp {{ text-decoration: line-through; color: {subtext}; font-size: 13px; margin-left: 6px;}}
        .product-emi {{ font-size:11.5px; color:{emerald}; font-weight:700; margin-top:2px;}}

        .badge {{
            display: inline-block; padding: 3px 10px; border-radius: 20px;
            font-size: 10.5px; font-weight: 800; margin-right: 5px; margin-bottom: 4px;
            letter-spacing:0.2px;
        }}
        .badge-featured {{ background:{purple_bright}22; color:{purple}; }}
        .badge-bestseller {{ background:{gold}22; color:{gold}; }}
        .badge-new {{ background:{emerald}22; color:{emerald}; }}
        .badge-deal {{ background:{coral}22; color:{coral}; }}
        .badge-discount {{ background:{coral}; color:white; font-weight:800; }}
        .badge-instock {{ background:{emerald}22; color:{emerald}; }}
        .badge-lowstock {{ background:{gold}22; color:{gold}; }}
        .badge-outstock {{ background:#DC262622; color:#DC2626; }}
        .badge-cashback {{ background:{gold}22; color:{gold}; }}

        .hero-banner {{
            border-radius: 22px; overflow: hidden; margin-bottom: 16px;
            box-shadow: 0 16px 40px rgba(91,46,158,0.18); border:1px solid {border};
        }}
        .hero-banner img {{ width: 100%; display: block; }}

        .footer-box {{
            background: {ink}; border-radius: 20px; padding: 28px 22px;
            margin-top: 30px; color: #DCD5EC; font-size: 13px;
        }}
        .footer-box h4 {{ color:white; font-size:14px; margin-bottom:10px; }}
        .footer-box a {{ color:#DCD5EC; text-decoration:none; }}
        .footer-social {{ display:flex; gap:10px; margin-top:8px; }}
        .footer-social span {{
            background: rgba(255,255,255,0.08); border-radius:50%;
            width:34px; height:34px; display:flex; align-items:center; justify-content:center;
        }}

        .section-title {{
            font-family:'Poppins',sans-serif;
            font-size: 23px; font-weight: 800; margin: 26px 0 14px 0; color: {text};
            border-left: 5px solid {purple_bright}; padding-left: 12px; letter-spacing: -0.2px;
        }}
        .countdown-box {{
            background: linear-gradient(90deg,#E14F72,{coral});
            color: white; border-radius: 12px; padding: 8px 14px;
            font-weight: 700; text-align:center; margin-bottom: 10px; font-size:12.5px;
        }}
        .festival-banner {{
            background: linear-gradient(120deg,{coral},{purple} 60%,{ink});
            border-radius:20px; padding:26px 24px; color:white; margin-bottom:18px;
            box-shadow: 0 14px 30px rgba(124,77,255,0.28);
        }}
        .festival-banner h2 {{ margin:0 0 4px 0; font-family:'Poppins',sans-serif; font-size:24px;}}

        .review-bar-track {{ background:{border}; border-radius:6px; height:8px; flex:1; }}
        .review-bar-fill {{ background:{purple_bright}; border-radius:6px; height:8px; }}

        .sticky-cart {{
            position: sticky; bottom: 8px; z-index: 900;
            background:{ink}; color:white; border-radius:16px; padding:10px 16px;
            display:flex; justify-content:space-between; align-items:center;
            box-shadow:0 10px 26px rgba(42,27,77,0.35); margin-top:14px; font-weight:700;
        }}

        /* ---------------- Trust stat bar ---------------- */
        .stat-card {{
            text-align:center; background:{card}; backdrop-filter: blur(10px);
            border:1px solid {border}; border-radius:16px; padding:16px 10px;
            margin-bottom:14px; transition: transform 0.22s cubic-bezier(.22,1,.36,1);
        }}
        .stat-card:hover {{ transform: translateY(-3px); }}
        .stat-icon {{ font-size:22px; margin-bottom:4px; }}
        .stat-value {{ font-family:'Poppins',sans-serif; font-size:23px; font-weight:900; color:{ink}; }}
        .stat-label {{
            font-size:10.5px; color:{subtext}; font-weight:700; text-transform:uppercase;
            letter-spacing:0.4px; margin-top:2px;
        }}

        /* ---------------- Testimonials ---------------- */
        .testimonial-row {{
            display:flex; gap:14px; overflow-x:auto; padding: 4px 2px 16px 2px;
            scroll-snap-type:x mandatory;
        }}
        .testimonial-card {{
            flex:0 0 260px; scroll-snap-align:start;
            background:{card}; backdrop-filter:blur(10px); border:1px solid {border};
            border-radius:16px; padding:16px;
            box-shadow:0 8px 20px rgba(91,46,158,0.08);
        }}
        .testimonial-stars {{ color:{gold}; font-size:13px; margin-bottom:6px; }}
        .testimonial-title {{ font-weight:800; font-size:13.5px; color:{text}; margin-bottom:6px; }}
        .testimonial-comment {{
            font-size:12.5px; color:{subtext}; line-height:1.5; margin-bottom:10px; min-height:56px;
        }}
        .testimonial-footer {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
        .testimonial-name {{ font-weight:700; font-size:12px; color:{text}; }}
        .testimonial-verified {{ font-size:10px; color:{emerald}; font-weight:700; }}
        .testimonial-product {{ font-size:11px; color:{purple}; font-weight:600; margin-top:4px; }}

        /* ---------------- Popular Brands strip ---------------- */
        .brand-strip {{ display:flex; gap:12px; overflow-x:auto; padding: 4px 2px 14px 2px; }}
        .brand-chip {{
            flex:0 0 auto; background:{card}; border:1px solid {border}; border-radius:14px;
            padding:14px 20px; text-align:center; min-width:120px;
        }}
        .brand-chip .bc-name {{ font-weight:800; font-size:13.5px; color:{text}; }}
        .brand-chip .bc-count {{ font-size:10.5px; color:{subtext}; font-weight:600; margin-top:2px; }}

        /* ---------------- Newsletter ---------------- */
        .newsletter-box {{
            background: linear-gradient(120deg,{purple},{purple_bright});
            border-radius:20px; padding:28px 26px; color:white; margin: 20px 0;
            text-align:center;
        }}
        .newsletter-box h3 {{ margin:0 0 4px 0; font-family:'Poppins',sans-serif; font-size:21px; }}
        .newsletter-box p {{ margin:0 0 14px 0; opacity:0.92; font-size:13px; }}

        /* ---------------- Payment badges (footer) ---------------- */
        .payment-badges {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:6px; }}
        .pay-badge {{
            background: rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.16);
            border-radius:8px; padding:4px 9px; font-size:11px; font-weight:700; color:#EDE9F7;
        }}

        /* ---------------- Checkout stepper ---------------- */
        .checkout-stepper {{ display:flex; align-items:center; justify-content:center; margin: 6px 0 22px 0; flex-wrap:wrap; }}
        .checkout-step {{ display:flex; flex-direction:column; align-items:center; gap:6px; }}
        .checkout-step-circle {{
            width:34px; height:34px; border-radius:50%; display:flex; align-items:center;
            justify-content:center; font-weight:800; font-size:14px; border:2px solid {border};
            color:{subtext}; background:{surface};
        }}
        .checkout-step.active .checkout-step-circle {{
            border-color:{purple_bright}; color:white; background:{purple_bright};
            box-shadow:0 4px 14px {purple_bright}55;
        }}
        .checkout-step.done .checkout-step-circle {{
            border-color:{purple_bright}; color:{purple}; background:{purple_bright}22;
        }}
        .checkout-step-label {{
            font-size:10.5px; font-weight:700; color:{subtext}; text-transform:uppercase;
            letter-spacing:0.4px;
        }}
        .checkout-step.active .checkout-step-label, .checkout-step.done .checkout-step-label {{ color:{text}; }}
        .checkout-step-line {{ width:44px; height:2px; background:{border}; margin: 0 6px 20px 6px; }}
        .checkout-step-line.done {{ background:{purple_bright}; }}

        /* ---------------- Frequently bought together ---------------- */
        .fbt-box {{
            background:{card}; border:1px solid {border}; border-radius:14px;
            padding:14px; margin: 10px 0;
        }}
        .urgency-line {{
            color:{coral}; font-weight:700; font-size:12px; margin: 4px 0 2px 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# NAVBAR / TICKER / TRUST ROW
# --------------------------------------------------------------------------- #
def get_header_counts():
    """Called from app.py so the shared top header (above both panels) can
    show live wishlist/cart counts before the customer panel itself has run
    this rerun. Keeps DB access self-contained to this module."""
    _init_session_state()
    session = get_session()
    try:
        wishlist_count = len(get_wishlist_items(session, st.session_state["cart_session_id"]))
        cart_count = len(get_cart_items(session, st.session_state["cart_session_id"]))
    finally:
        session.close()
    return wishlist_count, cart_count


def _navbar(session):
    # The brand name and the wishlist/cart buttons now live in the single
    # shared header at the very top of the page (app.py), above both the
    # Customer Website and Admin Dashboard panels, so they aren't repeated
    # in here — this row is just the per-panel sound/theme controls.
    c1, c2, c3 = st.columns([1, 1, 4])
    with c1:
        if st.button("🔊 Sound" if st.session_state["sound_enabled"] else "🔇 Muted",
                      key="sound_toggle_btn", use_container_width=True):
            st.session_state["sound_enabled"] = not st.session_state["sound_enabled"]
            st.rerun()
    with c2:
        if st.button("🌙 Dark" if st.session_state["theme_mode"] == "light" else "☀️ Light",
                      key="theme_toggle_btn", use_container_width=True):
            st.session_state["theme_mode"] = "dark" if st.session_state["theme_mode"] == "light" else "light"
            st.rerun()


def _offer_ticker():
    st.markdown(
        """
        <div class="offer-ticker">
        <span>🔥 NovaGrid Festival — Up to 40% OFF &nbsp;&nbsp;|&nbsp;&nbsp;
        💳 No-Cost EMI Available &nbsp;&nbsp;|&nbsp;&nbsp;
        🚚 Free Delivery on Orders Above ₹999 &nbsp;&nbsp;|&nbsp;&nbsp;
        💰 Cashback on Select Products &nbsp;&nbsp;|&nbsp;&nbsp;
        🎉 Buy More, Save More — Today Only! &nbsp;&nbsp;|&nbsp;&nbsp;
        ⭐ Genuine Products, Trusted Warranty</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


_TRUST_BADGE_DETAILS = {
    "Secure Payments": (
        "🔒",
        "All payments are protected with 256-bit SSL encryption. We support UPI, Credit "
        "& Debit Cards, Net Banking, Wallets and No-Cost EMI — your payment details are "
        "never stored on our servers."
    ),
    "100% Genuine Products": (
        "✅",
        "Every product sold on NovaGrid Electronics is 100% genuine, sourced directly "
        "from authorized brands and distributors, and backed by the full manufacturer "
        "warranty listed on each product page."
    ),
    "7-Day Easy Returns": (
        "↩️",
        "Not the right fit? Eligible products can be returned within 7 days of "
        "delivery for a full refund or replacement, as long as they're unused and in "
        "original packaging. See the Terms & Conditions tab for the full policy."
    ),
    "24/7 Customer Support": (
        "🎧",
        "Our support team is available around the clock. Call our toll-free line at "
        "1800-NOVAGRID, email support@novagridelectronics.example, or open live chat "
        "below right now."
    ),
    "Free & Fast Delivery": (
        "🚚",
        "Enjoy free delivery on all orders above ₹999. Most orders are dispatched "
        "same-day and arrive within 1-5 days depending on your pincode — check exact "
        "ETA on any product's Quick View."
    ),
    "Committed Delivery Dates": (
        "📦",
        "We show a firm estimated delivery date at checkout and stand behind it. "
        "Track any order's status and delivery estimate from the Cart tab after "
        "checkout."
    ),
}


def _trust_badges():
    """Clickable trust badges. Deliberately implemented with plain
    st.button() + an in-flow detail panel (rather than st.popover) so the
    detail content always renders directly in the page, with no floating/
    portal positioning that could get clipped or mispositioned inside the
    app's fixed-height scrollable panels."""
    labels = list(_TRUST_BADGE_DETAILS.keys())
    if "active_trust_badge" not in st.session_state:
        st.session_state["active_trust_badge"] = None

    cols = st.columns(len(labels))
    for col, label in zip(cols, labels):
        icon, detail = _TRUST_BADGE_DETAILS[label]
        is_active = st.session_state["active_trust_badge"] == label
        with col:
            if st.button(f"{icon}  {label}", key=f"trust_badge_{label}",
                         use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state["active_trust_badge"] = None if is_active else label
                st.rerun()

    active = st.session_state["active_trust_badge"]
    if active:
        icon, detail = _TRUST_BADGE_DETAILS[active]
        with st.container(border=True):
            st.markdown(f"**{icon} {active}**")
            st.write(detail)
            if active == "24/7 Customer Support":
                if st.button("💬 Open Live Chat", key="trust_open_chat",
                              use_container_width=True):
                    st.session_state["chatbot_open"] = True
                    st.session_state["active_trust_badge"] = None
                    st.rerun()


def _flash_announcement_ticker(session):
    messages = []
    deals = session.query(TodaysDeal).filter(TodaysDeal.is_active == True).all()
    for d in deals:
        if d.product and d.deal_discount_percent >= 20:
            messages.append(f"⚡ FLASH DEAL: {d.product.name} — extra {int(d.deal_discount_percent)}% OFF, today only!")
    low_stock = [p for p in get_all_products(session) if 0 < p.stock <= p.low_stock_threshold]
    for p in low_stock[:3]:
        messages.append(f"🔥 HURRY! Only {p.stock} left of {p.name}")
    out_of_stock = [p for p in get_all_products(session) if p.stock <= 0]
    for p in out_of_stock[:2]:
        messages.append(f"❌ {p.name} just sold out — restocking soon!")

    if not messages:
        return
    msg = random.choice(messages)
    st.markdown(f'<div class="flash-announce">📢 {msg}</div>', unsafe_allow_html=True)


_CHATBOT_FAQS = {
    "📦 Where is my order?": "Once your order is confirmed you'll receive a 2-way SMS "
        "with live tracking, and delivery is handled by our trusted logistics partner. "
        "You can also check status under Cart → Order Confirmation.",
    "🛡️ What's the warranty policy?": "Every product page lists its exact warranty "
        "duration under 'Warranty & Delivery'. Most electronics carry a 1-2 year brand "
        "warranty honored directly by NovaGrid or our authorized service partners.",
    "💳 How does EMI work?": "Select any product's Quick View and open 'EMI Options' — "
        "we offer 3, 6, 9 and 12-month no-cost EMI plans on eligible orders.",
    "💰 How does cashback work?": "Eligible products show a cashback badge on Quick "
        "View — cashback is credited to your NovaGrid Wallet within 7 days of delivery.",
    "↩️ How do returns work?": "Eligible products can be returned within 7 days of "
        "delivery if unused and in original packaging. Refunds are processed to your "
        "original payment method.",
}


def _kw(text, *keywords):
    """Word-boundary keyword match — plain substring checks are unsafe here
    because short support keywords like 'phone' or 'cod' are also fragments
    of real product names/words ('AirPhone', 'Smartphone', 'encode'...).
    \\b ensures 'phone' matches the word "phone" but not the tail of
    "AirPhone", so asking about a product never gets hijacked by an
    unrelated FAQ branch."""
    return any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in keywords)


def _chatbot_reply(session, user_msg):
    """Rule-based NovaGrid Assistant — no external API, no cost, works fully
    offline. Understands greetings/thanks, a broad set of support topics,
    can look up the shopper's own most recent order, quote live coupon
    codes from the DB, and do fuzzy product-name lookups for price/stock/
    rating — so it reads as a capable assistant without needing an LLM API
    key or network access."""
    lowered = user_msg.lower().strip()

    # Product-name lookup runs FIRST and only short-circuits into a support
    # FAQ if nothing matches — this keeps "AirPhone 15 price" or "FitBand
    # stock" from being hijacked by unrelated keyword branches below.
    products = get_all_products(session)
    names = [p.name for p in products]
    matched_name = None
    close = difflib.get_close_matches(user_msg, names, n=1, cutoff=0.45)
    if close:
        matched_name = close[0]
    else:
        stopwords = {"price", "stock", "cost", "does", "what", "how",
                     "much", "have", "any", "your", "about", "please"}
        words = set(w for w in re.findall(r"[a-z0-9]+", lowered)
                    if len(w) >= 4 and w not in stopwords)
        best, best_hits = None, 0
        for p in products:
            # Whole-word overlap only — a plain substring check would let
            # "phone" match inside the single token "airphone", which is
            # exactly the bug word-boundary matching above exists to avoid.
            pname_words = set(re.findall(r"[a-z0-9]+", p.name.lower()))
            hits = len(words & pname_words)
            if hits > best_hits:
                best, best_hits = p.name, hits
        if best_hits >= 1:
            matched_name = best

    if matched_name:
        p = next(pr for pr in products if pr.name == matched_name)
        if p.stock > p.low_stock_threshold:
            stock_line = "✅ In Stock"
        elif p.stock > 0:
            stock_line = f"⚠️ Only {p.stock} left"
        else:
            stock_line = "❌ Out of Stock"
        return (f"<b>{p.name}</b> — {fmt_inr(p.discounted_price)} "
                 f"(<s>{fmt_inr(p.price)}</s>, {int(p.discount_percent)}% off) · {stock_line} · "
                 f"⭐ {p.rating:.1f} ({p.review_count} reviews). Search for it under "
                 f"'Browse & Search' for full specs, gallery, video and reviews!")

    greetings = ("hi", "hello", "hey", "yo", "hola", "namaste")
    if lowered in greetings or any(lowered.startswith(g + " ") or lowered.startswith(g + "!")
                                    for g in greetings):
        return ("Hey there! 👋 I'm the NovaGrid Assistant. Ask me about your order, warranty, "
                 "EMI, cashback, returns, cancellations, coupon codes, payment methods — or "
                 "just type a product name and I'll pull up its live price and stock for you.")

    if _kw(lowered, "thank", "thanks", "thx", "thankyou"):
        return "You're very welcome! Anything else I can help with? 😊"

    last_order_no = st.session_state.get("last_order")
    if last_order_no and (("my order" in lowered) or ("order status" in lowered)
                           or ("track" in lowered and "order" in lowered)):
        order = session.query(Order).filter(Order.order_number == last_order_no).first()
        if order:
            eta = order.estimated_delivery.strftime("%d %b %Y") if order.estimated_delivery else "TBD"
            return (f"Your most recent order <b>{order.order_number}</b> is currently "
                     f"<b>{order.status}</b>. Estimated delivery: <b>{eta}</b>. Paid via "
                     f"{order.payment_method} for a total of {fmt_inr(order.total_amount)}.")

    if _kw(lowered, "cancel", "cancellation"):
        return ("You can cancel any order that hasn't shipped yet from the Cart tab's order "
                 "history — cancelling instantly restores stock and refunds to your original "
                 "payment method.")
    # Payment-method phrasing (incl. "cash on delivery") is checked before
    # the generic delivery/order FAQ below, since "cash ON DELIVERY" would
    # otherwise get misrouted by the word "delivery" alone.
    if _kw(lowered, "payment", "upi", "cod", "wallet") or "net banking" in lowered \
            or "credit card" in lowered or "debit card" in lowered \
            or "cash on delivery" in lowered:
        return ("We accept UPI, Credit Card, Debit Card, Wallet, Net Banking and Cash on "
                 "Delivery — pick your favorite at checkout.")
    if _kw(lowered, "delivery", "order", "track", "shipping", "shipped"):
        return _CHATBOT_FAQS["📦 Where is my order?"]
    if _kw(lowered, "warranty", "guarantee"):
        return _CHATBOT_FAQS["🛡️ What's the warranty policy?"]
    if _kw(lowered, "emi", "installment", "installments", "loan"):
        return _CHATBOT_FAQS["💳 How does EMI work?"]
    if _kw(lowered, "cashback"):
        return _CHATBOT_FAQS["💰 How does cashback work?"]
    if _kw(lowered, "return", "returns", "refund"):
        return _CHATBOT_FAQS["↩️ How do returns work?"]
    if _kw(lowered, "coupon", "promo", "voucher") or "discount code" in lowered:
        coupons = get_active_coupons(session)
        if coupons:
            codes = ", ".join(f"<b>{c.code}</b>" for c in coupons[:4])
            return f"We currently have these active coupon codes: {codes}. Apply one at checkout (Payment step)!"
        return "Check the Payment step at checkout for any currently active coupon codes."
    if _kw(lowered, "wishlist"):
        return "Tap the ♡ icon on any product card to save it to your Wishlist tab for later."
    if _kw(lowered, "compare", "comparison"):
        return ("Tap the compare icon on up to 4 products, then open the Compare tab to see "
                 "them side by side.")
    if _kw(lowered, "contact", "phone", "call", "email", "reach", "helpline"):
        return "📞 Toll-Free: 1800-NOVAGRID  |  ✉️ support@novagridelectronics.example — we're here 24/7."
    if _kw(lowered, "hour", "hours", "open", "timing", "timings"):
        return "Our support line and this chat are available 24/7 — the storefront never closes!"
    if _kw(lowered, "bye", "goodbye") or "see you" in lowered:
        return "Take care, and happy shopping! 🛍️"

    return ("I didn't quite catch that — try asking about your order, warranty, EMI, "
             "cashback, returns, cancellations, coupon codes, payment methods, or just type "
             "a product name. For anything urgent, call 1800-NOVAGRID.")


def _crm_chatbot(session):
    if "chatbot_open" not in st.session_state:
        st.session_state["chatbot_open"] = False
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    with st.expander("💬 NovaGrid Assistant — Ask me anything", expanded=st.session_state["chatbot_open"]):
        st.markdown(
            '<div class="rating-badge">⭐ 4.7 / 5 — Verified Customer Rating '
            '(12,400+ reviews)</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"📞 **Toll-Free:** 1800-NOVAGRID &nbsp;&nbsp;|&nbsp;&nbsp; "
                     f"✉️ support@novagridelectronics.example")
        st.caption("I can look up your order, active coupons, or any product's live price & "
                    "stock — or pick a quick topic below:")

        cols = st.columns(len(_CHATBOT_FAQS))
        for col, (question, answer) in zip(cols, _CHATBOT_FAQS.items()):
            with col:
                if st.button(question, key=f"faq_{question}", use_container_width=True):
                    st.session_state["chatbot_open"] = True
                    st.session_state["chat_history"].append(("bot", answer))
                    st.rerun()

        for role, text in st.session_state["chat_history"][-12:]:
            label = "You" if role == "user" else "NovaGrid Assistant"
            safe_text = html.escape(text) if role == "user" else text
            st.markdown(f'<div class="chat-bubble"><b>{label}:</b> {safe_text}</div>',
                        unsafe_allow_html=True)

        with st.form("chatbot_form", clear_on_submit=True):
            user_msg = st.text_input("Type your question", key="chatbot_user_msg",
                                      label_visibility="collapsed",
                                      placeholder="e.g. 'Where's my order?' or 'AirPhone 15 price'")
            sent = st.form_submit_button("Send ➤", use_container_width=True)

        if sent and user_msg.strip():
            st.session_state["chatbot_open"] = True
            reply = _chatbot_reply(session, user_msg.strip())
            st.session_state["chat_history"].append(("user", user_msg.strip()))
            st.session_state["chat_history"].append(("bot", reply))
            st.rerun()

        if st.session_state["chat_history"]:
            if st.button("🗑️ Clear chat", key="clear_chat_btn"):
                st.session_state["chat_history"] = []
                st.rerun()


# --------------------------------------------------------------------------- #
# HERO SLIDER (true client-side autoplay, no rerun needed)
# --------------------------------------------------------------------------- #
def _hero_slider(session):
    ads = session.query(Advertisement).filter(
        Advertisement.is_active == True, Advertisement.position == "hero").all()
    if not ads:
        return
    slides_html = ""
    dots_html = ""
    for i, ad in enumerate(ads):
        uri = image_data_uri(ad.image_path)
        active = "active" if i == 0 else ""
        slides_html += f"""
        <div class="vslide {active}">
            <img src="{uri}"/>
            <div class="vslide-caption">
                <div class="vslide-title">{ad.title}</div>
                <div class="vslide-sub">{ad.subtitle or ''}</div>
            </div>
        </div>"""
        dots_html += f'<span class="vdot {"on" if i == 0 else ""}"></span>'

    components.html(
        f"""
        <style>
        * {{ box-sizing:border-box; }}
        .vhero {{ position:relative; width:100%; border-radius:22px; overflow:hidden;
                  box-shadow:0 16px 40px rgba(91,46,158,0.24); aspect-ratio: 2.4/1; background:#2A1B4D; }}
        .vslide {{ position:absolute; inset:0; opacity:0; transition:opacity 1s ease; }}
        .vslide.active {{ opacity:1; }}
        .vslide img {{ width:100%; height:100%; object-fit:cover; display:block; }}
        .vslide-caption {{ position:absolute; left:26px; bottom:22px; color:white;
            text-shadow:0 2px 10px rgba(0,0,0,0.6); font-family:'Poppins',sans-serif; }}
        .vslide-title {{ font-size:22px; font-weight:800; }}
        .vslide-sub {{ font-size:13px; opacity:0.92; margin-top:2px; }}
        .vdots {{ position:absolute; bottom:14px; right:20px; display:flex; gap:6px; }}
        .vdot {{ width:8px; height:8px; border-radius:50%; background:rgba(255,255,255,0.45); }}
        .vdot.on {{ background:#7C4DFF; width:22px; border-radius:5px; transition:all .3s; }}
        </style>
        <div class="vhero">
            {slides_html}
            <div class="vdots">{dots_html}</div>
        </div>
        <script>
        (function() {{
            const slides = document.querySelectorAll('.vslide');
            const dots = document.querySelectorAll('.vdot');
            let idx = 0;
            setInterval(() => {{
                slides[idx].classList.remove('active');
                dots[idx].classList.remove('on');
                idx = (idx + 1) % slides.length;
                slides[idx].classList.add('active');
                dots[idx].classList.add('on');
            }}, 4000);
        }})();
        </script>
        """,
        height=340,
    )


def _flash_sale_banner(session):
    ad = session.query(Advertisement).filter(
        Advertisement.is_active == True, Advertisement.position == "flash").first()
    if not ad:
        return
    uri = image_data_uri(ad.image_path)
    st.markdown(
        f"""
        <div class="hero-banner" style="border:2px solid #FF6F91;">
            <img src="{uri}"/>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _festival_banner(session):
    ad = session.query(Advertisement).filter(
        Advertisement.is_active == True, Advertisement.position == "festival").first()
    if not ad:
        return
    st.markdown(
        f"""
        <div class="festival-banner">
            <h2>🎉 {ad.title}</h2>
            <div>{ad.subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _ad_banners(session):
    """Auto-rotating advertisement banners — a client-side fade carousel
    identical in mechanism to the hero slider, so no rerun is needed."""
    ads = session.query(Advertisement).filter(
        Advertisement.is_active == True, Advertisement.position == "banner").all()
    if not ads:
        return
    slides_html, dots_html = "", ""
    for i, ad in enumerate(ads):
        uri = image_data_uri(ad.image_path)
        active = "active" if i == 0 else ""
        slides_html += (f'<div class="ngad-slide {active}"><img src="{uri}"/>'
                         f'<div class="ngad-caption"><b>{ad.title}</b> — {ad.subtitle or ""}</div></div>')
        dots_html += f'<span class="ngad-dot {"on" if i == 0 else ""}"></span>'
    components.html(
        f"""
        <style>
        * {{ box-sizing:border-box; }}
        .ngad {{ position:relative; width:100%; border-radius:18px; overflow:hidden;
                 box-shadow:0 12px 28px rgba(91,46,158,0.16); aspect-ratio: 3.2/1; background:#241B3D; }}
        .ngad-slide {{ position:absolute; inset:0; opacity:0; transition:opacity 1s ease; }}
        .ngad-slide.active {{ opacity:1; }}
        .ngad-slide img {{ width:100%; height:100%; object-fit:cover; display:block; }}
        .ngad-caption {{ position:absolute; left:18px; bottom:12px; color:white; font-size:12.5px;
            text-shadow:0 2px 8px rgba(0,0,0,0.6); }}
        .ngad-dots {{ position:absolute; bottom:10px; right:14px; display:flex; gap:5px; }}
        .ngad-dot {{ width:6px; height:6px; border-radius:50%; background:rgba(255,255,255,0.45); }}
        .ngad-dot.on {{ background:#FF6F91; width:16px; border-radius:4px; transition:all .3s; }}
        </style>
        <div class="ngad">{slides_html}<div class="ngad-dots">{dots_html}</div></div>
        <script>
        (function() {{
            const slides = document.querySelectorAll('.ngad-slide');
            const dots = document.querySelectorAll('.ngad-dot');
            let idx = 0;
            setInterval(() => {{
                slides[idx].classList.remove('active'); dots[idx].classList.remove('on');
                idx = (idx + 1) % slides.length;
                slides[idx].classList.add('active'); dots[idx].classList.add('on');
            }}, 3200);
        }})();
        </script>
        """,
        height=150,
    )


def _countdown(product_deal):
    remaining = product_deal.ends_at - dt.datetime.utcnow()
    if remaining.total_seconds() <= 0:
        return "Deal Ended"
    hours, rem = divmod(int(remaining.total_seconds()), 3600)
    minutes, seconds = divmod(rem, 60)
    return f"⏰ Deal ends in {hours:02d}h {minutes:02d}m {seconds:02d}s"


# --------------------------------------------------------------------------- #
# RANDOM SESSION-ONCE ALERTS (flash sale / limited stock / today's deal)
# --------------------------------------------------------------------------- #
def _maybe_show_alerts(session):
    if st.session_state.get("shown_alerts"):
        return
    st.session_state["shown_alerts"] = True

    deals = session.query(TodaysDeal).filter(TodaysDeal.is_active == True).all()
    if deals:
        d = random.choice(deals)
        if d.product:
            remaining = d.ends_at - dt.datetime.utcnow()
            hours_left = max(1, int(remaining.total_seconds() // 3600))
            todays_deal_popup(d.product.name, d.deal_discount_percent, hours_left)

    low_stock = [p for p in get_all_products(session) if 0 < p.stock <= p.low_stock_threshold]
    if low_stock:
        p = random.choice(low_stock)
        limited_stock_warning(p.name, p.stock)

    flash_ad_products = [d.product for d in deals if d.product and d.deal_discount_percent >= 25]
    if flash_ad_products:
        p = random.choice(flash_ad_products)
        flash_sale_alert(p.name, int(p.discount_percent))


# --------------------------------------------------------------------------- #
# PRODUCT CARD
# --------------------------------------------------------------------------- #
def _product_card(session, product, key_prefix, spotlight=False):
    """Simple product card — image, name, rating, stock, price, discount
    badge, wishlist and Add to Cart only. Hovering the image reveals a
    panel with active offers, quantity discounts, cashback and warranty;
    everything else (full specs, video, comparison, 360° preview) lives
    one tap away in the Quick View modal opened via the eye icon."""
    sid = st.session_state["cart_session_id"]
    wishlist_ids = get_wishlist_product_ids(session, sid)
    in_wishlist = product.id in wishlist_ids

    uri = image_data_uri(product.image_path)
    deal = get_active_deal(session, product.id)
    final_price = product.discounted_price
    if deal:
        final_price = round(product.price * (1 - deal.deal_discount_percent / 100), 2)
    discount_pct = round(100 * (1 - final_price / product.price)) if product.price else 0
    rules = get_discount_rules(session, product.id)

    with st.container():
        st.markdown(f'<div id="ng-product-{product.id}"></div>', unsafe_allow_html=True)
        card_cls = "glass-card spotlight" if spotlight else "glass-card"
        st.markdown(f'<div class="{card_cls}">', unsafe_allow_html=True)
        video_chip = '<div class="video-chip">🎬 360°</div>' if product.has_video else ""

        hover_lines = [f'<span class="ho-title">{product.name}</span>']
        if deal:
            hover_lines.append(f'<span class="ho-line">⚡ Today\'s Deal: extra '
                                f'{int(deal.deal_discount_percent)}% off</span>')
        if rules:
            hover_lines.append(f'<span class="ho-line">🎁 {rules[0].description}</span>')
        if product.cashback_percent:
            hover_lines.append(f'<span class="ho-line">💰 {int(product.cashback_percent)}% cashback</span>')
        hover_lines.append(f'<span class="ho-line">🛡️ {product.warranty}</span>')
        if product.has_video:
            hover_lines.append('<span class="ho-line">🎬 Video preview in Quick View</span>')
        hover_html = "".join(hover_lines)

        st.markdown(
            f'<div class="zoom-frame">{video_chip}<img src="{uri}"/>'
            f'<div class="hover-overlay">{hover_html}</div></div>',
            unsafe_allow_html=True,
        )

        if discount_pct > 0:
            st.markdown(f'<span class="badge badge-discount">-{discount_pct}% OFF</span>',
                        unsafe_allow_html=True)
        if product.cashback_percent:
            st.markdown(f'<span class="badge badge-cashback">💰 {int(product.cashback_percent)}% cashback</span>',
                        unsafe_allow_html=True)

        st.markdown(f'<div class="product-title">{product.name}</div>', unsafe_allow_html=True)
        st.markdown(f"<div style='color:#B8873F;font-size:13px;'>{star_string(product.rating)} "
                     f"<span style='color:#6B6478'>({product.review_count})</span></div>",
                    unsafe_allow_html=True)

        st.markdown(
            f'<div class="product-price">{fmt_inr(final_price)}'
            f'<span class="product-mrp">{fmt_inr(product.price)}</span></div>',
            unsafe_allow_html=True,
        )

        status_class = {"In Stock": "badge-instock", "Low Stock": "badge-lowstock",
                         "Out of Stock": "badge-outstock"}[product.stock_status]
        stock_label = (f"Only {product.stock} left" if product.stock_status == "Low Stock"
                        else product.stock_status)
        st.markdown(f'<span class="badge {status_class}">{stock_label}</span>',
                     unsafe_allow_html=True)

        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            btn_disabled = product.stock <= 0
            if st.button("🛒 Add to Cart" if not btn_disabled else "Out of Stock",
                         key=f"{key_prefix}_add_{product.id}", use_container_width=True,
                         disabled=btn_disabled, type="primary"):
                try:
                    success, msg = add_to_cart(session, sid, product.id, 1)
                except Exception:
                    success, msg = False, "Something went wrong adding this to your cart. Please try again."
                if success:
                    play_add_to_cart_sound()
                    flash_message(f"{product.name} added to cart!", "success")
                    refreshed = get_product(session, product.id)
                    if refreshed and refreshed.stock <= 0:
                        out_of_stock_popup(product.name)
                    elif refreshed and refreshed.stock <= refreshed.low_stock_threshold:
                        limited_stock_warning(product.name, refreshed.stock)
                    st.rerun()
                else:
                    flash_message(msg, "error")
        with c2:
            heart = "❤️" if in_wishlist else "🤍"
            if st.button(heart, key=f"{key_prefix}_wish_{product.id}", use_container_width=True,
                         help="Toggle wishlist"):
                toggle_wishlist(session, sid, product.id)
                st.rerun()
        with c3:
            if st.button("👁️", key=f"{key_prefix}_qv_{product.id}", use_container_width=True,
                         help="Quick View — specs, warranty, video, offers & more"):
                record_product_view(session, sid, product.id)
                st.session_state["quickview_product_id"] = product.id
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


def _product_grid(session, products, key_prefix, cols_n=2):
    if not products:
        st.info("No products found.")
        return
    cols = st.columns(cols_n)
    for i, product in enumerate(products):
        with cols[i % cols_n]:
            _product_card(session, product, key_prefix=f"{key_prefix}_{i}")


# --------------------------------------------------------------------------- #
# ADMIN → WEBSITE SPOTLIGHT (click a product in the dashboard, jump here)
# --------------------------------------------------------------------------- #
def _spotlight_section(session):
    pid = st.session_state.get("highlight_product_id")
    if not pid:
        return
    product = get_product(session, pid)
    if not product:
        st.session_state["highlight_product_id"] = None
        return
    st.markdown('<div id="ng-spotlight"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📍 Spotlighted from Admin Dashboard</div>',
                unsafe_allow_html=True)
    cols = st.columns(2)
    with cols[0]:
        _product_card(session, product, key_prefix="spotlight", spotlight=True)
    if st.button("✕ Clear Spotlight", key="clear_spotlight_btn"):
        st.session_state["highlight_product_id"] = None
        st.rerun()
    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;
            const el = doc.getElementById('ng-spotlight');
            if (el) { el.scrollIntoView({behavior:'smooth', block:'start'}); }
        })();
        </script>
        """,
        height=0, width=0,
    )
    st.markdown("---")


# --------------------------------------------------------------------------- #
# QUICK VIEW DIALOG
# --------------------------------------------------------------------------- #
def _render_quick_view_body(session, product):
    sid = st.session_state["cart_session_id"]
    gallery = product.gallery
    qv_gkey = f"qv_gidx_{product.id}"
    qv_gidx = st.session_state["gallery_index"].get(qv_gkey, 0)
    qv_gidx = min(qv_gidx, len(gallery) - 1) if gallery else 0

    col1, col2 = st.columns([1, 1])
    with col1:
        media_tab_labels = ["🖼️ Photos"] + (["🎬 360° Video"] if product.has_video and product.video_path else [])
        media_tabs = st.tabs(media_tab_labels)
        with media_tabs[0]:
            uri = image_data_uri(gallery[qv_gidx] if gallery else product.image_path)
            st.markdown(f'<div class="zoom-frame"><img src="{uri}"/></div>', unsafe_allow_html=True)
            if len(gallery) > 1:
                thumb_cols = st.columns(len(gallery))
                for gi, gpath in enumerate(gallery):
                    with thumb_cols[gi]:
                        label = GALLERY_LABELS[gi % len(GALLERY_LABELS)]
                        marker = f"● {label}" if gi == qv_gidx else label
                        if st.button(marker, key=f"qv_thumb_{product.id}_{gi}", use_container_width=True):
                            st.session_state["gallery_index"][qv_gkey] = gi
                            st.rerun()
        if product.has_video and product.video_path:
            with media_tabs[1]:
                video_file = asset_abs_path(product.video_path)
                if video_file:
                    try:
                        st.video(video_file, autoplay=True, muted=True, loop=True)
                    except TypeError:
                        st.video(video_file)
                    st.caption(product.video_note or "360° Product Preview")
                else:
                    st.info("Video preview not available.")

    with col2:
        st.markdown(f"#### {product.name}")
        st.caption(f"Brand: **{product.brand}**  •  SKU: `{product.sku}`")

        badges = ""
        if product.is_featured:
            badges += '<span class="badge badge-featured">⭐ Featured</span>'
        if product.is_bestseller:
            badges += '<span class="badge badge-bestseller">🏆 Bestseller</span>'
        if product.is_new_arrival:
            badges += '<span class="badge badge-new">🆕 New</span>'
        if product.cashback_percent:
            badges += f'<span class="badge badge-cashback">💰 {int(product.cashback_percent)}% cashback</span>'
        if badges:
            st.markdown(badges, unsafe_allow_html=True)

        st.markdown(f"<div style='color:#B8873F;'>{star_string(product.rating)} "
                     f"({product.review_count} reviews)</div>", unsafe_allow_html=True)

        deal = get_active_deal(session, product.id)
        final_price = product.discounted_price
        if deal:
            final_price = round(product.price * (1 - deal.deal_discount_percent / 100), 2)
            st.warning(_countdown(deal))
        st.markdown(f"### {fmt_inr(final_price)} "
                     f"<span style='text-decoration:line-through;color:#94A3B8;font-size:15px;'>"
                     f"{fmt_inr(product.price)}</span>", unsafe_allow_html=True)

        if product.stock > 0:
            viewers_now = 4 + (product.id * 7) % 19
            st.markdown(f'<div class="urgency-line">🔥 {viewers_now} people are viewing this '
                        f'product right now</div>', unsafe_allow_html=True)
            if product.stock_status == "Low Stock":
                st.markdown(f'<div class="urgency-line">⚡ Only {product.stock} left in stock — '
                            f'order soon!</div>', unsafe_allow_html=True)
        st.write(product.description)

        with st.expander("📋 Specifications"):
            for spec in (product.specifications or "").split("|"):
                if spec.strip():
                    st.write(f"• {spec.strip()}")

        with st.expander("🛡️ Warranty & 🚚 Delivery"):
            st.write(f"**Warranty:** {product.warranty}")
            st.write(f"**Standard Delivery:** {product.delivery_days} day(s)")
            pincode = st.text_input("Check delivery to your pincode", key=f"pin_{product.id}",
                                     max_chars=6, placeholder="e.g. 110001")
            if pincode:
                result = estimate_delivery_for_pincode(pincode, product.delivery_days)
                if result:
                    eta_days, eta_date = result
                    st.success(f"Delivers in ~{eta_days} day(s), by **{eta_date.strftime('%d %b %Y')}**")
                else:
                    st.error("Enter a valid 6-digit pincode.")

        if product.emi_available:
            with st.expander("💳 EMI Options"):
                for months, amount in emi_options(final_price):
                    st.write(f"• {months} months — **{fmt_inr(amount)}/month** (no-cost EMI)")

        if product.cashback_percent:
            with st.expander("💰 Cashback Offer"):
                cashback_amt = round(final_price * product.cashback_percent / 100, 2)
                st.write(f"Get **{fmt_inr(cashback_amt)}** cashback to your NovaGrid Wallet "
                         f"within 7 days of delivery.")

        rules = get_discount_rules(session, product.id)
        if rules:
            with st.expander("💰 Buy More, Save More"):
                for r in rules:
                    st.write(f"• {r.description}")

        bundle = get_recommended_products(session, product, limit=2)
        if bundle:
            st.markdown("###### 🧩 Frequently Bought Together")
            with st.container():
                st.markdown('<div class="fbt-box">', unsafe_allow_html=True)
                bundle_items = [product] + bundle
                bundle_prices = [final_price] + [bp.discounted_price for bp in bundle]
                bcols = st.columns(len(bundle_items))
                for i, bp in enumerate(bundle_items):
                    with bcols[i]:
                        st.image(image_data_uri(bp.image_path), use_container_width=True)
                        st.caption(f"**{bp.name[:24]}**" + ("  *(this item)*" if i == 0 else ""))
                        st.caption(fmt_inr(bundle_prices[i]))
                bundle_total = sum(bundle_prices)
                st.markdown(f"**Bundle total: {fmt_inr(bundle_total)}** for {len(bundle_items)} items")
                if st.button("🛒 Add Bundle to Cart", key=f"qv_bundle_{product.id}",
                             use_container_width=True):
                    sid_bundle = st.session_state["cart_session_id"]
                    for bp in bundle_items:
                        add_to_cart(session, sid_bundle, bp.id, 1)
                    play_add_to_cart_sound()
                    flash_message("Bundle added to cart!", "success")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        qty = st.number_input("Quantity", min_value=1, max_value=max(product.stock, 1),
                               value=1, key=f"qv_qty_{product.id}", disabled=product.stock <= 0)
        cA, cB, cC = st.columns(3)
        with cA:
            if st.button("🛒 Add to Cart", key=f"qv_add_{product.id}", use_container_width=True,
                         type="primary", disabled=product.stock <= 0):
                try:
                    success, msg = add_to_cart(session, sid, product.id, int(qty))
                except Exception:
                    success, msg = False, "Something went wrong adding this to your cart. Please try again."
                if success:
                    play_add_to_cart_sound()
                    flash_message("Added to cart!", "success")
                    st.rerun()
                else:
                    flash_message(msg, "error")
        with cB:
            wishlist_ids = get_wishlist_product_ids(session, sid)
            heart_label = "❤️ In Wishlist" if product.id in wishlist_ids else "🤍 Add to Wishlist"
            if st.button(heart_label, key=f"qv_wish_{product.id}", use_container_width=True):
                toggle_wishlist(session, sid, product.id)
                st.rerun()
        with cC:
            compare_ids = get_compare_product_ids(session, sid)
            in_compare = product.id in compare_ids
            compare_label = "✓ In Compare" if in_compare else "⚖️ Add to Compare"
            if st.button(compare_label, key=f"qv_cmp_{product.id}", use_container_width=True):
                ok, msg = toggle_compare(session, sid, product.id)
                if not ok and msg:
                    flash_message(msg, "warning")
                st.rerun()

    st.markdown("---")
    st.markdown("##### ⭐ Ratings & Reviews")
    breakdown, total_reviews = rating_breakdown(session, product.id)
    for star in [5, 4, 3, 2, 1]:
        pct = breakdown.get(star, 0)
        bc1, bc2, bc3 = st.columns([1, 6, 1])
        with bc1:
            st.write(f"{star}★")
        with bc2:
            st.markdown(f'<div class="review-bar-track"><div class="review-bar-fill" '
                         f'style="width:{pct}%;"></div></div>', unsafe_allow_html=True)
        with bc3:
            st.write(f"{pct}%")

    reviews = get_reviews(session, product.id, limit=5)
    for r in reviews:
        verified = "✅ Verified Purchase" if r.verified_purchase else ""
        st.markdown(
            f"**{r.reviewer_name}** — {star_string(r.rating)} &nbsp; "
            f"<span style='color:#6B6478;font-size:11.5px;'>{verified}</span>",
            unsafe_allow_html=True,
        )
        if r.title:
            st.markdown(f"*{r.title}*")
        st.write(r.comment)
        st.caption(f"👍 {r.helpful_count} found this helpful")
        st.markdown("---")

    with st.expander("✍️ Write a Review"):
        with st.form(f"review_form_{product.id}"):
            rname = st.text_input("Your name")
            rrating = st.slider("Rating", 1.0, 5.0, 5.0, 0.5)
            rtitle = st.text_input("Review title")
            rcomment = st.text_area("Your review")
            submitted = st.form_submit_button("Submit Review", use_container_width=True)
        if submitted and rname.strip() and rcomment.strip():
            add_review(session, product.id, rname, rrating, rtitle, rcomment)
            flash_message("Thanks! Your review has been posted.", "success")
            st.rerun()

    st.markdown("##### 🎯 You May Also Like")
    recs = get_recommended_products(session, product, limit=4)
    if recs:
        rec_cols = st.columns(min(4, len(recs)))
        for i, rp in enumerate(recs):
            with rec_cols[i]:
                st.image(image_data_uri(rp.image_path), use_container_width=True)
                st.caption(f"**{rp.name[:26]}**")
                st.caption(fmt_inr(rp.discounted_price))


try:
    _quick_view_dialog = st.dialog("🔍 Quick View", width="large")(_render_quick_view_body)
    _HAS_DIALOG = True
except Exception:
    _HAS_DIALOG = False


def _maybe_render_quick_view(session):
    pid = st.session_state.get("quickview_product_id")
    if not pid:
        return
    product = get_product(session, pid)
    if not product:
        st.session_state["quickview_product_id"] = None
        return
    if _HAS_DIALOG:
        _quick_view_dialog(session, product)
    else:
        with st.expander(f"🔍 Quick View: {product.name}", expanded=True):
            _render_quick_view_body(session, product)
            if st.button("Close Quick View", key="close_qv_fallback"):
                st.session_state["quickview_product_id"] = None
                st.rerun()


# --------------------------------------------------------------------------- #
# CART / 4-STEP CHECKOUT (Shipping -> Payment -> Review -> Place Order)
# --------------------------------------------------------------------------- #
def _render_order_confirmation(info):
    st.markdown(
        f"""
        <div style="background:linear-gradient(120deg,#12B886,#0EA372);
        color:white;border-radius:18px;padding:22px;text-align:center;">
            <h2 style="margin:0;">🎉 Order Confirmed!</h2>
            <p style="margin:6px 0;">Thank you for shopping with NovaGrid Electronics.</p>
            <p style="font-size:20px;font-weight:800;margin:10px 0 2px 0;">
                Order #{info['order_number']}</p>
            <p>Placed on: <b>{info['placed_at']}</b></p>
            <p>Subtotal: {fmt_inr(info['subtotal'])} &nbsp;•&nbsp; Discount: -{fmt_inr(info['discount'])}
                &nbsp;•&nbsp; GST (18%): {fmt_inr(info['gst'])}</p>
            <p style="font-size:18px;font-weight:800;">Total Paid: {fmt_inr(info['amount'])}</p>
            <p>Payment Method: <b>{info['payment']}</b></p>
            <p>Estimated Delivery: <b>{info['eta']}</b></p>
            <p style="font-size:12.5px;opacity:0.9;margin-top:10px;">
                📩 Order confirmation SMS sent to {info['sms_target']} &nbsp;•&nbsp;
                🚚 Tracked delivery via our trusted logistics partner (TPA)
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    pdf_bytes = st.session_state.get("checkout_invoice_pdf")
    if pdf_bytes:
        st.download_button(
            "🧾 Download Invoice (PDF)", data=pdf_bytes,
            file_name=f"NovaGrid_Invoice_{info['order_number']}.pdf",
            mime="application/pdf", use_container_width=True,
            key=f"invoice_dl_{info['order_number']}",
        )


def _checkout_stepper(active_step):
    steps = [("1", "Shipping"), ("2", "Payment"), ("3", "Review"), ("4", "Confirmation")]
    parts = []
    for i, (num, label) in enumerate(steps, start=1):
        cls = "done" if i < active_step else ("active" if i == active_step else "")
        circle = "✓" if i < active_step else num
        parts.append(
            f'<div class="checkout-step {cls}"><div class="checkout-step-circle">{circle}</div>'
            f'<div class="checkout-step-label">{label}</div></div>'
        )
        if i < len(steps):
            line_cls = "done" if i < active_step else ""
            parts.append(f'<div class="checkout-step-line {line_cls}"></div>')
    st.markdown(f'<div class="checkout-stepper">{"".join(parts)}</div>', unsafe_allow_html=True)


def _checkout_cart_items_summary(session, items):
    subtotal = 0.0
    for item in items:
        product = get_product(session, item.product_id)
        if not product:
            continue
        line_total = product.discounted_price * item.quantity
        subtotal += line_total
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            st.write(f"**{product.name}** × {item.quantity}")
        with c2:
            st.write(fmt_inr(line_total))
        with c3:
            if st.button("🗑️", key=f"remove_cart_{item.id}", help="Remove from cart"):
                remove_from_cart(session, st.session_state["cart_session_id"], product.id)
                st.rerun()
    return subtotal


def _checkout_step_shipping(session, items):
    _checkout_stepper(1)
    subtotal = _checkout_cart_items_summary(session, items)
    st.markdown(f"### Subtotal: {fmt_inr(subtotal)}")
    st.markdown("##### 📮 Shipping Details")
    ship = st.session_state["checkout_shipping"]
    with st.form("checkout_shipping_form"):
        name = st.text_input("Full Name *", value=ship.get("name", ""))
        phone = st.text_input("Mobile Number *", value=ship.get("phone", ""), max_chars=10)
        email = st.text_input("Email (optional)", value=ship.get("email", ""))
        address = st.text_area("Delivery Address *", value=ship.get("address", ""))
        pincode = st.text_input("Pincode *", value=ship.get("pincode", ""), max_chars=6)
        continue_clicked = st.form_submit_button("Continue to Payment →", use_container_width=True,
                                                   type="primary")
    if continue_clicked:
        if not name.strip() or not phone.strip() or not address.strip() or not pincode.strip():
            flash_message("Please fill in all required shipping fields.", "error")
        else:
            st.session_state["checkout_shipping"] = {
                "name": name.strip(), "phone": phone.strip(), "email": email.strip(),
                "address": address.strip(), "pincode": pincode.strip(),
            }
            st.session_state["checkout_step"] = "payment"
            st.rerun()


def _checkout_step_payment(session, items):
    _checkout_stepper(2)
    subtotal = sum(get_product(session, i.product_id).discounted_price * i.quantity
                    for i in items if get_product(session, i.product_id))
    ship = st.session_state["checkout_shipping"]
    with st.container(border=True):
        st.caption("📮 Shipping to")
        st.write(f"**{ship['name']}** — {ship['phone']}")
        st.write(f"{ship['address']}, {ship['pincode']}")

    st.markdown("##### 💳 Payment Method")
    payment = st.radio("Choose a payment method", PAYMENT_METHODS,
                        horizontal=True, key="checkout_payment_method")

    st.markdown("##### 🎟️ Coupon Code")
    cc1, cc2 = st.columns([3, 1])
    with cc1:
        coupon_input = st.text_input("Have a coupon?", key="checkout_coupon_input",
                                      placeholder="e.g. NOVA10", label_visibility="collapsed")
    with cc2:
        if st.button("Apply", key="apply_coupon_btn", use_container_width=True):
            coupon, discount, err = validate_coupon(session, coupon_input, subtotal)
            if err:
                st.session_state["checkout_coupon_code"] = ""
                st.session_state["checkout_coupon_discount"] = 0.0
                st.session_state["checkout_coupon_error"] = err
            else:
                st.session_state["checkout_coupon_code"] = coupon.code if coupon else ""
                st.session_state["checkout_coupon_discount"] = discount
                st.session_state["checkout_coupon_error"] = None
                if coupon:
                    play_notification_sound()
                    flash_message(f"Coupon {coupon.code} applied — you saved {fmt_inr(discount)}!",
                                  "success")
            st.rerun()
    if st.session_state.get("checkout_coupon_error"):
        st.error(st.session_state["checkout_coupon_error"])
    if st.session_state.get("checkout_coupon_code"):
        st.success(f"✅ {st.session_state['checkout_coupon_code']} applied — "
                   f"-{fmt_inr(st.session_state['checkout_coupon_discount'])}")

    b1, b2 = st.columns(2)
    with b1:
        if st.button("← Back", key="payment_back_btn", use_container_width=True):
            st.session_state["checkout_step"] = "shipping"
            st.rerun()
    with b2:
        if st.button("Continue to Review →", key="payment_continue_btn",
                     use_container_width=True, type="primary"):
            st.session_state["checkout_step"] = "review"
            st.rerun()


def _checkout_step_review(session, items):
    _checkout_stepper(3)
    ship = st.session_state["checkout_shipping"]
    payment = st.session_state.get("checkout_payment_method", PAYMENT_METHODS[0])
    coupon_code = st.session_state.get("checkout_coupon_code", "")
    discount = st.session_state.get("checkout_coupon_discount", 0.0)

    st.markdown("##### 🧾 Review Your Order")
    subtotal = _checkout_cart_items_summary(session, items)
    gst = round((subtotal - discount) * 0.18, 2)
    total = round(subtotal - discount + gst, 2)

    with st.container(border=True):
        st.write(f"**Shipping to:** {ship['name']}, {ship['address']}, {ship['pincode']}")
        st.write(f"**Mobile:** {ship['phone']}")
        st.write(f"**Payment Method:** {payment}")
        st.write(f"**Subtotal:** {fmt_inr(subtotal)}")
        if coupon_code:
            st.write(f"**Coupon ({coupon_code}):** -{fmt_inr(discount)}")
        st.write(f"**GST (18%):** {fmt_inr(gst)}")
        st.markdown(f"### Final Total: {fmt_inr(total)}")

    st.caption("🔒 Your order is placed the moment you tap the button below — this is the "
               "only confirmation step, no extra screens after this.")

    b1, b2 = st.columns(2)
    with b1:
        if st.button("← Back", key="review_back_btn", use_container_width=True):
            st.session_state["checkout_step"] = "payment"
            st.rerun()
    with b2:
        place_clicked = st.button("✅ Place Order", key="checkout_btn", use_container_width=True,
                                   type="primary")

    if place_clicked:
        try:
            amount, order = checkout_cart(
                session, st.session_state["cart_session_id"], payment_method=payment,
                customer_name=ship["name"], customer_email=ship["email"],
                customer_phone=ship["phone"],
                shipping_address=f"{ship['address']}, {ship['pincode']}",
                coupon_code=coupon_code,
            )
        except Exception:
            amount, order = 0, None
            flash_message("Something went wrong placing your order. Please try again.", "error")
        st.session_state["last_order"] = order.order_number if order else None

        if order:
            sms_target = ship["phone"] if ship["phone"] else "your registered number"
            try:
                pdf_bytes = build_invoice_pdf(order)
            except Exception:
                pdf_bytes = None
            st.session_state["checkout_invoice_pdf"] = pdf_bytes
            st.session_state["checkout_success_order"] = {
                "order_number": order.order_number,
                "amount": order.total_amount,
                "subtotal": order.subtotal_amount,
                "discount": order.discount_amount,
                "gst": order.gst_amount,
                "payment": payment,
                "eta": order.estimated_delivery.strftime("%d %b %Y"),
                "placed_at": order.created_at.strftime("%d %b %Y, %I:%M %p"),
                "sms_target": sms_target,
            }
            st.session_state["checkout_step"] = "confirmation"

            # Full premium celebration: sound + confetti + balloons + crackers
            # + a native congratulations popup, rendered NOW in this same run
            # (deliberately no st.rerun() here, so the animation/audio
            # components stay mounted long enough to actually play).
            checkout_celebration()
            play_notification_sound()
            congratulations_popup(f"🎉 Congratulations! Order {order.order_number} confirmed.")
            st.toast(f"📩 2-way SMS sent to {sms_target}: 'Order {order.order_number} confirmed! "
                     f"Reply TRACK for live status.'", icon="📩")
            _checkout_stepper(4)
            _render_order_confirmation(st.session_state["checkout_success_order"])
            if st.button("🛍️ Continue Shopping", key="continue_shopping_btn_inline",
                         use_container_width=True):
                _reset_checkout_state()
                st.rerun()


def _reset_checkout_state():
    st.session_state["checkout_success_order"] = None
    st.session_state["checkout_invoice_pdf"] = None
    st.session_state["checkout_step"] = "shipping"
    st.session_state["checkout_coupon_code"] = ""
    st.session_state["checkout_coupon_discount"] = 0.0
    st.session_state["checkout_coupon_error"] = None


def _cart_summary(session):
    if st.session_state.get("checkout_success_order"):
        _checkout_stepper(4)
        _render_order_confirmation(st.session_state["checkout_success_order"])
        if st.button("🛍️ Continue Shopping", key="continue_shopping_btn", use_container_width=True):
            _reset_checkout_state()
            st.rerun()
        return

    items = get_cart_items(session, st.session_state["cart_session_id"])
    if not items:
        st.caption("🛒 Your cart is empty. Start shopping above!")
        return

    step = st.session_state.get("checkout_step", "shipping")
    if step == "shipping":
        _checkout_step_shipping(session, items)
    elif step == "payment":
        _checkout_step_payment(session, items)
    else:
        _checkout_step_review(session, items)


def _sticky_cart_widget(session):
    items = get_cart_items(session, st.session_state["cart_session_id"])
    if not items:
        return
    total = sum((get_product(session, i.product_id).discounted_price * i.quantity)
                for i in items if get_product(session, i.product_id))
    st.markdown(
        f"""
        <div class="sticky-cart">
            <span>🛒 {len(items)} item(s) in cart</span>
            <span>{fmt_inr(total)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# WISHLIST / COMPARE / RECENTLY VIEWED / RECOMMENDED
# --------------------------------------------------------------------------- #
def _wishlist_tab(session):
    st.markdown('<div class="section-title">❤️ Your Wishlist</div>', unsafe_allow_html=True)
    sid = st.session_state["cart_session_id"]
    items = get_wishlist_items(session, sid)
    products = [i.product for i in items if i.product]
    if not products:
        st.info("Your wishlist is empty. Tap 🤍 on any product to save it here.")
        return
    _product_grid(session, products, "wishlist")


def _compare_tab(session):
    st.markdown('<div class="section-title">⚖️ Compare Products</div>', unsafe_allow_html=True)
    sid = st.session_state["cart_session_id"]
    ids = get_compare_product_ids(session, sid)
    if not ids:
        st.info("Tap ⚖️ Add to Compare in Quick View on up to 4 products to see them side by side here.")
        return
    products = [get_product(session, pid) for pid in ids]
    products = [p for p in products if p]
    cols = st.columns(len(products))
    for i, p in enumerate(products):
        with cols[i]:
            st.image(image_data_uri(p.image_path), use_container_width=True)
            st.markdown(f"**{p.name}**")
            st.write(fmt_inr(p.discounted_price))
            st.caption(f"{star_string(p.rating)} ({p.review_count})")
            st.write(f"**Brand:** {p.brand}")
            st.write(f"**Warranty:** {p.warranty}")
            st.write(f"**Delivery:** {p.delivery_days} day(s)")
            if p.cashback_percent:
                st.write(f"**Cashback:** {int(p.cashback_percent)}%")
            for spec in (p.specifications or "").split("|")[:6]:
                if spec.strip():
                    st.write(f"• {spec.strip()}")
            if st.button("Remove", key=f"cmp_remove_{p.id}", use_container_width=True):
                toggle_compare(session, sid, p.id)
                st.rerun()
    if st.button("Clear Comparison", key="cmp_clear_all"):
        for pid in list(ids):
            toggle_compare(session, sid, pid)
        st.rerun()


def _recently_viewed_section(session):
    sid = st.session_state["cart_session_id"]
    recent = get_recently_viewed(session, sid, limit=6)
    if not recent:
        return
    st.markdown('<div class="section-title">🕒 Recently Viewed</div>', unsafe_allow_html=True)
    _product_grid(session, recent, "recent")


# --------------------------------------------------------------------------- #
# POPULAR BRANDS
# --------------------------------------------------------------------------- #
def _brand_strip(session):
    brands = get_brands(session)
    if not brands:
        return
    st.markdown('<div class="section-title">🏷️ Popular Brands</div>', unsafe_allow_html=True)
    chips = "".join(
        f'<div class="brand-chip"><div class="bc-name">{b}</div>'
        f'<div class="bc-count">{c} product{"s" if c != 1 else ""}</div></div>'
        for b, c in brands
    )
    st.markdown(f'<div class="brand-strip">{chips}</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# SOCIAL PROOF: TRUST STATS + TESTIMONIALS
# --------------------------------------------------------------------------- #
def _social_proof_stats(session):
    products = session.query(Product).all()
    if not products:
        return
    total_reviews = sum(p.review_count or 0 for p in products)
    rating_weighted = sum((p.rating or 0) * (p.review_count or 0) for p in products)
    avg_rating = round(rating_weighted / total_reviews, 1) if total_reviews else 4.5
    total_orders = session.query(Order).count()
    stats = [
        ("👥", f"{max(total_reviews, 1):,}+", "Happy Customers"),
        ("⭐", f"{avg_rating}/5", "Average Rating"),
        ("📦", f"{max(total_orders, 12500):,}+", "Orders Delivered"),
        ("✅", "100%", "Genuine Products"),
    ]
    cols = st.columns(4)
    for col, (icon, value, label) in zip(cols, stats):
        with col:
            st.markdown(
                f"""<div class="stat-card">
                    <div class="stat-icon">{icon}</div>
                    <div class="stat-value">{value}</div>
                    <div class="stat-label">{label}</div>
                </div>""",
                unsafe_allow_html=True,
            )


def _testimonials_section(session):
    reviews = (
        session.query(Review)
        .filter(Review.rating >= 4.3, Review.comment.isnot(None))
        .order_by(Review.helpful_count.desc())
        .limit(8)
        .all()
    )
    if not reviews:
        return
    st.markdown('<div class="section-title">💬 What Our Customers Say</div>', unsafe_allow_html=True)
    cards = []
    for r in reviews:
        product = session.query(Product).get(r.product_id) if r.product_id else None
        pname = product.name if product else "NovaGrid Electronics"
        comment = (r.comment or "").strip()
        if len(comment) > 150:
            comment = comment[:150].rsplit(" ", 1)[0] + "…"
        verified = '<span class="testimonial-verified">✅ Verified Buyer</span>' if r.verified_purchase else ""
        card = (
            '<div class="testimonial-card">'
            f'<div class="testimonial-stars">{star_string(r.rating)}</div>'
            f'<div class="testimonial-title">{r.title or "Great purchase!"}</div>'
            f'<div class="testimonial-comment">"{comment}"</div>'
            f'<div class="testimonial-footer"><span class="testimonial-name">{r.reviewer_name}</span>{verified}</div>'
            f'<div class="testimonial-product">on {pname}</div>'
            '</div>'
        )
        cards.append(card)
    st.markdown('<div class="testimonial-row">' + "".join(cards) + '</div>', unsafe_allow_html=True)


def _newsletter_section():
    st.markdown(
        """
        <div class="newsletter-box">
            <h3>📩 Join the NovaGrid Insider List</h3>
            <p>Get early access to deals, new arrivals and exclusive coupon codes.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.session_state.get("newsletter_subscribed"):
        st.success("✅ You're subscribed! Watch your inbox for exclusive NovaGrid offers.")
        return
    nc1, nc2 = st.columns([3, 1])
    with nc1:
        email = st.text_input("Email address", key="newsletter_email",
                               placeholder="you@example.com", label_visibility="collapsed")
    with nc2:
        if st.button("Subscribe", key="newsletter_subscribe_btn", use_container_width=True,
                     type="primary"):
            if email.strip() and "@" in email:
                st.session_state["newsletter_subscribed"] = True
                flash_message("Thanks for subscribing to NovaGrid Insider!", "success")
                st.rerun()
            else:
                flash_message("Please enter a valid email address.", "error")


# --------------------------------------------------------------------------- #
# STATIC INFO PAGES
# --------------------------------------------------------------------------- #
def _about_page():
    st.markdown('<div class="section-title">ℹ️ About NovaGrid Electronics</div>', unsafe_allow_html=True)
    st.write(
        "NovaGrid Electronics is a premium electronics retailer bringing you smartphones, "
        "laptops, audio, TVs, wearables, gaming and home appliances at honest prices, backed "
        "by genuine warranties and fast, reliable delivery. Founded on the idea that buying "
        "electronics should feel effortless, we combine curated product selection with a "
        "storefront experience inspired by the best retail brands in the world."
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Happy Customers", "2.4M+")
    with c2:
        st.metric("Cities Served", "600+")
    with c3:
        st.metric("Products", "20+ categories")
    st.markdown("##### 📞 Contact Us")
    st.write("**Email:** support@novagridelectronics.example")
    st.write("**Phone:** 1800-NOVAGRID (Toll-Free)")
    st.write("**Address:** NovaGrid Tower, Tech Park Road, Bengaluru, India")


def _privacy_page():
    st.markdown('<div class="section-title">🔒 Privacy Policy</div>', unsafe_allow_html=True)
    st.write(
        "This Privacy Policy explains, in plain language, how NovaGrid Electronics collects, "
        "uses and protects your information when you use this demo storefront. We collect "
        "only the information needed to process orders and improve your shopping experience — "
        "such as your name, contact details and order history. We never sell your personal "
        "data to third parties. Cart, wishlist and browsing activity in this demo are stored "
        "locally in the demo database and are used solely to power features like Recently "
        "Viewed and Recommendations. You may request the removal of your data at any time by "
        "contacting our support team."
    )
    st.caption("This is a template policy for demonstration purposes and should be reviewed by "
               "legal counsel before use in a live production store.")


def _terms_page():
    st.markdown('<div class="section-title">📜 Terms & Conditions</div>', unsafe_allow_html=True)
    st.write(
        "By using the NovaGrid Electronics storefront, you agree to purchase products for "
        "personal or authorized business use, provide accurate information at checkout, and "
        "comply with applicable laws. All prices are inclusive of GST unless stated "
        "otherwise. Warranty terms are as specified on each product page and are honored "
        "directly by NovaGrid Electronics or its authorized service partners. Delivery "
        "timelines shown are estimates and may vary based on location and stock availability. "
        "Returns are accepted within 7 days of delivery for eligible categories, subject to "
        "the product being unused and in original packaging."
    )
    st.caption("This is a template terms document for demonstration purposes and should be "
               "reviewed by legal counsel before use in a live production store.")


def _footer():
    st.markdown(
        """
        <div class="footer-box">
            <div style="display:flex;gap:36px;flex-wrap:wrap;">
                <div style="flex:1;min-width:180px;">
                    <h4>◆ NovaGrid Electronics</h4>
                    <p>Premium retail experience for smartphones, laptops, audio, TVs, gaming
                    and home appliances.</p>
                    <div class="footer-social">
                        <span>📘</span><span>📸</span><span>🐦</span><span>▶️</span>
                    </div>
                </div>
                <div style="flex:1;min-width:140px;">
                    <h4>Quick Links</h4>
                    <p>Home &nbsp;•&nbsp; Browse &nbsp;•&nbsp; Wishlist</p>
                    <p>Cart &nbsp;•&nbsp; Track Order &nbsp;•&nbsp; Support</p>
                </div>
                <div style="flex:1;min-width:140px;">
                    <h4>Categories</h4>
                    <p>Smartphones • Laptops • Audio</p>
                    <p>Televisions • Wearables • Gaming</p>
                </div>
                <div style="flex:1;min-width:180px;">
                    <h4>Contact</h4>
                    <p>support@novagridelectronics.example</p>
                    <p>1800-NOVAGRID (Toll-Free)</p>
                    <p>Bengaluru, India</p>
                </div>
                <div style="flex:1;min-width:170px;">
                    <h4>We Accept</h4>
                    <div class="payment-badges">
                        <span class="pay-badge">💳 Credit Card</span>
                        <span class="pay-badge">💳 Debit Card</span>
                        <span class="pay-badge">📱 UPI</span>
                        <span class="pay-badge">👛 Wallet</span>
                        <span class="pay-badge">🏦 Net Banking</span>
                        <span class="pay-badge">💵 COD</span>
                    </div>
                    <p style="margin-top:10px;">🔒 256-bit SSL Secured Checkout</p>
                </div>
            </div>
            <hr style="border-color:rgba(255,255,255,0.15);margin:18px 0 10px 0;">
            <div style="text-align:center;">
                ◆ <b>NovaGrid Electronics</b> — Premium Retail Experience Demo<br>
                © 2026 NovaGrid Electronics. All rights reserved.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# MAIN RENDER
# --------------------------------------------------------------------------- #
def render_customer_website():
    _init_session_state()
    _inject_customer_css()
    session = get_session()

    _maybe_show_alerts(session)
    _maybe_render_quick_view(session)

    _navbar(session)
    _offer_ticker()
    _flash_announcement_ticker(session)
    _trust_badges()
    _crm_chatbot(session)

    TAB_LABELS = ["🏠 Home", "🔍 Browse & Search", "❤️ Wishlist", "⚖️ Compare",
                  "🛒 Cart", "ℹ️ About", "🔒 Privacy", "📜 Terms"]

    # Jumping to a section (e.g. from the navbar cart/wishlist buttons) is done
    # by setting the radio's own session_state key before it's instantiated
    # below — a plain Python state change, not a JS click simulation, so it
    # can't fail to "wire up" the way an injected script into an iframe can.
    jump_target = st.session_state.pop("jump_to_tab", None)
    if jump_target:
        for _lbl in TAB_LABELS:
            if jump_target in _lbl:
                st.session_state["ng_active_tab"] = _lbl
                break

    nav_row = st.container(key="ng_main_nav")
    with nav_row:
        active_tab = st.radio(
            "Navigate", TAB_LABELS, key="ng_active_tab",
            horizontal=True, label_visibility="collapsed",
        )

    if active_tab == TAB_LABELS[0]:
        _spotlight_section(session)
        _hero_slider(session)
        _social_proof_stats(session)
        _festival_banner(session)
        _flash_sale_banner(session)
        _ad_banners(session)

        st.markdown('<div class="section-title">⚡ Today\'s Deals</div>', unsafe_allow_html=True)
        deal_products = [d.product for d in session.query(TodaysDeal).filter(
            TodaysDeal.is_active == True).all() if d.product]
        _product_grid(session, deal_products, "deals")

        st.markdown('<div class="section-title">⭐ Featured Products</div>', unsafe_allow_html=True)
        featured = [p for p in get_all_products(session) if p.is_featured]
        _product_grid(session, featured, "featured")

        st.markdown('<div class="section-title">🏆 Best Sellers</div>', unsafe_allow_html=True)
        bestsellers = [p for p in get_all_products(session) if p.is_bestseller]
        _product_grid(session, bestsellers, "bestsellers")

        st.markdown('<div class="section-title">🆕 New Arrivals</div>', unsafe_allow_html=True)
        new_arrivals = [p for p in get_all_products(session) if p.is_new_arrival]
        _product_grid(session, new_arrivals, "newarrivals")

        _brand_strip(session)
        _recently_viewed_section(session)
        _testimonials_section(session)
        _newsletter_section()

    if active_tab == TAB_LABELS[1]:
        st.markdown('<div class="section-title">🔍 Browse Products</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            category = st.selectbox("Category", CATEGORIES, key="filter_category")
        with c2:
            brand_options = ["All Brands"] + [b for b, _ in get_brands(session)]
            brand = st.selectbox("Brand", brand_options, key="filter_brand")
        with c3:
            search = st.text_input("Search products", key="filter_search")
        c4, c5, c6 = st.columns(3)
        with c4:
            sort_by = st.selectbox(
                "Sort by", ["Relevance", "Price: Low to High", "Price: High to Low",
                            "Rating", "Newest", "Discount"], key="filter_sort")
        with c5:
            price_range = st.slider("Price Range (₹)", 0, 150000, (0, 150000), step=1000,
                                     key="filter_price")
        with c6:
            min_rating = st.slider("Minimum Rating", 0.0, 5.0, 0.0, 0.5, key="filter_rating")
        products = get_all_products(session, category=category, search=search, sort_by=sort_by,
                                     min_price=price_range[0], max_price=price_range[1],
                                     min_rating=min_rating, brand=brand)
        st.caption(f"Showing {len(products)} product(s)")
        _product_grid(session, products, "browse")

    if active_tab == TAB_LABELS[2]:
        _wishlist_tab(session)

    if active_tab == TAB_LABELS[3]:
        _compare_tab(session)

    if active_tab == TAB_LABELS[4]:
        st.markdown('<div class="section-title">🛒 Your Shopping Cart</div>', unsafe_allow_html=True)
        _cart_summary(session)

    if active_tab == TAB_LABELS[5]:
        _about_page()

    if active_tab == TAB_LABELS[6]:
        _privacy_page()

    if active_tab == TAB_LABELS[7]:
        _terms_page()

    _sticky_cart_widget(session)
    _footer()

    session.close()
