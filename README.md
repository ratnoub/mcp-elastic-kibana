# mcp-elastic-kibana

MCP server (FastMCP) untuk terhubung ke Elasticsearch. Menyediakan 14 tools
untuk operasi cluster, index, dan document.

## Struktur

```
.
├── pyproject.toml
├── config.example.yaml
├── .gitignore
└── src/
    └── mcp_elastic_kibana/
        ├── __init__.py
        ├── __main__.py
        ├── cli.py
        ├── daemon.py
        └── server.py
```

## Konfigurasi

Server mencari kredensial Elasticsearch dengan urutan:

1. Environment variable `ES_HOST`, `ES_USER`, `ES_PASSWORD`
2. File yang ditunjuk `MCP_ELASTIC_KIBANA_CONFIG`
3. `~/.config/mcp-elastic-kibana/config.yaml`
4. `./config.yaml` (direktori kerja)

Format file config (salin dari `config.example.yaml`):

```yaml
kibana:
  ES_HOST: http://localhost:9200
  ES_USER: elastic
  ES_PASSWORD: your-password-here
```

> ⚠️ File `config.yaml` berisi kredensial dan sudah di-exclude via `.gitignore`.
> Jangan pernah commit file tersebut.

## Instalasi

### Opsi 1 — pipx (direkomendasikan)

```bash
pipx install .
```

### Opsi 2 — virtualenv

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install .
```

## Menjalankan

Default: transport **http** di `0.0.0.0:5755`, endpoint MCP di `http://IP:5755/mcp`.

```bash
mcp-elastic-kibana                          # http di 0.0.0.0:5755 (foreground)
mcp-elastic-kibana --port 9000              # http di port lain
mcp-elastic-kibana --transport stdio        # transport stdio
```

### Daemon (background)

```bash
mcp-elastic-kibana --daemon                 # jalankan di background
mcp-elastic-kibana --status                 # cek status (PID, port, URL, log)
mcp-elastic-kibana --stop                   # hentikan daemon
```

File daemon disimpan di `~/.config/mcp-elastic-kibana/`:

- `daemon.pid` — PID proses background
- `daemon.log` — output server

## Registrasi di MCP client

Endpoint HTTP (setelah daemon/foreground berjalan):

```json
{
  "mcpServers": {
    "mcp-elastic-kibana": {
      "url": "http://<ip-server>:5755/mcp"
    }
  }
}
```

Atau via stdio (client menjalankan prosesnya sendiri):

```json
{
  "mcpServers": {
    "mcp-elastic-kibana": {
      "command": "mcp-elastic-kibana",
      "args": ["--transport", "stdio"]
    }
  }
}
```

## Tools

| Tool | Deskripsi |
|------|-----------|
| `es_cluster_health` | Kesehatan cluster (status, node, shard) |
| `es_cluster_info` | Info cluster: nama node, versi ES |
| `es_list_indices` | Daftar semua index + ukuran + jumlah dokumen |
| `es_get_index` | Detail index (settings, mappings, alias) |
| `es_get_mappings` | Field mappings sebuah index |
| `es_create_index` | Buat index baru (opsional settings/mappings) |
| `es_delete_index` | Hapus index (destruktif) |
| `es_refresh_index` | Refresh index agar dokumen baru bisa di-search |
| `es_search` | Search dengan Query DSL (paginasi via `from_`/`size`) |
| `es_count` | Hitung dokumen yang cocok dengan query |
| `es_get_document` | Ambil dokumen berdasarkan ID |
| `es_index_document` | Simpan/ganti dokumen |
| `es_update_document` | Partial update dokumen |
| `es_delete_document` | Hapus dokumen (destruktif) |