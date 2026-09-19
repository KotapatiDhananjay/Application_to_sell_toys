# ToyVerse - Wonder & Play Toy Store

ToyVerse is a full-stack e-commerce web application dedicated to providing a magical shopping experience for toys, games, puzzles, and learning adventures for kids of all ages.

## 🚀 Tech Stack

### Backend
* **Framework:** Django 5 & Django REST Framework (DRF)
* **Authentication:** JWT (JSON Web Tokens) via `rest_framework_simplejwt`
* **Database:** SQLite (default for development)
* **Structure:** Modular architecture with specific apps for `accounts`, `catalog`, `cart`, `wishlist`, and `orders`.

### Frontend
* **Core:** HTML5, Vanilla CSS3, and Vanilla JavaScript
* **Features:** Responsive design, dynamic DOM manipulation, interactive cart and wishlist drawers, modular UI components, and modern CSS variables for theming.
* **Integration:** Served by Django as static/template files for seamless deployment.

## ✨ Key Features
* **User Authentication:** Registration, login, and secure profile management using JWT.
* **Product Catalog:** Browse toys with dynamic rendering, quick filters, and advanced sorting/filtering (by price, age, stock, etc.).
* **Shopping Cart:** Slide-over drawer to manage cart items, subtotal calculation, and a free shipping progress tracker.
* **Wishlist:** Save favorite toys for later with a dedicated wishlist drawer.
* **User Profiles:** Manage saved shipping addresses and personal information.
* **Interactive UI:** Smooth transitions, micro-animations, and a responsive design tailored for both desktop and mobile devices.

## 🛠️ Project Structure
```
Toy_Store/
│
├── backend/                # Django Backend Application
│   ├── apps/               # Django apps (core, accounts, catalog, cart, wishlist, orders)
│   ├── config/             # Django project settings and URLs
│   ├── media/              # User-uploaded media and product images
│   ├── requirements.txt    # Python dependencies
│   ├── manage.py           # Django command-line utility
│   └── .env.example        # Example environment variables file
│
└── frontend/               # Frontend Assets (Served by Django)
    ├── index.html          # Main HTML entry point
    ├── styles.css          # Vanilla CSS stylesheet
    └── app.js              # Vanilla JS application logic
```

## 💻 Local Setup Instructions

Follow these steps to get the project up and running on your local machine.

### Prerequisites
* Python 3.10+
* pip (Python package installer)

### 1. Clone the repository and navigate to the project directory
```bash
# Navigate to the project folder
cd Toy_Store
```

### 2. Set up the Backend
```bash
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# (Make sure to open .env and add a secret key if required)

# Run database migrations
python manage.py migrate

# Create a superuser (optional, for admin panel access)
python manage.py createsuperuser
```

### 3. Run the Application
Start the Django development server:
```bash
python manage.py runserver
```

The application will now be running at `http://127.0.0.1:8000/`. The frontend is served directly by the Django backend, so you can access the full app from this URL.

## 📝 License
This project is for educational and showcase purposes.
