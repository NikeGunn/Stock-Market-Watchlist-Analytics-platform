# 🚀 Postman API Testing Guide

## 📥 Quick Setup

### 1. Import Files into Postman

**Step A: Import Collection**
1. Open Postman
2. Click "Import" button (top left)
3. Drag & drop `Stock_Watchlist_API.postman_collection.json`
4. Click "Import"

**Step B: Import Environment**
1. Click "Environments" (left sidebar)
2. Click "Import"
3. Drag & drop `Stock_Watchlist_Local.postman_environment.json`
4. Click "Import"
5. **Select "Stock Watchlist - Local" environment** (top right dropdown)

---

## 🎯 Testing Workflow (Follow This Order)

### Step 1: Health Check (No Auth Required)
```
GET /api/v1/health/
```
**Purpose:** Verify system is running  
**Expected:** `{"status": "healthy"}`

---

### Step 2: Login & Get Token
```
POST /api/v1/auth/token/
Body:
{
    "email": "standard@test.com",
    "password": "test123"
}
```
**What Happens:** 
- ✅ Auto-saves `access_token` to environment
- ✅ Auto-saves `refresh_token` to environment
- ✅ All future requests use this token automatically

**Note:** We created sample users with `create_sample_data` command:
- `standard@test.com` / `test123` (Standard tier - 1 watchlist)
- `premium@test.com` / `test123` (Premium tier - 10 watchlists)

---

### Step 3: Get Your Profile
```
GET /api/v1/accounts/users/me/
```
**Purpose:** See your account info  
**Response:**
```json
{
    "data": {
        "id": "uuid",
        "email": "standard@test.com",
        "profile": {
            "account_tier": "STANDARD",
            "max_watchlists": 1
        }
    }
}
```

---

### Step 4: Browse Stocks
```
GET /api/v1/stocks/stocks/
```
**Purpose:** See all available stocks  
**Response:** List of stocks (AAPL, GOOGL, MSFT, TSLA, AMZN)

**Search Example:**
```
GET /api/v1/stocks/stocks/search/?query=AAPL
```

---

### Step 5: Get Latest Price
```
GET /api/v1/pricing/prices/latest/?symbol=AAPL
```
**Purpose:** Get current price (cached for 5 minutes)  
**Response:**
```json
{
    "data": {
        "symbol": "AAPL",
        "price": 185.50,
        "timestamp": "2026-01-01T10:00:00Z"
    }
}
```

---

### Step 6: Create Watchlist
```
POST /api/v1/watchlists/watchlists/
Body:
{
    "name": "My Tech Stocks",
    "description": "Top tech companies"
}
```
**What Happens:**
- ✅ Creates watchlist
- ✅ Auto-saves `watchlist_id` to environment

---

### Step 7: Add Stocks to Watchlist

**Single Stock:**
```
POST /api/v1/watchlists/watchlists/{{watchlist_id}}/add_stock/
Body:
{
    "stock_symbol": "AAPL",
    "notes": "Apple - strong buy"
}
```

**Multiple Stocks:**
```
POST /api/v1/watchlists/watchlists/{{watchlist_id}}/bulk_add/
Body:
{
    "stock_symbols": ["AAPL", "GOOGL", "MSFT", "TSLA"]
}
```

---

### Step 8: View Watchlist with Prices
```
GET /api/v1/watchlists/watchlists/{{watchlist_id}}/
```
**Response:** Watchlist with all stocks and their current prices

---

### Step 9: Create Price Alert
```
POST /api/v1/notifications/alerts/
Body:
{
    "stock_symbol": "AAPL",
    "condition_type": "PRICE_ABOVE",
    "threshold_value": 200.00,
    "one_time": true
}
```
**What Happens:**
- ✅ Creates alert
- ✅ Auto-saves `alert_id` to environment
- ✅ Celery evaluates every 5 minutes
- ✅ Email notification when triggered

**Alert Types:**
- `PRICE_ABOVE` - Alert when price > threshold
- `PRICE_BELOW` - Alert when price < threshold
- `PERCENT_CHANGE` - Alert when price changes by X%

---

### Step 10: Check Notifications
```
GET /api/v1/notifications/notifications/unread/
```
**Purpose:** See triggered alerts

---

## 🔐 Authentication Details

### How JWT Works in This Collection

1. **Login** → Get `access_token` (expires in 1 hour)
2. **Auto-injection** → All requests automatically use Bearer token
3. **Token expires?** → Use "Refresh Token" request
4. **Refresh Token** → Get new `access_token` without re-login

### Collection-Level Auth
```
Authorization: Bearer {{access_token}}
```
This is set at **collection level**, so all requests inherit it automatically.

---

## 📊 Understanding Responses

### Success Response Format
```json
{
    "data": {
        // Your actual data here
    },
    "meta": {
        "message": "Success",
        "timestamp": "2026-01-01T10:00:00Z"
    }
}
```

### Error Response Format
```json
{
    "errors": [
        {
            "field": "email",
            "message": "User with this email already exists"
        }
    ],
    "meta": {
        "status": "error"
    }
}
```

---

## 🎓 Advanced Testing Scenarios

### Scenario 1: Price Monitoring
1. Create watchlist
2. Add stocks (AAPL, GOOGL, MSFT)
3. Create alerts for each stock
4. Check prices: `GET /prices/latest/?symbol=AAPL`
5. Wait 5 minutes (Celery evaluates alerts)
6. Check notifications: `GET /notifications/unread/`

### Scenario 2: Historical Analysis (Premium Only)
```
POST /api/v1/pricing/prices/historical/
Body:
{
    "stock_symbol": "AAPL",
    "start_date": "2024-12-01T00:00:00Z",
    "end_date": "2024-12-31T23:59:59Z"
}
```
**Note:** Standard users get 403 Forbidden

### Scenario 3: Statistics
```
POST /api/v1/pricing/prices/statistics/
Body:
{
    "stock_symbol": "AAPL",
    "start_date": "2024-12-01T00:00:00Z",
    "end_date": "2024-12-31T23:59:59Z"
}
```
**Response:**
```json
{
    "average": 180.50,
    "min": 165.00,
    "max": 195.00,
    "volatility": 8.5
}
```

---

## 🧪 Test Scripts Explained

### Auto-Save Access Token
```javascript
// In "Login - Get JWT Token" request
var jsonData = pm.response.json();
pm.environment.set("access_token", jsonData.access);
pm.environment.set("refresh_token", jsonData.refresh);
```
**What it does:** Saves tokens automatically when you login

### Auto-Save IDs
```javascript
// In "Create Watchlist" request
var jsonData = pm.response.json();
if (jsonData.data && jsonData.data.id) {
    pm.environment.set("watchlist_id", jsonData.data.id);
}
```
**What it does:** Saves watchlist ID for use in other requests

---

## 🔥 Common Issues & Solutions

### Issue 1: "Unauthorized" Error
**Solution:** 
1. Run "Login - Get JWT Token" first
2. Check environment is selected (top right)
3. Verify `{{access_token}}` has a value

### Issue 2: "Stock not found"
**Solution:**
1. Run `docker-compose exec web python manage.py create_sample_data`
2. Or create stocks using "Create Stock (Admin)" endpoint

### Issue 3: "Watchlist limit exceeded"
**Solution:**
- Standard users: Max 1 watchlist
- Premium users: Max 10 watchlists
- Login as `premium@test.com` for more watchlists

### Issue 4: Historical data returns 403
**Solution:**
- Standard users can only access last 30 days
- Premium users have unlimited history
- Login as `premium@test.com` to test

---

## 📱 Testing User Tiers

### Standard User (`standard@test.com`)
- ✅ Create 1 watchlist
- ✅ Add unlimited stocks
- ✅ Create unlimited alerts
- ✅ View last 30 days history
- ❌ Cannot create 2nd watchlist
- ❌ Cannot access old historical data

### Premium User (`premium@test.com`)
- ✅ Create 10 watchlists
- ✅ Add unlimited stocks
- ✅ Create unlimited alerts
- ✅ View unlimited history
- ✅ Access all statistics

---

## 🎯 Interview Tips - Explain Like an Expert

### "How does authentication work?"
**Answer:**
"We use JWT (JSON Web Tokens) for stateless authentication. When a user logs in, they receive an `access_token` (1 hour expiry) and `refresh_token` (7 days). The access token is sent in the Authorization header as `Bearer <token>` for every request. When it expires, the refresh token gets a new access token without re-login. This is more scalable than sessions because tokens are self-contained and don't require server-side storage."

### "How do you handle different user tiers?"
**Answer:**
"We have custom permissions (`IsPremiumOrAdmin`, `CanAccessHistoricalData`) that check the user's `account_tier` field. For example, historical data endpoint checks if user is Premium before allowing access. We also use custom throttling - Standard users get 100 req/hour, Premium gets 1000 req/hour. This is enforced at the view level using DRF's permission classes."

### "How does caching work?"
**Answer:**
"We use Redis for caching latest stock prices with 5-minute TTL. When `/prices/latest/` is called, Django checks Redis first. If cached, returns immediately (fast). If not, queries database and caches the result. This reduces database load by ~80% for frequently accessed data. Cache keys are prefixed with `stockwatchlist:price:{symbol}` for namespacing."

### "How do price alerts work?"
**Answer:**
"Celery Beat runs `evaluate_price_alerts` task every 5 minutes. It fetches all active alerts, gets latest prices, evaluates conditions (PRICE_ABOVE, PRICE_BELOW, PERCENT_CHANGE), and triggers notifications. For one-time alerts, they're automatically deactivated after triggering. Email notifications are sent asynchronously via Celery worker with retry logic (3 attempts with exponential backoff)."

---

## 🚀 Next Steps

1. **Test all endpoints** in order listed above
2. **Try error cases** (wrong password, invalid stock symbol)
3. **Test permissions** (try creating 2 watchlists as Standard user)
4. **Monitor Celery logs** while testing alerts
5. **Check Redis cache** effectiveness

**Pro Tip:** Use Postman's "Tests" tab to write assertions and automate testing!

---

## 📞 Quick Reference - All Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/token/` | No | Login |
| POST | `/auth/token/refresh/` | No | Refresh token |
| GET | `/accounts/users/me/` | Yes | My profile |
| POST | `/accounts/users/` | No | Register |
| GET | `/stocks/stocks/` | Yes | List stocks |
| GET | `/stocks/stocks/search/` | Yes | Search stocks |
| GET | `/pricing/prices/latest/` | Yes | Latest price |
| POST | `/pricing/prices/historical/` | Premium | Historical data |
| POST | `/pricing/prices/statistics/` | Yes | Price stats |
| GET | `/watchlists/watchlists/` | Yes | My watchlists |
| POST | `/watchlists/watchlists/` | Yes | Create watchlist |
| POST | `/watchlists/{id}/add_stock/` | Yes | Add stock |
| POST | `/watchlists/{id}/bulk_add/` | Yes | Add multiple |
| DELETE | `/watchlists/{id}/remove_stock/` | Yes | Remove stock |
| GET | `/notifications/alerts/` | Yes | My alerts |
| POST | `/notifications/alerts/` | Yes | Create alert |
| POST | `/alerts/{id}/activate/` | Yes | Activate alert |
| GET | `/notifications/unread/` | Yes | Unread notifications |
| GET | `/health/` | No | System health |

---

**Happy Testing! 🎉**
