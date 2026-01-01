"""
Celery tasks for pricing app.

WHY CELERY?
Background tasks run asynchronously without blocking API requests.
Examples:
- Fetching stock prices from external APIs
- Processing large datasets
- Scheduled periodic tasks

CELERY BEAT:
Scheduled tasks that run at specific intervals (like cron jobs).
"""

from celery import shared_task
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import requests
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def fetch_stock_prices(self):
    """
    Fetch latest stock prices from external API.
    
    WHY @shared_task?
    Makes task available to all Celery workers.
    
    WHY bind=True?
    Gives access to self (the task instance) for retry logic.
    
    SCHEDULED: Every 15 minutes (configured in celery.py)
    """
    from stocks.models import Stock
    from .models import StockPrice
    
    try:
        # Get all active stocks
        stocks = Stock.objects.active()
        
        logger.info(f'Fetching prices for {stocks.count()} stocks')
        
        for stock in stocks:
            try:
                # Fetch price from Alpha Vantage API
                price_data = fetch_stock_price_from_api(stock.symbol)
                
                if price_data:
                    # Create price record (idempotent - won't create duplicates)
                    StockPrice.objects.get_or_create(
                        stock=stock,
                        timestamp=price_data['timestamp'],
                        defaults={
                            'price': price_data['price'],
                            'volume': price_data.get('volume', 0),
                            'source': 'ALPHA_VANTAGE'
                        }
                    )
                    logger.info(f'Price updated for {stock.symbol}: ${price_data["price"]}')
                
            except Exception as e:
                logger.error(f'Error fetching price for {stock.symbol}: {e}')
                # Continue with next stock instead of failing entire task
                continue
        
        return {'status': 'success', 'stocks_processed': stocks.count()}
    
    except Exception as exc:
        # Retry task if it fails
        logger.error(f'Task failed: {exc}')
        raise self.retry(exc=exc, countdown=60)  # Retry after 60 seconds


def fetch_stock_price_from_api(symbol):
    """
    Fetch stock price from Alpha Vantage API.
    
    WHY SEPARATE FUNCTION?
    - Easier to test
    - Can be reused
    - Single responsibility
    
    API DOCS: https://www.alphavantage.co/documentation/
    """
    api_key = settings.ALPHA_VANTAGE_API_KEY
    base_url = settings.ALPHA_VANTAGE_BASE_URL
    
    # Use GLOBAL_QUOTE function for latest price
    params = {
        'function': 'GLOBAL_QUOTE',
        'symbol': symbol,
        'apikey': api_key
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for API errors
        if 'Error Message' in data:
            logger.error(f'API error for {symbol}: {data["Error Message"]}')
            return None
        
        if 'Note' in data:
            # API rate limit reached
            logger.warning(f'API rate limit: {data["Note"]}')
            return None
        
        # Parse response
        global_quote = data.get('Global Quote', {})
        
        if not global_quote:
            logger.warning(f'No data for {symbol}')
            return None
        
        return {
            'price': float(global_quote.get('05. price', 0)),
            'volume': int(global_quote.get('06. volume', 0)),
            'timestamp': timezone.now()
        }
    
    except requests.RequestException as e:
        logger.error(f'API request failed for {symbol}: {e}')
        return None
    except (KeyError, ValueError) as e:
        logger.error(f'Error parsing API response for {symbol}: {e}')
        return None


@shared_task
def cleanup_old_prices():
    """
    Delete price records older than retention period.
    
    WHY: Time-series data grows infinitely.
    We need data retention policies to manage storage.
    
    RETENTION POLICY:
    - Standard data: Keep 1 year
    - Detailed data: Keep 90 days
    
    SCHEDULED: Daily at 2 AM (configured in celery.py)
    """
    from .models import StockPrice
    
    # Delete prices older than 1 year
    one_year_ago = timezone.now() - timedelta(days=365)
    
    deleted_count = StockPrice.objects.filter(
        timestamp__lt=one_year_ago
    ).delete()[0]
    
    logger.info(f'Cleaned up {deleted_count} old price records')
    
    return {'deleted': deleted_count}


@shared_task(bind=True, max_retries=3)
def fetch_historical_data(self, stock_symbol, start_date, end_date):
    """
    Fetch historical price data for a stock.
    
    WHY ASYNC?
    Historical data fetching can take time.
    Don't block API requests.
    
    USAGE: Called on-demand when user upgrades to Premium.
    """
    from stocks.models import Stock
    from .models import StockPrice
    
    try:
        stock = Stock.objects.get(symbol=stock_symbol, is_active=True)
        
        # This is a simplified version - in production, use TIME_SERIES_DAILY
        # Alpha Vantage endpoint for batch historical data
        
        api_key = settings.ALPHA_VANTAGE_API_KEY
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': stock_symbol,
            'apikey': api_key,
            'outputsize': 'full'  # Get all available data
        }
        
        response = requests.get(settings.ALPHA_VANTAGE_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        time_series = data.get('Time Series (Daily)', {})
        
        created_count = 0
        for date_str, values in time_series.items():
            date = timezone.datetime.strptime(date_str, '%Y-%m-%d')
            date = timezone.make_aware(date)
            
            # Only import within requested range
            if start_date <= date <= end_date:
                _, created = StockPrice.objects.get_or_create(
                    stock=stock,
                    timestamp=date,
                    defaults={
                        'price': float(values['4. close']),
                        'volume': int(values['5. volume']),
                        'source': 'ALPHA_VANTAGE'
                    }
                )
                if created:
                    created_count += 1
        
        logger.info(f'Imported {created_count} historical prices for {stock_symbol}')
        return {'status': 'success', 'records_created': created_count}
    
    except Exception as exc:
        logger.error(f'Historical data fetch failed: {exc}')
        raise self.retry(exc=exc, countdown=120)
