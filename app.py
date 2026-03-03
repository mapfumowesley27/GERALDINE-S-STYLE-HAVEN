from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

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


# Routes
@app.route('/')
def index():
    featured_products = Product.query.limit(4).all()
    return render_template('index.html', featured_products=featured_products)


@app.route('/products')
def products():
    category = request.args.get('category', 'all')
    if category and category != 'all':
        products = Product.query.filter_by(category=category).all()
    else:
        products = Product.query.all()

    categories = db.session.query(Product.category).distinct().all()
    categories = [c[0] for c in categories]

    return render_template('products.html', products=products, categories=categories, current_category=category)


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
            name="Geraldine Smith",
            role="Founder & Creative Director",
            bio="With over 15 years in fashion, Geraldine brings her unique vision to every collection.",
            image="owners/geraldine.jpg",
            story="Geraldine started her journey in fashion working as a stylist in New York before realizing her dream of opening her own boutique. Her passion for sustainable fashion and unique designs led to the creation of Geraldine's Style Haven.",
            quote="Fashion is not just about clothes, it's about expressing your true self."
        ),
        Owner(
            name="Marcus Chen",
            role="Co-founder & Operations Manager",
            bio="Marcus combines his business acumen with a love for fashion to ensure every customer has an amazing experience.",
            image="owners/marcus.jpg",
            story="After working in retail management for 10 years, Marcus joined forces with Geraldine to create a shopping experience that combines style with exceptional service.",
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
            colors="White,Black,Blush"
        ),
        Product(
            name="Premium Cotton T-Shirt",
            price=29.99,
            description="Essential cotton t-shirt made from premium materials for ultimate comfort and durability.",
            category="Men",
            image="products/cotton-tshirt.jpg",
            sizes="S,M,L,XL,XXL",
            colors="White,Black,Navy,Heather Grey"
        ),
        Product(
            name="Designer Jeans",
            price=129.99,
            description="Perfectly fitted designer jeans with sustainable denim production.",
            category="Women",
            image="products/designer-jeans.jpg",
            sizes="24,25,26,27,28,29,30,31,32",
            colors="Blue,Black,Washed"
        ),
        Product(
            name="Leather Jacket",
            price=299.99,
            description="Classic leather jacket that never goes out of style. Made from genuine leather.",
            category="Men",
            image="products/leather-jacket.jpg",
            sizes="S,M,L,XL",
            colors="Black,Brown"
        ),
        Product(
            name="Summer Dress",
            price=79.99,
            description="Light and airy summer dress perfect for warm days. Features a beautiful floral pattern.",
            category="Women",
            image="products/summer-dress.jpg",
            sizes="XS,S,M,L",
            colors="Floral Print,Navy,Red"
        ),
        Product(
            name="Wool Sweater",
            price=99.99,
            description="Cozy wool sweater for cold winter days. Made from premium merino wool.",
            category="Unisex",
            image="products/wool-sweater.jpg",
            sizes="S,M,L,XL",
            colors="Cream,Grey,Burgundy"
        )
    ]

    for product in products:
        db.session.add(product)

    db.session.commit()
    return jsonify({'message': 'Database initialized with sample data!'})


def init_database():
    """Initialize database with tables and sample data"""
    db.create_all()
    
    # Check if data already exists
    if not Product.query.first():
        # Add sample owners
        owners = [
            Owner(
                name="Geraldine Smith",
                role="Founder & Creative Director",
                bio="With over 15 years in fashion, Geraldine brings her unique vision to every collection.",
                image="owners/geraldine.jpg",
                story="Geraldine started her journey in fashion working as a stylist in New York before realizing her dream of opening her own boutique. Her passion for sustainable fashion and unique designs led to the creation of Geraldine's Style Haven.",
                quote="Fashion is not just about clothes, it's about expressing your true self."
            ),
            Owner(
                name="Marcus Chen",
                role="Co-founder & Operations Manager",
                bio="Marcus combines his business acumen with a love for fashion to ensure every customer has an amazing experience.",
                image="owners/marcus.jpg",
                story="After working in retail management for 10 years, Marcus joined forces with Geraldine to create a shopping experience that combines style with exceptional service.",
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
                colors="White,Black,Blush"
            ),
            Product(
                name="Premium Cotton T-Shirt",
                price=29.99,
                description="Essential cotton t-shirt made from premium materials.",
                category="Men",
                image="products/cotton-tshirt.jpg",
                sizes="S,M,L,XL,XXL",
                colors="White,Black,Navy,Heather Grey"
            ),
            Product(
                name="Designer Jeans",
                price=129.99,
                description="Perfectly fitted designer jeans with sustainable denim production.",
                category="Women",
                image="products/designer-jeans.jpg",
                sizes="24,25,26,27,28,29,30,31,32",
                colors="Blue,Black,Washed"
            ),
            Product(
                name="Leather Jacket",
                price=299.99,
                description="Classic leather jacket that never goes out of style.",
                category="Men",
                image="products/leather-jacket.jpg",
                sizes="S,M,L,XL",
                colors="Black,Brown"
            ),
            Product(
                name="Summer Dress",
                price=79.99,
                description="Light and airy summer dress perfect for warm days.",
                category="Women",
                image="products/summer-dress.jpg",
                sizes="XS,S,M,L",
                colors="Floral Print,Navy,Red"
            ),
            Product(
                name="Wool Sweater",
                price=99.99,
                description="Cozy wool sweater for cold winter days.",
                category="Unisex",
                image="products/wool-sweater.jpg",
                sizes="S,M,L,XL",
                colors="Cream,Grey,Burgundy"
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