"""
Quick script to test notification generation.

Run: docker-compose exec web python test_notifications.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from stocks.models import Stock
from pricing.models import StockPrice
from notifications.models import PriceAlert, Notification
from decimal import Decimal
from django.utils import timezone

print("\n" + "="*60)
print("📬 NOTIFICATION SYSTEM TEST")
print("="*60 + "\n")

# Get or create test user
user, _ = User.objects.get_or_create(
    email='standard@test.com',
    defaults={'first_name': 'Standard', 'last_name': 'User'}
)
if not user.check_password('test123'):
    user.set_password('test123')
    user.save()

print(f"✓ User: {user.email}")

# Get AAPL stock
try:
    stock = Stock.objects.get(symbol='AAPL')
    print(f"✓ Stock: {stock.symbol} - {stock.name}")
except Stock.DoesNotExist:
    print("✗ AAPL stock not found. Run create_sample_data first.")
    exit(1)

# Check latest price
latest_price = StockPrice.objects.latest_price(stock)
if latest_price:
    print(f"✓ Latest price: ${latest_price.price} (at {latest_price.timestamp})")
    current_price = float(latest_price.price)
else:
    print("✗ No price data available. Creating sample price...")
    latest_price = StockPrice.objects.create(
        stock=stock,
        price=Decimal('175.50'),
        volume=1000000,
        timestamp=timezone.now()
    )
    current_price = 175.50
    print(f"✓ Created sample price: ${current_price}")

print("\n" + "-"*60)
print("CREATING TEST ALERTS")
print("-"*60 + "\n")

# Create alert that will trigger immediately
alert1 = PriceAlert.objects.create(
    user=user,
    stock=stock,
    condition_type='PRICE_BELOW',
    threshold_value=Decimal(str(current_price + 10)),  # Above current price
    one_time=True,
    is_active=True
)
print(f"✓ Created PRICE_BELOW alert (threshold: ${alert1.threshold_value})")
print(f"  → Will trigger because ${current_price} < ${alert1.threshold_value}")

# Create alert that won't trigger
alert2 = PriceAlert.objects.create(
    user=user,
    stock=stock,
    condition_type='PRICE_ABOVE',
    threshold_value=Decimal(str(current_price + 100)),  # Way above current price
    one_time=True,
    is_active=True
)
print(f"\n✓ Created PRICE_ABOVE alert (threshold: ${alert2.threshold_value})")
print(f"  → Won't trigger because ${current_price} < ${alert2.threshold_value}")

print("\n" + "-"*60)
print("RUNNING ALERT EVALUATION")
print("-"*60 + "\n")

# Run alert evaluation manually
from notifications.tasks import evaluate_price_alerts
result = evaluate_price_alerts()

print(f"✓ Evaluated: {result['evaluated']} alerts")
print(f"✓ Triggered: {result['triggered']} alerts")

print("\n" + "-"*60)
print("CHECKING NOTIFICATIONS")
print("-"*60 + "\n")

notifications = Notification.objects.filter(user=user).order_by('-created_at')
print(f"Total notifications: {notifications.count()}\n")

for i, notif in enumerate(notifications[:5], 1):
    print(f"{i}. {notif.subject}")
    print(f"   Status: {notif.status}")
    print(f"   Type: {notif.notification_type}")
    print(f"   Created: {notif.created_at}")
    if notif.alert:
        print(f"   Alert: {notif.alert.stock.symbol} {notif.alert.condition_type}")
    print(f"   Read: {'Yes' if notif.read_at else 'No'}")
    print()

print("-"*60)
print("ALERT STATUS")
print("-"*60 + "\n")

alerts = PriceAlert.objects.filter(user=user).order_by('-created_at')
for alert in alerts[:5]:
    status = "🔴 Triggered" if alert.triggered_at else "🟢 Active"
    print(f"{status} | {alert.stock.symbol} | {alert.get_condition_type_display()}")
    print(f"  Threshold: ${alert.threshold_value}")
    print(f"  Active: {alert.is_active}")
    if alert.triggered_at:
        print(f"  Triggered at: {alert.triggered_at}")
    print()

print("\n" + "="*60)
print("✅ TEST COMPLETE!")
print("="*60 + "\n")

print("📋 Next Steps:")
print("1. Check notifications API: GET /api/v1/notifications/notifications/")
print("2. View unread: GET /api/v1/notifications/notifications/unread/")
print("3. Mark as read: POST /api/v1/notifications/notifications/mark_read/")
print("\n💡 Celery Beat runs automatically every 5 minutes!")
print("   You can wait or manually trigger with:")
print("   docker-compose exec celery_worker celery -A config call notifications.tasks.evaluate_price_alerts")
print()
