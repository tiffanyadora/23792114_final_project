# WildcatWear
### By: Tiffany Adora (23792114)

**WildcatWear** is an e-commerce website for University of Arizona merchandise, built using **Django** as the backend stack, **HTML/CSS** as the frontend stack, as well as **Javascript**. Now fully-functioned, the platform supports user authentication, product management, shopping functionality, order processing, and many more. 

Please follow the instructions below on how to spin up this project.

## Setup & Installation

### Prerequisites
- Python 3.8+
- PostgreSQL
- pip

### Environment Setup

1. Clone the repository
    ```bash
    git clone [repository-url]
    cd wildcatwear
    ```

2. Create a virtual environment & activate it
    ```bash
    python -m venv venv

    # Windows
    venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3. Install dependencies
    ```bash
    pip install -r requirements.txt
    ```

4. Set up environment variables

    Create a `.env` file in the project root with the following variables..
    ```
    # Database Configuration
    DB_NAME=wildcatwear_db
    DB_USER=your_db_user
    DB_PASSWORD=your_db_password
    DB_HOST=localhost
    DB_PORT=5432

    # API Keys (without quotation)
    MAILJET_API_KEY=your_mailjet_api_key
    MAILJET_API_SECRET=your_mailjet_secret_key
    OPENWEATHER_API_KEY=your_openweather_api_key
    OPENAI_API_KEY=your_openai_api_key
    ```

### Database Setup

1. Create PostgreSQL database
    ```bash
    psql -U postgres
    CREATE DATABASE wildcatwear_db;
    CREATE USER your_db_user WITH PASSWORD 'your_db_password';
    ALTER ROLE your_db_user SET client_encoding TO 'utf8';
    ALTER ROLE your_db_user SET default_transaction_isolation TO 'read committed';
    ALTER ROLE your_db_user SET timezone TO 'UTC';
    GRANT ALL PRIVILEGES ON DATABASE wildcatwear_db TO your_db_user;
    \q
    ```
2. To run the database server..
    1. Start the PosgreSQL
        ```bash
        # Powershell
        Start-Service postgresql
        # on macOS
        brew services start postgresql
        ```
    2. Connect to the database (and manage it)
        - Open the pgAdmin 4 application.
        - In the left sidebar, expand Servers.
        - Enter your master password if prompted.
        - Double-click the listed PostgreSQL server.
        - Enter the PostgreSQL user password (e.g., for postgres).
        - Expand Databases and select your database.

    #### Little notes from me (from which I experienced): 
    If you're getting  "connection timeout expired" error when trying to connect to your PostGreSQL server, you can try do it manually by:
    - Go to Windows Run (windows + R)
    - Type in "services.msc"
    - Find the Postgresql service, right click and manually start it
    - Then open pgAdmin again to start the database server

3. Run migrations
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

4. Create a superuser
    ```bash
    python manage.py createsuperuser
    ```

5. Start the development server
    ```bash
    python manage.py runserver
    ```

    Now visit `http://127.0.0.1:8000/` to access the application.

## API

### MailJet API

This is going to be used for transactional emails like verification and password reset.

To create your API key, please follow below steps:
1. Sign up at https://www.mailjet.com/
2. Get your API Key and Secret Key
3. Add them to your `.env` file
4. The system will automatically use these credentials for sending emails

### ipapi.co

No API key is required. Fetched directly fron JSON endpoint.

### OpenWeather API

This is going to be used for weather data on product shipping locations.

To create your API key, please follow below steps:
1. Sign up at https://openweathermap.org/
2. Get your API key
3. Add to your `.env` file as `OPENWEATHER_API_KEY`

### OpenAI API
This will be used for generating product keywords by admin.

To create your API key, please follow the steps below:
1. Sign up or log in at https://platform.openai.com/
2. Go to your "API Keys" page
3. Create a new API key
4. Add to your `.env` file as `OPENAI_API_KEY`

## Features and Testing

### User Roles

The system has several Users with their role and permissions:
- **Admin** (the first user) Full access to all features
    - **Admin Tools** dashboard (`/admin-tools/`)
- **Moderator**: Review management and content moderation
    - **Moderator Dashboard** (`/moderator-dashboard/`) 
- **Customer Service**: Order management and customer support
    - **Customer Service** (`/customer-service-dashboard/`)
- **Seller**: Product management and order 
    - **Seller Dashboard** (`/seller-dashboard/`)
- **Customer**: Default user account

### Country Detection

The system uses ipapi.co API to automatically detect and select the user's country during registration/update profile:

- The function `get_country_from_ip()` in `forms.py` makes a request to ipapi.co
- The API returns country information based on the user's IP

### Authentication - Email Verification and Password Reset

Email functionality is implemented using MailJet API:
- When a user registers, a verification email is sent
- For password resets, an email with a secure token is sent
- The tokens expire after a set time period

To test:
1. Register a new account from the navbar menu or at `/register/`
2. Check your email for verification
3. Log in from the navbar menu or at `/login/`
4. Test password reset by clicking "Forgot Password?" or at `/password-reset/`
5. Check your email and follow the link to reset the password

### Product Management

Sellers and admins can:
- Add new products
- Edit existing products
- Delete products
- Manage product inventory

To test, log in as an admin or seller and:
1. Visit seller dashboard to manage products
2. Add a new product with the form
3. Edit product details
4. Toggle product listing status
5. Delete a product

### Shopping

Users can:
- Browse products by category
- Search for products with filters
- Add items to cart
- Manage cart (update quantities, remove items)
- Complete checkout process

To test:
1. Browse products on the home page
2. Search for products using the search bar
3. Add products to cart
4. Adjust quantities in cart
5. Proceed to checkout

### Order Management

Users can view their order history, while sellers and admins can manage orders:

To test:
1. Place an order as a customer
2. View order details in "My Orders"
3. Log in as a seller to fulfill orders
4. Log in as customer service to cancel/refund order

### Notification System

The platform includes a real-time notification system:
- Order status updates
- Product price changes and restocks
- Messaging notifications
- System notifications

To test:
1. Subscribe to products using the "Subscribe" button
2. Place an order to receive order notifications
3. Check the notification bell in the header

### Messaging System

Users can communicate with each other:
- Customer to seller inquiries
- Customer service support
- Private messaging between users

To test:
1. Log in and click the Messages icon in the header
2. Start a new conversation with another user
3. Exchange messages
4. Check notification when receiving messages
