import time
from django_redis import get_redis_connection

class MeteringService:
    def __init__(self):
        # Retrieve the default connection configured in settings.py (django-redis)
        self.redis = get_redis_connection("default")

    def check_quota(self, customer_id: str, limit: int) -> tuple[bool, int]:
        """
        Uses Redis Token Bucket to verify and deduct credit in one atomic operation.
        Key structure:
        - 'quota:{customer_id}:tokens' -> current token count
        - 'quota:{customer_id}:last_checked' -> epoch timestamp
        """
        # Lua Script guarantees thread-safe execution under concurrent load
        lua_script = """
        local key_tokens = KEYS[1]
        local key_last = KEYS[2]
        local limit = tonumber(ARGV[1])
        local now = tonumber(ARGV[2])
        local rate = 0.1 -- Generate 1 token every 10 seconds (refill rate)

        local current_tokens = tonumber(redis.call('get', key_tokens))
        local last_update = tonumber(redis.call('get', key_last))

        if not current_tokens then
            current_tokens = limit
            last_update = now
            redis.call('set', key_tokens, current_tokens)
            redis.call('set', key_last, last_update)
        else
            -- Refill logic
            local elapsed = now - last_update
            local refill = math.floor(elapsed * rate)
            if refill > 0 then
                current_tokens = math.min(limit, current_tokens + refill)
                last_update = now
                redis.call('set', key_tokens, current_tokens)
                redis.call('set', key_last, last_update)
            end
        end

        if current_tokens >= 1 then
            current_tokens = current_tokens - 1
            redis.call('set', key_tokens, current_tokens)
            return {1, current_tokens}
        else
            return {0, current_tokens}
        end
        """
        keys = [f"quota:{customer_id}:tokens", f"quota:{customer_id}:last_checked"]
        args = [str(limit), str(int(time.time()))]
        
        # Execute script atomically using register_script
        script_obj = self.redis.register_script(lua_script)
        result = script_obj(keys=keys, args=args)
        allowed, remaining_tokens = result[0], result[1]
        
        if allowed == 1:
            # Buffer the usage event in Redis list for batch background processing
            self.redis.rpush(f"usage_buffer:{customer_id}", "1")
            return True, remaining_tokens
        
        return False, remaining_tokens

    def get_buffered_usage(self, customer_id: str) -> int:
        """Reads number of raw usage events waiting to be written to DB."""
        return self.redis.llen(f"usage_buffer:{customer_id}")

    def clear_buffer(self, customer_id: str, count: int):
        """Removes items from buffer after successful DB write."""
        self.redis.ltrim(f"usage_buffer:{customer_id}", count, -1)
