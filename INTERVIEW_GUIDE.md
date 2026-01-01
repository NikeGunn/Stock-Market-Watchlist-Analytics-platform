# 🎓 INTERVIEW PREPARATION GUIDE
## Understanding Your Stock Watchlist API

This document explains everything you need to know to confidently discuss this project in your interview.

---

## 📖 Table of Contents
1. [High-Level Overview](#high-level-overview)
2. [Key Concepts Explained](#key-concepts-explained)
3. [Architecture Decisions](#architecture-decisions)
4. [Common Interview Questions & Answers](#common-interview-questions--answers)
5. [Code Walkthrough](#code-walkthrough)
6. [Best Practices Applied](#best-practices-applied)

---

## 🎯 High-Level Overview

### What Does This System Do?

Imagine you're interested in stocks like Apple, Google, Tesla. This system lets you:

1. **Track Stocks**: Create watchlists (like playlists for stocks)
2. **Get Prices**: See current and historical stock prices
3. **Set Alerts**: Get notified when AAPL hits $200
4. **Analytics**: See min/max/average prices over time

### Who Uses It?

- **Standard Users**: Free tier, basic features
- **Premium Users**: Pay for more watchlists and historical data
- **Admins**: Manage the system, add new stocks

---

## 💡 Key Concepts Explained

### 1. **Django vs Flask: Why Django?**

**Simple Answer:**
"Django is like a complete toolkit that comes with batteries included. It has built-in admin panel, authentication, ORM, etc. Flask is minimalist - you build everything yourself."

**When to use each:**
- Django: Large projects, need admin panel, built-in features
- Flask: Microservices, APIs only, maximum flexibility

### 2. **REST API: What is it?**

**Think of it like a restaurant menu:**
- Menu (API Documentation) lists what you can order
- You make requests (GET, POST, PUT, DELETE)
- Kitchen (Backend) processes your order
- You get responses (JSON data)

**Example:**
```
GET /api/v1/stocks/AAPL/     → "Get me Apple stock info"
POST /api/v1/watchlists/     → "Create a new watchlist"
```

### 3. **JWT Authentication: How does it work?**

**Simple Analogy: Concert Wristband**

1. You show ID at entrance (login with email/password)
2. They give you a wristband (JWT token)
3. You show wristband to access different areas (API requests)
4. Wristband expires after concert (token expires after 1 hour)

**In code:**
```python
# User logs in
POST /api/v1/auth/token/
{
  "email": "user@example.com",
  "password": "password"
}

# Gets token
Response: {
  "access": "eyJhbGciOiJIUzI1...",  # The wristband
  "refresh": "eyJhbGciOiJIUzI1..."   # Get new wristband
}

# Use token in requests
Headers: {
  "Authorization": "Bearer eyJhbGciOiJIUzI1..."
}
```

### 4. **Celery: Why background tasks?**

**Problem:** 
Fetching stock prices from external API takes 5 seconds. If user requests it, they wait 5 seconds. Bad UX!

**Solution: Celery**
```python
# Instead of this (blocks for 5 seconds):
def get_stock_price(symbol):
    data = fetch_from_api(symbol)  # Takes 5 seconds
    return data

# Do this (returns immediately):
@celery.task
def fetch_stock_price(symbol):
    data = fetch_from_api(symbol)  # Runs in background
    save_to_database(data)

# User's request:
fetch_stock_price.delay('AAPL')  # Returns immediately
# Celery worker does the heavy lifting in the background
```

**Real-world uses:**
- Sending emails (slow)
- Processing images (CPU intensive)
- Generating reports (long-running)
- Scheduled tasks (every 15 minutes)

### 5. **Redis: Why do we need it?**

**Redis is like a super-fast notepad in RAM**

**Problem:**
```python
# Getting latest price from database: 50ms
latest_price = StockPrice.objects.filter(stock=aapl).latest()
```

**Solution with Redis:**
```python
# Check Redis first: 2ms
cached = cache.get('latest_price:AAPL')
if cached:
    return cached  # Super fast!

# If not in cache, get from DB and cache it
latest_price = StockPrice.objects.filter(stock=aapl).latest()
cache.set('latest_price:AAPL', latest_price, 300)  # Cache for 5 min
```

**Speed difference:**
- Database: 50ms
- Redis: 2ms
- **25x faster!**

### 6. **Docker: Why containerize?**

**Problem: "It works on my machine!"**

Your computer:
- Python 3.11
- PostgreSQL 14
- Redis 6

Interviewer's computer:
- Python 3.9
- PostgreSQL 12
- No Redis

**Solution: Docker**
Docker is like a shipping container. Everything inside works the same way, regardless of the ship (computer) it's on.

```yaml
# docker-compose.yml defines all containers
services:
  web:        # Django app
  db:         # PostgreSQL
  redis:      # Redis
  celery:     # Background worker
```

**One command runs everything:**
```bash
docker-compose up
```

---

## 🏗️ Architecture Decisions

### 1. **Why separate Stock and StockPrice models?**

**Bad Design (Single Table):**
```python
class Stock(models.Model):
    symbol = models.CharField()
    name = models.CharField()
    current_price = models.DecimalField()  # Changes every minute!
    price_history = models.JSONField()  # Gets huge!
```

**Good Design (Separate Tables):**
```python
# Rarely changes
class Stock(models.Model):
    symbol = models.CharField()
    name = models.CharField()

# Changes every minute, millions of records
class StockPrice(models.Model):
    stock = models.ForeignKey(Stock)
    price = models.DecimalField()
    timestamp = models.DateTimeField()
```

**Why?**
- Stock info changes rarely → Small table, fast queries
- Price data grows constantly → Can partition, archive, optimize separately
- Different access patterns → Can use different databases later

### 2. **Why Cursor Pagination instead of Page Number?**

**Page Number Pagination:**
```python
# Page 1: Items 1-20
# Page 2: Items 21-40  ← But what if new item added to page 1?
# Page 2 now shows: Items 22-41 (duplicates item 21!)
```

**Cursor Pagination:**
```python
# Uses timestamp or ID as cursor
# Next page: "Give me 20 items after timestamp X"
# New items don't affect results!
```

**Trade-off:**
- ✅ Consistent results
- ✅ Fast (uses index)
- ❌ Can't jump to page 100

### 3. **Why Role-Based Access Control (RBAC)?**

**Without RBAC:**
```python
# Every view needs checks
if user.is_premium:
    # Show advanced features
elif user.is_admin:
    # Show admin features
else:
    # Show basic features
```

**With RBAC:**
```python
# Define once
class IsPremiumUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.profile.account_tier == 'PREMIUM'

# Use everywhere
class HistoricalDataView(APIView):
    permission_classes = [IsPremiumUser]  # Done!
```

**Benefits:**
- DRY (Don't Repeat Yourself)
- Centralized security logic
- Easy to audit
- Easy to change

---

## 🤔 Common Interview Questions & Answers

### Q1: "Explain the flow when a user creates a watchlist"

**Answer:**

```
1. User sends POST request to /api/v1/watchlists/
   Headers: Authorization: Bearer <token>
   Body: { "name": "Tech Stocks" }

2. Django middleware checks JWT token
   ↓
3. DRF calls WatchlistSerializer
   - Validates data
   - Checks if user can create watchlists (tier limits)
   ↓
4. Serializer creates Watchlist object
   - Sets user from request context (security!)
   - Saves to PostgreSQL
   ↓
5. Django signals fire (post_save)
   - Could trigger welcome email
   - Could log to analytics
   ↓
6. Response sent back
   {
     "data": { "id": "uuid", "name": "Tech Stocks" },
     "meta": { "message": "Watchlist created" },
     "errors": []
   }
```

### Q2: "How do you ensure data consistency?"

**Answer:**

1. **Database Constraints:**
```python
class Meta:
    constraints = [
        UniqueConstraint(
            fields=['watchlist', 'stock'],
            name='no_duplicate_stocks'
        )
    ]
```

2. **Transactions:**
```python
@transaction.atomic  # All-or-nothing
def bulk_add_stocks(stocks):
    for stock in stocks:
        WatchlistItem.objects.create(...)
    # If any fails, ALL are rolled back
```

3. **Serializer Validation:**
```python
def validate(self, attrs):
    if attrs['price_above'] <= attrs['price_below']:
        raise ValidationError("Logic error!")
    return attrs
```

### Q3: "How would you scale this to 1 million users?"

**Answer:**

**Current State:**
- Single Django instance
- One PostgreSQL database
- One Redis instance

**Scaling Strategy:**

1. **Horizontal Scaling (More Servers):**
```
Load Balancer
    ↓
┌─────┬─────┬─────┐
│ Web │ Web │ Web │  3 Django instances
└─────┴─────┴─────┘
    ↓
PostgreSQL (Primary)
    ↓
Read Replicas (3)  ← Separate DB for reads
```

2. **Database Optimizations:**
- Partition `stock_prices` table by date
- Add more indexes
- Connection pooling (PgBouncer)

3. **Caching:**
- Cache hot data in Redis
- CDN for static files
- Cache at multiple layers

4. **Async Everything:**
- All heavy tasks in Celery
- Message queue (RabbitMQ)
- Event-driven architecture

5. **Monitoring:**
- Prometheus for metrics
- Grafana for dashboards
- Sentry for errors
- ELK for logs

### Q4: "Explain a security vulnerability and how you prevented it"

**Answer:**

**SQL Injection:**

**Vulnerable code (DON'T DO THIS):**
```python
# User input directly in SQL
symbol = request.GET['symbol']
query = f"SELECT * FROM stocks WHERE symbol = '{symbol}'"
# Attacker sends: symbol = "'; DROP TABLE stocks; --"
```

**How we prevent:**
```python
# Django ORM escapes all parameters
Stock.objects.filter(symbol=symbol)
# Even if symbol = "'; DROP TABLE", it's treated as text
```

**Other protections:**

1. **CSRF:** Django's CSRF middleware
2. **XSS:** Template auto-escaping
3. **Rate Limiting:** Throttling per user tier
4. **Authentication:** JWT with short expiry
5. **Permissions:** RBAC at every endpoint

### Q5: "Walk me through how alerts work"

**Answer:**

```
1. User creates alert:
   POST /api/v1/notifications/alerts/
   {
     "stock_symbol": "AAPL",
     "condition_type": "PRICE_ABOVE",
     "threshold_value": 200.00
   }

2. Alert saved to database (is_active=True)

3. Every 5 minutes, Celery Beat triggers evaluate_price_alerts()
   
4. For each active alert:
   a. Get latest stock price
   b. Check: current_price > threshold?
   c. If YES:
      - Mark alert as triggered
      - Create Notification record
      - Send email (async task)

5. Email task (retryable):
   - Tries to send email
   - If fails → retry up to 3 times
   - Updates notification status
```

---

## 👨‍💻 Code Walkthrough

### Example 1: Custom Manager (Reusable Queries)

```python
class StockManager(models.Manager):
    def active(self):
        """Get only active stocks"""
        return self.filter(is_active=True)
    
    def by_exchange(self, exchange):
        """Get stocks by exchange"""
        return self.active().filter(exchange=exchange)

# Usage
Stock.objects.active()  # Clean!
Stock.objects.by_exchange('NASDAQ')  # Reusable!

# Instead of:
Stock.objects.filter(is_active=True)  # Repetitive everywhere
```

### Example 2: Serializer Validation

```python
class WatchlistSerializer(serializers.ModelSerializer):
    def validate_name(self, value):
        """Ensure unique name per user"""
        if Watchlist.objects.filter(
            user=self.context['request'].user,
            name=value
        ).exists():
            raise ValidationError("Name already exists!")
        return value
```

### Example 3: Custom Permission

```python
class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user.is_staff:
            return True
        
        # Owner can access their own
        return obj.user == request.user

# Usage in view
class WatchlistViewSet(ModelViewSet):
    permission_classes = [IsOwnerOrAdmin]
```

---

## ✅ Best Practices Applied

### 1. **DRY (Don't Repeat Yourself)**

**Bad:**
```python
# In 10 different views:
if not request.user.profile.account_tier == 'PREMIUM':
    return Response({'error': 'Premium required'})
```

**Good:**
```python
# Define once
class IsPremiumUser(BasePermission):
    ...

# Use everywhere
permission_classes = [IsPremiumUser]
```

### 2. **Separation of Concerns**

Each component has ONE job:
- **Models:** Data structure and business logic
- **Serializers:** Validation and transformation
- **Views:** HTTP request/response handling
- **Permissions:** Access control
- **Tasks:** Background processing

### 3. **Explicit is Better Than Implicit**

```python
# Bad (magic)
def create(self, validated_data):
    return super().create(validated_data)  # Where does user come from?

# Good (explicit)
def create(self, validated_data):
    validated_data['user'] = self.context['request'].user
    return super().create(validated_data)  # Clear!
```

### 4. **Fail Fast**

```python
def create_alert(self, stock_symbol):
    # Validate BEFORE doing work
    if not StockPrice.objects.filter(stock__symbol=stock_symbol).exists():
        raise ValidationError("No price data available")
    
    # Now do the work
    alert = PriceAlert.objects.create(...)
```

### 5. **Defensive Programming**

```python
try:
    send_email(user.email, message)
except Exception as e:
    logger.error(f"Email failed: {e}")
    # Don't crash entire system if email fails
```

---

## 🎤 How to Present This Project

### Opening Statement:

*"I built a production-grade stock market watchlist API that demonstrates scalable architecture, security best practices, and real-world async processing. The system handles multi-tier user access, real-time price tracking via external APIs, and intelligent alerting with email notifications."*

### Key Highlights:

1. **Architecture:** "I used Django REST Framework with separate apps for concerns, making it modular and maintainable."

2. **Scalability:** "Implemented Redis caching, Celery for async tasks, and cursor pagination for large datasets."

3. **Security:** "JWT authentication, role-based permissions, rate limiting, and comprehensive input validation."

4. **Testing:** "80%+ test coverage using pytest with unit, integration, and API tests."

5. **Production-Ready:** "Fully Dockerized, health checks, structured logging, and error handling."

### When Asked "Why Django?"

*"Django provides a robust foundation with built-in security, admin panel, and ORM. For a system handling financial data and user accounts, I wanted battle-tested components rather than building everything from scratch. The trade-off is less flexibility than microframeworks, but the security and built-in features were worth it."*

---

## 📝 Final Tips

1. **Don't memorize code:** Understand CONCEPTS
2. **Be honest:** "I chose this approach because X, but in production I'd also consider Y"
3. **Show trade-offs:** Every decision has pros and cons
4. **Ask questions:** "What scale are we talking about?"
5. **Connect to real world:** "This is like how Netflix/Amazon does X"

---

**Remember:** You built this. You understand it. Be confident! 🚀
