# HooperZone - Sports Injury Recovery E-commerce

A full-stack e-commerce application for selling sport injury recovery equipment, built with Django REST Framework backend and React frontend.

## Tech Stack

### Backend
- Python 3.12, Django 6.0.2, Django REST Framework 3.16.1
- SQLite3 (development)
- djangorestframework-simplejwt for JWT authentication
- Pillow for image handling
- django-cors-headers for frontend communication

### Frontend
- React 19 with Vite
- React Router for navigation
- Axios for API requests
- Modern CSS with design tokens (CSS variables)

---

## Important Commands

### Initial Setup
```bash
# Clone and navigate to project
cd hooperzone

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create admin superuser
python manage.py createsuperuser

# Seed sample data (optional)
python manage.py seed_demo_data
```

### Running the Application
```bash
# Terminal 1 - Backend (from project root)
cd hooperzone
source venv/bin/activate
python manage.py runserver

# Terminal 2 - Frontend (from project root)
cd hooperzone/frontend
npm install
npm run dev
```

### Running Tests
```bash
# Run all backend tests
cd hooperzone
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest hooperzone/tests/test_api.py
```

### Build for Production
```bash
# Build frontend
cd frontend
npm run build

# Collect static files (Django)
cd ../hooperzone
python manage.py collectstatic
```

---

## Access Points

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000/api/ |
| Admin Panel | http://localhost:8000/admin/ |
| API Root | http://localhost:8000/ |

---

## Features

### Authentication (OTP-based)
- Phone number registration with OTP verification
- OTP-based login (no password required for login)
- Password reset via OTP
- JWT token authentication for API access

### Products
- Product catalog with categories
- Filter by injury type (knee, ankle, back, neck, shoulder, wrist, elbow, hip)
- Search, filter by price, category, brand, size
- Product images and detailed descriptions
- Stock management
- Featured products

### Shopping Cart
- Add/remove/update items
- Persistent cart for authenticated users
- Stock validation

### Orders
- Order creation from cart
- Order history and detail view
- Visual order tracking timeline
- Order cancellation (for pending/confirmed orders)
- Automatic stock management

### Favorites/Wishlist
- Add/remove products from favorites
- Favorites page with product grid
- Favorites count in header

### Reviews
- Product reviews with star ratings
- Verified purchase badge
- One review per product per user
- Review form on product detail page

---

## Repository Layout

```
hooperzone/
├── hooperzone/          # Django project settings
│   ├── settings/
│   │   ├── base.py        # Shared settings
│   │   ├── local.py       # Development settings
│   │   └── production.py  # Production settings
│   ├── urls.py            # Root URL configuration
│   └── tests/             # API tests
├── accounts/              # User authentication & OTP
├── products/              # Product catalog
│   └── management/commands/seed_demo_data.py
├── cart/                  # Shopping cart
├── orders/                # Order management
├── reviews/               # Product reviews
├── favorites/             # Wishlist/favorites
├── frontend/              # React frontend
│   ├── src/
│   │   ├── api/           # API client & endpoints
│   │   ├── components/    # Reusable components
│   │   ├── context/       # Auth, Cart, Favorites contexts
│   │   ├── pages/         # Page components
│   │   ├── styles/        # CSS design system
│   │   └── App.jsx        # Main app with routes
│   └── package.json
├── requirements.txt
└── manage.py
```

---

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/otp/send/` | Send OTP to phone number |
| POST | `/api/auth/otp/verify/` | Verify OTP code |
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/password/reset/` | Reset password via OTP |
| GET/PATCH | `/api/auth/profile/` | Get/update user profile |
| POST | `/api/token/refresh/` | Refresh JWT token |

### Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products/categories/` | List all categories |
| GET | `/api/products/` | List products (with filters) |
| GET | `/api/products/:slug/` | Product detail |
| GET | `/api/products/featured/` | Featured products |
| GET | `/api/products/injury_types/` | List injury types |

**Query Params for Products:**
- `?search=<text>` - Search by name, description, brand
- `?category=<slug>` - Filter by category
- `?injury_type=<type>` - Filter by injury type
- `?brand=<brand>` - Filter by brand
- `?size=<size>` - Filter by size
- `?min_price=<price>&max_price=<price>` - Price range
- `?in_stock=true` - Only in-stock items
- `?ordering=<field>` - Sort (price, -price, name, created_at)

### Cart

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cart/` | View cart |
| POST | `/api/cart/add/` | Add item to cart |
| PATCH | `/api/cart/update/` | Update item quantity |
| DELETE | `/api/cart/remove/` | Remove item from cart |
| DELETE | `/api/cart/clear/` | Clear cart |

### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orders/` | List user orders |
| POST | `/api/orders/create/` | Create order from cart |
| GET | `/api/orders/:order_number/` | Order detail |
| POST | `/api/orders/:order_number/cancel/` | Cancel order |

### Reviews

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reviews/product/:slug/` | List product reviews |
| POST | `/api/reviews/product/:slug/create/` | Create review |
| PATCH | `/api/reviews/:id/update/` | Update review |
| DELETE | `/api/reviews/:id/delete/` | Delete review |

### Favorites

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/favorites/` | View favorites |
| POST | `/api/favorites/add/` | Add to favorites |
| DELETE | `/api/favorites/remove/` | Remove from favorites |
| DELETE | `/api/favorites/clear/` | Clear favorites |

---

## OTP Authentication Flow

### Registration
```bash
# 1. Send OTP
curl -X POST http://localhost:8000/api/auth/otp/send/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1234567890", "otp_type": "register"}'

# 2. Verify OTP (use code from response)
curl -X POST http://localhost:8000/api/auth/otp/verify/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1234567890", "code": "123456", "otp_type": "register"}'

# 3. Complete registration
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1234567890", "password": "securepass123", "first_name": "John"}'
```

### Login
```bash
# 1. Send OTP
curl -X POST http://localhost:8000/api/auth/otp/send/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1234567890", "otp_type": "login"}'

# 2. Verify OTP (returns JWT tokens)
curl -X POST http://localhost:8000/api/auth/otp/verify/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1234567890", "code": "123456", "otp_type": "login"}'
```

---

## Adding Images

### Product Images
1. Go to http://localhost:8000/admin/
2. Navigate to **Products** → **Products**
3. Edit a product
4. Scroll to **Product Images** section
5. Click **Add Product Image** and upload
6. Check **is_primary** for the main image

### Category Images
1. Go to **Products** → **Categories**
2. Edit a category and upload an image

### Homepage Images
Edit `frontend/src/pages/Home.jsx` and replace the Unsplash URLs:
```javascript
const bodyParts = [
  {
    id: 'knee',
    name: 'Knee',
    image: 'YOUR_IMAGE_URL_HERE', // Replace with your image
  },
  // ...
];
```

---

## Models

### User (accounts)
- Custom user model with phone as username
- OTP codes for verification

### Product (products)
- Categories for organization
- Products with injury type classification
- Multiple images per product

### Cart (cart)
- One cart per user
- Cart items with quantity

### Order (orders)
- Order with shipping details
- Order items (snapshot of product at time of purchase)
- Status tracking (pending → confirmed → processing → shipped → delivered)

### Review (reviews)
- User reviews with ratings (1-5)
- Verified purchase tracking

### Favorite (favorites)
- One favorite list per user
- Multiple favorite items

---

## Running Tests

```bash
cd hooperzone
pytest
```

Tests cover:
- OTP authentication (send, verify, register, login)
- Product listing, filtering, and search
- Cart operations (add, update, remove, clear)
- Order creation and cancellation
- Review creation and listing

---

## Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## License

This project is for educational purposes.
