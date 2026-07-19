"""
NovaGrid Electronics - Shared Utility Functions
Reusable helpers used by both the customer website and admin dashboard
to avoid code duplication (formatting, querying, cart/wishlist/order
logic, coupons, GST invoicing, order cancellation, reviews,
recently-viewed tracking, EMI & delivery estimates).
"""

import os
import base64
import random
import string
import datetime as dt
import json

import pandas as pd

from database.db_setup import (
    get_session, Product, Advertisement, VideoAd, DiscountRule,
    TodaysDeal, Dealer, Enquiry, CartItem, WishlistItem, CompareItem,
    ProductView, Review, Order, Sale, InventoryLog, Coupon, GST_RATE
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --------------------------------------------------------------------------- #
# FORMATTING
# --------------------------------------------------------------------------- #
def fmt_inr(amount):
    """Format a number as Indian Rupees, e.g. ₹1,23,456"""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return "₹0"
    s = f"{amount:,.0f}"
    return f"₹{s}"


def img_to_base64(path):
    full_path = path if os.path.isabs(path) else os.path.join(BASE_DIR, path)
    if not os.path.exists(full_path):
        return ""
    with open(full_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def image_data_uri(path):
    b64 = img_to_base64(path)
    if not b64:
        return ""
    ext = os.path.splitext(path)[1].lstrip(".") or "png"
    return f"data:image/{ext};base64,{b64}"


def asset_abs_path(path):
    """Resolves a project-relative asset path (image or video) to an
    absolute filesystem path, or None if it doesn't exist. Used for
    st.video(), which plays far more efficiently from a file path than
    from a base64 data URI."""
    if not path:
        return None
    full_path = path if os.path.isabs(path) else os.path.join(BASE_DIR, path)
    return full_path if os.path.exists(full_path) else None


def star_string(rating):
    full = int(rating)
    half = 1 if (rating - full) >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + ("½" if half else "") + "☆" * empty


def show_image(st_module, data_uri, caption=None):
    """Display an image in a way that works across old and new Streamlit
    versions (use_container_width was added in newer releases, and
    use_column_width is deprecated/removed in the newest ones)."""
    if not data_uri:
        return
    try:
        st_module.image(data_uri, use_container_width=True, caption=caption)
    except TypeError:
        try:
            st_module.image(data_uri, use_column_width=True, caption=caption)
        except TypeError:
            st_module.image(data_uri, caption=caption)


# --------------------------------------------------------------------------- #
# PRODUCT QUERIES
# --------------------------------------------------------------------------- #
def get_all_products(session=None, category=None, search=None, sort_by=None,
                      min_price=None, max_price=None, min_rating=None, brand=None):
    own_session = session is None
    session = session or get_session()
    q = session.query(Product)
    if category and category != "All":
        q = q.filter(Product.category == category)
    if brand and brand != "All Brands":
        q = q.filter(Product.brand == brand)
    if search:
        like = f"%{search.lower()}%"
        q = q.filter(Product.name.ilike(like))
    products = q.all()

    if min_price is not None:
        products = [p for p in products if p.discounted_price >= min_price]
    if max_price is not None:
        products = [p for p in products if p.discounted_price <= max_price]
    if min_rating is not None:
        products = [p for p in products if p.rating >= min_rating]

    if sort_by == "Price: Low to High":
        products.sort(key=lambda p: p.discounted_price)
    elif sort_by == "Price: High to Low":
        products.sort(key=lambda p: p.discounted_price, reverse=True)
    elif sort_by == "Rating":
        products.sort(key=lambda p: p.rating, reverse=True)
    elif sort_by == "Newest":
        products.sort(key=lambda p: p.created_at, reverse=True)
    elif sort_by == "Discount":
        products.sort(key=lambda p: p.discount_percent, reverse=True)

    if own_session:
        session.close()
    return products


def get_brands(session):
    """Returns [(brand, product_count), ...] sorted by product_count desc,
    used for the homepage 'Popular Brands' strip and the Browse brand filter."""
    products = session.query(Product).all()
    counts = {}
    for p in products:
        counts[p.brand] = counts.get(p.brand, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)


def products_dataframe(session=None):
    own_session = session is None
    session = session or get_session()
    products = session.query(Product).all()
    data = [{
        "ID": p.id, "SKU": p.sku, "Name": p.name, "Category": p.category, "Brand": p.brand,
        "Price": p.price, "Discount %": p.discount_percent,
        "Final Price": p.discounted_price, "Stock": p.stock,
        "Status": p.stock_status, "Rating": p.rating,
        "Featured": p.is_featured, "Bestseller": p.is_bestseller,
        "New Arrival": p.is_new_arrival,
    } for p in products]
    if own_session:
        session.close()
    return pd.DataFrame(data)


def get_product(session, product_id):
    return session.query(Product).filter(Product.id == product_id).first()


def get_discount_rules(session, product_id):
    return session.query(DiscountRule).filter(DiscountRule.product_id == product_id).all()


def get_active_deal(session, product_id):
    now = dt.datetime.utcnow()
    return (session.query(TodaysDeal)
            .filter(TodaysDeal.product_id == product_id,
                    TodaysDeal.is_active == True,
                    TodaysDeal.ends_at >= now)
            .first())


def get_recommended_products(session, product, limit=4):
    q = (session.query(Product)
         .filter(Product.category == product.category, Product.id != product.id))
    candidates = q.all()
    candidates.sort(key=lambda p: p.rating, reverse=True)
    return candidates[:limit]


# --------------------------------------------------------------------------- #
# REVIEWS
# --------------------------------------------------------------------------- #
def get_reviews(session, product_id, limit=None):
    q = (session.query(Review).filter(Review.product_id == product_id)
         .order_by(Review.created_at.desc()))
    return q.limit(limit).all() if limit else q.all()


def add_review(session, product_id, reviewer_name, rating, title, comment):
    review = Review(product_id=product_id, reviewer_name=reviewer_name, rating=rating,
                     title=title, comment=comment, verified_purchase=False)
    session.add(review)
    product = get_product(session, product_id)
    if product:
        all_reviews = get_reviews(session, product_id) + [review]
        product.rating = round(sum(r.rating for r in all_reviews) / len(all_reviews), 1)
        product.review_count = (product.review_count or 0) + 1
    session.commit()
    return review


def rating_breakdown(session, product_id):
    """Returns dict {5: pct, 4: pct, ...} of star distribution for a product."""
    reviews = get_reviews(session, product_id)
    counts = {i: 0 for i in range(1, 6)}
    for r in reviews:
        counts[max(1, min(5, round(r.rating)))] += 1
    total = max(1, len(reviews))
    return {k: round(v / total * 100) for k, v in counts.items()}, len(reviews)


# --------------------------------------------------------------------------- #
# WISHLIST
# --------------------------------------------------------------------------- #
def get_wishlist_items(session, session_id):
    return session.query(WishlistItem).filter(WishlistItem.session_id == session_id).all()


def get_wishlist_product_ids(session, session_id):
    return {w.product_id for w in get_wishlist_items(session, session_id)}


def toggle_wishlist(session, session_id, product_id):
    item = (session.query(WishlistItem)
            .filter(WishlistItem.session_id == session_id, WishlistItem.product_id == product_id)
            .first())
    if item:
        session.delete(item)
        session.commit()
        return False  # removed
    session.add(WishlistItem(session_id=session_id, product_id=product_id))
    session.commit()
    return True  # added


# --------------------------------------------------------------------------- #
# RECENTLY VIEWED
# --------------------------------------------------------------------------- #
def record_product_view(session, session_id, product_id):
    session.add(ProductView(session_id=session_id, product_id=product_id))
    session.commit()


def get_recently_viewed(session, session_id, exclude_id=None, limit=6):
    views = (session.query(ProductView)
             .filter(ProductView.session_id == session_id)
             .order_by(ProductView.viewed_at.desc())
             .all())
    seen, ordered_ids = set(), []
    for v in views:
        if v.product_id in seen or v.product_id == exclude_id:
            continue
        seen.add(v.product_id)
        ordered_ids.append(v.product_id)
        if len(ordered_ids) >= limit:
            break
    products = []
    for pid in ordered_ids:
        p = get_product(session, pid)
        if p:
            products.append(p)
    return products


def get_most_viewed_products(session, limit=5):
    views = session.query(ProductView).all()
    counts = {}
    for v in views:
        counts[v.product_id] = counts.get(v.product_id, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    results = []
    for pid, cnt in ranked:
        p = get_product(session, pid)
        if p:
            results.append((p, cnt))
    return results


# --------------------------------------------------------------------------- #
# CART / INVENTORY LOGIC (dynamic sync between customer + admin)
# --------------------------------------------------------------------------- #
def add_to_cart(session, session_id, product_id, quantity=1):
    product = get_product(session, product_id)
    if not product or product.stock < quantity:
        return False, "Insufficient stock available."

    item = (session.query(CartItem)
            .filter(CartItem.session_id == session_id, CartItem.product_id == product_id)
            .first())
    if item:
        item.quantity += quantity
    else:
        item = CartItem(session_id=session_id, product_id=product_id, quantity=quantity)
        session.add(item)

    # decrease live inventory immediately (reserved on add-to-cart, demo behaviour)
    product.stock -= quantity
    session.add(InventoryLog(product_id=product_id, change=-quantity,
                              reason="Added to cart", timestamp=dt.datetime.utcnow()))
    session.commit()
    return True, "Added to cart."


def remove_from_cart(session, session_id, product_id):
    item = (session.query(CartItem)
            .filter(CartItem.session_id == session_id, CartItem.product_id == product_id)
            .first())
    if item:
        product = get_product(session, product_id)
        if product:
            product.stock += item.quantity
            session.add(InventoryLog(product_id=product_id, change=item.quantity,
                                      reason="Removed from cart", timestamp=dt.datetime.utcnow()))
        session.delete(item)
        session.commit()


def get_cart_items(session, session_id):
    return session.query(CartItem).filter(CartItem.session_id == session_id).all()


def generate_order_number():
    date_part = dt.datetime.utcnow().strftime("%Y%m%d")
    rand_part = "".join(random.choices(string.digits, k=5))
    return f"NVG-{date_part}-{rand_part}"


# --------------------------------------------------------------------------- #
# COUPONS
# --------------------------------------------------------------------------- #
def get_active_coupons(session):
    now = dt.datetime.utcnow()
    return (session.query(Coupon)
            .filter(Coupon.is_active == True)
            .filter((Coupon.expires_at == None) | (Coupon.expires_at >= now))  # noqa: E711
            .all())


def validate_coupon(session, code, subtotal):
    """Returns (coupon_or_None, discount_amount, error_message_or_None)."""
    if not code or not code.strip():
        return None, 0.0, None
    now = dt.datetime.utcnow()
    coupon = (session.query(Coupon)
              .filter(Coupon.code == code.strip().upper(), Coupon.is_active == True)
              .first())
    if not coupon:
        return None, 0.0, "Invalid or inactive coupon code."
    if coupon.expires_at and coupon.expires_at < now:
        return None, 0.0, "This coupon has expired."
    if subtotal < coupon.min_order_value:
        return None, 0.0, f"Add {fmt_inr(coupon.min_order_value - subtotal)} more to use this coupon."
    discount = round(subtotal * coupon.discount_percent / 100, 2)
    discount = min(discount, coupon.max_discount_amount)
    return coupon, discount, None


# --------------------------------------------------------------------------- #
# COMPARE
# --------------------------------------------------------------------------- #
def get_compare_product_ids(session, session_id):
    return [c.product_id for c in
            session.query(CompareItem).filter(CompareItem.session_id == session_id).all()]


def toggle_compare(session, session_id, product_id, limit=4):
    item = (session.query(CompareItem)
            .filter(CompareItem.session_id == session_id, CompareItem.product_id == product_id)
            .first())
    if item:
        session.delete(item)
        session.commit()
        return False, "Removed from compare."
    if len(get_compare_product_ids(session, session_id)) >= limit:
        return False, f"You can compare up to {limit} products at a time."
    session.add(CompareItem(session_id=session_id, product_id=product_id))
    session.commit()
    return True, "Added to compare."


def checkout_cart(session, session_id, payment_method="UPI", customer_name="Guest Customer",
                   customer_email="", customer_phone="", shipping_address="", coupon_code=""):
    """Convert cart items into an Order (with GST + coupon discount applied)
    and Sale records (for revenue analytics), then clear the cart. Returns
    (final_total, order)."""
    items = get_cart_items(session, session_id)
    subtotal = 0.0
    order_items = []
    max_delivery_days = 2
    for item in items:
        product = get_product(session, item.product_id)
        if product:
            amount = product.discounted_price * item.quantity
            subtotal += amount
            max_delivery_days = max(max_delivery_days, product.delivery_days or 3)
            order_items.append({
                "product_id": product.id, "name": product.name,
                "quantity": item.quantity, "price": product.discounted_price,
            })
        session.delete(item)

    order = None
    if order_items:
        order_number = generate_order_number()
        _coupon, discount, _err = validate_coupon(session, coupon_code, subtotal)
        gst_amount = round((subtotal - discount) * GST_RATE, 2)
        total = round(subtotal - discount + gst_amount, 2)
        order = Order(
            order_number=order_number,
            session_id=session_id,
            customer_name=(customer_name or "").strip() or "Guest Customer",
            customer_email=(customer_email or "").strip(),
            customer_phone=(customer_phone or "").strip(),
            shipping_address=(shipping_address or "").strip(),
            items_json=json.dumps(order_items),
            subtotal_amount=round(subtotal, 2),
            coupon_code=_coupon.code if _coupon else "",
            discount_amount=discount,
            gst_amount=gst_amount,
            total_amount=total,
            payment_method=payment_method,
            estimated_delivery=dt.datetime.utcnow() + dt.timedelta(days=max_delivery_days),
            status="Confirmed",
        )
        session.add(order)
        for oi in order_items:
            session.add(Sale(product_id=oi["product_id"], quantity=oi["quantity"],
                              amount=round(oi["price"] * oi["quantity"], 2),
                              order_number=order_number, timestamp=dt.datetime.utcnow()))
    session.commit()
    return (order.total_amount if order else 0.0), order


def cancel_order(session, order_id):
    """Cancels an order, restores the stock for every item in it, and voids
    the associated Sale records so Revenue/analytics update immediately."""
    order = session.query(Order).get(order_id)
    if not order:
        return False, "Order not found."
    if order.status == "Cancelled":
        return False, "This order is already cancelled."
    try:
        items = json.loads(order.items_json or "[]")
    except (ValueError, TypeError):
        items = []
    for it in items:
        product = get_product(session, it.get("product_id"))
        qty = it.get("quantity", 0) or 0
        if product:
            product.stock += qty
            session.add(InventoryLog(product_id=product.id, change=qty,
                                      reason=f"Order {order.order_number} cancelled",
                                      timestamp=dt.datetime.utcnow()))
    for sale in session.query(Sale).filter(Sale.order_number == order.order_number).all():
        sale.is_voided = True
    order.status = "Cancelled"
    order.cancelled_at = dt.datetime.utcnow()
    session.commit()
    return True, f"Order {order.order_number} cancelled — stock restored and revenue adjusted."


# --------------------------------------------------------------------------- #
# CUSTOMERS (aggregated from Orders — this demo has no login/account system)
# --------------------------------------------------------------------------- #
def get_customers(session):
    orders = session.query(Order).order_by(Order.created_at.asc()).all()
    agg = {}
    for o in orders:
        key = (o.customer_email or o.customer_name or "guest").strip().lower()
        d = agg.setdefault(key, {
            "name": o.customer_name or "Guest Customer", "email": o.customer_email or "",
            "phone": o.customer_phone or "", "orders": 0, "total_spent": 0.0,
            "last_order": o.created_at,
        })
        d["orders"] += 1
        if o.status != "Cancelled":
            d["total_spent"] += o.total_amount
        d["last_order"] = o.created_at
    return sorted(agg.values(), key=lambda x: x["total_spent"], reverse=True)


# --------------------------------------------------------------------------- #
# DELIVERY / EMI HELPERS
# --------------------------------------------------------------------------- #
def estimate_delivery_for_pincode(pincode, base_days):
    """Lightweight, deterministic 'delivery ETA' simulation based on pincode."""
    if not pincode or not pincode.strip().isdigit() or len(pincode.strip()) != 6:
        return None
    digit_sum = sum(int(d) for d in pincode.strip())
    extra = digit_sum % 3
    eta_days = max(1, base_days + extra - 1)
    eta_date = dt.date.today() + dt.timedelta(days=eta_days)
    return eta_days, eta_date


def emi_options(price):
    """Simple EMI table for common tenures (no-cost demo estimate)."""
    tenures = [3, 6, 9, 12]
    return [(t, round(price / t)) for t in tenures]


# --------------------------------------------------------------------------- #
# ADMIN KPI HELPERS
# --------------------------------------------------------------------------- #
def get_kpis(session):
    total_products = session.query(Product).count()
    inventory_remaining = sum(p.stock for p in session.query(Product).all())
    low_stock = session.query(Product).filter(
        Product.stock > 0, Product.stock <= Product.low_stock_threshold).count()
    out_of_stock = session.query(Product).filter(Product.stock <= 0).count()
    active_ads = session.query(Advertisement).filter(Advertisement.is_active == True).count()
    cart_items = session.query(CartItem).count()
    wishlist_items = session.query(WishlistItem).count()
    enquiries = session.query(Enquiry).count()
    dealers = session.query(Dealer).count()
    orders = session.query(Order).count()
    cancelled_orders = session.query(Order).filter(Order.status == "Cancelled").count()
    active_coupons = session.query(Coupon).filter(Coupon.is_active == True).count()
    customers = len(get_customers(session))
    revenue = sum(s.amount for s in session.query(Sale).filter(Sale.is_voided == False).all())
    return {
        "Total Products": total_products,
        "Inventory Remaining": inventory_remaining,
        "Low Stock": low_stock,
        "Out of Stock": out_of_stock,
        "Active Advertisements": active_ads,
        "Cart Items": cart_items,
        "Wishlist Items": wishlist_items,
        "Orders Placed": orders,
        "Cancelled Orders": cancelled_orders,
        "Active Coupons": active_coupons,
        "Customers": customers,
        "Customer Enquiries": enquiries,
        "Dealers": dealers,
        "Revenue": revenue,
    }


def dataframe_to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")
