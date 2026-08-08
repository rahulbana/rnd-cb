#!/usr/bin/env python3
"""Create and seed the ecommerce SQLite database.

Usage:
    python scripts/init_db.py            # uses DB_PATH from env or data/ecommerce.db
    python scripts/init_db.py --force    # recreate even if the file exists

The data is generated with a fixed random seed, so every run produces the same
realistic-looking catalogue, customers, and order history — handy for demos and
reproducible testing.
"""

from __future__ import annotations

import argparse
import os
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "data" / "schema.sql"

random.seed(42)

# --- Reference data --------------------------------------------------------

CATEGORIES = [
    ("Electronics", "electronics", "Phones, laptops, audio and accessories"),
    ("Home & Kitchen", "home-kitchen", "Appliances, cookware and home essentials"),
    ("Books", "books", "Print and reference books across genres"),
    ("Fashion", "fashion", "Apparel, footwear and accessories"),
    ("Sports & Outdoors", "sports-outdoors", "Fitness gear and outdoor equipment"),
    ("Beauty & Personal Care", "beauty", "Skincare, grooming and wellness"),
    ("Toys & Games", "toys-games", "Toys, board games and puzzles"),
    ("Office Supplies", "office", "Stationery and office equipment"),
]

# (name, category_slug, price, cost, stock) — cost drives margin queries.
PRODUCTS = [
    ("Aurora Wireless Earbuds Pro", "electronics", 129.99, 62.00, 340),
    ("Nimbus 14 Ultrabook Laptop", "electronics", 1299.00, 940.00, 55),
    ("Pulse Smartwatch Series 5", "electronics", 249.99, 130.00, 120),
    ("Vertex 4K Action Camera", "electronics", 179.50, 96.00, 80),
    ("EchoDome Smart Speaker", "electronics", 89.99, 41.00, 200),
    ("Blaze USB-C 65W Charger", "electronics", 34.99, 12.50, 500),
    ("ClearView 27\" Monitor", "electronics", 219.00, 148.00, 65),
    ("Cascade Stainless Cookware Set", "home-kitchen", 159.00, 88.00, 90),
    ("BrewMaster Drip Coffee Maker", "home-kitchen", 74.99, 33.00, 150),
    ("AeroChef Air Fryer 5.5L", "home-kitchen", 119.99, 61.00, 110),
    ("PureMist Humidifier", "home-kitchen", 44.99, 18.00, 220),
    ("SlumberSoft Weighted Blanket", "home-kitchen", 69.99, 30.00, 130),
    ("The Pragmatic Founder", "books", 24.99, 6.00, 300),
    ("Data Structures Demystified", "books", 39.99, 9.50, 180),
    ("Mindful Mornings Journal", "books", 16.99, 4.00, 400),
    ("Atlas of Modern Design", "books", 54.00, 18.00, 60),
    ("Summit Trail Running Shoes", "fashion", 98.00, 44.00, 140),
    ("Metro Slim Fit Chinos", "fashion", 49.99, 19.00, 260),
    ("Harbor Waterproof Jacket", "fashion", 139.00, 66.00, 95),
    ("Loom Merino Wool Sweater", "fashion", 84.99, 38.00, 120),
    ("Everyday Canvas Backpack", "fashion", 59.99, 24.00, 210),
    ("FlexCore Adjustable Dumbbells", "sports-outdoors", 199.00, 118.00, 70),
    ("TrailBlazer 40L Hiking Pack", "sports-outdoors", 129.00, 61.00, 85),
    ("AquaGlide Insulated Bottle", "sports-outdoors", 27.99, 9.00, 380),
    ("Zephyr 2-Person Tent", "sports-outdoors", 179.00, 92.00, 60),
    ("GripMax Yoga Mat", "sports-outdoors", 39.99, 14.00, 240),
    ("Velvet Glow Vitamin C Serum", "beauty", 32.00, 8.50, 300),
    ("Cedar & Sage Beard Kit", "beauty", 42.00, 15.00, 160),
    ("Silk Touch Hair Dryer", "beauty", 79.99, 34.00, 100),
    ("PureClean Electric Toothbrush", "beauty", 59.99, 22.00, 190),
    ("Galaxy Builder 1200pc Set", "toys-games", 64.99, 28.00, 130),
    ("Riverbend Strategy Board Game", "toys-games", 44.99, 17.00, 150),
    ("Puzzle Peaks 1000pc", "toys-games", 19.99, 6.50, 280),
    ("RoboPup Interactive Toy", "toys-games", 89.99, 41.00, 90),
    ("Meridian Ergonomic Chair", "office", 289.00, 168.00, 45),
    ("Standwell Adjustable Desk", "office", 399.00, 245.00, 35),
    ("InkFlow Rollerball Pens (12pk)", "office", 18.99, 5.50, 420),
    ("Focus Noise-Cancelling Headset", "office", 149.00, 78.00, 75),
    ("PaperPro Notebook Bundle", "office", 22.99, 7.00, 340),
    ("DeskLite LED Lamp", "office", 36.99, 13.00, 200),
]

FIRST_NAMES = [
    "Olivia", "Liam", "Emma", "Noah", "Ava", "Ethan", "Sophia", "Mason",
    "Isabella", "Lucas", "Mia", "Aiden", "Amelia", "Rahul", "Priya",
    "Wei", "Ines", "Diego", "Fatima", "Kenji", "Nadia", "Marco",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Patel", "Chen", "Nguyen", "Kim",
    "Silva", "Okafor", "Rossi", "Haddad", "Sato", "Novak",
]
CITIES = [
    ("New York", "NY"), ("Los Angeles", "CA"), ("Chicago", "IL"),
    ("Houston", "TX"), ("Phoenix", "AZ"), ("Seattle", "WA"),
    ("Denver", "CO"), ("Boston", "MA"), ("Austin", "TX"), ("Miami", "FL"),
]
STREETS = ["Maple St", "Oak Ave", "Pine Rd", "Cedar Ln", "Elm Blvd",
           "Sunset Dr", "Lakeview Ct", "Birch Way", "Willow Ter", "Grove St"]

REVIEW_SNIPPETS = [
    (5, "Exactly what I needed", "Works great and arrived quickly. Highly recommend."),
    (4, "Solid value", "Does the job well, minor niggles but happy overall."),
    (5, "Love it", "Exceeded my expectations, would buy again."),
    (3, "It's okay", "Fine for the price but nothing special."),
    (2, "Disappointed", "Not as described, quality could be better."),
    (4, "Pretty good", "Comfortable and well made, shipping was slow."),
    (5, "Fantastic", "Best purchase I've made this year."),
    (1, "Would not recommend", "Stopped working after a week."),
]

STATUS_WEIGHTS = [
    ("delivered", 45), ("shipped", 20), ("paid", 15),
    ("pending", 8), ("cancelled", 7), ("refunded", 5),
]
PAY_METHODS = ["card", "card", "card", "paypal", "bank_transfer", "gift_card"]
TAX_RATE = 0.08


def weighted_status() -> str:
    population = [s for s, w in STATUS_WEIGHTS for _ in range(w)]
    return random.choice(population)


def build(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())

    # Categories
    slug_to_id: dict[str, int] = {}
    for name, slug, desc in CATEGORIES:
        cur = conn.execute(
            "INSERT INTO categories (name, slug, description) VALUES (?,?,?)",
            (name, slug, desc),
        )
        slug_to_id[slug] = cur.lastrowid

    # Products
    product_ids: list[int] = []
    product_price: dict[int, float] = {}
    for i, (name, cat_slug, price, cost, stock) in enumerate(PRODUCTS, start=1):
        sku = f"SKU-{cat_slug[:3].upper()}-{i:04d}"
        created = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 300))
        cur = conn.execute(
            "INSERT INTO products (sku, name, description, category_id, price, cost, "
            "stock_quantity, is_active, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (sku, name, f"{name} — quality {cat_slug.replace('-', ' ')} product.",
             slug_to_id[cat_slug], price, cost, stock, 1,
             created.strftime("%Y-%m-%d %H:%M:%S")),
        )
        product_ids.append(cur.lastrowid)
        product_price[cur.lastrowid] = price

    # Customers + addresses
    customer_ids: list[int] = []
    customer_addr: dict[int, int] = {}
    used_emails: set[str] = set()
    for _ in range(24):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        email = f"{first.lower()}.{last.lower()}@example.com"
        n = 1
        base = email
        while email in used_emails:
            email = base.replace("@", f"{n}@")
            n += 1
        used_emails.add(email)
        created = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 400))
        cur = conn.execute(
            "INSERT INTO customers (first_name, last_name, email, phone, created_at) "
            "VALUES (?,?,?,?,?)",
            (first, last, email,
             f"+1-{random.randint(200,989)}-{random.randint(200,999)}-{random.randint(1000,9999)}",
             created.strftime("%Y-%m-%d %H:%M:%S")),
        )
        cid = cur.lastrowid
        customer_ids.append(cid)

        city, state = random.choice(CITIES)
        addr = conn.execute(
            "INSERT INTO addresses (customer_id, line1, city, state, postal_code, "
            "country, is_default) VALUES (?,?,?,?,?,?,1)",
            (cid, f"{random.randint(10, 9999)} {random.choice(STREETS)}", city,
             state, f"{random.randint(10000, 99999)}", "USA"),
        )
        customer_addr[cid] = addr.lastrowid

    # Orders + items + payments
    for _ in range(60):
        cid = random.choice(customer_ids)
        status = weighted_status()
        order_date = datetime(2024, 3, 1) + timedelta(
            days=random.randint(0, 420), hours=random.randint(0, 23)
        )
        cur = conn.execute(
            "INSERT INTO orders (customer_id, status, order_date, shipping_address_id, "
            "subtotal, tax, shipping_fee, total) VALUES (?,?,?,?,0,0,0,0)",
            (cid, status, order_date.strftime("%Y-%m-%d %H:%M:%S"), customer_addr[cid]),
        )
        oid = cur.lastrowid

        n_items = random.randint(1, 4)
        chosen = random.sample(product_ids, n_items)
        subtotal = 0.0
        for pid in chosen:
            qty = random.randint(1, 3)
            unit = product_price[pid]
            line = round(unit * qty, 2)
            subtotal += line
            conn.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price, "
                "line_total) VALUES (?,?,?,?,?)",
                (oid, pid, qty, unit, line),
            )
        subtotal = round(subtotal, 2)
        tax = round(subtotal * TAX_RATE, 2)
        shipping = 0.0 if subtotal > 75 else 6.99
        total = round(subtotal + tax + shipping, 2)
        conn.execute(
            "UPDATE orders SET subtotal=?, tax=?, shipping_fee=?, total=? WHERE id=?",
            (subtotal, tax, shipping, total, oid),
        )

        # Payment (skip for pending/cancelled to keep data realistic)
        if status not in {"pending", "cancelled"}:
            pay_status = "refunded" if status == "refunded" else "captured"
            paid_at = (order_date + timedelta(minutes=random.randint(1, 120)))
            conn.execute(
                "INSERT INTO payments (order_id, method, amount, status, paid_at) "
                "VALUES (?,?,?,?,?)",
                (oid, random.choice(PAY_METHODS), total, pay_status,
                 paid_at.strftime("%Y-%m-%d %H:%M:%S")),
            )

    # Reviews — from customers who actually bought delivered products.
    delivered = conn.execute(
        "SELECT DISTINCT oi.product_id, o.customer_id "
        "FROM order_items oi JOIN orders o ON o.id = oi.order_id "
        "WHERE o.status = 'delivered'"
    ).fetchall()
    seen_pairs: set[tuple[int, int]] = set()
    for product_id, customer_id in delivered:
        if random.random() < 0.5:
            continue
        if (product_id, customer_id) in seen_pairs:
            continue
        seen_pairs.add((product_id, customer_id))
        rating, title, body = random.choice(REVIEW_SNIPPETS)
        created = datetime(2024, 6, 1) + timedelta(days=random.randint(0, 300))
        conn.execute(
            "INSERT INTO reviews (product_id, customer_id, rating, title, body, "
            "created_at) VALUES (?,?,?,?,?,?)",
            (product_id, customer_id, rating, title, body,
             created.strftime("%Y-%m-%d %H:%M:%S")),
        )

    conn.commit()

    # Report
    def count(table: str) -> int:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    print(f"Seeded database at {db_path}")
    for t in ("categories", "products", "customers", "addresses",
              "orders", "order_items", "payments", "reviews"):
        print(f"  {t:<12} {count(t):>4} rows")
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create and seed the ecommerce DB.")
    parser.add_argument("--db", default=os.getenv("DB_PATH", str(ROOT / "data" / "ecommerce.db")))
    parser.add_argument("--force", action="store_true", help="recreate if it exists")
    args = parser.parse_args()

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        if not args.force:
            print(f"{db_path} already exists. Use --force to recreate.")
            return
        db_path.unlink()

    build(db_path)


if __name__ == "__main__":
    main()
