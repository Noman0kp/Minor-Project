"""
seed_data.py  —  One-Time Database Population Script
======================================================
Run this ONCE before starting the app:

    python seed_data.py

What it does:
  1. Creates the DB schema (tables)
  2. Inserts 28 real-world-style products across 10 categories,
     each category has 2-3 sustainability variants
     (e.g. "Organic Cotton T-Shirt" vs "Standard T-Shirt")
  3. Inserts 16 demo users  (password for all: demo1234)
  4. Generates ~300 synthetic ratings that reflect realistic behaviour:
       — "eco users"    give higher ratings to eco-friendly products
       — "regular users" rate more randomly
"""

import random
import os
import sys

# Make sure the local modules are importable when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import create_tables, get_connection, hash_password

random.seed(42)   # reproducible synthetic data


# ============================================================================
# PRODUCT CATALOGUE
# 10 base categories  ×  2-3 sustainability variants  =  28 products
# sustainability_score:  1=Very Low  2=Low  3=Moderate  4=Good  5=Excellent
# ============================================================================

PRODUCTS = [

    # ---- LAPTOP ------------------------------------------------------------
    {"product_id": "P001", "product_name": "Refurbished Laptop Pro (Eco-Certified)",
     "base_name": "Laptop", "category": "Electronics", "brand": "GreenTech",
     "price": 649.99, "sustainability_score": 5, "eco_label": "Eco-Certified Refurbished",
     "description": "Professionally refurbished, 2-yr warranty. 80% less CO₂ than a new unit."},

    {"product_id": "P002", "product_name": "Standard Business Laptop",
     "base_name": "Laptop", "category": "Electronics", "brand": "TechPro",
     "price": 799.99, "sustainability_score": 3, "eco_label": "Energy Star",
     "description": "Reliable everyday laptop with Energy Star certification."},

    {"product_id": "P003", "product_name": "High-Performance Gaming Laptop",
     "base_name": "Laptop", "category": "Electronics", "brand": "PowerEdge",
     "price": 1299.99, "sustainability_score": 2, "eco_label": "None",
     "description": "High energy consumption, no eco certification."},

    # ---- T-SHIRT -----------------------------------------------------------
    {"product_id": "P004", "product_name": "Organic Cotton T-Shirt",
     "base_name": "T-Shirt", "category": "Clothing", "brand": "EcoWear",
     "price": 29.99, "sustainability_score": 5, "eco_label": "GOTS Organic",
     "description": "100% GOTS-certified organic cotton. No pesticides, fair-trade production."},

    {"product_id": "P005", "product_name": "Recycled Polyester T-Shirt",
     "base_name": "T-Shirt", "category": "Clothing", "brand": "ReThread",
     "price": 24.99, "sustainability_score": 4, "eco_label": "Recycled Content",
     "description": "Made from 100% recycled plastic bottles."},

    {"product_id": "P006", "product_name": "Standard Cotton T-Shirt",
     "base_name": "T-Shirt", "category": "Clothing", "brand": "BasicWear",
     "price": 14.99, "sustainability_score": 2, "eco_label": "None",
     "description": "Conventional cotton — high water and pesticide use in production."},

    # ---- COFFEE ------------------------------------------------------------
    {"product_id": "P007", "product_name": "Organic Fair-Trade Coffee",
     "base_name": "Coffee", "category": "Food & Beverages", "brand": "EarthBean",
     "price": 18.99, "sustainability_score": 5, "eco_label": "Organic & Fair Trade",
     "description": "USDA Organic + Fair Trade certified, shade-grown, biodiversity-friendly."},

    {"product_id": "P008", "product_name": "Regular Ground Coffee",
     "base_name": "Coffee", "category": "Food & Beverages", "brand": "MorningBrew",
     "price": 11.99, "sustainability_score": 2, "eco_label": "None",
     "description": "Conventional commercially grown coffee, no certifications."},

    # ---- WATER BOTTLE ------------------------------------------------------
    {"product_id": "P009", "product_name": "Recycled Stainless Steel Bottle",
     "base_name": "Water Bottle", "category": "Home & Kitchen", "brand": "EcoSip",
     "price": 34.99, "sustainability_score": 5, "eco_label": "Recycled Material",
     "description": "90% recycled stainless steel. Lifetime warranty, zero plastic."},

    {"product_id": "P010", "product_name": "BPA-Free Reusable Plastic Bottle",
     "base_name": "Water Bottle", "category": "Home & Kitchen", "brand": "HydroMax",
     "price": 14.99, "sustainability_score": 3, "eco_label": "BPA-Free",
     "description": "Reusable BPA-free plastic — better than single-use but not recycled material."},

    {"product_id": "P011", "product_name": "Single-Use Plastic Bottle (24-pack)",
     "base_name": "Water Bottle", "category": "Home & Kitchen", "brand": "AquaPack",
     "price": 5.99, "sustainability_score": 1, "eco_label": "None",
     "description": "Disposable plastic bottles — very high environmental impact."},

    # ---- NOTEBOOK ----------------------------------------------------------
    {"product_id": "P012", "product_name": "100% Recycled Paper Notebook",
     "base_name": "Notebook", "category": "Stationery", "brand": "GreenWrite",
     "price": 9.99, "sustainability_score": 5, "eco_label": "Recycled Paper (FSC)",
     "description": "100% post-consumer recycled paper. FSC certified, no virgin pulp."},

    {"product_id": "P013", "product_name": "Standard Spiral Notebook",
     "base_name": "Notebook", "category": "Stationery", "brand": "WriteRight",
     "price": 4.99, "sustainability_score": 2, "eco_label": "None",
     "description": "Conventional notebook — virgin paper pulp, no recycled content."},

    # ---- HEADPHONES --------------------------------------------------------
    {"product_id": "P014", "product_name": "Eco-Certified Wireless Headphones",
     "base_name": "Headphones", "category": "Electronics", "brand": "SoundGreen",
     "price": 129.99, "sustainability_score": 4, "eco_label": "Eco-Certified",
     "description": "Recycled-plastic housing, minimal packaging, long battery life."},

    {"product_id": "P015", "product_name": "Standard Wireless Headphones",
     "base_name": "Headphones", "category": "Electronics", "brand": "SoundMax",
     "price": 89.99, "sustainability_score": 3, "eco_label": "Energy Efficient",
     "description": "Quality audio, standard manufacturing process."},

    # ---- BACKPACK ----------------------------------------------------------
    {"product_id": "P016", "product_name": "Recycled Ocean Plastic Backpack",
     "base_name": "Backpack", "category": "Accessories", "brand": "OceanPack",
     "price": 79.99, "sustainability_score": 5, "eco_label": "Ocean Recycled",
     "description": "Made from recovered ocean plastic. Each bag clears ~30 bottles from the sea."},

    {"product_id": "P017", "product_name": "Standard Polyester Backpack",
     "base_name": "Backpack", "category": "Accessories", "brand": "DayPack",
     "price": 39.99, "sustainability_score": 2, "eco_label": "None",
     "description": "Standard polyester. No eco certifications."},

    # ---- SHAMPOO -----------------------------------------------------------
    {"product_id": "P018", "product_name": "Organic Zero-Waste Shampoo Bar",
     "base_name": "Shampoo", "category": "Personal Care", "brand": "PureRoot",
     "price": 12.99, "sustainability_score": 5, "eco_label": "Zero Waste Organic",
     "description": "Zero plastic packaging, 100% natural ingredients, cruelty-free."},

    {"product_id": "P019", "product_name": "Regular Shampoo (500 ml)",
     "base_name": "Shampoo", "category": "Personal Care", "brand": "CleanHair",
     "price": 7.99, "sustainability_score": 2, "eco_label": "None",
     "description": "Conventional shampoo with plastic bottle and synthetic chemicals."},

    # ---- SNEAKERS ----------------------------------------------------------
    {"product_id": "P020", "product_name": "Eco Vegan Sneakers",
     "base_name": "Sneakers", "category": "Footwear", "brand": "EcoStep",
     "price": 89.99, "sustainability_score": 5, "eco_label": "Vegan & Recycled",
     "description": "Recycled materials + natural rubber. Carbon-neutral shipping."},

    {"product_id": "P021", "product_name": "Standard Running Sneakers",
     "base_name": "Sneakers", "category": "Footwear", "brand": "RunFast",
     "price": 69.99, "sustainability_score": 2, "eco_label": "None",
     "description": "Standard synthetic rubber and foam. No eco certifications."},

    # ---- COFFEE MUG --------------------------------------------------------
    {"product_id": "P022", "product_name": "Recycled Glass Coffee Mug",
     "base_name": "Coffee Mug", "category": "Home & Kitchen", "brand": "GreenSip",
     "price": 19.99, "sustainability_score": 5, "eco_label": "Recycled Glass",
     "description": "Handcrafted from 100% recycled glass. Dishwasher safe."},

    {"product_id": "P023", "product_name": "Ceramic Coffee Mug",
     "base_name": "Coffee Mug", "category": "Home & Kitchen", "brand": "BrewMate",
     "price": 12.99, "sustainability_score": 4, "eco_label": "Lead-Free Glaze",
     "description": "Durable, long-lasting ceramic. No plastic."},

    {"product_id": "P024", "product_name": "Disposable Paper Cups (50-pack)",
     "base_name": "Coffee Mug", "category": "Home & Kitchen", "brand": "CupQuick",
     "price": 8.99, "sustainability_score": 1, "eco_label": "None",
     "description": "Single-use, plastic-lined paper cups — not recyclable."},

    # ---- PHONE CHARGER -----------------------------------------------------
    {"product_id": "P025", "product_name": "Portable Solar Charger",
     "base_name": "Phone Charger", "category": "Electronics", "brand": "SolarPow",
     "price": 49.99, "sustainability_score": 5, "eco_label": "Solar Powered",
     "description": "Charges devices entirely from sunlight. Zero grid electricity needed."},

    {"product_id": "P026", "product_name": "Standard USB Wall Charger",
     "base_name": "Phone Charger", "category": "Electronics", "brand": "ChargeFast",
     "price": 14.99, "sustainability_score": 3, "eco_label": "Energy Efficient",
     "description": "Smart-chip wall charger that minimises standby energy draw."},

    # ---- YOGA MAT ----------------------------------------------------------
    {"product_id": "P027", "product_name": "Natural Rubber Eco Yoga Mat",
     "base_name": "Yoga Mat", "category": "Sports & Fitness", "brand": "ZenGreen",
     "price": 69.99, "sustainability_score": 5, "eco_label": "Natural Rubber",
     "description": "Sustainably harvested natural rubber. Fully biodegradable."},

    {"product_id": "P028", "product_name": "Standard PVC Yoga Mat",
     "base_name": "Yoga Mat", "category": "Sports & Fitness", "brand": "FlexFit",
     "price": 24.99, "sustainability_score": 2, "eco_label": "None",
     "description": "Conventional PVC mat — not biodegradable, contains plasticisers."},
]

# ============================================================================
# DEMO USERS  (all use password: demo1234)
# ============================================================================

DEMO_USERS = [
    {"username": "alice",   "email": "alice@demo.com"},
    {"username": "bob",     "email": "bob@demo.com"},
    {"username": "carol",   "email": "carol@demo.com"},
    {"username": "david",   "email": "david@demo.com"},
    {"username": "eve",     "email": "eve@demo.com"},
    {"username": "frank",   "email": "frank@demo.com"},
    {"username": "grace",   "email": "grace@demo.com"},
    {"username": "henry",   "email": "henry@demo.com"},
    {"username": "iris",    "email": "iris@demo.com"},
    {"username": "james",   "email": "james@demo.com"},
    {"username": "kate",    "email": "kate@demo.com"},
    {"username": "liam",    "email": "liam@demo.com"},
    {"username": "mia",     "email": "mia@demo.com"},
    {"username": "noah",    "email": "noah@demo.com"},
    {"username": "olivia",  "email": "olivia@demo.com"},
    {"username": "admin",   "email": "admin@demo.com"},
]

# ============================================================================
# SYNTHETIC RATINGS GENERATOR
# ============================================================================

def generate_ratings() -> list:
    """
    Simulate realistic rating behaviour:
    • Eco-conscious users:  prefer products with higher sustainability_score
    • Regular users:        rate more uniformly (price/quality driven)
    Each user rates a random 60-80% of the catalogue.
    Returns a list of (username, product_id, rating) tuples.
    """
    ECO_USERS = {"alice", "carol", "eve", "grace", "iris", "kate", "olivia", "mia"}
    pid_list  = [p["product_id"] for p in PRODUCTS]
    eco_map   = {p["product_id"]: p["sustainability_score"] for p in PRODUCTS}
    ratings   = []

    for user in DEMO_USERS:
        uname  = user["username"]
        is_eco = uname in ECO_USERS
        n_rate = random.randint(
            int(len(pid_list) * 0.60),
            int(len(pid_list) * 0.80)
        )
        chosen = random.sample(pid_list, n_rate)

        for pid in chosen:
            eco = eco_map[pid]          # 1-5
            if is_eco:
                # Eco users: higher eco score → higher rating
                base = 2.0 + (eco / 5.0) * 2.5   # range 2.5 – 4.5
            else:
                # Regular users: random base, slight quality bias
                base = random.uniform(2.5, 4.5)

            noise  = random.uniform(-0.5, 0.5)
            rating = round(min(5.0, max(1.0, base + noise)), 1)
            ratings.append((uname, pid, rating))

    return ratings


# ============================================================================
# MAIN SEED FUNCTION
# ============================================================================

def seed():
    print("\n🌱  Seeding the database …\n")

    # 1. Create schema
    create_tables()
    print("  ✅  Tables created (or already exist).")

    conn = get_connection()
    cur  = conn.cursor()

    # 2. Products
    for p in PRODUCTS:
        cur.execute("""
            INSERT OR IGNORE INTO products
                (product_id, product_name, base_name, category, brand, price,
                 sustainability_score, eco_label, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["product_id"], p["product_name"], p["base_name"],
            p["category"],   p["brand"],         p["price"],
            p["sustainability_score"], p["eco_label"], p["description"]
        ))
    print(f"  ✅  {len(PRODUCTS)} products inserted.")

    # 3. Users  (all share the same demo password)
    pw_hash = hash_password("demo1234")
    for u in DEMO_USERS:
        cur.execute("""
            INSERT OR IGNORE INTO users (username, password_hash, email)
            VALUES (?, ?, ?)
        """, (u["username"], pw_hash, u["email"]))
    print(f"  ✅  {len(DEMO_USERS)} demo users inserted.")

    # 4. Ratings
    ratings = generate_ratings()
    for uname, pid, r in ratings:
        cur.execute("""
            INSERT OR IGNORE INTO ratings (username, product_id, rating)
            VALUES (?, ?, ?)
        """, (uname, pid, r))
    print(f"  ✅  {len(ratings)} synthetic ratings inserted.")

    conn.commit()
    conn.close()

    print("\n" + "="*55)
    print("  🎉  Database ready!")
    print()
    print("  Demo login — username : alice … olivia  or  admin")
    print("               password : demo1234")
    print()
    print("  Start the app:")
    print("      streamlit run app.py")
    print("="*55 + "\n")


if __name__ == "__main__":
    seed()