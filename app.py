from flask import (
    Flask,
    render_template,
    session,
    redirect,
    url_for,
    flash,
    request,
    abort,
)

import database
import os
from werkzeug.utils import secure_filename
from PIL import Image
import time
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Initialize the database
database.init_db()

UPLOAD_FOLDER = "static/images/products"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def datetimeformat(value, format="%Y-%m-%d %H:%M:%S"):
    """Format a datetime object or timestamp string"""
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            # Try to parse the string as a datetime
            if "T" in value:  # ISO format
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:  # SQLite format
                value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return value
    return value.strftime(format)


# Register the datetimeformat filter with Jinja2
app.jinja_env.filters["datetimeformat"] = datetimeformat


@app.context_processor
def inject_template_vars():
    """Inject common variables into all templates"""
    return {
        "get_categories_for_nav": lambda: database.get_categories(),
        "now": datetime.now(),
    }


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def process_image(image_file):
    # Open the image
    img = Image.open(image_file)

    # Convert to RGB if necessary
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize if too large while maintaining aspect ratio
    max_size = (800, 800)
    img.thumbnail(max_size, Image.LANCZOS)

    # Generate unique filename
    original_filename = secure_filename(image_file.filename)
    filename = f"{os.path.splitext(original_filename)[0]}_{int(time.time())}.jpg"

    # Save the processed image
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    img.save(save_path, "JPEG", quality=85)

    return filename


@app.route("/")
def home():
    if "cart" not in session:
        session["cart"] = {}
    featured_products = database.get_featured_products()
    return render_template("home.html", featured_products=featured_products)


@app.route("/<category>")
def category_page(category):
    # Get filter/sort params from query string
    sort = request.args.get("sort", "newest")
    brands = request.args.getlist("brand")
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")
    # Convert price_min/max to float if present
    price_min = float(price_min) if price_min else None
    price_max = float(price_max) if price_max else None
    # Fetch all brands for this category for the filter UI
    all_brands = database.get_brands_for_category(category)
    # Fetch filtered/sorted products
    products = database.get_products_by_category(
        category_slug=category,
        brands=brands if brands else None,
        price_min=price_min,
        price_max=price_max,
        sort=sort,
    )
    if products is not None:
        return render_template(
            "category.html", category=category, products=products, brands=all_brands
        )
    return "Category not found", 404


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    # Require login
    if "user_id" not in session:
        flash("Musisz być zalogowany, aby złożyć zamówienie.", "danger")
        return redirect(url_for("login", next=url_for("checkout")))
    # Require cart
    cart = session.get("cart", {})
    total = sum(item["price"] * item["quantity"] for item in cart.values())
    user = database.get_user_by_id(session["user_id"])
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        address = request.form.get("address", "").strip()
        blik_code = request.form.get("blik_code", "").strip()
        if not full_name or not address:
            flash("Imię i nazwisko oraz adres są wymagane.", "danger")
            return render_template("checkout.html", cart=cart, total=total, user=user)
        if not blik_code or not blik_code.isdigit() or len(blik_code) != 6:
            flash("Wprowadź poprawny 6-cyfrowy kod BLIK.", "danger")
            return render_template("checkout.html", cart=cart, total=total, user=user)
        if not cart or total <= 0:
            flash("Twój koszyk jest pusty.", "danger")
            return redirect(url_for("home"))
        try:
            order_id = database.create_order(
                user_id=session["user_id"],
                full_name=full_name,
                address=address,
                cart=cart,
                total=total,
            )
            session["cart"] = {}
            session.modified = True
            flash("Zamówienie zostało złożone pomyślnie!", "success")
            return redirect(url_for("order_confirmation", order_id=order_id))
        except Exception as e:
            flash(f"Błąd podczas składania zamówienia: {e}", "danger")
            return render_template("checkout.html", cart=cart, total=total, user=user)
    return render_template("checkout.html", cart=cart, total=total, user=user)


@app.route("/order_confirmation/<int:order_id>")
def order_confirmation(order_id):
    return render_template("order_confirmation.html", order_id=order_id)


@app.route("/order_history")
def order_history():
    if "user_id" not in session:
        flash("Musisz być zalogowany, aby zobaczyć historię zamówień.", "danger")
        return redirect(url_for("login", next=url_for("order_history")))
    orders = database.get_orders_for_user(session["user_id"])
    # Attach items to each order
    for order in orders:
        order["items"] = database.get_order_items(order["id"])
    return render_template("order_history.html", orders=orders)


@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    product_name = request.form.get("product_name")

    if "cart" not in session:
        session["cart"] = {}

    product = database.get_product_by_name(product_name)

    if product:
        cart_item = {
            "name": product["name"],
            "price": product["price"],
            "image": product["image"],
            "category": product["category"],
            "quantity": 1,
        }

        if product_name in session["cart"]:
            session["cart"][product_name]["quantity"] += 1
        else:
            session["cart"][product_name] = cart_item

        session.modified = True
        flash("Produkt dodany do koszyka!", "success")

    # Redirect back to referring page, or home if not available
    referrer = request.referrer or url_for("home")
    return redirect(referrer)


@app.route("/cart")
def view_cart():
    if "cart" not in session:
        session["cart"] = {}

    total = sum(item["price"] * item["quantity"] for item in session["cart"].values())
    return render_template("cart.html", cart=session["cart"], total=total)


@app.route("/remove_from_cart/<product_name>")
def remove_from_cart(product_name):
    if product_name in session["cart"]:
        del session["cart"][product_name]
        session.modified = True
        flash("Produkt usunięty z koszyka!", "success")
    return redirect(url_for("view_cart"))


@app.route("/update_quantity", methods=["POST"])
def update_quantity():
    product_name = request.form.get("product_name")
    quantity = int(request.form.get("quantity"))

    if product_name in session["cart"]:
        if quantity > 0:
            session["cart"][product_name]["quantity"] = quantity
        else:
            del session["cart"][product_name]
        session.modified = True

    return redirect(url_for("view_cart"))


@app.route("/admin/add_product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        description = request.form.get("description")
        category = request.form.get("category")
        brand = request.form.get("brand")
        stock_quantity = request.form.get("stock_quantity")
        image = request.files.get("image")

        if not all([name, price, description, category, brand, stock_quantity, image]):
            flash("Wszystkie pola są wymagane")
            return redirect(request.url)

        if not allowed_file(image.filename):
            flash("Niedozwolony format pliku")
            return redirect(request.url)

        if image.content_length > MAX_FILE_SIZE:
            flash("Plik jest za duży (max 5MB)")
            return redirect(request.url)

        try:
            filename = process_image(image)
            new_product = database.add_product(
                name,
                float(price),
                description,
                filename,
                category,
                brand=brand,
                stock_quantity=int(stock_quantity),
            )
            flash("Produkt został dodany pomyślnie")
            if isinstance(new_product, dict) and "id" in new_product:
                return redirect(
                    url_for("product_detail", product_identifier=new_product["id"])
                )
            return redirect(url_for("category_page", category=category))
        except Exception as e:
            flash(f"Wystąpił błąd: {str(e)}")
            return redirect(request.url)

    categories = database.get_categories()
    return render_template("admin/add_product.html", categories=categories)


@app.route("/debug/products")
def debug_products():
    products = database.get_all_products()
    return render_template("debug_products.html", products=products)


# User Authentication Routes


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")

        if not all([full_name, email, password, password_confirm]):
            flash("Wszystkie pola są wymagane!", "danger")
            return redirect(url_for("register"))

        if password != password_confirm:
            flash("Hasła nie są identyczne!", "danger")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        if database.create_user(email, hashed_password, full_name, ""):
            flash("Rejestracja pomyślna! Możesz się teraz zalogować.", "success")
            return redirect(url_for("login"))
        else:
            flash("Użytkownik o tym adresie email już istnieje!", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            flash("Email i hasło są wymagane!", "danger")
            return redirect(url_for("login"))

        user = database.get_user_by_email(email)

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_email"] = user["email"]
            session["is_admin"] = user["is_admin"]
            flash("Zalogowano pomyślnie!", "success")
            return redirect(url_for("home"))  # Or redirect to a profile page
        else:
            flash("Nieprawidłowy email lub hasło.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user_email", None)
    session.pop("is_admin", None)
    flash("Wylogowano pomyślnie.", "info")
    return redirect(url_for("home"))


@app.route("/search")
def search():
    """Handle product search"""
    query = request.args.get("q", "").strip()
    if not query:
        return redirect(url_for("home"))

    products = database.search_products(query)
    return render_template(
        "search_results.html",
        products=products,
        search_query=query,
        result_count=len(products),
    )


@app.route("/product/<path:product_identifier>")
def product_detail(product_identifier):
    """Display product details and reviews"""
    print(f"Looking for product with identifier: {product_identifier}")
    product = database.get_product_by_id_or_slug(product_identifier)
    print(f"Found product: {product}")

    if not product:
        print(f"Product not found for identifier: {product_identifier}")
        abort(404)

    # Get product reviews
    reviews = database.get_product_reviews(product["id"])
    print(f"Found {len(reviews)} reviews for product {product['id']}")

    # Calculate average rating
    avg_rating = 0
    if reviews:
        avg_rating = sum(review["rating"] for review in reviews) / len(reviews)

    # Debug output
    print(
        f"Rendering template with product: {product['name']}, price: {product['price']}, image: {product['image']}"
    )

    return render_template(
        "product_detail.html",
        product=product,
        reviews=reviews,
        avg_rating=round(avg_rating, 1) if reviews else 0,
        review_count=len(reviews),
    )


@app.route("/product/<int:product_id>/review", methods=["POST"])
def submit_review(product_id):
    """Handle review submission"""
    if "user_id" not in session:
        flash("Musisz być zalogowany, aby dodać opinię.", "danger")
        return redirect(url_for("login", next=request.url))

    rating = request.form.get("rating")
    comment = request.form.get("comment", "").strip()

    # Validate input
    if not rating or not rating.isdigit() or int(rating) < 1 or int(rating) > 5:
        flash("Proszę podać ocenę od 1 do 5 gwiazdek.", "danger")
        return redirect(url_for("product_detail", product_identifier=product_id))

    if not comment or len(comment) < 10:
        flash("Komentarz musi zawierać co najmniej 10 znaków.", "danger")
        return redirect(url_for("product_detail", product_identifier=product_id))

    # Add the review
    if database.add_product_review(
        product_id=product_id,
        user_id=session["user_id"],
        rating=int(rating),
        comment=comment,
    ):
        flash("Dziękujemy za dodanie opinii!", "success")
    else:
        flash(
            "Wystąpił błąd podczas dodawania opinii. Spróbuj ponownie później.",
            "danger",
        )

    return redirect(url_for("product_detail", product_identifier=product_id))


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.route("/admin/orders")
def admin_orders():
    if not session.get("is_admin"):
        flash(
            "Brak dostępu. Tylko administratorzy mogą przeglądać zamówienia.", "danger"
        )
        return redirect(url_for("home"))
    orders = database.get_all_orders_with_users()
    return render_template("admin/orders.html", orders=orders)


@app.route("/admin/users")
def admin_users():
    if not session.get("is_admin"):
        flash("Brak dostępu.", "danger")
        return redirect(url_for("home"))
    users = database.get_all_users()
    return render_template("admin/users.html", users=users)


@app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
def admin_edit_user(user_id):
    from werkzeug.security import generate_password_hash

    if not session.get("is_admin"):
        flash("Brak dostępu.", "danger")
        return redirect(url_for("home"))
    user = database.get_user_by_id(user_id)
    if not user:
        flash("Nie znaleziono użytkownika.", "danger")
        return redirect(url_for("admin_users"))
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        is_admin = int(request.form.get("is_admin", 0))
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not full_name or not email:
            flash("Imię i nazwisko oraz email są wymagane.", "danger")
        elif new_password and new_password != confirm_password:
            flash("Nowe hasła nie są zgodne.", "danger")
        elif new_password and len(new_password) < 6:
            flash("Nowe hasło musi mieć przynajmniej 6 znaków.", "danger")
        else:
            try:
                database.update_user_info(user_id, full_name, email, address)
                with database.get_db() as db:
                    db.execute(
                        "UPDATE users SET is_admin = ? WHERE id = ?",
                        (is_admin, user_id),
                    )
                    db.commit()
                if new_password:
                    database.update_user_password(
                        user_id, generate_password_hash(new_password)
                    )
                flash("Dane użytkownika zostały zaktualizowane.", "success")
                return redirect(url_for("admin_users"))
            except Exception as e:
                flash("Błąd podczas aktualizacji danych: " + str(e), "danger")
    return render_template("admin/edit_user.html", user=user)


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def admin_delete_user(user_id):
    if not session.get("is_admin"):
        flash("Brak dostępu.", "danger")
        return redirect(url_for("home"))
    if user_id == session.get("user_id"):
        flash("Nie można usunąć własnego konta przez panel admina.", "danger")
        return redirect(url_for("admin_users"))
    database.delete_user(user_id)
    flash("Użytkownik został usunięty.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/orders/<int:order_id>", methods=["GET", "POST"])
def admin_order_detail(order_id):
    if not session.get("is_admin"):
        flash("Brak dostępu.", "danger")
        return redirect(url_for("home"))
    order = database.get_order_by_id(order_id)
    if not order:
        flash("Nie znaleziono zamówienia.", "danger")
        return redirect(url_for("admin_orders"))
    order["items"] = database.get_order_items(order_id)
    if request.method == "POST":
        new_status = request.form.get("status")
        if new_status and new_status != order["status"]:
            database.update_order_status(order_id, new_status)
            flash("Status zamówienia został zaktualizowany.", "success")
            return redirect(url_for("admin_order_detail", order_id=order_id))
    return render_template("admin/order_detail.html", order=order)


@app.route("/account", methods=["GET", "POST"])
def account():
    from werkzeug.security import check_password_hash, generate_password_hash

    if "user_id" not in session:
        flash("Musisz być zalogowany, aby zobaczyć swoje konto.", "danger")
        return redirect(url_for("login"))
    user = database.get_user_by_id(session["user_id"])
    if request.method == "POST":
        # Password change form
        if request.form.get("change_password") == "1":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")
            if not current_password or not new_password or not confirm_password:
                flash("Wszystkie pola są wymagane.", "danger")
            elif not check_password_hash(user["password_hash"], current_password):
                flash("Aktualne hasło jest nieprawidłowe.", "danger")
            elif new_password != confirm_password:
                flash("Nowe hasła nie są zgodne.", "danger")
            elif len(new_password) < 6:
                flash("Nowe hasło musi mieć przynajmniej 6 znaków.", "danger")
            else:
                new_hash = generate_password_hash(new_password)
                database.update_user_password(session["user_id"], new_hash)
                flash("Hasło zostało zmienione.", "success")
                return redirect(url_for("account"))
        # Account info form
        else:
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip()
            address = request.form.get("address", "").strip()
            if not full_name or not email:
                flash("Imię i nazwisko oraz email są wymagane.", "danger")
            else:
                try:
                    database.update_user_info(
                        session["user_id"], full_name, email, address
                    )
                    session["user_email"] = email
                    flash("Dane konta zostały zaktualizowane.", "success")
                    return redirect(url_for("account"))
                except Exception as e:
                    flash("Błąd podczas aktualizacji danych: " + str(e), "danger")
    return render_template("account.html", user=user)


if __name__ == "__main__":
    app.run(debug=True)
