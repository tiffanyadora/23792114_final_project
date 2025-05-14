import os
import csv
import django
import sys

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wildcatwear.settings')
django.setup()

from store.models import Category, Product, VisualContent

def migrate_products():
    print("Migrating products......")
    
    # Define the path to the product.csv file
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PRODUCTS_FILE = os.path.join(BASE_DIR, 'static', 'data', 'product.csv')
    
    # Check if the file exists
    if not os.path.exists(PRODUCTS_FILE):
        print(f"Error: {PRODUCTS_FILE} does not exist.")
        return
    
    # Create categories
    categories = set()
    with open(PRODUCTS_FILE, newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            categories.add(row['Category'])
    
    # Add categories to the database
    for category_name in categories:
        Category.objects.get_or_create(name=category_name)
    
    # Create products
    with open(PRODUCTS_FILE, newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                category, _ = Category.objects.get_or_create(name=row['Category'])
                
                product, created = Product.objects.update_or_create(
                    id=int(row['ID']),
                    defaults={
                        'name': row['Name'],
                        'description': row['Description'],
                        'feature': row.get('Feature', ''),
                        'rating': float(row.get('Average Rating', 0)),
                        'price': float(row.get('Price', 0)),
                        'category': category,
                        'pokemon': row.get('Pokemon', ''),
                        'location': row.get('Location', ''),
                        'quantity': int(row.get('Quantity', 0))
                    }
                )
                
                if created:
                    print(f"Created product: {product.name}")
                else:
                    print(f"Updated product: {product.name}")
                    
            except Exception as e:
                print(f"Error importing product {row.get('ID', 'unknown')}: {e}")
    
    print("Product migration completed.")

def migrate_visuals():
    print("Migrating visual content...")
    
    # Define the path to the visualcontent.csv file
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    VISUALS_FILE = os.path.join(BASE_DIR, 'static', 'data', 'visualcontent.csv')
    
    # Check if the file exists
    if not os.path.exists(VISUALS_FILE):
        print(f"Error: {VISUALS_FILE} does not exist.")
        return
    
    # Create visual content
    with open(VISUALS_FILE, newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                product_id = int(row['Product ID'])
                
                try:
                    product = Product.objects.get(id=product_id)
                except Product.DoesNotExist:
                    print(f"Skipping visual for non-existent product ID: {product_id}")
                    continue
                
                visual, created = VisualContent.objects.update_or_create(
                    id=int(row['ID']),
                    defaults={
                        'name': row['Name'],
                        'description': row['Description'],
                        'short_name': row['Short Name'],
                        'file_type': row['File Type'],
                        'css_class': row['CSS Class'],
                        'product': product
                    }
                )
                
                if created:
                    print(f"Created visual: {visual.name}")
                else:
                    print(f"Updated visual: {visual.name}")
                    
            except Exception as e:
                print(f"Error importing visual {row.get('ID', 'unknown')}: {e}")
    
    print("Visual content migration completed.")

if __name__ == "__main__":
    print("Starting data migration...")
    
    # Migrate products first as visuals depend on them
    migrate_products()
    migrate_visuals()
    
    print("Data migration completed successfully.")