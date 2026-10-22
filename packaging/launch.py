"""Frozen-app entry point."""
import sys
from symmetrylab.desktop import main, start_server, data_dir

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == '--smoke-test':
        from smoke import check
        server = start_server(data_dir())
        try:
            check(server, data_dir(), sys.argv[2])
        finally:
            server.shutdown()
            server.server_close()
    else:
        sys.exit(main())
