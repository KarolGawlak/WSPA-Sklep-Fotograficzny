from flask import Flask, render_template, session, redirect, url_for, flash, request
from decimal import Decimal
import database
import os
from werkzeug.utils import secure_filename
from PIL import Image
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Initialize the database
database.init_db()

UPLOAD_FOLDER = 'static/images/products'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image(image_file):
    # Open the image
    img = Image.open(image_file)
    
    # Convert to RGB if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Resize if too large while maintaining aspect ratio
    max_size = (800, 800)
    img.thumbnail(max_size, Image.LANCZOS)
    
    # Generate unique filename
    original_filename = secure_filename(image_file.filename)
    filename = f"{os.path.splitext(original_filename)[0]}_{int(time.time())}.jpg"
    
    # Save the processed image
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img.save(save_path, 'JPEG', quality=85)
    
    return filename

@app.route('/')
def home():
    if 'cart' not in session:
        session['cart'] = {}
    featured_products = database.get_featured_products()
    return render_template('home.html', featured_products=featured_products)

@app.route('/<category>')
def category_page(category):
    products = database.get_products_by_category(category)
    if products:
        return render_template('category.html', 
                             category=category, 
                             products=products)
    return "Category not found", 404

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_name = request.form.get('product_name')
    
    if 'cart' not in session:
        session['cart'] = {}
    
    product = database.get_product_by_name(product_name)
    
    if product:
        cart_item = {
            'name': product['name'],
            'price': product['price'],
            'image': product['image'],
            'category': product['category'],
            'quantity': 1
        }
        
        if product_name in session['cart']:
            session['cart'][product_name]['quantity'] += 1
        else:
            session['cart'][product_name] = cart_item
        
        session.modified = True
        flash('Produkt dodany do koszyka!', 'success')
    
    return redirect(url_for('category_page', category=product['category']))

@app.route('/cart')
def view_cart():
    if 'cart' not in session:
        session['cart'] = {}
    
    total = sum(item['price'] * item['quantity'] for item in session['cart'].values())
    return render_template('cart.html', cart=session['cart'], total=total)

@app.route('/remove_from_cart/<product_name>')
def remove_from_cart(product_name):
    if product_name in session['cart']:
        del session['cart'][product_name]
        session.modified = True
        flash('Produkt usunięty z koszyka!', 'success')
    return redirect(url_for('view_cart'))

@app.route('/update_quantity', methods=['POST'])
def update_quantity():
    product_name = request.form.get('product_name')
    quantity = int(request.form.get('quantity'))
    
    if product_name in session['cart']:
        if quantity > 0:
            session['cart'][product_name]['quantity'] = quantity
        else:
            del session['cart'][product_name]
        session.modified = True
    
    return redirect(url_for('view_cart'))

@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        description = request.form.get('description')
        category = request.form.get('category')
        image = request.files.get('image')
        
        if not all([name, price, description, category, image]):
            flash('Wszystkie pola są wymagane')
            return redirect(request.url)
        
        if not allowed_file(image.filename):
            flash('Niedozwolony format pliku')
            return redirect(request.url)
        
        if image.content_length > MAX_FILE_SIZE:
            flash('Plik jest za duży (max 5MB)')
            return redirect(request.url)
        
        try:
            filename = process_image(image)
            database.add_product(name, float(price), description, filename, category)
            flash('Produkt został dodany pomyślnie')
            return redirect(url_for('category_page', category=category))
        except Exception as e:
            flash(f'Wystąpił błąd: {str(e)}')
            return redirect(request.url)
    
    categories = database.get_categories()
    return render_template('admin/add_product.html', categories=categories)

@app.route('/debug/products')
def debug_products():
    products = database.get_all_products()
    return render_template('debug_products.html', products=products)

if __name__ == '__main__':
    app.run(debug=True) 