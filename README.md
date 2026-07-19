# ✨ NovaGrid Electronics — Premium Retail Experience

A commercial-grade **Streamlit** retail storefront + admin console, styled
with a white / soft-lavender / purple / coral-pink / emerald-green / soft-gold
design system inspired by Nykaa, Apple Store, Reliance Digital and Croma. All
product and advertisement imagery is generated procedurally with Pillow under
the fictional **NovaGrid** brand family — no real-brand photography or
trademarks are used anywhere.

The app opens directly into a **permanent 50%-50% split screen**: the live
customer storefront on the left, the live admin console on the right. There
is no view-mode toggle and no resize slider — the split always stays exactly
50/50, and each panel scrolls independently of the other.

---

## ✨ What's inside

### Customer Storefront (left panel)
- White / lavender / purple / coral / emerald / gold **glassmorphism UI**
  with Poppins/Inter typography, large whitespace and rounded cards
- **Sticky navbar** with live cart, wishlist & compare counts, sound toggle
- **Auto-rotating hero banner slider** and a separate **auto-rotating
  advertisement carousel**, both pure client-side (no Streamlit reruns)
- **Flash sale banner**, **Today's Deals**, **Best Sellers**, **Featured
  Products**, **New Arrivals**, **Popular Brands strip**, **Customer
  Reviews**, **Newsletter** section and a full footer
- **Product cards** stay simple at rest; hovering reveals an offer panel
  (quantity discounts, cashback %, warranty, "watch video" preview) plus a
  **Quick View** button — gallery, specs, reviews, EMI, delivery, video
- **Wishlist**, **Compare** (DB-backed, up to 4 products side by side) and
  **Search + Category/Brand Filters**
- **Coupon codes** (`NOVA10`, `WELCOME15`, `FEST25`, `NOVAGOLD`) with live
  validation (min order value, max discount cap) applied at checkout
- **4-step single-click checkout** — Shipping → Payment → Review → Place
  Order (no double-confirmation) — with 6 payment methods: UPI, Credit
  Card, Debit Card, Wallet, Net Banking, Cash on Delivery
- **Checkout celebration** on success — confetti + balloons + firecrackers +
  sound + a congratulations popup — followed by a **downloadable GST tax
  invoice PDF** (invoice number, customer, items, GST, discount/coupon,
  payment method, date & time, final total)
- **Order tracking / cancellation** from the customer side, which instantly
  restores stock and voids revenue on the admin side
- **Spotlight scroll** — clicking "📍 View on Website" for a product inside
  the Admin Dashboard scrolls the storefront panel straight to that product

### Admin Dashboard (right panel)
- Secure admin login (`admin` / `novagrid@123`)
- Live glass-style KPI cards — Products, Inventory, Revenue, Orders, Low
  Stock, Out of Stock, Dealers, Customer Enquiries, Cancelled Orders,
  Active Coupons, Customers
- **Product CRUD** (incl. cashback %), **Inventory** with quick restock
- **Advertisement Manager** and **Video Advertisement Manager**
- **Today's Deal Manager**, **Discount Rule Manager**, **Coupon Manager**
- **Order Management** — status updates and one-click order cancellation
  (restores stock, voids revenue, no destructive row deletes)
- **Customer directory** — aggregated automatically from order history
- **Dealer Management**, **Customer Enquiry Management**, **Review
  Moderation**, **Customer Insights**, **Sales Simulation**
- **CSV Export** (Products, Dealers, Enquiries, Sales, Orders, Reviews,
  Customers, Coupons)
- **Plotly Analytics Suite** — revenue, inventory, product performance,
  category mix, low-stock analysis, discount performance, dealer
  growth/performance, enquiries, most-viewed/wishlisted products, review
  distribution, orders trend

### Two-Way Live Data Sync
Every panel reads/writes the same `novagrid.db` SQLite file. Admin changes
(price, stock, discount, ads, deals, coupons) become visible on the
storefront the moment they're saved; customer actions (cart, wishlist,
compare, checkout, cancellation, reviews, product views) update Admin KPIs,
Orders, Customers and Analytics in real time — every write on either side is
immediately followed by a rerun so the *other* panel never shows stale data.

---

## 🗂️ Project Structure

```
novagrid_electronics/
├── app.py                     # Entry point — permanent 50/50 split + global theme
├── requirements.txt
├── README.md
├── database/
│   ├── db_setup.py            # SQLAlchemy models (Coupon, CompareItem, GST, cancellation...)
│   └── seed_data.py           # Demo data + multi-image gallery / video generator
├── modules/
│   ├── utils.py                # Queries, cart/wishlist/compare/coupon/order logic
│   ├── auth.py                  # Admin login/logout
│   ├── effects.py               # Sounds, confetti/balloons/crackers, alerts
│   ├── analytics.py             # Plotly chart builders
│   ├── invoice.py               # GST tax invoice PDF generator (reportlab)
│   ├── customer_website.py      # Full storefront UI
│   └── admin_dashboard.py       # Full admin console UI
├── assets/images/{products,ads,banners}/   # Procedurally generated imagery
├── assets/videos/                          # Procedurally generated Ken-Burns preview clips
└── novagrid.db                   # Created automatically on first run
```

---

## 🖼️ Using Real Product Photos (Optional)

By default every product image and video preview is procedurally
generated with Pillow/ffmpeg — no external downloads, no copyright risk.
If you'd like to use real photography instead, drop your own (properly
licensed) images into:

```
assets/images/products_custom/<SKU>/
    1.jpg   ← becomes the cover image
    2.jpg   ← gallery image
    3.jpg
    4.jpg
```

Find each product's SKU in the Admin Dashboard → Products. Delete
`novagrid.db` and restart the app — it will automatically detect the
folder and use your photos instead of the generated illustration for that
product; any product without a matching folder still gets its procedural
image, so you can migrate a few products at a time.

Because this app's build environment can only reach package registries
(PyPI/npm/GitHub), it can't download photos from the internet on its own —
but any image you legally source yourself works here. Good free,
commercial-use-friendly sources to check (always confirm the license on
the specific image): Unsplash, Pexels, Pixabay, and manufacturer press-kit
pages. Avoid pairing real brand photos with this app's fictional brand
names if the demo will be shown publicly.

---

## 🚀 Running the App

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`. The database and all demo data
(22 products, galleries, video previews, reviews, ads, deals, dealers,
enquiries, coupons, sales history) are generated automatically on first
run.

**Admin Login:** `admin` / `novagrid@123`

---

## 🧱 Tech Stack (strictly limited)

| Purpose            | Library               |
|---------------------|------------------------|
| Web app framework   | `streamlit`            |
| Data handling       | `pandas`, `numpy`      |
| Charts              | `plotly`                |
| Database ORM        | `sqlalchemy` (SQLite)  |
| Image generation    | `pillow`                |
| Admin nav menu      | `streamlit-option-menu`|
| PDF invoices        | `reportlab`             |

No Flask, Django, React, Next.js, JavaScript frameworks, Docker, Redis or
Firebase are used anywhere in this project.

---

## 🎨 Design & Media Notes

- All product, advertisement, banner and video-preview imagery is
  **generated on the fly with Pillow / ffmpeg** — unique studio-style
  renders per item, no external image downloads or real-brand assets.
- Sound effects (add-to-cart, coupon applied, checkout, order success,
  notifications) are **synthesized WAV tones with NumPy**, played via
  embedded base64 HTML audio, and respect the navbar sound ON/OFF toggle.
- Confetti, balloons and firecracker celebrations are rendered with
  lightweight inline JavaScript/Canvas via `streamlit.components.v1.html`.
- The hero slider and ad carousel autoplay entirely client-side (CSS/JS
  crossfade) so they don't depend on Streamlit reruns.
- The dashboard→website "spotlight" scroll is implemented by rendering a
  guaranteed-visible highlighted card at the top of the storefront's Home
  tab plus a `scrollIntoView` JS injection, since Streamlit's own
  tab-panel DOM visibility can't be relied on for scrolling to an
  arbitrary grid position.

---

## ⚠️ Disclaimer

This is a demonstration / portfolio (MBA Product Management) project.
Revenue figures are simulated, admin credentials are intentionally simple
for demo purposes, delivery/EMI figures are illustrative estimates, and
there is no real payment gateway or order fulfilment integration — no
financial transaction of any kind is executed. All brand names
("NovaGrid", etc.) are fictional.
