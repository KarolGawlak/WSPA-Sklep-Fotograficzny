import os
import sqlite3
from werkzeug.security import generate_password_hash

def init_database():
    # Remove existing database if it exists
    if os.path.exists('store.db'):
        os.remove('store.db')
    
    # Connect to the database (this will create it)
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript('''
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        address TEXT,
        is_admin BOOLEAN NOT NULL DEFAULT 0
    );

    -- Categories table
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        slug TEXT NOT NULL UNIQUE
    );
    
    -- Products table
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
    );
    
    -- Orders table
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_date TEXT DEFAULT CURRENT_TIMESTAMP,
        total_amount DECIMAL(10,2) NOT NULL,
        status TEXT NOT NULL,
        shipping_address TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    
    -- Order Items table
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price DECIMAL(10,2) NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    );
    
    -- Product Reviews table
    CREATE TABLE IF NOT EXISTS product_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
        comment TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_products_category_id ON products (category_id);
    CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders (user_id);
    CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);
    CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id);
    CREATE INDEX IF NOT EXISTS idx_product_reviews_product_id ON product_reviews (product_id);
    CREATE INDEX IF NOT EXISTS idx_product_reviews_user_id ON product_reviews (user_id);
    CREATE INDEX IF NOT EXISTS idx_products_slug ON products (slug);
    ''')
    
    # Insert sample categories
    categories = [
        ('Aparaty', 'aparaty'),
        ('Sprzęt filmowy', 'sprzet-filmowy'),
        ('Oświetlenie studyjne', 'oswietlenie-studyjne'),
        ('Drukarki', 'drukarki'),
        ('Drony', 'drony'),
        ('Akcesoria do smartfonów', 'akcesoria-smartfony'),
        ('Aparaty analogowe', 'aparaty-analogowe')
    ]
    
    cursor.executemany('INSERT INTO categories (name, slug) VALUES (?, ?)', categories)
    
    # Insert sample products
    products = [
        ('Canon EOS R6', 12999, 'Profesjonalny aparat bezlusterkowy', 'eos_r6.jpg', 1, 'Canon', 10, 'canon-eos-r6'),
        ('Sony A7 IV', 13499, 'Pełnoklatkowy aparat mirrorless', 'sony_a7iv.jpg', 1, 'Sony', 8, 'sony-a7-iv'),
        ('Sony FX3', 22999, 'Profesjonalna kamera filmowa', 'sony_fx3.jpg', 2, 'Sony', 5, 'sony-fx3'),
        ('DJI RS 3 Pro', 3999, 'Profesjonalny gimbal', 'dji_rs3.jpg', 2, 'DJI', 15, 'dji-rs3-pro'),
        ('Profoto B10', 8999, 'Profesjonalna lampa studyjna', 'profoto_b10.jpg', 3, 'Profoto', 7, 'profoto-b10'),
        ('Canon PRO-1000', 4999, 'Profesjonalna drukarka fotograficzna', 'pro1000.jpg', 4, 'Canon', 3, 'canon-pro-1000'),
        ('DJI Mavic 3', 9999, 'Profesjonalny dron z kamerą 4/3"', 'mavic3.jpg', 5, 'DJI', 6, 'dji-mavic-3'),
        ('DJI OM 5', 599, 'Stabilizator do smartfona', 'om5.jpg', 6, 'DJI', 20, 'dji-om5'),
        ('Leica M6', 15999, 'Kultowy aparat analogowy', 'leica_m6.jpg', 7, 'Leica', 2, 'leica-m6')
    ]
    
    cursor.executemany('''
        INSERT INTO products (name, price, description, image, category_id, brand, stock_quantity, slug)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', products)
    
    # Create admin user (password: admin123)
    admin_password = generate_password_hash('admin123')
    cursor.execute('''
        INSERT INTO users (email, password_hash, full_name, is_admin)
        VALUES (?, ?, ?, 1)
    ''', ('admin@example.com', admin_password, 'Administrator'))
    
    # Create regular user (password: user123)
    user_password = generate_password_hash('user123')
    cursor.execute('''
        INSERT INTO users (email, password_hash, full_name)
        VALUES (?, ?, ?)
    ''', ('user@example.com', user_password, 'Jan Kowalski'))
    
    # Add some reviews
    reviews = [
        (1, 2, 5, 'Świetny aparat, bardzo dobra jakość zdjęć!'),
        (1, 2, 4, 'Dobry aparat, ale trochę drogi jak na moje możliwości.'),
        (2, 2, 5, 'Rewelacyjna jakość obrazu, polecam każdemu fotografowi!'),
        (7, 2, 5, 'Niesamowity dron, filmy w 5K wyglądają przepięknie!')
    ]
    
    cursor.executemany('''
        INSERT INTO product_reviews (product_id, user_id, rating, comment)
        VALUES (?, ?, ?, ?)
    ''', reviews)
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_database()
