
import os

import mysql.connector
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Hostinger VPS API")


def get_db_connection():
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
    )


@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "application": "Hostinger VPS",
        "backend": "FastAPI",
    }


@app.get("/api/messages")
def get_messages():
    try:
        with get_db_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(
                    "SELECT id, message, created_at "
                    "FROM test_data ORDER BY id DESC LIMIT 20"
                )
                rows = cursor.fetchall()
                return [
                    {
                        "id": row["id"],
                        "message": row["message"],
                        "created_at": row["created_at"].isoformat(),
                    }
                    for row in rows
                ]
            finally:
                cursor.close()
    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable",
        )

from oven_api import router as oven_router

app.include_router(oven_router)
