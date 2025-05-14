from models import Product, VisualContent

# Test to fetch all the products
print("Fetching all products...")
products = Product.get_all()
for product in products:
    print(product.__dict__)

# Test to fetch a single product by ID
test_product_id = "1"
product = Product.get_by_id(test_product_id)
if product:
    print(f"\nProduct with ID {test_product_id}:")
    print(product.__dict__)
    print(f"Image Name: {product.get_image_name()}")
else:
    print(f"\nProduct with ID {test_product_id} is not found.")

# Test to fetch visuals for the product
print(f"\nFetching visuals for Product {test_product_id}...")
visuals = VisualContent.get_for_product(test_product_id)
for visual in visuals:
    print(visual.__dict__)

# Test to generate HTML for the first visual
if visuals:
    print("\nGenerated HTML for the first visual:")
    print(visuals[0].get_html())