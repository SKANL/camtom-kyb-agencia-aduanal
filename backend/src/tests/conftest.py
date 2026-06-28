import pytest


class _FakeQuery:
    def __init__(self, table, store, fail_on_insert=None):
        self.table_name, self.store = table, store
        self._filters, self._neq_filters = {}, {}
        self._fail_on_insert = fail_on_insert if fail_on_insert is not None else {}

    def insert(self, data):
        if self.table_name in self._fail_on_insert:
            self._raise = self._fail_on_insert[self.table_name]
            return self
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

    def neq(self, field, value):
        self._neq_filters[field] = value
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args):
        return self

    def _matches(self, row):
        if not all(row.get(k) == v for k, v in self._filters.items()):
            return False
        # Semantica SQL: NULL <> X siempre evalua a NULL (no a true), nunca
        # matchea un filtro neq. Replicado aca para que el fake sea fiel a
        # PostgREST y no oculte filas huerfanas con valor NULL en produccion.
        for k, v in self._neq_filters.items():
            value = row.get(k)
            if value is None or value == v:
                return False
        return True

    def execute(self):
        if getattr(self, "_raise", None) is not None:
            raise self._raise
        rows = self.store.get(self.table_name, [])
        if getattr(self, "_delete", False):
            self.store[self.table_name] = [r for r in rows if not self._matches(r)]
        elif hasattr(self, "_update_data"):
            for r in rows:
                if self._matches(r):
                    r.update(self._update_data)
        else:
            self.data = [r for r in rows if self._matches(r)]
            return self
        self.data = []
        return self


class FakeSupabase:
    def __init__(self):
        self.store: dict[str, list[dict]] = {}
        self.fail_on_insert: dict[str, Exception] = {}

    def table(self, name):
        return _FakeQuery(name, self.store, self.fail_on_insert)


@pytest.fixture
def fake_supabase():
    return FakeSupabase()
