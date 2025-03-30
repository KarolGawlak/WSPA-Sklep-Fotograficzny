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
        db.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE
        )
        ''')
        
        db.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            description TEXT,
            image TEXT,
            category_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
        ''')
        
        # Insert initial categories
        categories = [
            ('Fotografia', 'fotografia'),
            ('Filmowanie', 'filmowanie'),
            ('Studio', 'studio'),
            ('Druk i edycja', 'druk'),
            ('Drony', 'drony'),
            ('Fotografia mobilna', 'mobile'),
            ('Fotografia analogowa', 'analogowa')
        ]
        
        db.executemany(
            'INSERT OR IGNORE INTO categories (name, slug) VALUES (?, ?)',
            categories
        )
        
        # Insert sample products
        products = [
            ('Canon EOS R6', 12999.00, 'Profesjonalny aparat bezlusterkowy', 'eos_r6.jpg', 'fotografia'),
            ('Sony A7 IV', 13499.00, 'Pełnoklatkowy aparat mirrorless', 'sony_a7iv.jpg', 'fotografia'),
            ('Sony FX3', 22999.00, 'Profesjonalna kamera filmowa', 'sony_fx3.jpg', 'filmowanie'),
            ('DJI RS 3 Pro', 3999.00, 'Profesjonalny gimbal', 'dji_rs3.jpg', 'filmowanie'),
            ('Profoto B10', 8999.00, 'Profesjonalna lampa studyjna', 'profoto_b10.jpg', 'studio'),
            ('Canon PRO-1000', 4999.00, 'Profesjonalna drukarka fotograficzna', 'pro1000.jpg', 'druk'),
            ('DJI Mavic 3', 9999.00, 'Profesjonalny dron z kamerą 4/3"', 'mavic3.jpg', 'drony'),
            ('DJI OM 5', 599.00, 'Stabilizator do smartfona', 'om5.jpg', 'mobile'),
            ('Leica M6', 15999.00, 'Kultowy aparat analogowy', 'leica_m6.jpg', 'analogowa')
        ]
        
        for product in products:
            name, price, description, image, category_slug = product
            db.execute('''
                INSERT OR IGNORE INTO products (name, price, description, image, category_id)
                SELECT ?, ?, ?, ?, categories.id
                FROM categories
                WHERE categories.slug = ?
            ''', (name, price, description, image, category_slug))
        
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