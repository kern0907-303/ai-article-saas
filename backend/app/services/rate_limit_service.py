from collections import defaultdict, deque
from time import time

from fastapi import HTTPException

_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(bucket_key: str, limit: int, window_seconds: int) -> None:
    now = time()
    q = _BUCKETS[bucket_key]

    while q and now - q[0] > window_seconds:
        q.popleft()

    if len(q) >= limit:
        raise HTTPException(status_code=429, detail="請求過於頻繁，請稍後再試")

    q.append(now)
