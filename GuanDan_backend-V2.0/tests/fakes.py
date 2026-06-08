import fnmatch


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.hashes = {}
        self.hashs = self.hashes
        self.sets = {}
        self.expires = {}

    def ping(self):
        return True

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value
        return True

    def setex(self, key, time, value):
        self.values[key] = value
        self.expires[key] = time
        return True

    def delete(self, *keys):
        removed = 0
        for key in keys:
            for store in (self.values, self.hashs, self.sets):
                if key in store:
                    del store[key]
                    removed += 1
            self.expires.pop(key, None)
        return removed

    def hset(self, name, key=None, value=None, mapping=None, field=None):
        if field is not None:
            key = field
        self.hashs.setdefault(name, {})
        updates = {}
        if mapping:
            updates.update(mapping)
        if key is not None:
            updates[key] = value

        created = 0
        for item_key, item_value in updates.items():
            if item_key not in self.hashs[name]:
                created += 1
            self.hashs[name][item_key] = item_value
        return created

    def hget(self, name, key):
        return self.hashs.get(name, {}).get(key)

    def hgetall(self, name):
        return dict(self.hashs.get(name, {}))

    def sadd(self, name, *values):
        self.sets.setdefault(name, set())
        before = len(self.sets[name])
        self.sets[name].update(values)
        return len(self.sets[name]) - before

    def smembers(self, name):
        return set(self.sets.get(name, set()))

    def srem(self, name, *values):
        current = self.sets.setdefault(name, set())
        before = len(current)
        for value in values:
            current.discard(value)
        return before - len(current)

    def scan_iter(self, match=None, count=None):
        keys = set(self.values) | set(self.hashs) | set(self.sets)
        for key in sorted(keys):
            if match is None or fnmatch.fnmatch(key, match):
                yield key

    def setnx(self, key, value):
        if key in self.values:
            return False
        self.values[key] = value
        return True

    def expire(self, key, time):
        exists = key in self.values or key in self.hashs or key in self.sets
        if exists:
            self.expires[key] = time
        return exists
