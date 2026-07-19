"""
NovaGrid Electronics - Main Application Entry Point
Run with:  streamlit run app.py

Renders a permanent, fixed 50%-50% split screen: the customer storefront
on the left, the live admin dashboard on the right. Both panels share one
SQLite database (database/db_setup.py) so any change made on the Admin
side is instantly reflected on the Customer side after a refresh, and
cart/order activity on the Customer side updates Admin KPIs in real time.
There is no view-mode toggle and no resize control — the split always
stays exactly 50%-50%, and each panel scrolls independently.
"""

import streamlit as st
import streamlit.components.v1 as components

from database.seed_data import seed_database
from modules.customer_website import render_customer_website, get_header_counts
from modules.admin_dashboard import render_admin_dashboard

st.set_page_config(
    page_title="NovaGrid Electronics | Premium Retail Experience",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --------------------------------------------------------------------------- #
# ONE-TIME DATABASE SEEDING
# --------------------------------------------------------------------------- #
seed_database(reset=False)

# --------------------------------------------------------------------------- #
# GLOBAL CSS
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800;900&family=Inter:wght@400;500;600;700&display=swap');

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stApp {
        background: linear-gradient(180deg, #FBFAFE 0%, #F3EFFB 100%);
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100% !important;
    }

    /* Independently scrollable panels via st.container(height=...) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 22px !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        border-radius: 22px !important;
    }

    /* Fixed 50/50 split (scoped to the top-level split row only, so nested
       product-grid / KPI columns elsewhere in the app are unaffected) */
    .st-key-ng_split_row > div[data-testid="stHorizontalBlock"] {
        gap: 1.25rem;
        flex-wrap: nowrap !important;
    }
    .st-key-ng_split_row > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        width: calc(50% - 0.625rem) !important;
        flex: 1 1 calc(50% - 0.625rem) !important;
        min-width: 0 !important;
    }

    .demo-title {
        text-align: center; color: #241B3D; font-size: 50px; font-weight: 900;
        margin-bottom: 2px; letter-spacing: 0.2px; font-family:'Poppins',sans-serif;
        text-shadow: 0 2px 0 rgba(36,27,61,0.05);
    }
    .demo-title span {
        background: linear-gradient(90deg,#7C4DFF,#FF6F91);
        -webkit-background-clip: text; background-clip: text; color: transparent;
    }
    .demo-tagline {
        text-align: center; color: #6B6478; font-size: 13.5px; font-weight: 700;
        letter-spacing: 3px; text-transform: uppercase; margin-bottom: 16px;
    }
    .demo-subtitle {
        text-align: center; color: #8F87A0; font-size: 11.5px; margin-bottom: 18px;
    }

    /* Shared top header row: company name on the left, wishlist/cart on the
       right — a single header shared by both the Customer Website and Admin
       Dashboard panels below, instead of a second, duplicate brand row
       living inside the customer panel. */
    .st-key-ng_top_header div[data-testid="stHorizontalBlock"] {
        align-items: center;
    }
    .demo-title-inline {
        color: #241B3D; font-size: 34px; font-weight: 900; line-height: 1.1;
        letter-spacing: 0.2px; font-family:'Poppins',sans-serif; white-space: nowrap;
    }
    .demo-title-inline span {
        background: linear-gradient(90deg,#7C4DFF,#FF6F91);
        -webkit-background-clip: text; background-clip: text; color: transparent;
    }
    .demo-tagline-inline {
        color: #6B6478; font-size: 11.5px; font-weight: 700;
        letter-spacing: 1.6px; text-transform: uppercase; margin-top: 2px;
    }
    .st-key-navbar_wishlist_jump_btn button, .st-key-navbar_cart_jump_btn button {
        border-radius: 999px !important; font-weight: 700 !important; font-size: 13px !important;
        padding: 7px 14px !important; border: none !important;
        box-shadow: none !important; min-height: 0 !important;
    }
    .st-key-navbar_wishlist_jump_btn button {
        background: #FFFFFF !important; color: #241B3D !important;
        border: 1px solid rgba(91,46,158,0.14) !important;
    }
    .st-key-navbar_wishlist_jump_btn button:hover {
        border-color: #7C4DFF !important; color: #7C4DFF !important;
    }
    .st-key-navbar_cart_jump_btn button {
        background: linear-gradient(90deg,#7C4DFF,#FF6F91) !important; color: white !important;
    }
    .st-key-navbar_cart_jump_btn button:hover {
        box-shadow: 0 6px 16px rgba(124,77,255,0.32) !important;
    }

    .split-label {
        text-align: center; font-size: 12.5px; font-weight: 800; letter-spacing: 1.5px;
        text-transform: uppercase; margin-bottom: 8px; padding: 6px 0;
        border-radius: 10px;
    }
    .split-label.customer {
        color: #7C4DFF; background: rgba(124,77,255,0.08);
    }
    .split-label.admin {
        color: #B8873F; background: rgba(184,135,63,0.10);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# SHARED TOP HEADER — company name + wishlist/cart, above both panels
# --------------------------------------------------------------------------- #
wishlist_count, cart_count = get_header_counts()

top_header = st.container(key="ng_top_header")
with top_header:
    title_col, wish_col, cart_col = st.columns([7, 1.3, 1.3])
    with title_col:
        st.markdown('<div class="demo-title-inline">✨ NOVAGRID <span>ELECTRONICS</span></div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="demo-tagline-inline">Premium Retail. Intelligently Connected.</div>',
                    unsafe_allow_html=True)
    with wish_col:
        wishlist_jump = st.button(
            f"❤️ {wishlist_count}", key="navbar_wishlist_jump_btn",
            use_container_width=True, help="Go to your wishlist",
        )
    with cart_col:
        cart_jump = st.button(
            f"🛒 {cart_count}", key="navbar_cart_jump_btn",
            use_container_width=True, help="Go to your cart",
        )

st.markdown(
    '<div class="demo-subtitle">One shared live database keeps the storefront and admin '
    'console perfectly in sync</div>',
    unsafe_allow_html=True,
)

if wishlist_jump:
    st.session_state["jump_to_tab"] = "Wishlist"
    st.rerun()
if cart_jump:
    st.session_state["jump_to_tab"] = "Cart"
    st.rerun()

# --------------------------------------------------------------------------- #
# PERMANENT 50% / 50% SPLIT — no toggle, no resize slider, always on
# --------------------------------------------------------------------------- #
PANEL_HEIGHT = 860  # pixels - panels scroll independently within this fixed height

split_row = st.container(key="ng_split_row")
with split_row:
    left_col, right_col = st.columns([1, 1], gap="medium")

    with left_col:
        st.markdown('<div class="split-label customer">🛍️ Customer Website</div>',
                    unsafe_allow_html=True)
        left_panel = st.container(height=PANEL_HEIGHT, border=True)
        with left_panel:
            render_customer_website()

    with right_col:
        st.markdown('<div class="split-label admin">🛠️ Admin Dashboard</div>',
                    unsafe_allow_html=True)
        right_panel = st.container(height=PANEL_HEIGHT, border=True)
        with right_panel:
            render_admin_dashboard()

# --------------------------------------------------------------------------- #
# SCROLL-POSITION MEMORY
# Every st.rerun() (triggered by either panel) redraws the whole app, and
# Streamlit recreates the two scrollable panel <div>s from scratch — which
# resets their scroll offset to the top. Without this, an admin edit that
# triggers a rerun DOES update the data instantly, but the customer panel
# visually snaps back to the top of the Home tab, so the change looks like
# it "didn't happen" until you scroll back down to find it again. This
# script remembers each panel's scrollTop on `window.parent` (which is
# never torn down, unlike the iframe this snippet itself runs in) and
# re-applies it right after every rerun, so both panels stay exactly where
# you left them.
# --------------------------------------------------------------------------- #
components.html(
    """
    <script>
    (function() {
        const doc = window.parent.document;
        const win = window.parent;
        if (!win.__ngScrollPos) { win.__ngScrollPos = [0, 0]; }
        if (!win.__ngScrollBound) { win.__ngScrollBound = new WeakSet(); }

        function apply() {
            const panels = doc.querySelectorAll(
                '.st-key-ng_split_row div[data-testid="stVerticalBlockBorderWrapper"] > div'
            );
            panels.forEach(function(el, idx) {
                if (idx > 1) return;
                if (typeof win.__ngScrollPos[idx] === 'number' && el.scrollTop !== win.__ngScrollPos[idx]) {
                    el.scrollTop = win.__ngScrollPos[idx];
                }
                if (!win.__ngScrollBound.has(el)) {
                    win.__ngScrollBound.add(el);
                    el.addEventListener('scroll', function() {
                        win.__ngScrollPos[idx] = el.scrollTop;
                    }, { passive: true });
                }
            });
        }

        let tries = 0;
        const timer = setInterval(function() {
            apply();
            tries += 1;
            if (tries > 25) clearInterval(timer);
        }, 100);
    })();
    </script>
    """,
    height=0, width=0,
)
