-- ===========================================================================
-- Ecommerce schema (SQLite dialect).
-- Written to be Postgres-friendly: swap AUTOINCREMENT for SERIAL/IDENTITY and
-- the CHECK/timestamp defaults carry over almost unchanged.
-- ===========================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS addresses;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS customers;

CREATE TABLE categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    slug        TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE products (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    sku            TEXT NOT NULL UNIQUE,
    name           TEXT NOT NULL,
    description    TEXT,
    category_id    INTEGER NOT NULL REFERENCES categories(id),
    price          REAL NOT NULL CHECK (price >= 0),
    cost           REAL NOT NULL CHECK (cost >= 0),
    currency       TEXT NOT NULL DEFAULT 'USD',
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    is_active      INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE customers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name  TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE,
    phone      TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE addresses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    line1       TEXT NOT NULL,
    city        TEXT NOT NULL,
    state       TEXT,
    postal_code TEXT,
    country     TEXT NOT NULL DEFAULT 'USA',
    is_default  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE orders (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id         INTEGER NOT NULL REFERENCES customers(id),
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','paid','shipped','delivered','cancelled','refunded')),
    order_date          TEXT NOT NULL DEFAULT (datetime('now')),
    shipping_address_id INTEGER REFERENCES addresses(id),
    subtotal            REAL NOT NULL DEFAULT 0,
    tax                 REAL NOT NULL DEFAULT 0,
    shipping_fee        REAL NOT NULL DEFAULT 0,
    total               REAL NOT NULL DEFAULT 0,
    currency            TEXT NOT NULL DEFAULT 'USD'
);

CREATE TABLE order_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    line_total REAL NOT NULL CHECK (line_total >= 0)
);

CREATE TABLE payments (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    method   TEXT NOT NULL CHECK (method IN ('card','paypal','bank_transfer','gift_card')),
    amount   REAL NOT NULL CHECK (amount >= 0),
    status   TEXT NOT NULL DEFAULT 'captured'
             CHECK (status IN ('authorized','captured','failed','refunded')),
    paid_at  TEXT
);

CREATE TABLE reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    rating      INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title       TEXT,
    body        TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_orders_customer   ON orders(customer_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_reviews_product   ON reviews(product_id);
