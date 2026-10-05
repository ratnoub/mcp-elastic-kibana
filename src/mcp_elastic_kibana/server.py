"""mcp-elastic-kibana — MCP server (FastMCP) untuk Elasticsearch.

Membaca konfigurasi (host, user, password) dari file config.yaml dengan
urutan pencarian:
  1. Environment variable ES_HOST / ES_USER / ES_PASSWORD
  2. File yang ditunjuk environment variable MCP_ELASTIC_KIBANA_CONFIG
  3. ~/.config/mcp-elastic-kibana/config.yaml
  4. ./config.yaml (direktori kerja saat ini)
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Optional

import yaml
from elasticsearch import (
    ApiError,
    ConnectionError as ESConnectionError,
    Elasticsearch,
    NotFoundError,
)
from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------


def _find_config_file() -> Optional[Path]:
    """Cari file config.yaml sesuai urutan prioritas."""
    env_path = os.environ.get("MCP_ELASTIC_KIBANA_CONFIG")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
    home_cfg = Path.home() / ".config" / "mcp-elastic-kibana" / "config.yaml"
    if home_cfg.exists():
        return home_cfg
    local_cfg = Path.cwd() / "config.yaml"
    if local_cfg.exists():
        return local_cfg
    return None


def _load_config() -> dict:
    """Muat konfigurasi; environment variable selalu menang atas file."""
    file_cfg: dict = {}
    cfg_file = _find_config_file()
    if cfg_file is not None:
        with open(cfg_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        file_cfg = data.get("kibana", {}) or {}
    return {
        "host": os.environ.get("ES_HOST", file_cfg.get("ES_HOST", "http://localhost:9200")),
        "user": os.environ.get("ES_USER", file_cfg.get("ES_USER", "")),
        "password": os.environ.get("ES_PASSWORD", file_cfg.get("ES_PASSWORD", "")),
    }


_config = _load_config()

ES = Elasticsearch(
    _config["host"],
    basic_auth=(_config["user"], _config["password"]) if _config["user"] else None,
    request_timeout=30,
)

mcp = FastMCP("mcp-elastic-kibana")


def _json(data: Any) -> str:
    if hasattr(data, "body"):
        data = data.body
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _call(fn, *args, **kwargs) -> str:
    """Jalankan panggilan Elasticsearch dengan pesan error yang actionable."""
    try:
        return _json(fn(*args, **kwargs))
    except NotFoundError as e:
        return _json({"error": f"Resource tidak ditemukan: {e.message}"})
    except ApiError as e:
        return _json({"error": f"Elasticsearch API error {e.status_code}: {e.message}"})
    except ESConnectionError as e:
        return _json(
            {
                "error": (
                    f"Gagal terhubung ke Elasticsearch di {_config['host']}: {e.message}. "
                    "Periksa apakah server berjalan dan kredensial di config.yaml benar."
                )
            }
        )
    except Exception as e:  # noqa: BLE001
        return _json({"error": f"Kesalahan tak terduga: {type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# Cluster
# ---------------------------------------------------------------------------


@mcp.tool
async def es_cluster_health() -> str:
    """Cek kesehatan cluster Elasticsearch (status, jumlah node, shard)."""
    return _call(ES.cluster.health, wait_for_status="yellow")


@mcp.tool
async def es_cluster_info() -> str:
    """Info cluster: nama node, nama cluster, versi Elasticsearch, dan tagline."""
    return _call(ES.info)


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


@mcp.tool
async def es_list_indices() -> str:
    """Daftar semua index beserta health, jumlah dokumen, dan ukuran (bytes)."""
    return _call(
        ES.cat.indices,
        format="json",
        h="health,index,pri,rep,docs.count,store.size",
        s="index",
    )


@mcp.tool
async def es_get_index(index: str) -> str:
    """Detail satu index: settings, mappings, dan alias.

    Args:
        index: Nama index (mis. 'nginx-access-2026.09').
    """
    return _call(ES.indices.get, index=index, include_aliases=True)


@mcp.tool
async def es_get_mappings(index: str) -> str:
    """Ambil field mappings untuk sebuah index.

    Args:
        index: Nama index.
    """
    return _call(ES.indices.get_mapping, index=index)


@mcp.tool
async def es_create_index(index: str, body: Optional[str] = None) -> str:
    """Buat index baru.

    Args:
        index: Nama index baru.
        body: JSON string berisi settings/mappings (opsional),
            mis. '{"settings": {"number_of_shards": 1}}'.
    """
    settings = json.loads(body) if body else None
    kwargs: dict[str, Any] = {}
    if settings:
        if "settings" in settings:
            kwargs["settings"] = settings["settings"]
        if "mappings" in settings:
            kwargs["mappings"] = settings["mappings"]
    return _call(ES.indices.create, index=index, **kwargs)


@mcp.tool
async def es_delete_index(index: str) -> str:
    """Hapus index (DESTRUKTIF — data hilang permanen).

    Args:
        index: Nama index yang akan dihapus.
    """
    return _call(ES.indices.delete, index=index)


@mcp.tool
async def es_refresh_index(index: str) -> str:
    """Refresh index agar dokumen yang baru di-index bisa langsung di-search.

    Args:
        index: Nama index.
    """
    return _call(ES.indices.refresh, index=index)


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


@mcp.tool
async def es_search(
    index: str,
    query: Optional[str] = None,
    size: int = 10,
    from_: int = 0,
    sort: Optional[str] = None,
) -> str:
    """Search dokumen dengan Query DSL Elasticsearch.

    Args:
        index: Nama index (atau wildcard/pattern, mis. 'nginx-*').
        query: JSON string Query DSL (opsional). Default match_all.
            Contoh: '{"match": {"status": 200}}' atau
            '{"range": {"@timestamp": {"gte": "2026-09-01"}}}'.
        size: Jumlah hasil per halaman (default 10, maks 1000).
        from_: Offset untuk paginasi (default 0).
        sort: JSON array sort (opsional), mis. '["@timestamp:desc"]'.
    """
    kwargs: dict[str, Any] = {"from_": from_, "size": min(size, 1000)}
    if query:
        kwargs["query"] = json.loads(query)
    if sort:
        kwargs["sort"] = json.loads(sort)
    return _call(ES.search, index=index, **kwargs)


@mcp.tool
async def es_count(index: str, query: Optional[str] = None) -> str:
    """Hitung jumlah dokumen yang cocok dengan query.

    Args:
        index: Nama index (atau wildcard).
        query: JSON string Query DSL (opsional). Default match_all.
    """
    kwargs: dict[str, Any] = {}
    if query:
        kwargs["query"] = json.loads(query)
    return _call(ES.count, index=index, **kwargs)


@mcp.tool
async def es_get_document(index: str, doc_id: str) -> str:
    """Ambil satu dokumen berdasarkan ID.

    Args:
        index: Nama index.
        doc_id: ID dokumen.
    """
    return _call(ES.get, index=index, id=doc_id)


@mcp.tool
async def es_index_document(
    index: str,
    source: str,
    doc_id: Optional[str] = None,
) -> str:
    """Simpan (index) dokumen baru. Jika doc_id diberikan, dokumen dengan ID
    tersebut akan ditimpa.

    Args:
        index: Nama index.
        source: JSON string isi dokumen, mis. '{"status": 200, "path": "/"}'.
        doc_id: ID dokumen (opsional; jika kosong, ES membuatkan ID).
    """
    return _call(ES.index, index=index, id=doc_id, document=json.loads(source))


@mcp.tool
async def es_update_document(index: str, doc_id: str, source: str) -> str:
    """Update sebagian isi dokumen (partial update).

    Args:
        index: Nama index.
        doc_id: ID dokumen.
        source: JSON string field yang di-update, mis. '{"status": 500}'.
    """
    return _call(ES.update, index=index, id=doc_id, doc=json.loads(source))


@mcp.tool
async def es_delete_document(index: str, doc_id: str) -> str:
    """Hapus satu dokumen (DESTRUKTIF).

    Args:
        index: Nama index.
        doc_id: ID dokumen.
    """
    return _call(ES.delete, index=index, id=doc_id)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Console entry point: `mcp-elastic-kibana`."""
    parser = argparse.ArgumentParser(
        prog="mcp-elastic-kibana",
        description="MCP server (FastMCP) untuk Elasticsearch.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport MCP (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host untuk transport http")
    parser.add_argument("--port", type=int, default=8000, help="Port untuk transport http")
    args = parser.parse_args()

    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()