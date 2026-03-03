"""
Database initialization script for Geraldine's Style Haven
Run this script to create the database and add sample data.
"""
import os
import sys

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Product, Owner

def init_database():
    with app.app_context():
        # Create all database tables
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created")
        
        # Check if data already exists
        if Product.query.first():
            print("⚠ Database already contains data. Skipping sample data insertion.")
            return
        
        # Add sample owners
        print("Adding sample owners...")
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
        print("✓ Added sample owners")

        # Add sample products
        print("Adding sample products...")
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
        print("✓ Added sample products")

        # Commit all changes
        db.session.commit()
        
        print("\n" + "="*50)
        print("✅ Database initialized successfully!")
        print("="*50)
        print(f"Total owners: {Owner.query.count()}")
        print(f"Total products: {Product.query.count()}")
        print("\nRun 'python app.py' to start the server")
        print("Visit http://localhost:5000/ to view the store")

if __name__ == '__main__':
    init_database()