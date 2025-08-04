from django.utils.timezone import now
import uuid

def generate_order_id():
    date_str = now().strftime('%Y%m%d')
    rand = uuid.uuid4().hex[:6].upper()
    return f"INV-{date_str}-{rand}"
