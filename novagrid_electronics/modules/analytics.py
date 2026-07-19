"""
NovaGrid Electronics - Plotly Analytics
Builds all analytics charts used inside the Admin Dashboard: revenue,
inventory, product performance, category distribution, low stock,
discount performance, dealer growth and customer enquiries.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from database.db_setup import (
    get_session, Product, Sale, Dealer, Enquiry, DiscountRule,
    ProductView, WishlistItem, Review, Order
)

TEMPLATE = "plotly_dark"
COLOR_SEQ = px.colors.sequential.Purples
ACCENT = "#7C4DFF"


def _empty_fig(msg="No data available"):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=16, color="gray"))
    fig.update_layout(template=TEMPLATE, height=320)
    return fig


def revenue_trend_chart():
    session = get_session()
    sales = session.query(Sale).all()
    session.close()
    if not sales:
        return _empty_fig()
    df = pd.DataFrame([{"date": s.timestamp.date(), "amount": s.amount} for s in sales])
    daily = df.groupby("date", as_index=False)["amount"].sum().sort_values("date")
    fig = px.area(daily, x="date", y="amount", template=TEMPLATE,
                   color_discrete_sequence=[ACCENT], title="Revenue Trend (Simulated)")
    fig.update_traces(line_shape="spline")
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def inventory_levels_chart():
    session = get_session()
    products = session.query(Product).all()
    session.close()
    if not products:
        return _empty_fig()
    df = pd.DataFrame([{"name": p.name, "stock": p.stock, "category": p.category} for p in products])
    df = df.sort_values("stock", ascending=True).tail(15)
    fig = px.bar(df, x="stock", y="name", orientation="h", color="category",
                 template=TEMPLATE, title="Inventory Levels by Product",
                 color_discrete_sequence=px.colors.qualitative.Bold)
    fig.update_layout(height=440, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def product_performance_chart():
    session = get_session()
    sales = session.query(Sale).all()
    products = {p.id: p for p in session.query(Product).all()}
    session.close()
    if not sales:
        return _empty_fig()
    agg = {}
    for s in sales:
        agg.setdefault(s.product_id, 0)
        agg[s.product_id] += s.quantity
    df = pd.DataFrame([
        {"product": products[pid].name if pid in products else f"#{pid}", "units_sold": qty}
        for pid, qty in agg.items()
    ]).sort_values("units_sold", ascending=False).head(10)
    fig = px.bar(df, x="product", y="units_sold", template=TEMPLATE,
                 title="Top 10 Products by Units Sold", color="units_sold",
                 color_continuous_scale=COLOR_SEQ)
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10), xaxis_tickangle=-35)
    return fig


def category_distribution_chart():
    session = get_session()
    products = session.query(Product).all()
    session.close()
    if not products:
        return _empty_fig()
    df = pd.DataFrame([{"category": p.category} for p in products])
    counts = df["category"].value_counts().reset_index()
    counts.columns = ["category", "count"]
    fig = px.pie(counts, names="category", values="count", template=TEMPLATE, hole=0.45,
                 title="Product Category Distribution",
                 color_discrete_sequence=px.colors.qualitative.Set3)
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def low_stock_analysis_chart():
    session = get_session()
    products = session.query(Product).all()
    session.close()
    if not products:
        return _empty_fig()
    df = pd.DataFrame([{
        "name": p.name, "stock": p.stock, "threshold": p.low_stock_threshold,
        "status": p.stock_status
    } for p in products])
    low_df = df[df["status"].isin(["Low Stock", "Out of Stock"])]
    if low_df.empty:
        return _empty_fig("All products are healthily stocked!")
    fig = px.bar(low_df.sort_values("stock"), x="name", y="stock", color="status",
                 template=TEMPLATE, title="Low Stock & Out-of-Stock Analysis",
                 color_discrete_map={"Low Stock": "#f4b400", "Out of Stock": "#db4437"})
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10), xaxis_tickangle=-35)
    return fig


def discount_performance_chart():
    session = get_session()
    products = session.query(Product).all()
    session.close()
    if not products:
        return _empty_fig()
    df = pd.DataFrame([{
        "name": p.name, "discount": p.discount_percent, "rating": p.rating,
        "category": p.category
    } for p in products])
    fig = px.scatter(df, x="discount", y="rating", color="category", size="discount",
                      hover_name="name", template=TEMPLATE,
                      title="Discount % vs Rating by Category",
                      color_discrete_sequence=px.colors.qualitative.Vivid)
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def dealer_growth_chart():
    session = get_session()
    dealers = session.query(Dealer).all()
    session.close()
    if not dealers:
        return _empty_fig()
    df = pd.DataFrame([{
        "name": d.name, "join_date": d.join_date.date(),
        "products_supplied": d.products_supplied, "performance": d.performance_score,
        "region": d.region
    } for d in dealers]).sort_values("join_date")
    df["cumulative_dealers"] = range(1, len(df) + 1)
    fig = px.line(df, x="join_date", y="cumulative_dealers", markers=True,
                   template=TEMPLATE, title="Dealer Network Growth Over Time",
                   color_discrete_sequence=[ACCENT])
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def dealer_performance_chart():
    session = get_session()
    dealers = session.query(Dealer).all()
    session.close()
    if not dealers:
        return _empty_fig()
    df = pd.DataFrame([{
        "name": d.name, "region": d.region, "performance": d.performance_score,
        "products_supplied": d.products_supplied
    } for d in dealers])
    fig = px.bar(df.sort_values("performance"), x="performance", y="name",
                 orientation="h", color="region", template=TEMPLATE,
                 title="Dealer Performance Score",
                 color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def enquiries_chart():
    session = get_session()
    enquiries = session.query(Enquiry).all()
    session.close()
    if not enquiries:
        return _empty_fig()
    df = pd.DataFrame([{"status": e.status, "date": e.created_at.date()} for e in enquiries])
    counts = df["status"].value_counts().reset_index()
    counts.columns = ["status", "count"]
    fig = px.pie(counts, names="status", values="count", template=TEMPLATE, hole=0.4,
                 title="Customer Enquiry Status Breakdown",
                 color_discrete_map={"Open": "#db4437", "In Progress": "#f4b400",
                                      "Resolved": "#0f9d58"})
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def enquiries_trend_chart():
    session = get_session()
    enquiries = session.query(Enquiry).all()
    session.close()
    if not enquiries:
        return _empty_fig()
    df = pd.DataFrame([{"date": e.created_at.date()} for e in enquiries])
    daily = df.groupby("date").size().reset_index(name="count").sort_values("date")
    fig = px.bar(daily, x="date", y="count", template=TEMPLATE,
                 title="Enquiries Received Over Time", color_discrete_sequence=[ACCENT])
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def most_viewed_products_chart():
    session = get_session()
    views = session.query(ProductView).all()
    products = {p.id: p for p in session.query(Product).all()}
    session.close()
    if not views:
        return _empty_fig("No product views tracked yet")
    agg = {}
    for v in views:
        agg.setdefault(v.product_id, 0)
        agg[v.product_id] += 1
    df = pd.DataFrame([
        {"product": products[pid].name if pid in products else f"#{pid}", "views": cnt}
        for pid, cnt in agg.items()
    ]).sort_values("views", ascending=False).head(10)
    fig = px.bar(df, x="views", y="product", orientation="h", template=TEMPLATE,
                 title="Most Viewed Products", color="views",
                 color_continuous_scale=COLOR_SEQ)
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def wishlist_activity_chart():
    session = get_session()
    items = session.query(WishlistItem).all()
    products = {p.id: p for p in session.query(Product).all()}
    session.close()
    if not items:
        return _empty_fig("No wishlist activity yet")
    agg = {}
    for w in items:
        agg.setdefault(w.product_id, 0)
        agg[w.product_id] += 1
    df = pd.DataFrame([
        {"product": products[pid].name if pid in products else f"#{pid}", "wishlisted": cnt}
        for pid, cnt in agg.items()
    ]).sort_values("wishlisted", ascending=False).head(10)
    fig = px.bar(df, x="wishlisted", y="product", orientation="h", template=TEMPLATE,
                 title="Most Wishlisted Products", color_discrete_sequence=[ACCENT])
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def review_rating_distribution_chart():
    session = get_session()
    reviews = session.query(Review).all()
    session.close()
    if not reviews:
        return _empty_fig("No reviews yet")
    df = pd.DataFrame([{"rating": round(r.rating)} for r in reviews])
    counts = df["rating"].value_counts().sort_index().reset_index()
    counts.columns = ["rating", "count"]
    fig = px.bar(counts, x="rating", y="count", template=TEMPLATE,
                 title="Customer Review Rating Distribution",
                 color_discrete_sequence=[ACCENT])
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def orders_trend_chart():
    session = get_session()
    orders = session.query(Order).all()
    session.close()
    if not orders:
        return _empty_fig("No orders placed yet")
    df = pd.DataFrame([{"date": o.created_at.date(), "amount": o.total_amount} for o in orders])
    daily = df.groupby("date", as_index=False).agg(orders=("amount", "count"), revenue=("amount", "sum"))
    fig = px.bar(daily, x="date", y="orders", template=TEMPLATE,
                 title="Orders Placed Over Time", color_discrete_sequence=[ACCENT])
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10))
    return fig
