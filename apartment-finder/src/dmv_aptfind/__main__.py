"""CLI entry point — starts uvicorn and opens the browser."""

import threading
import webbrowser

import uvicorn

PORT = 8788


def main():
    url = f"http://127.0.0.1:{PORT}"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run("dmv_aptfind.main:app", host="127.0.0.1", port=PORT)


if __name__ == "__main__":
    main()
