"""
NovaGrid Electronics - Database Setup
Defines all SQLAlchemy ORM models and the SQLite engine used by both
the Customer Website and the Admin Dashboard. Because both panels
read/write to this single database, any change made by the admin is
immediately visible to the customer website on the next rerun, and
every customer action (cart, order, cancellation) updates admin KPIs
in real time.
"""

import os
import json
import datetime as dt

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "novagrid.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
Base = declarative_base()

GST_RATE = 0.18  # 18% GST, shown itemized on the invoice like a real Indian e-commerce checkout


# --------------------------------------------------------------------------- #
# MODELS
# --------------------------------------------------------------------------- #
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    sku = Column(String(40))
    name = Column(String(150), nullable=False)
    category = Column(String(80), nullable=False)
    brand = Column(String(80), nullable=False)
    price = Column(Float, nullable=False)                 # MRP
    discount_percent = Column(Float, default=0.0)          # 0-90
    stock = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=10)
    image_path = Column(String(255))          # primary / cover image
    gallery_json = Column(Text, default="[]")  # JSON list of extra gallery image paths
    rating = Column(Float, default=4.0)
    review_count = Column(Integer, default=0)
    description = Column(Text)
    specifications = Column(Text)          # pipe separated "Key: Value|Key: Value"
    warranty = Column(String(120), default="1 Year Brand Warranty")
    delivery_days = Column(Integer, default=3)
    emi_available = Column(Boolean, default=True)
    cashback_percent = Column(Float, default=0.0)
    is_featured = Column(Boolean, default=False)
    is_bestseller = Column(Boolean, default=False)
    is_new_arrival = Column(Boolean, default=False)
    has_video = Column(Boolean, default=False)
    video_note = Column(String(255), default="")
    video_path = Column(String(255), default="")
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    @property
    def discounted_price(self):
        return round(self.price * (1 - self.discount_percent / 100), 2)

    @property
    def stock_status(self):
        if self.stock <= 0:
            return "Out of Stock"
        elif self.stock <= self.low_stock_threshold:
            return "Low Stock"
        return "In Stock"

    @property
    def gallery(self):
        try:
            imgs = json.loads(self.gallery_json or "[]")
        except Exception:
            imgs = []
        all_imgs = [self.image_path] + [i for i in imgs if i and i != self.image_path]
        return [i for i in all_imgs if i]

    @property
    def emi_monthly(self):
        """Simple 9-month no-cost EMI estimate on the discounted price."""
        if not self.emi_available:
            return None
        return round(self.discounted_price / 9, 0)


class Advertisement(Base):
    __tablename__ = "advertisements"

    id = Column(Integer, primary_key=True)
    title = Column(String(150), nullable=False)
    subtitle = Column(String(255))
    image_path = Column(String(255))
    is_active = Column(Boolean, default=True)
    position = Column(String(50), default="hero")   # hero / banner / flash / festival
    link_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class VideoAd(Base):
    __tablename__ = "video_ads"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    title = Column(String(150))
    video_path = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    product = relationship("Product")


class DiscountRule(Base):
    __tablename__ = "discount_rules"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    min_qty = Column(Integer, nullable=False)
    extra_discount_percent = Column(Float, nullable=False)
    description = Column(String(255))

    product = relationship("Product")


class TodaysDeal(Base):
    __tablename__ = "todays_deals"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    deal_discount_percent = Column(Float, nullable=False)
    starts_at = Column(DateTime, default=dt.datetime.utcnow)
    ends_at = Column(DateTime)
    is_active = Column(Boolean, default=True)

    product = relationship("Product")


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True)
    code = Column(String(40), unique=True, nullable=False)
    discount_percent = Column(Float, nullable=False)
    min_order_value = Column(Float, default=0.0)
    max_discount_amount = Column(Float, default=100000.0)
    is_active = Column(Boolean, default=True)
    description = Column(String(255), default="")
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class Dealer(Base):
    __tablename__ = "dealers"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    region = Column(String(100))
    contact_email = Column(String(150))
    contact_phone = Column(String(30))
    products_supplied = Column(Integer, default=0)
    performance_score = Column(Float, default=75.0)
    join_date = Column(DateTime, default=dt.datetime.utcnow)


class Enquiry(Base):
    __tablename__ = "enquiries"

    id = Column(Integer, primary_key=True)
    customer_name = Column(String(150), nullable=False)
    email = Column(String(150))
    phone = Column(String(30))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    message = Column(Text)
    status = Column(String(30), default="Open")   # Open / In Progress / Resolved
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    product = relationship("Product")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(80), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    added_at = Column(DateTime, default=dt.datetime.utcnow)

    product = relationship("Product")


class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(80), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    added_at = Column(DateTime, default=dt.datetime.utcnow)

    product = relationship("Product")


class CompareItem(Base):
    """Persisted compare-list, mirrored into session_state for speed but kept
    here too so the 'dynamic system' concept extends to every customer action."""
    __tablename__ = "compare_items"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(80), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    added_at = Column(DateTime, default=dt.datetime.utcnow)

    product = relationship("Product")


class ProductView(Base):
    """Tracks recently-viewed products per session, and product popularity overall."""
    __tablename__ = "product_views"

    id = Column(Integer, primary_key=True)
    session_id = Column(String(80), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    viewed_at = Column(DateTime, default=dt.datetime.utcnow)

    product = relationship("Product")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    reviewer_name = Column(String(120), nullable=False)
    rating = Column(Float, nullable=False)
    title = Column(String(150))
    comment = Column(Text)
    verified_purchase = Column(Boolean, default=True)
    helpful_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    product = relationship("Product")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    order_number = Column(String(40), unique=True)
    session_id = Column(String(80))
    customer_name = Column(String(150), default="Guest Customer")
    customer_email = Column(String(150), default="")
    customer_phone = Column(String(30), default="")
    shipping_address = Column(Text, default="")
    items_json = Column(Text, default="[]")
    subtotal_amount = Column(Float, default=0.0)
    coupon_code = Column(String(40), default="")
    discount_amount = Column(Float, default=0.0)
    gst_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    payment_method = Column(String(40), default="UPI")
    estimated_delivery = Column(DateTime)
    status = Column(String(30), default="Confirmed")   # Confirmed / Shipped / Delivered / Cancelled
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class Sale(Base):
    """Completed sales (from real checkouts and admin sales simulations),
    used to compute the Revenue KPI & analytics. `order_number` links a
    real-checkout sale row back to its Order so cancelling that order can
    void the corresponding revenue; simulated sales leave it blank."""
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    amount = Column(Float, default=0.0)
    order_number = Column(String(40), default="")
    is_voided = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=dt.datetime.utcnow)

    product = relationship("Product")


class InventoryLog(Base):
    __tablename__ = "inventory_log"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    change = Column(Integer)          # negative = removed, positive = restocked
    reason = Column(String(150))
    timestamp = Column(DateTime, default=dt.datetime.utcnow)

    product = relationship("Product")


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(120), nullable=False)  # demo only - plain text


def init_db():
    """Create all tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
