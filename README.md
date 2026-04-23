   

## ⚙️ Installation

### Prerequisites
- Python 3.11+
- PostgreSQL
- pip

### Steps

**1. Clone the repository**

    git clone https://github.com/AIUAkylaiTopoeva/Farm.git
    cd Farm

**2. Create virtual environment**

    python -m venv venv

    # Windows
    venv\Scripts\activate

    # Linux/Mac
    source venv/bin/activate

**3. Install dependencies**

    pip install -r req.txt

**4. Create `.env` file in project root**

    SECRET_KEY=your-secret-key-here
    DEBUG=True

    DB_NAME=agro_db
    DB_USER=your_db_user
    DB_PASSWORD=your_db_password
    DB_HOST=localhost
    DB_PORT=5432

    EMAIL_HOST_USER=your_gmail@gmail.com
    EMAIL_HOST_PASSWORD=your_gmail_app_password

**5. Create PostgreSQL database**

    CREATE DATABASE agro_db;

**6. Run migrations**

    python manage.py makemigrations
    python manage.py migrate

**7. Create superuser**

    python manage.py createsuperuser

**8. Run server**

    python manage.py runserver

---

## 📚 API Documentation

Once the server is running, visit:

- **Swagger UI:** `http://127.0.0.1:8000/swagger/`
- **ReDoc:** `http://127.0.0.1:8000/redoc/`
- **Django Admin:** `http://127.0.0.1:8000/admin/`

---

## 🔑 Authentication

The API uses JWT (JSON Web Token) authentication.

### Register
```http
POST /api/accounts/register/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "yourpassword",
  "role": "customer"
}
```

### Verify Email
```http
POST /api/accounts/verify/
Content-Type: application/json

{
  "email": "user@example.com",
  "code": "123456"
}
```

### Login
```http
POST /api/accounts/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

Response:
```json
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}
```

Use the access token in subsequent requests:
```http
Authorization: Bearer eyJ...
```

---

## 👥 User Roles

| Role | Permissions |
|------|------------|
| `customer` | Browse products, create orders, leave reviews |
| `farmer` | Add/edit own products, manage orders, set farm location |
| `admin` | Full access, verify farmers via Django Admin |

Users can switch between `farmer` and `customer` roles without re-registration:
```http
PATCH /api/accounts/change-role/
Authorization: Bearer eyJ...

{ "role": "farmer" }
```

---

## 🛒 Key Endpoints

### Accounts
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/accounts/register/` | Register new user |
| POST | `/api/accounts/login/` | Login (get JWT tokens) |
| POST | `/api/accounts/verify/` | Verify email with code |
| POST | `/api/accounts/resend-code/` | Resend verification code |
| GET | `/api/accounts/me/` | Get current user info |
| PATCH | `/api/accounts/change-role/` | Switch role |
| PATCH | `/api/accounts/farmer/profile/` | Update farm details |

### Products
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products/` | List all active products |
| POST | `/api/products/` | Create product (farmer only) |
| GET | `/api/products/{id}/` | Product detail |
| PATCH | `/api/products/{id}/` | Update product (owner only) |
| DELETE | `/api/products/{id}/` | Delete product (owner only) |
| GET | `/api/categories/` | List categories |

### Route Optimization
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/routing/optimize/` | Get optimized farm order |
| POST | `/api/routing/compare/` | Compare 3 route profiles |

### Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orders/` | List my orders |
| POST | `/api/orders/create/` | Create order |
| GET | `/api/orders/{id}/` | Order detail |
| PATCH | `/api/orders/{id}/status/` | Update status (farmer) |

### Reviews & Likes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products/{id}/reviews/` | List reviews |
| POST | `/api/products/{id}/reviews/` | Add review |
| POST | `/api/products/{id}/like/` | Toggle like |
| GET | `/api/products/{id}/likes/` | Like count |

---

## 🗺 Route Optimization

### How it works

**1.** User selects products from multiple farmers

**2.** System groups products by farmer location

**3.** Google OR-Tools solves the TSP (Travelling Salesman Problem)

**4.** Three route profiles are calculated with different weight configurations:

| Profile | w1 (Distance) | w2 (Cost) | w3 (Time) | w4 (Road) |
|---------|--------------|-----------|-----------|-----------|
| Cheapest | 0.1 | **0.6** | 0.2 | 0.1 |
| Fastest | 0.2 | 0.1 | **0.6** | 0.1 |
| Balanced | 0.25 | 0.25 | 0.25 | 0.25 |

**5.** System calculates real savings vs naive route

### Example Request
```http
POST /api/routing/compare/
Authorization: Bearer eyJ...

{
  "product_ids": [1, 2, 3],
  "start": {"lat": 42.874, "lon": 74.569},
  "road_quality": "medium",
  "fuel_price": 55.0,
  "fuel_consumption": 8.0
}
```

### Example Response
```json
{
  "profiles": {
    "cheapest": {
      "distance_km": 118.77,
      "fuel_cost_som": 522.61,
      "travel_time_min": 178.2,
      "score": 2.44
    },
    "fastest": { "..." },
    "balanced": { "..." }
  },
  "naive": {
    "distance_km": 166.05,
    "fuel_cost_som": 730.62,
    "travel_time_min": 249.1
  },
  "savings": {
    "money_som": 208.01,
    "time_min": 70.9,
    "distance_km": 47.28,
    "money_pct": 28.5
  },
  "fuel_info": {
    "price_per_liter": 55.0,
    "consumption_per_100km": 8.0
  }
}
```

---

## 🌱 Road Quality Factors

| Quality | Factor | Description |
|---------|--------|-------------|
| `good` | 1.0 | Paved asphalt road |
| `medium` | 1.2 | Partially damaged road |
| `bad` | 1.5 | Dirt or mountain road |

---

## 📧 Email Configuration

The app sends verification emails via Gmail SMTP.

To set up Gmail App Password:
1. Enable 2-Factor Authentication on your Google account
2. Go to `myaccount.google.com/apppasswords`
3. Create a new app password
4. Copy the 16-character password to your `.env` file

---

## 🚀 Production Deployment

For production deployment on Railway or similar platforms:

```bash
pip install gunicorn dj-database-url dj-static
```

## 👩‍💻 Author

**Akylai Topoeva**
Diploma Project — American International University, Kyrgyzstan, 2025

---

## 📄 License

This project is developed for educational purposes as a diploma thesis.
