import copy
from types import SimpleNamespace

class Query:
    def __init__(self, client, table):
        self.client, self.table = client, table
        self.action = 'read'
        self.filters = []
        self.maximum = 1000
    def select(self, fields): return self
    def limit(self, maximum): self.maximum = maximum; return self
    def eq(self, name, value): self.filters.append((name, value)); return self
    def is_(self, name, value):
        assert value == 'null'
        return self.eq(name, None)
    def insert(self, payload): self.action, self.payload = 'insert', payload; return self
    def update(self, payload): self.action, self.payload = 'update', payload; return self
    def execute(self):
        rows = self.client.rows[self.table]
        found = [r for r in rows if all(r.get(k) == v for k, v in self.filters)]
        if self.action == 'read': return SimpleNamespace(data=copy.deepcopy(found[:self.maximum]))
        if self.table == 'documents':
            # Reproduce la regla usada por el migrador original del proyecto.
            for row in ([self.payload] if self.action == 'insert' else found):
                merged = {**row, **self.payload}
                expected = f"documents/{merged['id']}.{merged['extension']}"
                if merged['storage_path'] != expected:
                    raise RuntimeError('23514 canonical_storage_path')
        if self.client.fail == self.table: raise RuntimeError('Fallo simulado DB')
        self.client.events.append(('db', self.table, self.action))
        if self.action == 'insert':
            rows.append(copy.deepcopy(self.payload)); found = [rows[-1]]
        else:
            for r in found: r.update(copy.deepcopy(self.payload))
        return SimpleNamespace(data=copy.deepcopy(found))


class Bucket:
    def __init__(self, client, bucket): self.client, self.bucket = client, bucket
    def upload(self, path, data, options):
        if self.client.fail == self.bucket: raise RuntimeError('Fallo simulado Storage')
        self.client.events.append(('upload', self.bucket, path))
        self.client.objects[(self.bucket, path)] = data
    def get_public_url(self, path): return 'https://example.invalid/' + path


class Client:
    def __init__(self):
        self.rows = {'folders': [], 'documents': []}
        self.events = []
        self.objects = {}
        self.fail = None
        self.storage = self
    def table(self, name): return Query(self, name)
    def from_(self, bucket): return Bucket(self, bucket)
    def get_bucket(self, name): return SimpleNamespace(public=(name == 'repository-images'))


