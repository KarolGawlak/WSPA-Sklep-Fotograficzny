import sqlite3
from contextlib import contextmanager

DATABASE = 'store.db'

@contextmanager
def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    try:
        yield db
    finally:
        db.close()

def init_db():
    with get_db() as db:
        # Users table
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            address TEXT,
            is_admin BOOLEAN NOT NULL DEFAULT 0
        )
        """)

        # Categories table (updated to ensure slug is present as per PRD)
        db.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE
        )
        """)
        
        # Products table (with recommended additions)
        db.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            description TEXT,
            image TEXT,
            category_id INTEGER,
            brand TEXT,
            stock_quantity INTEGER NOT NULL DEFAULT 0,
            slug TEXT UNIQUE,
            date_added TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
        """)
        
        # Orders table
        db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_date TEXT DEFAULT CURRENT_TIMESTAMP,
            total_amount DECIMAL(10,2) NOT NULL,
            status TEXT NOT NULL,
            shipping_address TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        
        # Order Items table
        db.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10,2) NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
        """)
        
        # Product Reviews table
        db.execute("""
        CREATE TABLE IF NOT EXISTS product_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)

        # Indexes (as per PRD section 3.6, SQLite auto-creates for PK and UNIQUE)
        # Explicitly creating indexes for foreign keys as good practice,
        # though some SQLite versions might do it for F_K_ON.
        db.execute("CREATE INDEX IF NOT EXISTS idx_products_category_id ON products (category_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders (user_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_product_reviews_product_id ON product_reviews (product_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_product_reviews_user_id ON product_reviews (user_id)")

        # Note: Sample data insertion removed for now. Will be handled later if needed.
        # # Insert initial categories
        # categories = [
        #     ('Fotografia', 'fotografia'),
        #     ('Filmowanie', 'filmowanie'),
        #     ('Studio', 'studio'),
        #     ('Druk i edycja', 'druk'),
        #     ('Drony', 'drony'),
        #     ('Fotografia mobilna', 'mobile'),
        #     ('Fotografia analogowa', 'analogowa')
        # ]
        # 
        # db.executemany(
        #     'INSERT OR IGNORE INTO categories (name, slug) VALUES (?, ?)',
        #     categories
        # )
        # 
        # # Insert sample products - THIS WILL FAIL WITHOUT UPDATING TO NEW SCHEMA
        # # products = [
        # #     ('Canon EOS R6', 12999.00, 'Profesjonalny aparat bezlusterkowy', 'eos_r6.jpg', 'fotografia'),
        # #     ('Sony A7 IV', 13499.00, 'Pełnoklatkowy aparat mirrorless', 'sony_a7iv.jpg', 'fotografia'),
        # # ]
        # # 
        # # for product in products:
        # #     name, price, description, image, category_slug = product
        # #     # This needs to be updated if products table has new NOT NULL fields or different structure
        # #     db.execute('''
        # #         INSERT OR IGNORE INTO products (name, price, description, image, category_id)
        # #         SELECT ?, ?, ?, ?, categories.id
        # #         FROM categories
        # #         WHERE categories.slug = ?
        # #     ''', (name, price, description, image, category_slug))
        
        db.commit()

def get_products_by_category(category_slug):
    with get_db() as db:
        products = db.execute('''
            SELECT products.* 
            FROM products 
            JOIN categories ON products.category_id = categories.id
            WHERE categories.slug = ?
        ''', (category_slug,)).fetchall()
        return [dict(product) for product in products]

def get_product_by_name(product_name):
    with get_db() as db:
        product = db.execute('''
            SELECT products.*, categories.slug as category
            FROM products 
            JOIN categories ON products.category_id = categories.id
            WHERE products.name = ?
        ''', (product_name,)).fetchone()
        return dict(product) if product else None

def get_categories():
    with get_db() as db:
        categories = db.execute('SELECT * FROM categories').fetchall()
        return [dict(category) for category in categories]

def get_featured_products():
    with get_db() as db:
        products = db.execute('''
            SELECT p.*, c.slug as category, c.name as category_name
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.id IN (
                SELECT MIN(id)
                FROM products
                GROUP BY category_id
            )
            ORDER BY c.name
        ''').fetchall()
        return [dict(product) for product in products]

def add_product(name, price, description, image_filename, category_slug):
    with get_db() as db:
        db.execute('''
            INSERT INTO products (name, price, description, image, category_id)
            SELECT ?, ?, ?, ?, categories.id
            FROM categories
            WHERE categories.slug = ?
        ''', (name, price, description, image_filename, category_slug))
        db.commit()

def get_all_products():
    with get_db() as db:
        products = db.execute('''
            SELECT p.*, c.slug as category, c.name as category_name
            FROM products p
            JOIN categories c ON p.category_id = c.id
        ''').fetchall()
        return [dict(product) for product in products]

def get_product_by_id_or_slug(identifier):
    """Get product by ID or slug"""
    with get_db() as db:
        # First try to find by ID (if identifier is numeric)
        if str(identifier).isdigit():
            product = db.execute('''
                SELECT p.*, c.slug as category_slug, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.id = ?
            ''', (int(identifier),)).fetchone()
            if product:
                return dict(product)
        
        # If not found by ID or identifier is not numeric, try by slug
        product = db.execute('''
            SELECT p.*, c.slug as category_slug, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.slug = ?
        ''', (identifier,)).fetchone()
        
        return dict(product) if product else None

def get_product_reviews(product_id):
    """Get all reviews for a product"""
    with get_db() as db:
        reviews = db.execute('''
            SELECT pr.*, u.full_name as user_name, u.email as user_email
            FROM product_reviews pr
            JOIN users u ON pr.user_id = u.id
            WHERE pr.product_id = ?
            ORDER BY pr.created_at DESC
        ''', (product_id,)).fetchall()
        return [dict(review) for review in reviews]

def add_product_review(product_id, user_id, rating, comment):
    """Add a new product review"""
    with get_db() as db:
        try:
            db.execute('''
                INSERT INTO product_reviews (product_id, user_id, rating, comment)
                VALUES (?, ?, ?, ?)
            ''', (product_id, user_id, rating, comment))
            db.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding review: {e}")
            return False

# User related functions
def create_user(email, password_hash, full_name, address):
    with get_db() as db:
        try:
            # is_admin defaults to False (0)
            db.execute("""
                INSERT INTO users (email, password_hash, full_name, address, is_admin)
                VALUES (?, ?, ?, ?, 0)
            """, (email, password_hash, full_name, address))
            db.commit()
            return True # Indicate success
        except sqlite3.IntegrityError: # Handles UNIQUE constraint violation for email
            return False # Indicate failure (e.g., email already exists)

def get_user_by_email(email):
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(user) if user else None