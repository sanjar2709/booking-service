import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class RateLimiter:
    """Sliding window limit per client IP and endpoint.

    Kept in memory, so with several workers each one counts on its own.
    That is enough to slow down password guessing; a shared limit would need Redis.
    """

    def __init__(self, times: int, seconds: int):
        self.times = times
        self.seconds = seconds
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    async def __call__(self, request: Request):
        client = request.client.host if request.client else 'unknown'
        key = f'{client}:{request.url.path}'
        now = time.monotonic()
        hits = self.hits[key]

        while hits and hits[0] <= now - self.seconds:
            hits.popleft()
        if len(hits) >= self.times:
            retry_after = int(hits[0] + self.seconds - now) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail='Too many requests, try again later',
                headers={'Retry-After': str(retry_after)},
            )
        hits.append(now)

    def reset(self):
        self.hits.clear()
