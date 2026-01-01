# 🚀 Quick Reference Cheat Sheet

## Commands You'll Need

### Docker Commands
```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f

# Stop everything
docker-compose down

# Rebuild after code changes
docker-compose up --build

# Run Django commands
docker-compose exec web python manage.py <command>

# Access Django shell
docker-compose exec web python manage.py shell

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Run migrations
docker-compose exec web python manage.py migrate

# Create sample data
docker-compose exec web python manage.py create_sample_data
```

### Testing Commands
```bash
# Run all tests
docker-compose exec web pytest

# Run with coverage
docker-compose exec web pytest --cov=. --cov-report=html

# Run specific app tests
docker-compose exec web pytest accounts/tests.py -v

# Run specific test
docker-compose exec web pytest accounts/tests.py::TestUserAPI::test_register_user
```

### Database Commands
```bash
# Access PostgreSQL
docker-compose exec db psql -U postgres -d stockwatchlist

# Backup database
docker-compose exec db pg_dump -U postgres stockwatchlist > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres stockwatchlist < backup.sql
```

---

## API Endpoints Quick Reference

### Authentication
```bash
# Register
POST /api/v1/accounts/users/
{
  "email": "user@example.com",
  "password": "pass123",
  "password2": "pass123"
}

# Login (Get JWT)
POST /api/v1/auth/token/
{
  "email": "user@example.com",
  "password": "pass123"
}
Response: {"access": "...", "refresh": "..."}

# Refresh Token
POST /api/v1/auth/token/refresh/
{"refresh": "..."}

# Get My Profile
GET /api/v1/accounts/users/me/
Headers: Authorization: Bearer <access_token>
```

### Stocks
```bash
# List stocks
GET /api/v1/stocks/stocks/

# Search stocks
GET /api/v1/stocks/stocks/search/?query=AAPL

# Get stock detail
GET /api/v1/stocks/stocks/{id}/

# Create stock (admin only)
POST /api/v1/stocks/stocks/
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "exchange": "NASDAQ",
  "currency": "USD"
}
```

### Pricing
```bash
# Latest price for stock
GET /api/v1/pricing/prices/latest/?symbol=AAPL

# Historical prices
POST /api/v1/pricing/prices/historical/
{
  "stock_symbol": "AAPL",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z"
}

# Price statistics
POST /api/v1/pricing/prices/statistics/
{
  "stock_symbol": "AAPL",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z"
}
```

### Watchlists
```bash
# List my watchlists
GET /api/v1/watchlists/watchlists/

# Create watchlist
POST /api/v1/watchlists/watchlists/
{"name": "Tech Stocks"}

# Add stock to watchlist
POST /api/v1/watchlists/watchlists/{id}/add_stock/
{"stock_symbol": "AAPL"}

# Bulk add stocks
POST /api/v1/watchlists/watchlists/{id}/bulk_add/
{"stock_symbols": ["AAPL", "GOOGL", "MSFT"]}

# Remove stock
DELETE /api/v1/watchlists/watchlists/{id}/remove_stock/?symbol=AAPL
```

### Alerts & Notifications
```bash
# List my alerts
GET /api/v1/notifications/alerts/

# Create price alert
POST /api/v1/notifications/alerts/
{
  "stock_symbol": "AAPL",
  "condition_type": "PRICE_ABOVE",
  "threshold_value": 200.00,
  "one_time": true
}

# Activate/Deactivate alert
POST /api/v1/notifications/alerts/{id}/activate/
POST /api/v1/notifications/alerts/{id}/deactivate/

# Get unread notifications
GET /api/v1/notifications/notifications/unread/

# Mark notifications as read
POST /api/v1/notifications/notifications/mark_read/
{"notification_ids": ["uuid1", "uuid2"]}
```

---

## Common Debugging

### Container not starting?
```bash
# Check logs
docker-compose logs web

# Check if ports are in use
netstat -ano | findstr :8000
netstat -ano | findstr :5432

# Kill process on port
taskkill /PID <pid> /F
```

### Database connection errors?
```bash
# Check if DB is running
docker-compose ps

# Wait for DB to be ready
docker-compose exec db pg_isready

# Check DB connection from Django
docker-compose exec web python manage.py dbshell
```

### Celery not working?
```bash
# Check Celery logs
docker-compose logs celery_worker
docker-compose logs celery_beat

# Check Redis
docker-compose exec redis redis-cli ping
```

### Migration issues?
```bash
# Show migrations
docker-compose exec web python manage.py showmigrations

# Make migrations
docker-compose exec web python manage.py makemigrations

# Fake migration (if needed)
docker-compose exec web python manage.py migrate --fake appname

# Reset database (CAREFUL!)
docker-compose down -v  # Deletes volumes
docker-compose up -d
docker-compose exec web python manage.py migrate
```

---

## Environment Variables

```env
# Required
SECRET_KEY=change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=stockwatchlist
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Get free key: https://www.alphavantage.co/support/#api-key
ALPHA_VANTAGE_API_KEY=your_key_here

# Email (optional for testing)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

---

## Key Files & Their Purpose

```
├── config/settings.py          # All Django settings
├── config/celery.py            # Celery config & scheduled tasks
├── config/urls.py              # URL routing
├── config/middleware.py        # Request logging, correlation IDs
├── config/exceptions.py        # Error handling
├── config/permissions.py       # Reusable permissions
│
├── accounts/models.py          # User & Profile models
├── accounts/serializers.py     # User serialization
├── accounts/views.py           # User endpoints
├── accounts/permissions.py     # Custom permissions
│
├── stocks/models.py            # Stock master data
├── pricing/models.py           # Time-series price data
├── watchlists/models.py        # User watchlists
├── notifications/models.py     # Alerts & notifications
│
├── pricing/tasks.py            # Background price fetching
├── notifications/tasks.py      # Alert evaluation & emails
│
├── docker-compose.yml          # Container orchestration
├── Dockerfile                  # Python app container
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
└── README.md                   # Project documentation
```

---

## Testing Account Credentials

After running `python manage.py create_sample_data`:

```
Standard User:
- Email: standard@test.com
- Password: test123
- Tier: Standard (1 watchlist, 30-day history)

Premium User:
- Email: premium@test.com
- Password: test123
- Tier: Premium (10 watchlists, unlimited history)
```

---

## URLs to Remember

- **API Root:** http://localhost:8000/api/v1/
- **Admin Panel:** http://localhost:8000/admin/
- **API Docs (Swagger):** http://localhost:8000/api/docs/
- **API Schema (OpenAPI):** http://localhost:8000/api/schema/
- **Health Check:** http://localhost:8000/api/v1/health/

---

## Interview Quick Answers

**"What's the main tech stack?"**
Django 4.2, DRF, PostgreSQL, Redis, Celery, Docker

**"How many users can it handle?"**
Current: ~10K concurrent. With scaling: 1M+ (horizontal scaling, caching, read replicas)

**"What's the hardest part you built?"**
The alert system with async evaluation, retryable email delivery, and tier-based access control

**"How do you ensure security?"**
JWT auth, RBAC, input validation, rate limiting, CSRF/XSS protection, env-based secrets

**"How long did this take?"**
[Be honest about your time]

**"What would you improve?"**
WebSockets for real-time prices, GraphQL for flexible queries, microservices for scale

---

## Pro Tips

1. **Always check logs first:** `docker-compose logs -f`
2. **Use the API docs:** http://localhost:8000/api/docs/
3. **Test with Postman/Thunder Client** (VS Code extension)
4. **Check health endpoint** before debugging: http://localhost:8000/api/v1/health/
5. **Use sample data** for quick testing: `python manage.py create_sample_data`

---

**Good luck with your interview! 🎉**
