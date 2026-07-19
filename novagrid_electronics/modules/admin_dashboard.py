"""
NovaGrid Electronics - Admin Dashboard Panel
Full management console rendered in the RIGHT panel of the permanent
50/50 split. Provides KPIs, Product/Inventory/Advertisement/Video/Deal/
Discount/Coupon/Order/Customer/Dealer/Enquiry/Review management,
Customer Insights, Sales Simulation, CSV export and a Plotly analytics
suite. Every write commits to the shared SQLite DB and immediately
triggers a rerun, so the Customer Website reflects changes right away.
"""

import os
import random
import datetime as dt

import streamlit as st
from streamlit_option_menu import option_menu

from database.db_setup import (
    get_session, Product, Advertisement, VideoAd, DiscountRule,
    TodaysDeal, Dealer, Enquiry, CartItem, Sale, Review, Order,
    WishlistItem, ProductView, Coupon
)
from modules.utils import (
    get_all_products, products_dataframe, get_kpis, dataframe_to_csv_bytes,
    fmt_inr, image_data_uri, asset_abs_path, show_image, get_most_viewed_products,
    cancel_order, get_customers, get_active_coupons,
)
from modules.auth import is_admin_logged_in, login_form, logout_button
from modules.effects import (
    congratulations_popup, deal_activated_popup, flash_message, crackers_effect,
    confetti_burst, play_success_sound
)
from modules import analytics
from database.seed_data import generate_gradient_image, CATEGORY_COLORS, IMG_DIR

CATEGORIES = ["Smartphones", "Laptops", "Audio", "Televisions",
              "Wearables", "Home Appliances", "Gaming", "Cameras"]


def _inject_admin_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800;900&family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
            -webkit-font-smoothing: antialiased;
        }
        .admin-header {
            background: linear-gradient(120deg,#2A1B4D,#5B2E9E 60%,#3D2570);
            padding: 18px 24px; border-radius: 18px; margin-bottom: 16px;
            color: white; font-weight: 800; font-size: 21px;
            box-shadow: 0 10px 28px rgba(42,27,77,0.40);
            font-family:'Poppins',sans-serif; letter-spacing:-0.01em;
            display:flex; justify-content:space-between; align-items:center;
        }
        .kpi-card {
            background: linear-gradient(160deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02));
            backdrop-filter: blur(10px);
            border: 1px solid rgba(124,77,255,0.20); border-radius: 18px;
            padding: 16px 14px; text-align: center;
            transition: transform 0.22s cubic-bezier(.22,1,.36,1), border-color 0.22s ease, box-shadow 0.22s ease;
            margin-bottom: 12px;
        }
        .kpi-card:hover {
            transform: translateY(-4px);
            border-color: #7C4DFF;
            box-shadow: 0 12px 26px rgba(124,77,255,0.20);
        }
        .kpi-value {
            font-size: 24px; font-weight: 800; color: #7C4DFF;
            font-family:'Poppins',sans-serif; letter-spacing:-0.01em;
        }
        .kpi-label {
            font-size: 11px; color: #9CA3AF; font-weight: 600;
            text-transform: uppercase; letter-spacing: 0.4px; margin-top: 2px;
        }
        .stButton > button {
            border-radius: 980px !important; font-weight: 600 !important;
            transition: transform 0.16s cubic-bezier(.22,1,.36,1), box-shadow 0.16s ease !important;
        }
        .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 8px 18px rgba(42,27,77,0.18); }
        .stButton > button[kind="primary"] {
            background: linear-gradient(180deg,#5B2E9E,#43227A) !important; border: none !important;
        }
        div[data-testid="stMetric"] {
            background: rgba(91,46,158,0.04); border-radius: 14px; padding: 10px 14px;
            border: 1px solid rgba(91,46,158,0.10);
        }

        /* ---------------- Business snapshot: leaderboard + alerts ---------------- */
        .snapshot-title { font-weight:800; font-size:14px; margin-bottom:10px; }
        .leaderboard-row {
            display:flex; align-items:center; gap:12px;
            background: rgba(255,255,255,0.05); border:1px solid rgba(124,77,255,0.18);
            border-radius:14px; padding:10px 14px; margin-bottom:8px;
        }
        .leaderboard-rank { font-size:19px; width:26px; text-align:center; flex-shrink:0; }
        .leaderboard-info { flex:1; min-width:0; }
        .leaderboard-name {
            font-weight:700; font-size:12.5px; margin-bottom:4px;
            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
        }
        .leaderboard-bar-track { background:rgba(255,255,255,0.10); border-radius:6px; height:6px; width:100%; }
        .leaderboard-bar-fill { background:linear-gradient(90deg,#5B2E9E,#7C4DFF); border-radius:6px; height:6px; }
        .leaderboard-stats {
            text-align:right; font-size:12px; font-weight:800; color:#7C4DFF;
            white-space:nowrap; flex-shrink:0;
        }
        .leaderboard-stats span { display:block; font-size:10px; color:#9CA3AF; font-weight:600; }
        .alert-empty {
            background: rgba(18,184,134,0.10); border:1px solid rgba(18,184,134,0.35);
            border-radius:12px; padding:12px 14px; font-weight:700; font-size:12.5px; color:#12B886;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


_KPI_ICONS = {
    "Total Products": "📦", "Inventory Remaining": "🗃️", "Low Stock": "⚠️",
    "Out of Stock": "❌", "Active Advertisements": "📢", "Cart Items": "🛒",
    "Wishlist Items": "❤️", "Orders Placed": "🧾", "Cancelled Orders": "🚫",
    "Active Coupons": "🎟️", "Customers": "🧑‍🤝‍🧑", "Customer Enquiries": "💬",
    "Dealers": "🤝", "Revenue": "💰",
}


def _kpi_row(session):
    kpis = get_kpis(session)
    labels = list(kpis.keys())
    cols = st.columns(4)
    for i, label in enumerate(labels):
        value = kpis[label]
        display = fmt_inr(value) if label == "Revenue" else f"{value:,}"
        icon = _KPI_ICONS.get(label, "📊")
        with cols[i % 4]:
            st.markdown(
                f"""<div class="kpi-card"><div style="font-size:18px;">{icon}</div>
                <div class="kpi-value">{display}</div>
                <div class="kpi-label">{label}</div></div>""",
                unsafe_allow_html=True,
            )
        if (i + 1) % 4 == 0 and i != len(labels) - 1:
            cols = st.columns(4)


def _business_snapshot(session):
    st.markdown("#### ⚡ Business Snapshot")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="snapshot-title">🏆 Top 5 Products (by units sold)</div>',
                     unsafe_allow_html=True)
        sales = session.query(Sale).filter(Sale.is_voided == False).all()
        if not sales:
            st.caption("No sales data yet — check the Sales Sim tab to generate some.")
        else:
            agg = {}
            for s in sales:
                bucket = agg.setdefault(s.product_id, {"units": 0, "revenue": 0.0})
                bucket["units"] += s.quantity
                bucket["revenue"] += s.amount
            top = sorted(agg.items(), key=lambda kv: kv[1]["units"], reverse=True)[:5]
            max_units = top[0][1]["units"] or 1
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            for i, (pid, stats) in enumerate(top):
                product = session.query(Product).get(pid)
                if not product:
                    continue
                pct = max(6, int(100 * stats["units"] / max_units))
                st.markdown(
                    f"""<div class="leaderboard-row">
                        <div class="leaderboard-rank">{medals[i]}</div>
                        <div class="leaderboard-info">
                            <div class="leaderboard-name">{product.name}</div>
                            <div class="leaderboard-bar-track">
                                <div class="leaderboard-bar-fill" style="width:{pct}%;"></div>
                            </div>
                        </div>
                        <div class="leaderboard-stats">{stats['units']} sold
                            <span>{fmt_inr(stats['revenue'])}</span>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    with col2:
        st.markdown('<div class="snapshot-title">⚠️ Low Stock Alerts</div>', unsafe_allow_html=True)
        products = session.query(Product).all()
        low = sorted([p for p in products if p.stock_status in ("Low Stock", "Out of Stock")],
                     key=lambda p: p.stock)
        if not low:
            st.markdown('<div class="alert-empty">✅ All products are healthily stocked.</div>',
                         unsafe_allow_html=True)
        else:
            for p in low[:5]:
                color = "#DC2626" if p.stock_status == "Out of Stock" else "#B8873F"
                with st.container(border=True):
                    ac1, ac2 = st.columns([3, 1])
                    with ac1:
                        st.markdown(f"**{p.name}**")
                        st.markdown(
                            f"<span style='color:{color};font-weight:700;font-size:12px;'>"
                            f"{p.stock_status} — {p.stock} left</span>",
                            unsafe_allow_html=True,
                        )
                    with ac2:
                        if st.button("📥 +20", key=f"snap_restock_{p.id}", use_container_width=True):
                            p.stock += 20
                            session.commit()
                            flash_message(f"{p.name} restocked by 20 units. New stock: {p.stock}",
                                          "success")
                            st.rerun()
            if len(low) > 5:
                st.caption(f"+ {len(low) - 5} more low-stock item(s) — see the Inventory tab.")


# --------------------------------------------------------------------------- #
# PRODUCT CRUD + INVENTORY
# --------------------------------------------------------------------------- #
def _product_management(session):
    st.subheader("📦 Product Management (CRUD)")
    action = st.radio("Action", ["View / Edit", "Add New Product", "Delete Product"],
                       horizontal=True, key="product_action")

    if action == "View / Edit":
        products = get_all_products(session)
        if not products:
            st.info("No products yet.")
            return
        names = {f"#{p.id} - {p.name}": p.id for p in products}
        selected = st.selectbox("Select product to edit", list(names.keys()), key="edit_product_select")
        product = session.query(Product).get(names[selected])

        if st.session_state.get("highlight_product_id") == product.id:
            st.success(f"🔗 Highlighted on Customer Website: {product.name}")

        col1, col2 = st.columns([1, 2])
        with col1:
            show_image(st, image_data_uri(product.image_path))
            st.caption(f"SKU: `{product.sku}`")
            gallery = product.gallery
            if len(gallery) > 1:
                gcols = st.columns(len(gallery))
                for gi, gpath in enumerate(gallery):
                    with gcols[gi]:
                        show_image(st, image_data_uri(gpath))
            if product.has_video and product.video_path:
                video_file = asset_abs_path(product.video_path)
                if video_file:
                    st.video(video_file)
            if st.button("📍 View on Website", key=f"spotlight_{product.id}", use_container_width=True,
                         help="Jumps the customer storefront to this product, highlighted."):
                st.session_state["highlight_product_id"] = product.id
                flash_message(f"{product.name} is now spotlighted on the storefront.", "success")
                st.rerun()
        with col2:
            with st.form(f"edit_form_{product.id}"):
                name = st.text_input("Name", product.name)
                category = st.selectbox("Category", CATEGORIES,
                                         index=CATEGORIES.index(product.category)
                                         if product.category in CATEGORIES else 0)
                brand = st.text_input("Brand", product.brand)
                price = st.number_input("Price (MRP)", min_value=0.0, value=float(product.price), step=100.0)
                discount = st.slider("Discount %", 0, 90, int(product.discount_percent))
                stock = st.number_input("Stock", min_value=0, value=int(product.stock))
                low_thresh = st.number_input("Low Stock Threshold", min_value=1,
                                              value=int(product.low_stock_threshold))
                warranty = st.text_input("Warranty", product.warranty)
                delivery_days = st.number_input("Delivery Days", min_value=1, value=int(product.delivery_days))
                emi_available = st.checkbox("EMI Available", product.emi_available)
                cashback_percent = st.slider("Cashback %", 0, 20, int(product.cashback_percent or 0))
                description = st.text_area("Description", product.description or "")
                specifications = st.text_area("Specifications (pipe-separated)",
                                               product.specifications or "")
                c1, c2, c3 = st.columns(3)
                with c1:
                    featured = st.checkbox("Featured", product.is_featured)
                with c2:
                    bestseller = st.checkbox("Bestseller", product.is_bestseller)
                with c3:
                    new_arrival = st.checkbox("New Arrival", product.is_new_arrival)
                submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)

            if submitted:
                product.name = name
                product.category = category
                product.brand = brand
                product.price = price
                product.discount_percent = discount
                product.stock = stock
                product.low_stock_threshold = low_thresh
                product.warranty = warranty
                product.delivery_days = delivery_days
                product.emi_available = emi_available
                product.cashback_percent = cashback_percent
                product.description = description
                product.specifications = specifications
                product.is_featured = featured
                product.is_bestseller = bestseller
                product.is_new_arrival = new_arrival
                session.commit()
                flash_message(f"{name} updated successfully! Changes are live on the website.", "success")
                congratulations_popup(f"✅ {name} updated successfully!")
                st.rerun()

    elif action == "Add New Product":
        with st.form("add_product_form"):
            name = st.text_input("Product Name")
            category = st.selectbox("Category", CATEGORIES)
            brand = st.text_input("Brand", "NovaGrid")
            price = st.number_input("Price (MRP)", min_value=0.0, step=100.0, value=9999.0)
            discount = st.slider("Discount %", 0, 90, 10)
            stock = st.number_input("Initial Stock", min_value=0, value=25)
            warranty = st.text_input("Warranty", "1 Year Brand Warranty")
            delivery_days = st.number_input("Delivery Days", min_value=1, value=3)
            cashback_percent = st.slider("Cashback %", 0, 20, 0)
            description = st.text_area("Description", "Premium quality electronics from NovaGrid.")
            specifications = st.text_area("Specifications (pipe-separated)", "Feature 1|Feature 2")
            submitted = st.form_submit_button("➕ Add Product", use_container_width=True)

        if submitted:
            if not name.strip():
                flash_message("Product name is required.", "error")
            else:
                new_product = Product(
                    name=name, category=category, brand=brand, price=price,
                    discount_percent=discount, stock=stock, low_stock_threshold=10,
                    rating=4.0, review_count=0, description=description,
                    specifications=specifications, warranty=warranty,
                    delivery_days=delivery_days, emi_available=price >= 3000,
                    cashback_percent=cashback_percent,
                )
                session.add(new_product)
                session.commit()
                new_product.sku = f"NVG-{category[:3].upper()}-{new_product.id:03d}"
                colors = CATEGORY_COLORS.get(category, ("#241B3D", "#7C4DFF"))
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

                from database.seed_data import generate_product_studio_image, generate_video_preview
                import json as _json
                img_path = f"{IMG_DIR}/product_{new_product.id}_0.png"
                generate_product_studio_image(img_path, category, colors, variant=0, seed=new_product.id)
                new_product.image_path = os.path.relpath(img_path, base)

                gallery_paths = []
                for v in range(1, 4):
                    gp = f"{IMG_DIR}/product_{new_product.id}_{v}.png"
                    generate_product_studio_image(gp, category, colors, variant=v, seed=new_product.id)
                    gallery_paths.append(os.path.relpath(gp, base))
                new_product.gallery_json = _json.dumps(gallery_paths)

                vpath = os.path.join(base, "assets", "videos", f"product_{new_product.id}.mp4")
                has_video = generate_video_preview(vpath, category, colors, seed=new_product.id)
                if has_video:
                    new_product.has_video = True
                    new_product.video_path = os.path.relpath(vpath, base)
                    new_product.video_note = "360° Product Preview"

                session.commit()
                flash_message(f"{name} added successfully with a full premium image gallery"
                               f"{' and video preview' if has_video else ''}!", "success")
                congratulations_popup(f"🎉 {name} added to catalog!")
                st.rerun()

    elif action == "Delete Product":
        products = get_all_products(session)
        if not products:
            st.info("No products yet.")
            return
        names = {f"#{p.id} - {p.name}": p.id for p in products}
        selected = st.selectbox("Select product to delete", list(names.keys()), key="delete_product_select")
        if st.button("🗑️ Delete Product", use_container_width=True):
            product = session.query(Product).get(names[selected])
            pname = product.name
            session.delete(product)
            session.commit()
            flash_message(f"{pname} deleted.", "warning")
            st.rerun()


def _inventory_management(session):
    st.subheader("📊 Inventory Management")
    df = products_dataframe(session)
    st.dataframe(df[["ID", "SKU", "Name", "Category", "Stock", "Status"]],
                 use_container_width=True, hide_index=True)

    st.markdown("##### Quick Restock")
    products = get_all_products(session)
    names = {f"#{p.id} - {p.name} (Stock: {p.stock})": p.id for p in products}
    selected = st.selectbox("Select product", list(names.keys()), key="restock_select")
    qty = st.number_input("Quantity to add", min_value=1, value=10, key="restock_qty")
    if st.button("📥 Restock", use_container_width=True):
        product = session.query(Product).get(names[selected])
        product.stock += qty
        session.commit()
        flash_message(f"{product.name} restocked by {qty} units. New stock: {product.stock}", "success")
        st.rerun()


# --------------------------------------------------------------------------- #
# ADVERTISEMENT / VIDEO / DEAL / DISCOUNT / COUPON MANAGERS
# --------------------------------------------------------------------------- #
def _ad_management(session):
    st.subheader("📢 Advertisement Manager")
    ads = session.query(Advertisement).all()
    if ads:
        for ad in ads:
            with st.expander(f"{ad.title} ({'Active' if ad.is_active else 'Inactive'})"):
                show_image(st, image_data_uri(ad.image_path))
                new_active = st.checkbox("Active", ad.is_active, key=f"ad_active_{ad.id}")
                new_position = st.selectbox("Position", ["hero", "banner", "flash", "festival"],
                                             index=["hero", "banner", "flash", "festival"].index(ad.position)
                                             if ad.position in ["hero", "banner", "flash", "festival"] else 0,
                                             key=f"ad_pos_{ad.id}")
                if st.button("Update", key=f"ad_update_{ad.id}"):
                    ad.is_active = new_active
                    ad.position = new_position
                    session.commit()
                    flash_message(f"Advertisement '{ad.title}' updated.", "success")
                    st.rerun()

    st.markdown("##### ➕ Add New Advertisement")
    with st.form("add_ad_form"):
        title = st.text_input("Title")
        subtitle = st.text_input("Subtitle")
        position = st.selectbox("Position", ["hero", "banner", "flash", "festival"])
        submitted = st.form_submit_button("Add Advertisement", use_container_width=True)
    if submitted and title:
        colors = list(CATEGORY_COLORS.values())[len(title) % len(CATEGORY_COLORS)]
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "assets", "images", "ads", f"ad_custom_{title[:10]}.png")
        generate_gradient_image(path, title, subtitle, colors, size=(1400, 560), variant=1)
        session.add(Advertisement(title=title, subtitle=subtitle,
                                   image_path=os.path.relpath(path, base),
                                   is_active=True, position=position))
        session.commit()
        flash_message(f"Advertisement '{title}' created.", "success")
        st.rerun()


def _video_ad_management(session):
    st.subheader("🎬 Video Advertisement Manager")
    video_ads = session.query(VideoAd).all()
    if not video_ads:
        st.info("No video advertisements yet.")
    for va in video_ads:
        with st.expander(f"{va.title} ({'Active' if va.is_active else 'Inactive'})"):
            st.write(f"**Linked Product:** {va.product.name if va.product else 'N/A'}")
            if va.video_path:
                video_file = asset_abs_path(va.video_path)
                if video_file:
                    st.video(video_file)
                else:
                    st.caption("Video file not found on disk.")
            new_active = st.checkbox("Active", va.is_active, key=f"va_active_{va.id}")
            if st.button("Update", key=f"va_update_{va.id}"):
                va.is_active = new_active
                session.commit()
                flash_message(f"Video ad '{va.title}' updated.", "success")
                st.rerun()

    st.markdown("##### ➕ Register New Video Advertisement")
    products = get_all_products(session)
    names = {f"#{p.id} - {p.name}": p.id for p in products}
    with st.form("add_video_form"):
        product_choice = st.selectbox("Product", list(names.keys()))
        title = st.text_input("Video Title")
        submitted = st.form_submit_button("Add Video Advertisement", use_container_width=True)
    if submitted and title:
        pid = names[product_choice]
        product = session.query(Product).get(pid)
        colors = CATEGORY_COLORS.get(product.category, ("#241B3D", "#7C4DFF"))
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vpath = os.path.join(base, "assets", "videos", f"product_{pid}_custom.mp4")
        from database.seed_data import generate_video_placeholder
        generate_video_placeholder(vpath, product.name, colors, category=product.category)
        rel_path = os.path.relpath(vpath, base)
        session.add(VideoAd(product_id=pid, title=title, video_path=rel_path, is_active=True))
        product.has_video = True
        product.video_note = title
        product.video_path = rel_path
        session.commit()
        flash_message(f"Video advertisement '{title}' registered.", "success")
        play_success_sound()
        confetti_burst()
        st.rerun()


def _deal_management(session):
    st.subheader("⚡ Today's Deal Manager")
    now = dt.datetime.utcnow()
    deals = session.query(TodaysDeal).all()
    for deal in deals:
        remaining = deal.ends_at - now
        status = "🟢 Active" if deal.is_active and remaining.total_seconds() > 0 else "🔴 Expired"
        with st.expander(f"{deal.product.name if deal.product else 'N/A'} - {status}"):
            st.write(f"Discount: {deal.deal_discount_percent}%")
            st.write(f"Ends: {deal.ends_at.strftime('%Y-%m-%d %H:%M')} UTC")
            new_active = st.checkbox("Active", deal.is_active, key=f"deal_active_{deal.id}")
            if st.button("Update", key=f"deal_update_{deal.id}"):
                deal.is_active = new_active
                session.commit()
                flash_message("Deal updated.", "success")
                st.rerun()

    st.markdown("##### ➕ Create New Deal")
    products = get_all_products(session)
    names = {f"#{p.id} - {p.name}": p.id for p in products}
    with st.form("add_deal_form"):
        product_choice = st.selectbox("Product", list(names.keys()))
        discount = st.slider("Deal Discount %", 5, 70, 20)
        duration_hours = st.slider("Duration (hours)", 1, 72, 12)
        submitted = st.form_submit_button("🔥 Activate Deal", use_container_width=True)
    if submitted:
        pid = names[product_choice]
        session.add(TodaysDeal(
            product_id=pid, deal_discount_percent=discount, starts_at=now,
            ends_at=now + dt.timedelta(hours=duration_hours), is_active=True,
        ))
        session.commit()
        product = session.query(Product).get(pid)
        deal_activated_popup(product.name, discount)
        crackers_effect()
        flash_message(f"Deal activated for {product.name}!", "success")
        st.rerun()


def _discount_rule_management(session):
    st.subheader("💰 Discount Rule Manager (Buy More, Save More)")
    rules = session.query(DiscountRule).all()
    if rules:
        for r in rules:
            st.write(f"**{r.product.name if r.product else 'N/A'}** — "
                      f"Buy {r.min_qty}+, get extra {r.extra_discount_percent}% off "
                      f"({r.description})")
    else:
        st.info("No discount rules yet.")

    st.markdown("##### ➕ Add Discount Rule")
    products = get_all_products(session)
    names = {f"#{p.id} - {p.name}": p.id for p in products}
    with st.form("add_rule_form"):
        product_choice = st.selectbox("Product", list(names.keys()))
        min_qty = st.number_input("Minimum Quantity", min_value=2, value=2)
        extra_discount = st.slider("Extra Discount %", 1, 30, 5)
        description = st.text_input("Description", f"Buy {min_qty}+, get extra {extra_discount}% off")
        submitted = st.form_submit_button("Add Rule", use_container_width=True)
    if submitted:
        pid = names[product_choice]
        session.add(DiscountRule(product_id=pid, min_qty=min_qty,
                                  extra_discount_percent=extra_discount, description=description))
        session.commit()
        flash_message("Discount rule added.", "success")
        st.rerun()


def _coupon_management(session):
    st.subheader("🎟️ Coupon Manager")
    coupons = session.query(Coupon).order_by(Coupon.created_at.desc()).all()
    if coupons:
        for c in coupons:
            status = "🟢 Active" if c.is_active else "🔴 Inactive"
            with st.expander(f"{c.code} — {c.discount_percent}% off — {status}"):
                st.write(f"**Description:** {c.description or '-'}")
                st.write(f"**Min Order Value:** {fmt_inr(c.min_order_value)}")
                st.write(f"**Max Discount:** {fmt_inr(c.max_discount_amount)}")
                st.write(f"**Expires:** {c.expires_at.strftime('%Y-%m-%d') if c.expires_at else 'Never'}")
                new_active = st.checkbox("Active", c.is_active, key=f"coupon_active_{c.id}")
                if st.button("Update", key=f"coupon_update_{c.id}"):
                    c.is_active = new_active
                    session.commit()
                    flash_message(f"Coupon '{c.code}' updated.", "success")
                    st.rerun()
    else:
        st.info("No coupons yet.")

    st.markdown("##### ➕ Create New Coupon")
    with st.form("add_coupon_form"):
        code = st.text_input("Coupon Code", placeholder="e.g. SAVE20").upper()
        discount_percent = st.slider("Discount %", 1, 70, 10)
        min_order_value = st.number_input("Minimum Order Value (₹)", min_value=0.0, value=999.0, step=100.0)
        max_discount = st.number_input("Max Discount Amount (₹)", min_value=0.0, value=2000.0, step=100.0)
        description = st.text_input("Description", "Special discount")
        valid_days = st.slider("Valid for (days)", 1, 365, 90)
        submitted = st.form_submit_button("🎟️ Create Coupon", use_container_width=True)
    if submitted and code.strip():
        existing = session.query(Coupon).filter(Coupon.code == code.strip()).first()
        if existing:
            flash_message(f"Coupon code '{code}' already exists.", "error")
        else:
            session.add(Coupon(
                code=code.strip(), discount_percent=discount_percent,
                min_order_value=min_order_value, max_discount_amount=max_discount,
                description=description, is_active=True,
                expires_at=dt.datetime.utcnow() + dt.timedelta(days=valid_days),
            ))
            session.commit()
            flash_message(f"Coupon '{code}' created.", "success")
            st.rerun()


# --------------------------------------------------------------------------- #
# ORDERS + CUSTOMERS + DEALERS + ENQUIRIES + REVIEWS
# --------------------------------------------------------------------------- #
def _order_management(session):
    st.subheader("🧾 Order Management")
    orders = session.query(Order).order_by(Order.created_at.desc()).all()
    if not orders:
        st.info("No orders yet — complete a checkout on the storefront to see it here.")
        return
    status_filter = st.selectbox("Filter by status", ["All", "Confirmed", "Shipped", "Delivered", "Cancelled"],
                                  key="order_status_filter")
    for o in orders:
        if status_filter != "All" and o.status != status_filter:
            continue
        badge = {"Confirmed": "🟢", "Shipped": "🚚", "Delivered": "📦", "Cancelled": "🚫"}.get(o.status, "⚪")
        with st.expander(f"{badge} {o.order_number} — {o.customer_name} — {fmt_inr(o.total_amount)} — {o.status}"):
            st.write(f"**Customer:** {o.customer_name} | {o.customer_email or '-'} | {o.customer_phone or '-'}")
            st.write(f"**Shipping Address:** {o.shipping_address or '-'}")
            st.write(f"**Payment:** {o.payment_method}")
            st.write(f"**Subtotal:** {fmt_inr(o.subtotal_amount)}  •  "
                     f"**Discount:** -{fmt_inr(o.discount_amount)}"
                     f"{f' (coupon {o.coupon_code})' if o.coupon_code else ''}  •  "
                     f"**GST:** {fmt_inr(o.gst_amount)}")
            st.write(f"**Total:** {fmt_inr(o.total_amount)}")
            st.write(f"**Placed:** {o.created_at.strftime('%d %b %Y, %I:%M %p')}")
            if o.estimated_delivery:
                st.write(f"**Estimated Delivery:** {o.estimated_delivery.strftime('%d %b %Y')}")
            if o.cancelled_at:
                st.write(f"**Cancelled:** {o.cancelled_at.strftime('%d %b %Y, %I:%M %p')}")
            if o.status != "Cancelled":
                c1, c2 = st.columns(2)
                with c1:
                    new_status = st.selectbox("Update Status", ["Confirmed", "Shipped", "Delivered"],
                                               index=["Confirmed", "Shipped", "Delivered"].index(o.status)
                                               if o.status in ["Confirmed", "Shipped", "Delivered"] else 0,
                                               key=f"order_status_{o.id}")
                    if st.button("Update Status", key=f"order_status_update_{o.id}", use_container_width=True):
                        o.status = new_status
                        session.commit()
                        flash_message(f"Order {o.order_number} marked {new_status}.", "success")
                        st.rerun()
                with c2:
                    if st.button("🚫 Cancel Order", key=f"order_cancel_{o.id}", use_container_width=True):
                        ok, msg = cancel_order(session, o.id)
                        flash_message(msg, "success" if ok else "error")
                        st.rerun()


def _customer_management(session):
    st.subheader("🧑‍🤝‍🧑 Customer Directory")
    st.caption("Aggregated from orders placed on the storefront — this demo has no separate "
               "login/account system, so each unique name/email becomes one customer record.")
    customers = get_customers(session)
    if not customers:
        st.info("No customers yet — complete a checkout on the storefront to see it here.")
        return
    st.dataframe([{
        "Name": c["name"], "Email": c["email"] or "-", "Phone": c["phone"] or "-",
        "Orders": c["orders"], "Total Spent": fmt_inr(c["total_spent"]),
        "Last Order": c["last_order"].strftime("%Y-%m-%d") if c["last_order"] else "-",
    } for c in customers], use_container_width=True, hide_index=True)


def _dealer_management(session):
    st.subheader("🤝 Dealer Management")
    dealers = session.query(Dealer).all()
    if dealers:
        df_data = [{
            "Name": d.name, "Region": d.region, "Products Supplied": d.products_supplied,
            "Performance": d.performance_score, "Joined": d.join_date.strftime("%Y-%m-%d"),
        } for d in dealers]
        st.dataframe(df_data, use_container_width=True, hide_index=True)

    st.markdown("##### ➕ Add New Dealer")
    with st.form("add_dealer_form"):
        name = st.text_input("Dealer Name")
        region = st.selectbox("Region", ["North India", "South India", "East India", "West India"])
        email = st.text_input("Contact Email")
        phone = st.text_input("Contact Phone")
        products_supplied = st.number_input("Products Supplied", min_value=0, value=50)
        submitted = st.form_submit_button("Add Dealer", use_container_width=True)
    if submitted and name:
        session.add(Dealer(name=name, region=region, contact_email=email, contact_phone=phone,
                            products_supplied=products_supplied,
                            performance_score=75.0, join_date=dt.datetime.utcnow()))
        session.commit()
        flash_message(f"Dealer '{name}' added.", "success")
        st.rerun()


def _enquiry_management(session):
    st.subheader("📩 Customer Enquiry Management")
    enquiries = session.query(Enquiry).order_by(Enquiry.created_at.desc()).all()
    if not enquiries:
        st.info("No enquiries yet.")
        return
    for e in enquiries:
        with st.expander(f"{e.customer_name} — {e.status} "
                          f"({e.created_at.strftime('%Y-%m-%d')})"):
            st.write(f"**Product:** {e.product.name if e.product else 'General Enquiry'}")
            st.write(f"**Email:** {e.email}  |  **Phone:** {e.phone}")
            st.write(f"**Message:** {e.message}")
            new_status = st.selectbox("Status", ["Open", "In Progress", "Resolved"],
                                       index=["Open", "In Progress", "Resolved"].index(e.status),
                                       key=f"enquiry_status_{e.id}")
            if st.button("Update Status", key=f"enquiry_update_{e.id}"):
                e.status = new_status
                session.commit()
                flash_message("Enquiry status updated.", "success")
                st.rerun()


def _review_management(session):
    st.subheader("⭐ Review Moderation")
    reviews = session.query(Review).order_by(Review.created_at.desc()).limit(40).all()
    if not reviews:
        st.info("No reviews yet.")
        return
    for r in reviews:
        with st.expander(f"{r.reviewer_name} — {r.rating}★ on "
                          f"{r.product.name if r.product else 'N/A'}"):
            st.write(f"**Title:** {r.title}")
            st.write(r.comment)
            st.caption(f"Verified: {'Yes' if r.verified_purchase else 'No'} • "
                       f"Helpful votes: {r.helpful_count} • "
                       f"{r.created_at.strftime('%Y-%m-%d')}")
            if st.button("🗑️ Remove Review", key=f"del_review_{r.id}"):
                session.delete(r)
                session.commit()
                flash_message("Review removed.", "warning")
                st.rerun()


# --------------------------------------------------------------------------- #
# CUSTOMER INSIGHTS + SALES SIMULATION
# --------------------------------------------------------------------------- #
def _customer_insights(session):
    st.subheader("🧠 Customer Insights")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(analytics.most_viewed_products_chart(), use_container_width=True)
        st.plotly_chart(analytics.review_rating_distribution_chart(), use_container_width=True)
    with c2:
        st.plotly_chart(analytics.wishlist_activity_chart(), use_container_width=True)
        st.plotly_chart(analytics.orders_trend_chart(), use_container_width=True)

    st.markdown("##### 🔥 Most Viewed Products")
    top_viewed = get_most_viewed_products(session, limit=5)
    if top_viewed:
        for p, cnt in top_viewed:
            st.write(f"**{p.name}** — {cnt} view(s)")
    else:
        st.caption("No product views tracked yet — browse the storefront to generate data.")

    orders = session.query(Order).order_by(Order.created_at.desc()).limit(10).all()
    st.markdown("##### 🧾 Recent Orders")
    if orders:
        st.dataframe([{
            "Order #": o.order_number, "Total": fmt_inr(o.total_amount),
            "Payment": o.payment_method, "Status": o.status,
            "Placed": o.created_at.strftime("%Y-%m-%d %H:%M"),
            "ETA": o.estimated_delivery.strftime("%Y-%m-%d") if o.estimated_delivery else "",
        } for o in orders], use_container_width=True, hide_index=True)
    else:
        st.caption("No orders placed yet — complete a checkout on the storefront to see it here.")


def _sales_simulation(session):
    st.subheader("🧪 Sales Simulation")
    st.caption("Instantly generate a batch of simulated sales to demo revenue growth and analytics.")
    products = get_all_products(session)
    c1, c2 = st.columns(2)
    with c1:
        n_sales = st.slider("Number of simulated sales", 1, 50, 10, key="sim_n_sales")
    with c2:
        days_back = st.slider("Spread across past N days", 0, 30, 7, key="sim_days_back")
    if st.button("🚀 Run Sales Simulation", use_container_width=True, type="primary"):
        if not products:
            flash_message("No products available to simulate sales for.", "error")
        else:
            now = dt.datetime.utcnow()
            total_amount = 0.0
            for _ in range(n_sales):
                p = random.choice(products)
                qty = random.randint(1, 3)
                amount = round(p.discounted_price * qty, 2)
                total_amount += amount
                session.add(Sale(
                    product_id=p.id, quantity=qty, amount=amount,
                    timestamp=now - dt.timedelta(days=random.randint(0, days_back),
                                                  hours=random.randint(0, 23)),
                ))
            session.commit()
            play_success_sound()
            confetti_burst()
            flash_message(f"Simulated {n_sales} sales worth {fmt_inr(total_amount)}!", "success")
            st.rerun()


# --------------------------------------------------------------------------- #
# CSV EXPORT
# --------------------------------------------------------------------------- #
def _csv_export(session):
    st.subheader("📤 CSV Export")
    export_choice = st.selectbox("Select data to export",
                                  ["Products", "Dealers", "Enquiries", "Sales", "Orders",
                                   "Reviews", "Customers", "Coupons"])
    import pandas as pd
    if export_choice == "Products":
        df = products_dataframe(session)
    elif export_choice == "Dealers":
        dealers = session.query(Dealer).all()
        df = pd.DataFrame([{
            "Name": d.name, "Region": d.region, "Products Supplied": d.products_supplied,
            "Performance": d.performance_score, "Joined": d.join_date.strftime("%Y-%m-%d"),
        } for d in dealers])
    elif export_choice == "Enquiries":
        enquiries = session.query(Enquiry).all()
        df = pd.DataFrame([{
            "Customer": e.customer_name, "Email": e.email, "Phone": e.phone,
            "Product": e.product.name if e.product else "", "Status": e.status,
            "Message": e.message, "Date": e.created_at.strftime("%Y-%m-%d"),
        } for e in enquiries])
    elif export_choice == "Orders":
        orders = session.query(Order).all()
        df = pd.DataFrame([{
            "Order #": o.order_number, "Customer": o.customer_name, "Subtotal": o.subtotal_amount,
            "Discount": o.discount_amount, "GST": o.gst_amount, "Total": o.total_amount,
            "Payment": o.payment_method, "Status": o.status,
            "Placed": o.created_at.strftime("%Y-%m-%d %H:%M"),
        } for o in orders])
    elif export_choice == "Reviews":
        reviews = session.query(Review).all()
        df = pd.DataFrame([{
            "Product": r.product.name if r.product else "", "Reviewer": r.reviewer_name,
            "Rating": r.rating, "Title": r.title, "Verified": r.verified_purchase,
            "Date": r.created_at.strftime("%Y-%m-%d"),
        } for r in reviews])
    elif export_choice == "Customers":
        df = pd.DataFrame([{
            "Name": c["name"], "Email": c["email"], "Phone": c["phone"],
            "Orders": c["orders"], "Total Spent": c["total_spent"],
        } for c in get_customers(session)])
    elif export_choice == "Coupons":
        coupons = session.query(Coupon).all()
        df = pd.DataFrame([{
            "Code": c.code, "Discount %": c.discount_percent, "Min Order": c.min_order_value,
            "Max Discount": c.max_discount_amount, "Active": c.is_active,
        } for c in coupons])
    else:
        sales = session.query(Sale).all()
        df = pd.DataFrame([{
            "Product": s.product.name if s.product else "", "Quantity": s.quantity,
            "Amount": s.amount, "Voided": s.is_voided, "Date": s.timestamp.strftime("%Y-%m-%d %H:%M"),
        } for s in sales])

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download CSV", data=dataframe_to_csv_bytes(df),
                        file_name=f"novagrid_{export_choice.lower()}.csv", mime="text/csv",
                        use_container_width=True)


# --------------------------------------------------------------------------- #
# ANALYTICS
# --------------------------------------------------------------------------- #
def _analytics_tab():
    st.subheader("📈 Plotly Analytics Suite")
    a1, a2 = st.columns(2)
    with a1:
        st.plotly_chart(analytics.revenue_trend_chart(), use_container_width=True)
        st.plotly_chart(analytics.product_performance_chart(), use_container_width=True)
        st.plotly_chart(analytics.low_stock_analysis_chart(), use_container_width=True)
        st.plotly_chart(analytics.dealer_growth_chart(), use_container_width=True)
    with a2:
        st.plotly_chart(analytics.inventory_levels_chart(), use_container_width=True)
        st.plotly_chart(analytics.category_distribution_chart(), use_container_width=True)
        st.plotly_chart(analytics.discount_performance_chart(), use_container_width=True)
        st.plotly_chart(analytics.dealer_performance_chart(), use_container_width=True)
    st.plotly_chart(analytics.enquiries_chart(), use_container_width=True)
    st.plotly_chart(analytics.enquiries_trend_chart(), use_container_width=True)


# --------------------------------------------------------------------------- #
# MAIN RENDER
# --------------------------------------------------------------------------- #
def render_admin_dashboard():
    _inject_admin_css()
    st.markdown(
        '<div class="admin-header"><span>🛠️ NovaGrid Admin Dashboard</span>'
        '<span style="font-size:12px;opacity:0.75;">Business Console</span></div>',
        unsafe_allow_html=True,
    )

    if not is_admin_logged_in():
        login_form()
        return

    logout_button()
    session = get_session()

    kh1, kh2 = st.columns([5, 1])
    with kh1:
        st.markdown("#### 📊 Key Performance Indicators")
    with kh2:
        if st.button("🔄 Refresh", key="admin_refresh_btn", use_container_width=True,
                     help="Every number here is queried live from the database on each "
                          "render — this just forces an immediate re-render."):
            st.rerun()
    st.caption("Live from the database — every stock, price, discount, ad, order and "
               "inventory change appears here (and on the storefront) as soon as either "
               "side is refreshed. Nothing on this dashboard is cached.")
    _kpi_row(session)
    st.markdown("---")
    _business_snapshot(session)
    st.markdown("---")

    menu = option_menu(
        menu_title=None,
        options=["Products", "Inventory", "Ads", "Video Ads", "Deals",
                 "Discount Rules", "Coupons", "Orders", "Customers", "Dealers",
                 "Enquiries", "Reviews", "Customer Insights", "Sales Sim",
                 "CSV Export", "Analytics"],
        icons=["box-seam", "bar-chart-steps", "megaphone", "camera-reels",
               "lightning-charge", "percent", "ticket-perforated", "receipt",
               "people-fill", "people", "chat-dots", "star",
               "person-lines-fill", "rocket-takeoff", "download", "graph-up"],
        orientation="horizontal",
        default_index=0,
        styles={
            "container": {"padding": "0", "background-color": "rgba(255,255,255,0.03)"},
            "nav-link": {"font-size": "12px", "text-align": "center", "margin": "2px"},
            "nav-link-selected": {"background-color": "#5B2E9E"},
        },
    )

    if menu == "Products":
        _product_management(session)
    elif menu == "Inventory":
        _inventory_management(session)
    elif menu == "Ads":
        _ad_management(session)
    elif menu == "Video Ads":
        _video_ad_management(session)
    elif menu == "Deals":
        _deal_management(session)
    elif menu == "Discount Rules":
        _discount_rule_management(session)
    elif menu == "Coupons":
        _coupon_management(session)
    elif menu == "Orders":
        _order_management(session)
    elif menu == "Customers":
        _customer_management(session)
    elif menu == "Dealers":
        _dealer_management(session)
    elif menu == "Enquiries":
        _enquiry_management(session)
    elif menu == "Reviews":
        _review_management(session)
    elif menu == "Customer Insights":
        _customer_insights(session)
    elif menu == "Sales Sim":
        _sales_simulation(session)
    elif menu == "CSV Export":
        _csv_export(session)
    elif menu == "Analytics":
        _analytics_tab()

    session.close()
