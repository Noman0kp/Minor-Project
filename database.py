"""
database.py  —  SQLite Database Layer
======================================
Handles ALL database operations for the app:
  - Schema creation (users, products, ratings tables)
  - Password hashing & verification  (built-in hashlib — no extra install)
  - User CRUD: register, login, forgot-password lookup
  - Product CRUD: insert, fetch all, search by keyword
  - Ratings CRUD: add/update, fetch by user, fetch all for CF model
  - Analytics helpers

Database file: sustainable_products.db  (auto-created on first run)
"""

import sqlite3
import hashlib
import secrets
import os

# --------------------------------------------------------------------------
# Path to the SQLite file.  Sits next to this script in the project folder.
# --------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sustainable_products.db")


# ============================================================================
# CONNECTION
# ============================================================================

def get_connection() -> sqlite3.Connection:
    """Open (or create) the SQLite database and return a connection."""
    conn = sqlite3.connect(DB_PATH)
    # row_factory lets us read columns by name (like a dict)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================================
# SCHEMA CREATION  —  safe to call every startup (IF NOT EXISTS)
# ============================================================================

def create_tables():
    """Create all tables if they don't already exist."""
    conn = get_connection()
    cur  = conn.cursor()

    # -- users ---------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    """)

    # -- products ------------------------------------------------------------
    # base_name groups product variants (e.g. every "Laptop" variant shares
    # base_name = 'Laptop' — used by the search feature).
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id          TEXT    UNIQUE NOT NULL,
            product_name        TEXT    NOT NULL,
            base_name           TEXT    NOT NULL,
            category            TEXT    NOT NULL,
            brand               TEXT,
            price               REAL,
            sustainability_score INTEGER NOT NULL,
            eco_label           TEXT,
            description         TEXT
        )
    """)

    # -- ratings -------------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT    NOT NULL,
            product_id TEXT    NOT NULL,
            rating     REAL    NOT NULL,
            rated_at   TEXT    DEFAULT (datetime('now')),
            UNIQUE(username, product_id),
            FOREIGN KEY (username)   REFERENCES users(username),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    conn.commit()
    conn.close()


# ============================================================================
# PASSWORD HELPERS  (no extra library required)
# ============================================================================

def hash_password(password: str) -> str:
    """Return a salted SHA-256 hash  →  'salt:hash'"""
    salt   = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a plain password against the stored 'salt:hash' string."""
    try:
        salt, hashed = stored.split(":", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == hashed
    except Exception:
        return False


# ============================================================================
# USER OPERATIONS
# ============================================================================

def register_user(username: str, password: str, email: str) -> dict:
    """
    Register a new user.
    Returns {"success": True} or {"success": False, "error": "<reason>"}
    """
    username = username.strip()
    email    = email.strip().lower()

    if len(username) < 3:
        return {"success": False, "error": "Username must be at least 3 characters."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}
    if "@" not in email or "." not in email:
        return {"success": False, "error": "Please enter a valid email address."}

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
            (username, hash_password(password), email)
        )
        conn.commit()
        return {"success": True}
    except sqlite3.IntegrityError as exc:
        msg = str(exc)
        if "username" in msg:
            return {"success": False, "error": "Username already taken."}
        if "email" in msg:
            return {"success": False, "error": "Email already registered."}
        return {"success": False, "error": msg}
    finally:
        conn.close()


def login_user(username: str, password: str) -> dict:
    """
    Validate credentials.
    Returns {"success": True, "email": "..."} or {"success": False, "error": "..."}
    """
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username.strip(),))
    user = cur.fetchone()
    conn.close()

    if user and verify_password(password, user["password_hash"]):
        return {"success": True, "email": user["email"]}
    return {"success": False, "error": "Invalid username or password."}


def get_user_by_identifier(identifier: str):
    """Find a user by username OR email (for forgot-password flow)."""
    identifier = identifier.strip()
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT username, email FROM users WHERE username = ? OR email = ?",
        (identifier, identifier.lower())
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ============================================================================
# PRODUCT OPERATIONS
# ============================================================================

def insert_product(p: dict):
    """Insert one product row (skips silently if product_id already exists)."""
    conn = get_connection()
    conn.execute("""
        INSERT OR IGNORE INTO products
            (product_id, product_name, base_name, category, brand, price,
             sustainability_score, eco_label, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        p["product_id"], p["product_name"], p["base_name"],
        p["category"],   p.get("brand"),    p.get("price"),
        p["sustainability_score"], p.get("eco_label"), p.get("description")
    ))
    conn.commit()
    conn.close()


def get_all_products() -> list:
    """Return all products as a list of dicts, ordered by base_name then eco score."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT * FROM products
        ORDER BY base_name ASC, sustainability_score DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def search_products(query: str) -> list:
    """
    Search products by keyword (matches product_name, base_name, or category).
    Returns results sorted by sustainability_score DESC so the most eco-friendly
    variant always appears first — this is the core of the search feature.
    """
    q = f"%{query.strip().lower()}%"
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT * FROM products
        WHERE  LOWER(product_name) LIKE ?
            OR LOWER(base_name)    LIKE ?
            OR LOWER(category)     LIKE ?
            OR LOWER(eco_label)    LIKE ?
        ORDER BY sustainability_score DESC, product_name ASC
    """, (q, q, q, q))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ============================================================================
# RATINGS OPERATIONS
# ============================================================================

def get_all_ratings() -> list:
    """Fetch every rating — used to build the collaborative filtering model."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT username, product_id, rating FROM ratings")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def add_rating(username: str, product_id: str, rating: float) -> dict:
    """
    Insert or update a user's rating for a product.
    Uses SQLite UPSERT so re-rating a product just updates the value.
    """
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO ratings (username, product_id, rating)
            VALUES (?, ?, ?)
            ON CONFLICT(username, product_id) DO UPDATE SET rating = excluded.rating,
                                                            rated_at = datetime('now')
        """, (username, product_id, rating))
        conn.commit()
        return {"success": True}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    finally:
        conn.close()


def get_user_ratings(username: str) -> list:
    """Return all ratings a specific user has submitted, with product details."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT r.product_id,
               p.product_name,
               p.category,
               p.brand,
               p.sustainability_score,
               p.eco_label,
               r.rating,
               r.rated_at
        FROM   ratings  r
        JOIN   products p ON r.product_id = p.product_id
        WHERE  r.username = ?
        ORDER  BY r.rated_at DESC
    """, (username,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ============================================================================
# ANALYTICS HELPERS
# ============================================================================

def get_stats() -> dict:
    """Return high-level database statistics for the sidebar and analytics tab."""
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("SELECT COUNT(*) AS n FROM users")
    total_users = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) AS n FROM products")
    total_products = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) AS n FROM ratings")
    total_ratings = cur.fetchone()["n"]

    cur.execute("SELECT AVG(rating) AS a FROM ratings")
    avg = cur.fetchone()["a"]
    avg_rating = round(avg, 2) if avg else 0.0

    conn.close()
    return {
        "total_users":    total_users,
        "total_products": total_products,
        "total_ratings":  total_ratings,
        "avg_rating":     avg_rating,
    }