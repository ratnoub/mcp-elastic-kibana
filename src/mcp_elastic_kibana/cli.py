"""Command-line interface untuk mcp-elastic-kibana."""

import argparse
import sys

from . import __version__, daemon
from .server import DEFAULT_HOST, DEFAULT_PORT, run_server


def main() -> None:
    """Console entry point: `mcp-elastic-kibana`."""
    parser = argparse.ArgumentParser(
        prog="mcp-elastic-kibana",
        description="MCP server (FastMCP) untuk Elasticsearch.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="http",
        help="Transport MCP (default: http)",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Alamat bind untuk transport http (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port untuk transport http (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path ke file config.yaml (memilih file config yang dipakai)",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Jalankan server di background (daemon)",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Hentikan daemon background",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Tampilkan status daemon",
    )
    args = parser.parse_args()

    if args.stop:
        try:
            daemon.stop_daemon()
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print("Daemon dihentikan.")
        return

    if args.status:
        st = daemon.status(args.host, args.port)
        if st["running"]:
            print(f"Status : berjalan (PID {st['pid']})")
        else:
            print("Status : tidak berjalan")
        print(f"Port   : {'terbuka' if st['port_open'] else 'tertutup'} ({args.port})")
        print(f"URL    : {st['url']}")
        print(f"Log    : {st['log_file']}")
        return

    if args.daemon:
        try:
            pid = daemon.start_daemon(args.host, args.port, config_path=args.config)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"Daemon berjalan (PID {pid}).")
        print(f"Endpoint MCP : http://<ip-server>:{args.port}/mcp")
        print(f"Log          : {daemon.LOG_FILE}")
        print("Hentikan dengan: mcp-elastic-kibana --stop")
        return

    run_server(transport=args.transport, host=args.host, port=args.port,
               config_path=args.config)


if __name__ == "__main__":
    main()