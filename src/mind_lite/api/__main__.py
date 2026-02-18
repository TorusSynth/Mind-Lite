import os

from mind_lite.api.http_server import create_server


def main() -> None:
    state_file = os.environ.get("MIND_LITE_STATE_FILE")
    server = create_server(host="127.0.0.1", port=8000, state_file=state_file)
    print("Mind Lite API listening on http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
