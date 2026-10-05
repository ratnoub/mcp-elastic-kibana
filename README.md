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

Lalu jalankan:

```bash
mcp-elastic-kibana            # transport stdio (default)
mcp-elastic-kibana --transport http --port 8000
```

### Opsi 2 — virtualenv

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install .
mcp-elastic-kibana
```

## Registrasi di MCP client

Contoh (Claude Desktop / VS Code / Copilot CLI):

```json
{
  "mcpServers": {
    "mcp-elastic-kibana": {
      "command": "mcp-elastic-kibana"
    }
  }
}
```

Jika tidak diinstal via pipx, gunakan path python + modul:

```json
{
  "mcpServers": {
    "mcp-elastic-kibana": {
      "command": "D:\\venv\\mcp-elastic-kibana\\Scripts\\python.exe",
      "args": ["-m", "mcp_elastic_kibana.server"]
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