from datetime import datetime, timezone
from uuid import uuid4


def generate_reference(prefix: str) -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = uuid4().hex[:6].upper()
    return f"{prefix}-{date_part}-{random_part}"
