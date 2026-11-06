"""
Database Seeder for Enterprise E-Commerce & Analytics (NL2SQL Agent)
Generates a realistic SQLite database with 7 relational tables, verified relationships,
and deterministic data (random.seed(42)) suitable for enterprise BI testing and demonstrations.
"""

import os
import sqlite3
import random
from datetime import datetime, timedelta

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "enterprise_data.db")


def create_schema(cursor: sqlite3.Cursor):
    """Creates the relational schema with proper primary and foreign keys."""
    cursor.executescript("""
    DROP TABLE IF EXISTS marketing_campaigns;
    DROP TABLE IF EXISTS product_reviews;
    DROP TABLE IF EXISTS order_items;
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS products;
    DROP TABLE IF EXISTS categories;
    DROP TABLE IF EXISTS customers;

    -- Customers Table
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        city TEXT NOT NULL,
        country TEXT NOT NULL,
        segment TEXT NOT NULL CHECK(segment IN ('Enterprise', 'Mid-Market', 'SMB', 'Consumer')),
        loyalty_tier TEXT NOT NULL CHECK(loyalty_tier IN ('Bronze', 'Silver', 'Gold', 'Platinum')),
        signup_date DATE NOT NULL
    );

    -- Categories Table
    CREATE TABLE categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT NOT NULL UNIQUE,
        department TEXT NOT NULL
    );

    -- Products Table
    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        category_id INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        cost_price REAL NOT NULL,
        stock_quantity INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('In Stock', 'Low Stock', 'Discontinued')),
        FOREIGN KEY (category_id) REFERENCES categories (category_id)
    );

    -- Orders Table
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        order_date DATE NOT NULL,
        shipping_date DATE,
        status TEXT NOT NULL CHECK(status IN ('Completed', 'Shipped', 'Processing', 'Cancelled', 'Refunded')),
        payment_method TEXT NOT NULL CHECK(payment_method IN ('Credit Card', 'Wire Transfer', 'PayPal', 'UPI')),
        total_amount REAL NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
    );

    -- Order Items Table
    CREATE TABLE order_items (
        order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        discount_percent REAL NOT NULL DEFAULT 0.0,
        FOREIGN KEY (order_id) REFERENCES orders (order_id),
        FOREIGN KEY (product_id) REFERENCES products (product_id)
    );

    -- Product Reviews Table
    CREATE TABLE product_reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
        sentiment TEXT NOT NULL CHECK(sentiment IN ('Positive', 'Neutral', 'Negative')),
        review_date DATE NOT NULL,
        comment TEXT,
        FOREIGN KEY (product_id) REFERENCES products (product_id),
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
    );

    -- Marketing Campaigns Table
    CREATE TABLE marketing_campaigns (
        campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_name TEXT NOT NULL,
        channel TEXT NOT NULL CHECK(channel IN ('Google Ads', 'LinkedIn', 'Email', 'Meta Ads', 'SEO/Organic')),
        budget REAL NOT NULL,
        spent REAL NOT NULL,
        conversions INTEGER NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL
    );

    -- Performance Indexes
    CREATE INDEX idx_orders_customer ON orders(customer_id);
    CREATE INDEX idx_orders_date ON orders(order_date);
    CREATE INDEX idx_orders_status ON orders(status);
    CREATE INDEX idx_items_order ON order_items(order_id);
    CREATE INDEX idx_items_product ON order_items(product_id);
    """)


def seed_data(cursor: sqlite3.Cursor):
    """Seeds rich, realistic enterprise data."""
    random.seed(42)

    # 1. Categories
    categories = [
        ("Cloud Infrastructure", "Technology"),
        ("Developer Tools", "Technology"),
        ("Enterprise Security", "Technology"),
        ("Office Hardware", "Workplace"),
        ("Productivity Software", "Software"),
        ("AI & Data Analytics", "Software"),
        ("Ergonomic Furniture", "Workplace")
    ]
    cursor.executemany("INSERT INTO categories (category_name, department) VALUES (?, ?);", categories)

    # 2. Products
    products = [
        ("Cloud Server Pro (Monthly)", 1, 149.99, 45.00, 500, "In Stock"),
        ("Database Cluster Dedicated", 1, 499.00, 150.00, 120, "In Stock"),
        ("Edge CDN Accelerate", 1, 79.50, 18.00, 300, "In Stock"),
        ("DevSuite IDE Enterprise", 2, 29.99, 4.00, 1000, "In Stock"),
        ("CI/CD Pipeline Runner Hub", 2, 89.00, 20.00, 250, "In Stock"),
        ("API Gateway Gateway X", 2, 199.00, 40.00, 180, "In Stock"),
        ("ZeroTrust Identity Shield", 3, 249.00, 60.00, 150, "In Stock"),
        ("Endpoint Security Agent", 3, 19.99, 3.50, 800, "In Stock"),
        ("Vulnerability Scanner Suite", 3, 350.00, 75.00, 90, "In Stock"),
        ("4K UltraWide Monitor 34\"", 4, 699.99, 420.00, 45, "Low Stock"),
        ("Thunderbolt 4 Docking Station", 4, 189.50, 95.00, 85, "In Stock"),
        ("Mechanical Wireless Keyboard", 4, 129.00, 55.00, 140, "In Stock"),
        ("Workspace Collab Suite Tier 1", 5, 12.00, 2.00, 5000, "In Stock"),
        ("Workspace Collab Suite Tier 2", 5, 24.00, 3.50, 3500, "In Stock"),
        ("Enterprise Document Cloud", 5, 45.00, 8.00, 1200, "In Stock"),
        ("Predictive AI Engine API", 6, 599.00, 110.00, 200, "In Stock"),
        ("BI Dashboard Visualizer Pro", 6, 149.00, 25.00, 400, "In Stock"),
        ("Automated ETL Pipeline Tool", 6, 299.00, 50.00, 160, "In Stock"),
        ("Ergonomic High-Back Chair", 7, 450.00, 240.00, 30, "In Stock"),
        ("Motorized Standing Desk 60\"", 7, 650.00, 380.00, 15, "Low Stock"),
        ("Anti-Fatigue Standing Mat", 7, 59.99, 22.00, 90, "In Stock"),
        ("Legacy Backup Server V1", 1, 89.00, 70.00, 0, "Discontinued")
    ]
    cursor.executemany("""
        INSERT INTO products (product_name, category_id, unit_price, cost_price, stock_quantity, status)
        VALUES (?, ?, ?, ?, ?, ?);
    """, products)

    # 3. Customers (120 customers)
    first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Riley", "Cameron", "Avery",
                   "Dakota", "Reese", "Quinn", "Skyler", "Casey", "Harper", "Logan", "Peyton", "Finley", "Rowan",
                   "Vivek", "Aditi", "Rahul", "Pooja", "Arjun", "Neha", "Rohan", "Sneha", "Karan", "Ananya",
                   "Michael", "Sarah", "David", "Emily", "James", "Emma", "Daniel", "Olivia", "Liam", "Sophia"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Martinez", "Hernandez",
                  "Patel", "Sharma", "Verma", "Rao", "Gupta", "Mehta", "Singh", "Yadav", "Nair", "Reddy",
                  "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Wood", "Clark"]
    cities = [("San Francisco", "USA"), ("New York", "USA"), ("Austin", "USA"), ("Seattle", "USA"),
              ("London", "UK"), ("Manchester", "UK"), ("Bengaluru", "India"), ("Mumbai", "India"),
              ("Delhi", "India"), ("Hyderabad", "India"), ("Toronto", "Canada"), ("Berlin", "Germany"),
              ("Singapore", "Singapore"), ("Sydney", "Australia"), ("Tokyo", "Japan")]
    segments = ["Enterprise", "Mid-Market", "SMB", "Consumer"]
    segment_weights = [0.15, 0.25, 0.40, 0.20]
    tiers = ["Bronze", "Silver", "Gold", "Platinum"]
    tier_weights = [0.45, 0.30, 0.18, 0.07]

    customers = []
    base_date = datetime(2023, 1, 1)
    for i in range(1, 121):
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        email = f"{fn.lower()}.{ln.lower()}{i}@example.com"
        city, country = random.choice(cities)
        seg = random.choices(segments, weights=segment_weights)[0]
        tier = random.choices(tiers, weights=tier_weights)[0]
        signup = base_date + timedelta(days=random.randint(0, 700))
        customers.append((fn, ln, email, city, country, seg, tier, signup.strftime("%Y-%m-%d")))

    cursor.executemany("""
        INSERT INTO customers (first_name, last_name, email, city, country, segment, loyalty_tier, signup_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, customers)

    # 4. Orders and Order Items (500 orders across 2024 to 2026)
    order_statuses = ["Completed", "Shipped", "Processing", "Cancelled", "Refunded"]
    status_weights = [0.70, 0.14, 0.06, 0.06, 0.04]
    payment_methods = ["Credit Card", "Wire Transfer", "PayPal", "UPI"]

    order_records = []
    order_items_records = []

    order_id = 1
    order_item_id = 1
    start_order_date = datetime(2024, 1, 1)

    for _ in range(550):
        cust_id = random.randint(1, 120)
        # Random date between Jan 2024 and mid 2026
        ord_date = start_order_date + timedelta(days=random.randint(0, 850))
        status = random.choices(order_statuses, weights=status_weights)[0]
        pay_method = random.choice(payment_methods)

        if status in ("Completed", "Shipped"):
            ship_date = (ord_date + timedelta(days=random.randint(1, 4))).strftime("%Y-%m-%d")
        else:
            ship_date = None

        # Each order has 1 to 4 distinct items
        num_items = random.choices([1, 2, 3, 4], weights=[0.45, 0.35, 0.15, 0.05])[0]
        chosen_products = random.sample(products, num_items)

        order_total = 0.0
        for prod in chosen_products:
            # prod tuple: (name, cat_id, unit_price, cost_price, stock, status)
            prod_name = prod[0]
            # Look up product_id from products list index + 1
            prod_idx = [p[0] for p in products].index(prod_name) + 1
            price = prod[2]
            qty = random.choices([1, 2, 3, 5, 10], weights=[0.60, 0.22, 0.10, 0.05, 0.03])[0]
            disc = random.choice([0.0, 0.0, 0.05, 0.10, 0.15, 0.20])
            item_total = (price * qty) * (1.0 - disc)
            order_total += item_total

            order_items_records.append((
                order_item_id,
                order_id,
                prod_idx,
                qty,
                round(price, 2),
                round(disc * 100.0, 1)
            ))
            order_item_id += 1

        order_records.append((
            order_id,
            cust_id,
            ord_date.strftime("%Y-%m-%d"),
            ship_date,
            status,
            pay_method,
            round(order_total, 2)
        ))
        order_id += 1

    cursor.executemany("""
        INSERT INTO orders (order_id, customer_id, order_date, shipping_date, status, payment_method, total_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, order_records)

    cursor.executemany("""
        INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price, discount_percent)
        VALUES (?, ?, ?, ?, ?, ?);
    """, order_items_records)

    # 5. Product Reviews (160 reviews)
    review_comments = {
        5: ["Exceeded all expectations! Solid performance and flawless setup.",
            "Outstanding quality and enterprise reliability. Highly recommended.",
            "The ROI we achieved within our first month was incredible."],
        4: ["Very good solution, responsive support team, minor learning curve.",
            "Great feature set for the price. Performs reliably under heavy load.",
            "Integrates smoothly with our existing tech stack."],
        3: ["Decent performance, but documentation could be more extensive.",
            "Works as advertised though UI has room for improvement.",
            "Average experience, satisfied with essential capabilities."],
        2: ["Faced intermittent latency issues during peak business hours.",
            "Documentation was lacking some key configuration details.",
            "Customer service took over 48 hours to resolve initial ticket."],
        1: ["Did not meet our scalability requirements at all.",
            "Encountered multiple bugs and had to request a refund.",
            "Poor compatibility with our legacy architecture."]
    }

    reviews = []
    for r_id in range(1, 161):
        p_id = random.randint(1, len(products))
        c_id = random.randint(1, 120)
        rating = random.choices([5, 4, 3, 2, 1], weights=[0.45, 0.30, 0.12, 0.08, 0.05])[0]
        sentiment = "Positive" if rating >= 4 else ("Neutral" if rating == 3 else "Negative")
        rev_date = (start_order_date + timedelta(days=random.randint(30, 850))).strftime("%Y-%m-%d")
        comment = random.choice(review_comments[rating])
        reviews.append((p_id, c_id, rating, sentiment, rev_date, comment))

    cursor.executemany("""
        INSERT INTO product_reviews (product_id, customer_id, rating, sentiment, review_date, comment)
        VALUES (?, ?, ?, ?, ?, ?);
    """, reviews)

    # 6. Marketing Campaigns (8 campaigns)
    campaigns = [
        ("Q1 Enterprise Cloud Summit", "LinkedIn", 25000.0, 24200.0, 185, "2024-01-10", "2024-03-31"),
        ("Spring Developer Hackathon Push", "Google Ads", 15000.0, 14850.0, 320, "2024-04-01", "2024-05-31"),
        ("ZeroTrust Cybersecurity Webinar", "Email", 5000.0, 4700.0, 140, "2024-06-01", "2024-07-15"),
        ("Mid-Year Growth Retargeting", "Meta Ads", 12000.0, 11900.0, 210, "2024-07-01", "2024-08-31"),
        ("Q3 AI & BI Solutions Showcase", "LinkedIn", 30000.0, 28500.0, 290, "2024-09-01", "2024-11-30"),
        ("Black Friday Tech Deals 2024", "Google Ads", 20000.0, 19950.0, 540, "2024-11-15", "2024-12-05"),
        ("End of Year SaaS Renewal Drive", "Email", 8000.0, 7800.0, 260, "2024-12-01", "2024-12-31"),
        ("Q1 2025 Next-Gen Infra Launch", "Google Ads", 35000.0, 32100.0, 410, "2025-01-15", "2025-03-31")
    ]
    cursor.executemany("""
        INSERT INTO marketing_campaigns (campaign_name, channel, budget, spent, conversions, start_date, end_date)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, campaigns)


def init_db(db_path: str = DB_PATH):
    """Initializes and seeds the database file."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    create_schema(cursor)
    seed_data(cursor)
    conn.commit()

    # Verify counts
    tables = ["customers", "categories", "products", "orders", "order_items", "product_reviews", "marketing_campaigns"]
    counts = {}
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        counts[table] = cursor.fetchone()[0]

    conn.close()
    return counts


if __name__ == "__main__":
    print(f"Creating and seeding enterprise database at: {DB_PATH}")
    stats = init_db()
    print("Database seeding completed successfully!")
    for tbl, count in stats.items():
        print(f" - {tbl}: {count} records")
