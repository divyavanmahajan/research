import argparse
import uvicorn
from financeflow_api.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="FinanceFlow REST API")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--db", default="financeflow.db", help="SQLite DB path")
    parser.add_argument("--cors-origins", default="http://localhost:5173",
                        help="Comma-separated allowed CORS origins")
    args = parser.parse_args()

    app = create_app(
        db_path=args.db,
        cors_origins=args.cors_origins.split(","),
    )
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
