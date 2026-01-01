# 📬 How Notifications Work - Complete Guide

## 🎯 Overview

Notifications are **automatically generated** when price alerts are triggered. The system uses **Celery Beat** (scheduled tasks) to periodically check price alerts and create notifications when conditions are met.

---

## 🔄 Notification Flow (Step-by-Step)

```
1. User Creates Alert
   ↓
2. Celery Beat runs every 5 minutes
   ↓
3. evaluate_price_alerts() task runs
   ↓
4. Checks all active alerts against latest stock prices
   ↓
5. If condition met → Creates Notification + Sends Email
   ↓
6. Marks alert as triggered (if one_time=True)
```

---

## 📊 Current System Status

**Celery Beat Schedule** (configured in `config/celery.py`):

| Task | Schedule | Purpose |
|------|----------|---------|
| `fetch_stock_prices` | Every 15 minutes | Gets latest prices from Alpha Vantage API |
| `evaluate_price_alerts` | Every 5 minutes | Checks alerts and creates notifications |
| `cleanup_old_prices` | Daily at 2 AM | Removes old price data |

---

## 🧪 How to Generate Notifications (Testing)

### Method 1: Create Alert That Will Trigger Immediately

**Step 1:** Get current stock price
```http
GET {{base_url}}/api/v1/pricing/prices/latest/?symbol=AAPL
Authorization: Bearer {{access_token}}
```

**Example Response:**
```json
{
    "stock": "AAPL",
    "price": "175.5000",  ← Current price
    "timestamp": "2026-01-01T10:00:00Z"
}
```

**Step 2:** Create alert with threshold BELOW current price
```http
POST {{base_url}}/api/v1/notifications/alerts/
Authorization: Bearer {{access_token}}

{
    "stock_symbol": "AAPL",
    "condition_type": "PRICE_BELOW",
    "threshold_value": 180.00,  ← Higher than current (175.50)
    "one_time": true
}
```

**Result:** Alert is already triggered! When Celery Beat runs next (within 5 minutes), it will create a notification.

---

### Method 2: Manually Trigger Alert Evaluation (Instant)

You can manually run the Celery task to generate notifications immediately:

```powershell
# Run the alert evaluation task NOW (don't wait 5 minutes)
docker-compose exec celery_worker celery -A config call notifications.tasks.evaluate_price_alerts
```

**What happens:**
1. Checks all active alerts
2. Compares with latest stock prices
3. Creates notifications for triggered alerts
4. Sends emails (if EMAIL backend is configured)

---

### Method 3: Create Alert for Future Trigger

**Scenario:** You want notification when AAPL goes above $200

```http
POST {{base_url}}/api/v1/notifications/alerts/
Authorization: Bearer {{access_token}}

{
    "stock_symbol": "AAPL",
    "condition_type": "PRICE_ABOVE",
    "threshold_value": 200.00,
    "one_time": true
}
```

**When will notification be created?**
- Celery Beat fetches new prices every 15 minutes
- Celery Beat checks alerts every 5 minutes
- When AAPL price goes above $200, notification is created automatically

---

## 📧 Notification Details

### What Gets Created?

**1. Notification Database Record:**
```json
{
    "id": "uuid",
    "user": "user-id",
    "alert": "alert-id",
    "notification_type": "PRICE_ALERT",
    "channel": "EMAIL",
    "subject": "Price Alert: AAPL",
    "message": "Your price alert for Apple Inc. (AAPL) has been triggered!...",
    "status": "SENT",  // or PENDING/FAILED
    "sent_at": "2026-01-01T10:05:00Z",
    "read_at": null,
    "created_at": "2026-01-01T10:05:00Z"
}
```

**2. Email Notification:**
```
Subject: Price Alert: AAPL

Your price alert for Apple Inc. (AAPL) has been triggered!

Alert Condition: Price Above
Threshold: $200.00
Current Price: $205.50

View your watchlist: http://localhost:3000/watchlist/

Best regards,
Stock Watchlist Team
```

---

## 🔍 Check Your Notifications

### Get All Notifications
```http
GET {{base_url}}/api/v1/notifications/notifications/
Authorization: Bearer {{access_token}}
```

### Get Unread Notifications
```http
GET {{base_url}}/api/v1/notifications/notifications/unread/
Authorization: Bearer {{access_token}}
```

### Mark Notifications as Read
```http
POST {{base_url}}/api/v1/notifications/notifications/mark_read/
Authorization: Bearer {{access_token}}

{
    "notification_ids": ["uuid1", "uuid2"]
}
```

---

## 🛠️ Quick Test Workflow

**Complete test to generate a notification in 5 minutes:**

```http
### Step 1: Login
POST {{base_url}}/api/v1/auth/token/
Content-Type: application/json

{
    "email": "standard@test.com",
    "password": "test123"
}

### Step 2: Get current AAPL price
GET {{base_url}}/api/v1/pricing/prices/latest/?symbol=AAPL
Authorization: Bearer {{access_token}}

### Step 3: Create alert (set threshold BELOW current price)
POST {{base_url}}/api/v1/notifications/alerts/
Authorization: Bearer {{access_token}}

{
    "stock_symbol": "AAPL",
    "condition_type": "PRICE_BELOW",
    "threshold_value": 999.00,
    "one_time": true
}

### Step 4a: Wait 5 minutes for Celery Beat
# OR

### Step 4b: Manually trigger NOW
# Run in terminal:
docker-compose exec celery_worker celery -A config call notifications.tasks.evaluate_price_alerts

### Step 5: Check notifications
GET {{base_url}}/api/v1/notifications/notifications/
Authorization: Bearer {{access_token}}
```

---

## 🐛 Troubleshooting

### No Notifications Generated?

**1. Check Celery Beat is Running:**
```powershell
docker-compose ps
# celery_beat should show "Up"
```

**2. Check Celery Beat Logs:**
```powershell
docker-compose logs celery_beat --tail=50
```

**3. Check Celery Worker Logs:**
```powershell
docker-compose logs celery_worker --tail=50
```

**4. Check if Alerts Exist:**
```http
GET {{base_url}}/api/v1/notifications/alerts/
Authorization: Bearer {{access_token}}
```

**5. Manually Run Task:**
```powershell
# See if task runs without errors
docker-compose exec celery_worker celery -A config call notifications.tasks.evaluate_price_alerts
```

---

## 📋 Alert Types Explained

### 1. PRICE_ABOVE
**Trigger:** When stock price goes **above** threshold

**Example:**
```json
{
    "stock_symbol": "AAPL",
    "condition_type": "PRICE_ABOVE",
    "threshold_value": 200.00
}
```
**Triggers when:** AAPL price > $200.00

---

### 2. PRICE_BELOW
**Trigger:** When stock price goes **below** threshold

**Example:**
```json
{
    "stock_symbol": "TSLA",
    "condition_type": "PRICE_BELOW",
    "threshold_value": 150.00
}
```
**Triggers when:** TSLA price < $150.00

---

### 3. PERCENT_CHANGE
**Trigger:** When price changes by X% (currently not implemented - placeholder)

**Example:**
```json
{
    "stock_symbol": "GOOGL",
    "condition_type": "PERCENT_CHANGE",
    "threshold_value": 5.00
}
```
**Would trigger when:** GOOGL changes ±5% from previous close

---

## ⚙️ How It Works Internally

### 1. Celery Beat Scheduler
**File:** `config/celery.py`

```python
app.conf.beat_schedule = {
    'evaluate-price-alerts-every-5-minutes': {
        'task': 'notifications.tasks.evaluate_price_alerts',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    }
}
```

**What it does:** Runs `evaluate_price_alerts()` automatically every 5 minutes

---

### 2. Alert Evaluation Task
**File:** `notifications/tasks.py`

```python
@shared_task
def evaluate_price_alerts():
    # 1. Get all active alerts that haven't triggered yet
    alerts = PriceAlert.objects.active_alerts()
    
    for alert in alerts:
        # 2. Get latest stock price
        latest_price = StockPrice.objects.latest_price(alert.stock)
        
        # 3. Check if condition is met
        if alert.check_condition(latest_price):
            # 4. Mark alert as triggered
            alert.trigger()
            
            # 5. Create notification (separate task)
            send_price_alert_notification.delay(alert.id, latest_price.price)
```

**Key Points:**
- Only checks **active** alerts (`is_active=True`)
- Only checks **non-triggered** alerts (`triggered_at=NULL`)
- Updates `last_checked_at` timestamp for each alert
- If `one_time=True`, alert is deactivated after triggering

---

### 3. Notification Sending Task
**File:** `notifications/tasks.py`

```python
@shared_task(bind=True, max_retries=3)
def send_price_alert_notification(self, alert_id, current_price):
    # 1. Create Notification record
    notification = Notification.objects.create(
        user=alert.user,
        alert=alert,
        notification_type='PRICE_ALERT',
        channel='EMAIL',
        subject=f'Price Alert: {alert.stock.symbol}',
        message='...',
        status='PENDING'
    )
    
    # 2. Send email
    send_mail(subject, message, from_email, [user.email])
    
    # 3. Mark as sent
    notification.mark_as_sent()
```

**Key Points:**
- **Retries:** Up to 3 times if email fails
- **Separate task:** Doesn't block alert evaluation
- **Audit trail:** Creates database record before sending

---

## 🎓 Interview Explanation

**Q: "How does your notification system work?"**

**Answer:**

*"The notification system uses a combination of Celery Beat (scheduler) and Celery Workers (task processors) to create a reliable, asynchronous alert system.*

*Here's the flow:*

1. **User creates a price alert** - They specify a stock symbol, condition (price above/below), and threshold value

2. **Celery Beat runs every 5 minutes** - This is a scheduler that triggers the `evaluate_price_alerts` task

3. **Alert evaluation** - The task:
   - Fetches all active, non-triggered alerts
   - Gets latest price for each stock
   - Compares current price with alert threshold
   - If condition is met, marks alert as triggered

4. **Notification creation** - When triggered:
   - Creates a Notification database record (audit trail)
   - Sends email notification asynchronously (separate task)
   - Marks alert as inactive if it's one-time

5. **User retrieves notifications** - Through API endpoints they can:
   - List all notifications
   - Filter by read/unread status
   - Mark notifications as read

*Key design decisions:*

- **Separation of concerns:** Alert evaluation and email sending are separate tasks. If email fails, we can retry without re-evaluating alerts.

- **Retry mechanism:** Email sending has 3 retry attempts with exponential backoff (60 seconds between retries)

- **Database records:** Every notification is stored even if email fails, providing a complete audit trail

- **Performance:** Uses `select_related()` to minimize database queries and indexes for fast lookups

- **User control:** Alerts can be one-time or recurring, activated/deactivated via API"

---

## 📚 Related Files

| File | Purpose |
|------|---------|
| `notifications/models.py` | PriceAlert & Notification models |
| `notifications/tasks.py` | Celery tasks for evaluation & sending |
| `notifications/views.py` | API endpoints |
| `config/celery.py` | Celery Beat schedule configuration |
| `config/settings.py` | Email backend configuration |

---

## 🚀 Next Steps

1. **Test the system:**
   - Create an alert with threshold you know will trigger
   - Wait 5 minutes OR manually run the task
   - Check notifications endpoint

2. **Configure email (optional):**
   - Update `EMAIL_BACKEND` in settings.py to use real SMTP
   - Add `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER` credentials
   - Test with real email delivery

3. **Monitor in production:**
   - Use Celery Flower for task monitoring: `pip install flower`
   - Run: `celery -A config flower`
   - Access dashboard at http://localhost:5555

4. **Scale if needed:**
   - Add more Celery workers: `docker-compose up --scale celery_worker=3`
   - Use Redis as result backend for better performance
   - Add webhook channels for Slack/Discord notifications

---

## ✅ Summary

**Notifications are created automatically when:**
- Celery Beat runs `evaluate_price_alerts` every 5 minutes
- A price alert's condition is met (price above/below threshold)
- Current stock price matches the alert criteria

**To test immediately:**
```powershell
docker-compose exec celery_worker celery -A config call notifications.tasks.evaluate_price_alerts
```

**To view notifications:**
```http
GET {{base_url}}/api/v1/notifications/notifications/
```

---

**Need help?** Check the logs:
```powershell
docker-compose logs celery_beat --tail=100
docker-compose logs celery_worker --tail=100
```
