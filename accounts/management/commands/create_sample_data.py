"""
Management command to create sample data for testing.

Usage: python manage.py create_sample_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from stocks.models import Stock
from pricing.models import StockPrice
from watchlists.models import Watchlist, WatchlistItem
from notifications.models import PriceAlert
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates sample data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')

        # Create users
        self.stdout.write('Creating users...')
        
        standard_user, created = User.objects.get_or_create(
            email='standard@test.com',
            defaults={'first_name': 'Standard', 'last_name': 'User'}
        )
        if created:
            standard_user.set_password('test123')
            standard_user.save()
            self.stdout.write(self.style.SUCCESS('✓ Standard user created'))

        premium_user, created = User.objects.get_or_create(
            email='premium@test.com',
            defaults={'first_name': 'Premium', 'last_name': 'User'}
        )
        if created:
            premium_user.set_password('test123')
            premium_user.profile.account_tier = 'PREMIUM'
            premium_user.profile.save()
            premium_user.save()
            self.stdout.write(self.style.SUCCESS('✓ Premium user created'))

        # Create stocks
        self.stdout.write('Creating stocks...')
        
        stocks_data = [
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'exchange': 'NASDAQ', 'currency': 'USD'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'exchange': 'NASDAQ', 'currency': 'USD'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'exchange': 'NASDAQ', 'currency': 'USD'},
            {'symbol': 'TSLA', 'name': 'Tesla, Inc.', 'exchange': 'NASDAQ', 'currency': 'USD'},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'exchange': 'NASDAQ', 'currency': 'USD'},
        ]

        stocks = []
        for stock_data in stocks_data:
            stock, created = Stock.objects.get_or_create(**stock_data)
            stocks.append(stock)
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Stock created: {stock.symbol}'))

        # Create sample prices
        self.stdout.write('Creating sample prices...')
        
        base_prices = {
            'AAPL': Decimal('175.50'),
            'GOOGL': Decimal('140.25'),
            'MSFT': Decimal('380.00'),
            'TSLA': Decimal('245.75'),
            'AMZN': Decimal('155.30'),
        }

        for stock in stocks:
            base_price = base_prices[stock.symbol]
            
            # Create prices for last 30 days
            for i in range(30):
                timestamp = timezone.now() - timedelta(days=i)
                variation = Decimal(str((i % 10) - 5))  # ±5 variation
                price = base_price + variation
                
                StockPrice.objects.get_or_create(
                    stock=stock,
                    timestamp=timestamp,
                    defaults={
                        'price': price,
                        'volume': 1000000 + (i * 10000),
                        'source': 'MANUAL'
                    }
                )
            
            self.stdout.write(self.style.SUCCESS(f'✓ Prices created for {stock.symbol}'))

        # Create watchlists
        self.stdout.write('Creating watchlists...')
        
        watchlist, created = Watchlist.objects.get_or_create(
            user=standard_user,
            name='My Watchlist',
            defaults={'is_default': True}
        )

        if created:
            # Add stocks to watchlist
            for stock in stocks[:3]:  # Add first 3 stocks
                WatchlistItem.objects.get_or_create(
                    watchlist=watchlist,
                    stock=stock
                )
            self.stdout.write(self.style.SUCCESS('✓ Watchlist created'))

        # Create price alerts
        self.stdout.write('Creating price alerts...')
        
        alert, created = PriceAlert.objects.get_or_create(
            user=standard_user,
            stock=stocks[0],  # AAPL
            defaults={
                'condition_type': 'PRICE_ABOVE',
                'threshold_value': Decimal('180.00'),
                'one_time': True,
                'is_active': True
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS('✓ Price alert created'))

        self.stdout.write(self.style.SUCCESS('\n✅ Sample data created successfully!'))
        self.stdout.write('\nTest Users:')
        self.stdout.write('- Email: standard@test.com | Password: test123 | Tier: Standard')
        self.stdout.write('- Email: premium@test.com | Password: test123 | Tier: Premium')
