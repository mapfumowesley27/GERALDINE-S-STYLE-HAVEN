from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import uuid
import re
import secrets

# Try to import dotenv, but make it optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Continue without dotenv if not installed

# Email validation pattern
EMAIL_PATTERN = r'^[\w\.-]+@[\w\.-]+\.\w+$'

# Create Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'geraldine-style-haven-secret-key')
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# CSRF token generation and validation
def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(16)
    return session['csrf_token']

def validate_csrf_token(submitted_token):
    session_token = session.get('csrf_token')
    return session_token and submitted_token == session_token

# Add csrf_token to Jinja globals
app.jinja_env.globals['csrf_token'] = generate_csrf_token

db = SQLAlchemy(app)


# Database Models
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(200))
    sizes = db.Column(db.String(200))
    colors = db.Column(db.String(200))
    quantity = db.Column(db.Integer, default=0)
    in_stock = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_sizes_list(self):
        return self.sizes.split(',') if self.sizes else []

    def get_colors_list(self):
        return self.colors.split(',') if self.colors else []


class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100))
    bio = db.Column(db.Text)
    image = db.Column(db.String(200))
    story = db.Column(db.Text)
    quote = db.Column(db.String(200))


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_reference = db.Column(db.String(50), unique=True, nullable=False)
    customer_name = db.Column(db.String(100))
    customer_email = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(20), default='ecocash')
    payment_status = db.Column(db.String(20), default='pending')
    transaction_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.Column(db.Text)  # Store cart items as JSON

    def get_items_list(self):
        return json.loads(self.items) if self.items else []


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# Helper function to check if user is logged in
def is_admin_logged_in():
    return session.get('admin_logged_in') and session.get('admin_id')


# Decorator for admin-only routes
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_logged_in():
            flash('Please log in to access the admin panel.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# Routes
@app.route('/')
def index():
    featured_products = Product.query.limit(4).all()
    return render_template('index.html', featured_products=featured_products)


@app.route('/products')
def products():
    category = request.args.get('category', 'all')
    max_price = request.args.get('max_price', type=float)
    size = request.args.get('size', '')
    sort = request.args.get('sort', 'featured')
    
    # Base query
    query = Product.query
    
    # Category filter
    if category and category != 'all':
        query = query.filter_by(category=category)
    
    products = query.all()
    
    # Price filter
    if max_price:
        products = [p for p in products if p.price <= max_price]
    
    # Size filter - use exact match to avoid false positives (e.g., "S" matching "XS")
    if size:
        products = [p for p in products if p.sizes and size in [s.strip() for s in p.sizes.split(',')]]
    
    # Sort
    if sort == 'price_low':
        products = sorted(products, key=lambda x: x.price)
    elif sort == 'price_high':
        products = sorted(products, key=lambda x: x.price, reverse=True)
    # 'featured' and 'newest' keep original order

    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories]

    return render_template('products.html', products=products, categories=categories, current_category=category, max_price=max_price)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product-detail.html', product=product)


@app.route('/about')
def about():
    owners = Owner.query.all()
    return render_template('about.html', owners=owners)


@app.route('/stories')
def stories():
    owners = Owner.query.all()
    return render_template('stories.html', owners=owners)


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/cart')
def cart():
    cart_items = []
    total = 0

    cart = session.get('cart', [])
    for item in cart:
        product = Product.query.get(item['product_id'])
        if product:
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'size': item.get('size', ''),
                'color': item.get('color', '')
            })
            total += product.price * item['quantity']

    return render_template('cart.html', cart_items=cart_items, total=total)


@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    data = request.json
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))
    size = data.get('size', '')
    color = data.get('color', '')
    
    # Check if product exists and is in stock
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404
    
    if not product.in_stock:
        return jsonify({'success': False, 'message': 'Product out of stock'}), 400
    
    cart = session.get('cart', [])

    # Check if product already in cart
    found = False
    for item in cart:
        if item['product_id'] == product_id and item['size'] == size and item['color'] == color:
            item['quantity'] += quantity
            found = True
            break

    if not found:
        cart.append({
            'product_id': product_id,
            'quantity': quantity,
            'size': size,
            'color': color
        })

    session['cart'] = cart
    session.modified = True

    return jsonify({'success': True, 'cart_count': len(cart)})


@app.route('/update-cart', methods=['POST'])
def update_cart():
    data = request.json
    product_id = data.get('product_id')
    quantity = int(data.get('quantity'))
    size = data.get('size', '')
    color = data.get('color', '')

    cart = session.get('cart', [])

    for item in cart:
        if item['product_id'] == product_id and item['size'] == size and item['color'] == color:
            if quantity <= 0:
                cart.remove(item)
            else:
                item['quantity'] = quantity
            break

    session['cart'] = cart
    session.modified = True

    return jsonify({'success': True, 'cart_count': len(cart)})


@app.route('/remove-from-cart', methods=['POST'])
def remove_from_cart():
    data = request.json
    product_id = data.get('product_id')
    size = data.get('size', '')
    color = data.get('color', '')

    cart = session.get('cart', [])
    cart = [item for item in cart if not (item['product_id'] == product_id and item['size'] == size and item['color'] == color)]

    session['cart'] = cart
    session.modified = True

    return jsonify({'success': True, 'cart_count': len(cart)})


@app.route('/cart-data', methods=['GET'])
def cart_data():
    """Return cart data as JSON for AJAX updates"""
    cart = session.get('cart', [])
    total = 0
    
    for item in cart:
        product = Product.query.get(item['product_id'])
        if product:
            total += product.price * item['quantity']
    
    return jsonify({
        'total': total,
        'item_count': len(cart)
    })


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', [])
    
    if not cart:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('cart'))
    
    # Calculate total
    total = 0
    cart_items = []
    for item in cart:
        product = Product.query.get(item['product_id'])
        if product:
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'size': item.get('size', ''),
                'color': item.get('color', '')
            })
            total += product.price * item['quantity']

    if request.method == 'POST':
        # Validate CSRF token
        submitted_csrf = request.form.get('csrf_token')
        if not validate_csrf_token(submitted_csrf):
            flash('Invalid form submission. Please try again.', 'danger')
            return render_template('checkout.html', cart_items=cart_items, total=total)
        
        # Regenerate CSRF token after successful validation
        session.pop('csrf_token', None)
        
        # Process Ecocash payment
        customer_name = request.form.get('customer_name')
        customer_email = request.form.get('customer_email')
        customer_phone = request.form.get('customer_phone')

        # Validate required fields
        if not customer_name or not customer_email or not customer_phone:
            flash('Please fill in all required fields', 'danger')
            return render_template('checkout.html', cart_items=cart_items, total=total)

        # Validate email format
        if not re.match(EMAIL_PATTERN, customer_email):
            flash('Please enter a valid email address', 'danger')
            return render_template('checkout.html', cart_items=cart_items, total=total)

        # Validate Ecocash phone prefixes (077, 071, 073, 074, 076, 078)
        valid_prefixes = ('077', '071', '073', '074', '076', '078')
        if not customer_phone.startswith(valid_prefixes):
            flash('Please enter a valid Ecocash phone number (must start with 077, 071, 073, 074, 076, or 078)', 'danger')
            return render_template('checkout.html', cart_items=cart_items, total=total)

        # Generate order reference
        order_reference = f'GSH-{uuid.uuid4().hex[:8].upper()}'

        # Create order in database
        order = Order(
            order_reference=order_reference,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            total_amount=total,
            payment_method='ecocash',
            items=json.dumps(cart)
        )
        db.session.add(order)
        db.session.commit()

        # Initiate Ecocash payment
        from ecocash_payment import create_payment
        payment_result = create_payment(
            amount=total,
            phone=customer_phone,
            order_reference=order_reference
        )

        if payment_result.get('success'):
            # Update order with transaction ID
            order.transaction_id = payment_result.get('transaction_id')
            order.payment_status = 'pending'
            db.session.commit()

            # Clear cart
            session['cart'] = []
            session.modified = True

            # Show success page with payment details
            return render_template('payment_pending.html', 
                                   order=order, 
                                   payment=payment_result)
        else:
            flash(payment_result.get('message', 'Payment failed. Please try again.'), 'danger')
            return render_template('checkout.html', cart_items=cart_items, total=total)

    return render_template('checkout.html', cart_items=cart_items, total=total)


@app.route('/payment-status/<order_reference>')
def payment_status(order_reference):
    order = Order.query.filter_by(order_reference=order_reference).first_or_404()
    
    # Check payment status
    if order.transaction_id:
        from ecocash_payment import ecocash
        status = ecocash.check_payment_status(order.transaction_id)
        
        if status.get('status') == 'completed':
            order.payment_status = 'completed'
            order.status = 'confirmed'
            db.session.commit()
    
    return render_template('payment_status.html', order=order)


@app.route('/payment-complete/<order_reference>')
def payment_complete(order_reference):
    order = Order.query.filter_by(order_reference=order_reference).first_or_404()
    order.payment_status = 'completed'
    order.status = 'confirmed'
    db.session.commit()
    
    return render_template('order_confirmation.html', order=order)

# Admin Routes
# Hardcoded admin access key
ADMIN_ACCESS_KEY = "family6"


@app.route('/verify-key', methods=['GET', 'POST'])
def verify_key():
    """Verify admin access key before showing login page"""
    # If already logged in, redirect to admin
    if is_admin_logged_in():
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        key = request.form.get('access_key', '').strip()
        
        if key == ADMIN_ACCESS_KEY:
            session['key_verified'] = True
            session.modified = True
            return redirect(url_for('login'))
        else:
            flash('Invalid access key. Please try again.', 'danger')
    
    # Clear any previous key verification
    session.pop('key_verified', None)
    return render_template('verify_key.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if key was verified first
    if not session.get('key_verified'):
        flash('Please verify your access key first.', 'warning')
        return redirect(url_for('verify_key'))
    
    if is_admin_logged_in():
        return redirect(url_for('admin'))
    
    # Clear any previous login attempt data
    session.pop('login_error', None)
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            return render_template('login.html', username='')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_admin and user.is_active:
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Set session
            session['admin_logged_in'] = True
            session['admin_id'] = user.id
            session['admin_name'] = user.full_name or user.username
            session.modified = True
            
            # Clear key verification after successful login
            session.pop('key_verified', None)
            
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password.', 'danger')
            # Return with empty username to clear the field
            return render_template('login.html', username='')
    
    return render_template('login.html', username='')


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    session.pop('key_verified', None)
    session.modified = True
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/admin')
@admin_required
def admin():
    search_query = request.args.get('search', '')
    if search_query:
        products = Product.query.filter(
            (Product.name.ilike(f'%{search_query}%')) |
            (Product.category.ilike(f'%{search_query}%')) |
            (Product.description.ilike(f'%{search_query}%'))
        ).all()
    else:
        products = Product.query.all()
    
    # Process products to handle None values for in_stock and quantity
    processed_products = []
    in_stock_count = 0
    out_of_stock_count = 0
    total_value = 0
    
    for p in products:
        # Get in_stock with default True if None
        in_stock = getattr(p, 'in_stock', True)
        if in_stock is None:
            in_stock = True
        
        # Get quantity with default 0 if None
        quantity = getattr(p, 'quantity', 0)
        if quantity is None:
            quantity = 0
        
        # Create a dict with safe values
        processed_products.append({
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'category': p.category,
            'image': p.image,
            'in_stock': in_stock,
            'quantity': quantity
        })
        
        # Update counts
        if in_stock:
            in_stock_count += 1
        else:
            out_of_stock_count += 1
        total_value += p.price
    
    return render_template('admin.html', products=processed_products, search_query=search_query, 
                          in_stock_count=in_stock_count, out_of_stock_count=out_of_stock_count,
                          total_value=total_value)

@app.route('/admin/add-product', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price'))
        description = request.form.get('description')
        category = request.form.get('category')
        sizes = request.form.get('sizes')
        colors = request.form.get('colors')
        quantity = int(request.form.get('quantity', 0))
        in_stock = 'in_stock' in request.form
        
        # Handle image upload
        image = request.form.get('image_url')  # URL as fallback
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename and allowed_file(file.filename):
                # Create unique filename
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Ensure directory exists
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                file.save(filepath)
                image = f"images/{filename}"
        
        product = Product(
            name=name,
            price=price,
            description=description,
            category=category,
            image=image,
            sizes=sizes,
            colors=colors,
            quantity=quantity,
            in_stock=in_stock
        )
        db.session.add(product)
        db.session.commit()
        
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin'))
    
    return render_template('admin_add_product.html')

@app.route('/admin/edit-product/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.price = float(request.form.get('price'))
        product.description = request.form.get('description')
        product.category = request.form.get('category')
        product.sizes = request.form.get('sizes')
        product.colors = request.form.get('colors')
        product.quantity = int(request.form.get('quantity', 0))
        product.in_stock = 'in_stock' in request.form
        
        # Handle image upload
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename and allowed_file(file.filename):
                # Create unique filename
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Ensure directory exists
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                file.save(filepath)
                product.image = f"images/{filename}"
        elif request.form.get('image_url'):
            product.image = request.form.get('image_url')
        
        db.session.commit()
        
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin'))
    
    return render_template('admin_edit_product.html', product=product)

@app.route('/admin/delete-product/<int:product_id>')
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/toggle-stock/<int:product_id>')
@admin_required
def toggle_stock(product_id):
    product = Product.query.get_or_404(product_id)
    product.in_stock = not product.in_stock
    db.session.commit()
    
    status = 'in stock' if product.in_stock else 'out of stock'
    flash(f'Product marked as {status}!', 'success')
    return redirect(url_for('admin'))


@app.route('/create-admin', methods=['GET', 'POST'])
def create_admin():
    """Create admin user - FOR INITIAL SETUP ONLY"""
    # Check if admin already exists
    existing_admin = User.query.filter_by(is_admin=True).first()
    if existing_admin:
        return jsonify({'message': 'Admin user already exists. Please use the login page.'})
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        
        if not username or not email or not password:
            flash('Please fill in all required fields.', 'danger')
            return render_template('create_admin.html')
        
        # Validate password strength
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('create_admin.html')
        
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            is_admin=True,
            is_active=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Admin account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('create_admin.html')


@app.route('/init-db')
def init_db():
    """Initialize database with sample data - FOR DEVELOPMENT ONLY"""
    # Always create tables first (creates them if they don't exist)
    db.create_all()
    
    # Check if data already exists
    if Product.query.first():
        return jsonify({'message': 'Database already initialized with ' + str(Product.query.count()) + ' products'})

    # Add sample owners
    owners = [
        Owner(
            name="Mrs Phiri",
            role="Founder & Creative Director",
            bio="With over 15 years in fashion, Mrs Phiri brings her unique vision to every collection.",
            image="owners/IMG_1201.jpg",
            story="Mrs Phiri started her journey in fashion working as a stylist in Norton before realizing her dream of opening her own boutique. Her passion for sustainable fashion and unique designs led to the creation of Geraldine's Style Haven.",
            quote="Fashion is not just about clothes, it's about expressing your true self."
        ),
        Owner(
            name="Brenda Phiri",
            role="Co-founder & Operations Manager",
            bio="Brenda combines her business acumen with a love for fashion to ensure every customer has an amazing experience.",
            image="owners/IMG_1192.jpg",
            story="After working in retail management for 10 years, Brenda joined forces with Mrs Phiri to create a shopping experience that combines style with exceptional service.",
            quote="Great style should be accessible to everyone."
        )
    ]

    for owner in owners:
        db.session.add(owner)

    # Add sample products
    products = [
        Product(
            name="Elegant Silk Blouse",
            price=89.99,
            description="A luxurious silk blouse perfect for both office wear and evening events. Features a classic design with modern touches.",
            category="Women",
            image="products/silk-blouse.jpg",
            sizes="XS,S,M,L,XL",
            colors="White,Black,Blush",
            quantity=50,
            in_stock=True
        ),
        Product(
            name="Premium Cotton T-Shirt",
            price=29.99,
            description="Essential cotton t-shirt made from premium materials for ultimate comfort and durability.",
            category="Men",
            image="products/cotton-tshirt.jpg",
            sizes="S,M,L,XL,XXL",
            colors="White,Black,Navy,Heather Grey",
            quantity=100,
            in_stock=True
        ),
        Product(
            name="Designer Jeans",
            price=129.99,
            description="Perfectly fitted designer jeans with sustainable denim production.",
            category="Women",
            image="products/designer-jeans.jpg",
            sizes="24,25,26,27,28,29,30,31,32",
            colors="Blue,Black,Washed",
            quantity=30,
            in_stock=True
        ),
        Product(
            name="Leather Jacket",
            price=299.99,
            description="Classic leather jacket that never goes out of style. Made from genuine leather.",
            category="Men",
            image="products/leather-jacket.jpg",
            sizes="S,M,L,XL",
            colors="Black,Brown",
            quantity=15,
            in_stock=True
        ),
        Product(
            name="Summer Dress",
            price=79.99,
            description="Light and airy summer dress perfect for warm days. Features a beautiful floral pattern.",
            category="Women",
            image="products/summer-dress.jpg",
            sizes="XS,S,M,L",
            colors="Floral Print,Navy,Red",
            quantity=40,
            in_stock=True
        ),
        Product(
            name="Wool Sweater",
            price=99.99,
            description="Cozy wool sweater for cold winter days. Made from premium merino wool.",
            category="Unisex",
            image="products/wool-sweater.jpg",
            sizes="S,M,L,XL",
            colors="Cream,Grey,Burgundy",
            quantity=25,
            in_stock=True
        ),
        Product(
            name="Chanel No. 5 Perfume",
            price=150.00,
            description="The iconic floral fragrance that has been a symbol of elegance for decades.",
            category="Perfumes",
            image="products/chanel-perfume.jpg",
            sizes="",
            colors="",
            quantity=20,
            in_stock=True
        ),
        Product(
            name="Dior Sauvage",
            price=120.00,
            description="Bold and fresh masculine fragrance with bergamot and pepper.",
            category="Perfumes",
            image="products/dior-perfume.jpg",
            sizes="",
            colors="",
            quantity=20,
            in_stock=True
        )
    ]

    for product in products:
        db.session.add(product)

    db.session.commit()
    return jsonify({'message': 'Database initialized with sample data!'})


def init_database():
    """Initialize database with tables and sample data"""
    db.create_all()
    
    # Update existing owner records with correct image paths if needed
    owners = Owner.query.all()
    for owner in owners:
        if owner.name == "Mrs Phiri" and "geraldine" in (owner.image or "").lower():
            owner.image = "owners/IMG_1201.jpg"
        elif owner.name == "Brenda Phiri" and "marcus" in (owner.image or "").lower():
            owner.image = "owners/IMG_1192.jpg"
    db.session.commit()
    
    # Check if data already exists
    if not Product.query.first():
        # Add sample owners
        owners = [
            Owner(
                name="Mrs Phiri",
                role="Founder & Creative Director",
                bio="With over 15 years in fashion, Mrs Phiri brings her unique vision to every collection.",
                image="owners/IMG_1201.jpg",
                story="Mrs Phiri started her journey in fashion working as a stylist in Maridale before realizing her dream of opening her own boutique. Her passion for sustainable fashion and unique designs led to the creation of Geraldine's Style Haven.",
                quote="Fashion is not just about clothes, it's about expressing your true self."
            ),
            Owner(
                name="Brenda Phiri",
                role="Co-founder & Operations Manager",
                bio="Brenda combines her business acumen with a love for fashion to ensure every customer has an amazing experience.",
                image="owners/IMG_1192.jpg",
                story="After working in retail management for 10 years, Brenda joined forces with Mrs Phiri to create a shopping experience that combines style with exceptional service.",
                quote="Great style should be accessible to everyone."
            )
        ]
        for owner in owners:
            db.session.add(owner)

        # Add sample products
        products = [
            Product(
                name="Elegant Silk Blouse",
                price=89.99,
                description="A luxurious silk blouse perfect for both office wear and evening events.",
                category="Women",
                image="products/silk-blouse.jpg",
                sizes="XS,S,M,L,XL",
                colors="White,Black,Blush",
                quantity=50,
                in_stock=True       ),
            Product(
                name="Premium Cotton T-Shirt",
                price=29.99,
                description="Essential cotton t-shirt made from premium materials.",
                category="Men",
                image="products/cotton-tshirt.jpg",
                sizes="S,M,L,XL,XXL",
                colors="White,Black,Navy,Heather Grey",
                quantity=100,
                in_stock=True
            ),
            Product(
                name="Designer Jeans",
                price=129.99,
                description="Perfectly fitted designer jeans with sustainable denim production.",
                category="Women",
                image="products/designer-jeans.jpg",
                sizes="24,25,26,27,28,29,30,31,32",
                colors="Blue,Black,Washed",
                quantity=30,
                in_stock=True
            ),
            Product(
                name="Leather Jacket",
                price=299.99,
                description="Classic leather jacket that never goes out of style.",
                category="Men",
                image="products/leather-jacket.jpg",
                sizes="S,M,L,XL",
                colors="Black,Brown",
                quantity=15,
                in_stock=True
            ),
            Product(
                name="Summer Dress",
                price=79.99,
                description="Light and airy summer dress perfect for warm days.",
                category="Women",
                image="products/summer-dress.jpg",
                sizes="XS,S,M,L",
                colors="Floral Print,Navy,Red",
                quantity=40,
                in_stock=True
            ),
            Product(
                name="Wool Sweater",
                price=99.99,
                description="Cozy wool sweater for cold winter days.",
                category="Unisex",
                image="products/wool-sweater.jpg",
                sizes="S,M,L,XL",
                colors="Cream,Grey,Burgundy",
                quantity=25,
                in_stock=True
            ),
            Product(
                name="Chanel No. 5 Perfume",
                price=150.00,
                description="The iconic floral fragrance that has been a symbol of elegance for decades.",
                category="Perfumes",
                image="products/chanel-perfume.jpg",
                sizes="",
                colors="",
                quantity=20,
                in_stock=True
            ),
            Product(
                name="Dior Sauvage",
                price=120.00,
                description="Bold and fresh masculine fragrance with bergamot and pepper.",
                category="Perfumes",
                image="products/dior-perfume.jpg",
                sizes="",
                colors="",
                quantity=20,
                in_stock=True
            )
        ]
        for product in products:
            db.session.add(product)
        
        db.session.commit()
        print("✅ Database initialized with sample data!")
    else:
        print("✅ Database already initialized")

if __name__ == '__main__':
    with app.app_context():
        init_database()
    app.run(debug=True)