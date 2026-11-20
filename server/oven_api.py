
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

import mysql.connector
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from mysql.connector.errorcode import ER_DUP_ENTRY
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api")


# ---------------------------------------------------------
# Database connection
# ---------------------------------------------------------

def db_connect():
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
    )


# ---------------------------------------------------------
# Authentication
# ---------------------------------------------------------

def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def require_admin(
    x_admin_key: str = Header(alias="X-Admin-Key"),
):
    expected = os.environ.get("ADMIN_API_KEY")

    if not expected or not hmac.compare_digest(
        x_admin_key, expected
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid administrator key",
        )


def require_oven(
    x_oven_serial: str = Header(alias="X-Oven-Serial"),
    x_oven_key: str = Header(alias="X-Oven-Key"),
):
    try:
        with db_connect() as db:
            cursor = db.cursor(dictionary=True)
            try:
                cursor.execute(
                    "SELECT oven_id, api_key_hash "
                    "FROM ovens WHERE serial_number = %s",
                    (x_oven_serial,),
                )
                oven = cursor.fetchone()
            finally:
                cursor.close()

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )

    if (
        not oven
        or not oven["api_key_hash"]
        or not hmac.compare_digest(
            hash_key(x_oven_key),
            oven["api_key_hash"],
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid oven credentials",
        )

    return oven["oven_id"]


# ---------------------------------------------------------
# UTC timestamp handling
# ---------------------------------------------------------

def utc_datetime(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")

    return dt.astimezone(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------
# Request models
# ---------------------------------------------------------

class OvenRegistration(BaseModel):
    serial_number: str = Field(min_length=1, max_length=50)
    model_number: str | None = Field(default=None, max_length=50)
    firmware_version: str | None = Field(default=None, max_length=30)
    software_version: str | None = Field(default=None, max_length=30)


class CookingCycle(BaseModel):
    cycle_uuid: UUID
    recipe_name: str | None = Field(default=None, max_length=100)
    start_time: datetime
    end_time: datetime
    result: Literal["completed", "canceled", "failed"]


class OvenJob(CookingCycle):
    mode: Literal["AUTO", "MANUAL"]
    job_file: str | None = Field(default=None, max_length=255)
    job_settings: dict


class OvenEvent(BaseModel):
    event_uuid: UUID
    cycle_uuid: UUID | None = None
    event_time: datetime
    event_type: Literal["info", "warning", "fault"]
    event_code: str = Field(min_length=1, max_length=50)
    message: str | None = Field(default=None, max_length=255)


# ---------------------------------------------------------
# POST /api/ovens
# Register a new oven
# ---------------------------------------------------------

@router.post("/ovens", status_code=201)
def register_oven(
    data: OvenRegistration,
    _: None = Depends(require_admin),
):
    api_key = secrets.token_urlsafe(32)

    try:
        with db_connect() as db:
            cursor = db.cursor()

            try:
                cursor.execute(
                    "INSERT INTO ovens "
                    "(serial_number, model_number, "
                    "firmware_version, software_version, "
                    "api_key_hash) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (
                        data.serial_number,
                        data.model_number,
                        data.firmware_version,
                        data.software_version,
                        hash_key(api_key),
                    ),
                )

                oven_id = cursor.lastrowid
                db.commit()

            finally:
                cursor.close()

    except mysql.connector.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Oven already registered",
        )

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )

    # The key is returned only during registration.
    return {
        "oven_id": oven_id,
        "serial_number": data.serial_number,
        "api_key": api_key,
    }


# ---------------------------------------------------------
# GET /api/ovens
# List registered ovens
# ---------------------------------------------------------

@router.get("/ovens")
def list_ovens(
    _: None = Depends(require_admin),
):
    try:
        with db_connect() as db:
            cursor = db.cursor(dictionary=True)

            try:
                cursor.execute(
                    "SELECT oven_id, serial_number, "
                    "model_number, firmware_version, "
                    "software_version, status, last_seen "
                    "FROM ovens ORDER BY oven_id"
                )

                return cursor.fetchall()

            finally:
                cursor.close()

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )


# ---------------------------------------------------------
# POST /api/cooking-cycles
# Upload completed cooking cycle
# ---------------------------------------------------------

@router.post("/cooking-cycles")
def upload_cycle(
    data: CookingCycle,
    oven_id: int = Depends(require_oven),
):
    try:
        started = utc_datetime(data.start_time)
        ended = utc_datetime(data.end_time)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    if ended < started:
        raise HTTPException(
            status_code=422,
            detail="End time precedes start time",
        )

    duration = int((ended - started).total_seconds())
    uuid = str(data.cycle_uuid)

    try:
        with db_connect() as db:
            cursor = db.cursor(dictionary=True)

            try:
                try:
                    cursor.execute(
                        "INSERT INTO cooking_cycles "
                        "(oven_id, client_cycle_uuid, "
                        "recipe_name, start_time, end_time, "
                        "duration_seconds, result) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (
                            oven_id,
                            uuid,
                            data.recipe_name,
                            started,
                            ended,
                            duration,
                            data.result,
                        ),
                    )

                    cycle_id = cursor.lastrowid
                    db.commit()
                    duplicate = False

                except mysql.connector.IntegrityError:
                    db.rollback()

                    cursor.execute(
                        "SELECT * FROM cooking_cycles "
                        "WHERE client_cycle_uuid = %s",
                        (uuid,),
                    )

                    existing = cursor.fetchone()

                    if not existing:
                        raise HTTPException(
                            status_code=409,
                            detail="Cycle conflict",
                        )

                    if (
                        existing["oven_id"] != oven_id
                        or existing["recipe_name"] != data.recipe_name
                        or existing["start_time"] != started
                        or existing["end_time"] != ended
                        or existing["duration_seconds"] != duration
                        or existing["result"] != data.result
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail="Conflicting cycle UUID",
                        )

                    cycle_id = existing["cycle_id"]
                    duplicate = True

            finally:
                cursor.close()

        return {
            "cycle_id": cycle_id,
            "cycle_uuid": uuid,
            "duplicate": duplicate,
        }

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )


# ---------------------------------------------------------
# POST /api/oven-jobs
# Store a finished job and its cooking-cycle outcome atomically.
# ---------------------------------------------------------

@router.post(
    "/oven-jobs",
    status_code=201,
    responses={200: {"description": "Identical replay"}},
)
def upload_job(
    data: OvenJob,
    response: Response,
    oven_id: int = Depends(require_oven),
):
    try:
        started = utc_datetime(data.start_time)
        ended = utc_datetime(data.end_time)
        if ended < started:
            raise ValueError("End time precedes start time")
        if not data.job_settings:
            raise ValueError("Job settings must include the starting parameters")
        settings = json.dumps(data.job_settings, allow_nan=False)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    duration = int((ended - started).total_seconds())
    # oven_jobs uses DATETIME without fractional seconds. Normalize before
    # inserting so replays compare to the exact values persisted by MySQL.
    started = started.replace(microsecond=0)
    ended = ended.replace(microsecond=0)
    uuid = str(data.cycle_uuid)

    try:
        with db_connect() as db:
            cursor = db.cursor(dictionary=True)
            try:
                try:
                    cursor.execute(
                        "INSERT INTO oven_jobs "
                        "(oven_id, cycle_uuid, mode, job_file, job_settings, start_time, stop_time) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (oven_id, uuid, data.mode, data.job_file, settings, started, ended),
                    )
                except mysql.connector.IntegrityError as exc:
                    if exc.errno != ER_DUP_ENTRY:
                        raise
                    # Read in a fresh transaction after a concurrent insert.
                    db.rollback()
                    cursor.execute(
                        "SELECT j.job_id, j.mode, j.job_file, j.job_settings, "
                        "j.start_time, j.stop_time, c.cycle_id, c.recipe_name, "
                        "c.result, c.duration_seconds "
                        "FROM oven_jobs AS j JOIN cooking_cycles AS c "
                        "ON c.client_cycle_uuid = j.cycle_uuid AND c.oven_id = j.oven_id "
                        "WHERE j.oven_id = %s AND j.cycle_uuid = %s",
                        (oven_id, uuid),
                    )
                    existing = cursor.fetchone()
                    if (
                        not existing
                        or existing["mode"] != data.mode
                        or existing["job_file"] != data.job_file
                        or json.loads(existing["job_settings"]) != data.job_settings
                        or existing["start_time"] != started
                        or existing["stop_time"] != ended
                        or existing["recipe_name"] != data.recipe_name
                        or existing["result"] != data.result
                        or existing["duration_seconds"] != duration
                    ):
                        raise HTTPException(status_code=409, detail="Conflicting job UUID")

                    response.status_code = 200
                    return {
                        "job_id": existing["job_id"],
                        "cycle_id": existing["cycle_id"],
                        "cycle_uuid": uuid,
                        "duplicate": True,
                    }

                job_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO cooking_cycles "
                    "(oven_id, client_cycle_uuid, recipe_name, start_time, end_time, "
                    "duration_seconds, result) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (oven_id, uuid, data.recipe_name, started, ended, duration, data.result),
                )
                cycle_id = cursor.lastrowid
                db.commit()
            except mysql.connector.IntegrityError as exc:
                db.rollback()
                if exc.errno == ER_DUP_ENTRY:
                    raise HTTPException(status_code=409, detail="Conflicting cycle UUID") from exc
                raise
            except (HTTPException, mysql.connector.Error):
                db.rollback()
                raise
            finally:
                cursor.close()

        return {
            "job_id": job_id,
            "cycle_id": cycle_id,
            "cycle_uuid": uuid,
            "duplicate": False,
        }

    except mysql.connector.Error as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


# ---------------------------------------------------------
# POST /api/oven-events
# Upload oven event
# ---------------------------------------------------------

@router.post("/oven-events")
def upload_event(
    data: OvenEvent,
    oven_id: int = Depends(require_oven),
):
    try:
        event_time = utc_datetime(data.event_time)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    uuid = str(data.event_uuid)

    try:
        with db_connect() as db:
            cursor = db.cursor(dictionary=True)

            try:
                cycle_id = None

                if data.cycle_uuid is not None:
                    cursor.execute(
                        "SELECT cycle_id FROM cooking_cycles "
                        "WHERE client_cycle_uuid = %s "
                        "AND oven_id = %s",
                        (str(data.cycle_uuid), oven_id),
                    )

                    cycle = cursor.fetchone()

                    if not cycle:
                        raise HTTPException(
                            status_code=409,
                            detail="Referenced cycle not found",
                        )

                    cycle_id = cycle["cycle_id"]

                try:
                    cursor.execute(
                        "INSERT INTO oven_events "
                        "(oven_id, cycle_id, client_event_uuid, "
                        "event_time, event_type, event_code, message) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (
                            oven_id,
                            cycle_id,
                            uuid,
                            event_time,
                            data.event_type,
                            data.event_code,
                            data.message,
                        ),
                    )

                    event_id = cursor.lastrowid
                    db.commit()
                    duplicate = False

                except mysql.connector.IntegrityError:
                    db.rollback()

                    cursor.execute(
                        "SELECT * FROM oven_events "
                        "WHERE client_event_uuid = %s",
                        (uuid,),
                    )

                    existing = cursor.fetchone()

                    if not existing:
                        raise HTTPException(
                            status_code=409,
                            detail="Event conflict",
                        )

                    if (
                        existing["oven_id"] != oven_id
                        or existing["cycle_id"] != cycle_id
                        or existing["event_time"] != event_time
                        or existing["event_type"] != data.event_type
                        or existing["event_code"] != data.event_code
                        or existing["message"] != data.message
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail="Conflicting event UUID",
                        )

                    event_id = existing["event_id"]
                    duplicate = True

            finally:
                cursor.close()

        return {
            "event_id": event_id,
            "event_uuid": uuid,
            "duplicate": duplicate,
        }

    except mysql.connector.Error:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )

