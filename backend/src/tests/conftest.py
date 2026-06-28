import pytest


class _FakeQuery:
    def __init__(self, table, store):
        self.table_name, self.store, self._filters = table, store, {}

    def insert(self, data):
        self.store.setdefault(self.table_name, [])
        self.store[self.table_name].extend(data if isinstance(data, list) else [data])
        return self

    def update(self, data):
        self._update_data = data
        return self

    def delete(self):
        self._delete = True
        return self

    def select(self, *_args):
        return self

    def eq(self, field, value):
        self._filters[field] = value
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args):
        return self

    def execute(self):
        rows = self.store.get(self.table_name, [])
        if getattr(self, "_delete", False):
            self.store[self.table_name] = [r for r in rows if not all(r.get(k) == v for k, v in self._filters.items())]
        elif hasattr(self, "_update_data"):
            for r in rows:
                if all(r.get(k) == v for k, v in self._filters.items()):
                    r.update(self._update_data)
        else:
            self.data = [r for r in rows if all(r.get(k) == v for k, v in self._filters.items())]
            return self
        self.data = []
        return self


class FakeSupabase:
    def __init__(self):
        self.store: dict[str, list[dict]] = {}

    def table(self, name):
        return _FakeQuery(name, self.store)


@pytest.fixture
def fake_supabase():
    return FakeSupabase()
