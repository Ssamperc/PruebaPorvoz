import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, redirect, render_template, request, url_for
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

DB_PATH = os.environ.get("DB_PATH", "reminders.db")
APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "America/Mexico_City")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")
TWILIO_BASE_URL = os.environ.get("TWILIO_BASE_URL", "http://localhost:5000")

app = Flask(__name__)
scheduler = BackgroundScheduler(timezone=APP_TIMEZONE)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
            """
        )


def twilio_client() -> Client | None:
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER):
        return None
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def schedule_reminder_job(reminder_id: int, run_at_iso: str) -> None:
    run_at = datetime.fromisoformat(run_at_iso)
    if run_at.tzinfo is None:
        run_at = run_at.replace(tzinfo=ZoneInfo(APP_TIMEZONE))

    scheduler.add_job(
        func=trigger_call,
        trigger="date",
        run_date=run_at,
        args=[reminder_id],
        id=f"reminder-{reminder_id}",
        replace_existing=True,
        misfire_grace_time=60,
    )


def mark_reminder_status(reminder_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE reminders SET status = ? WHERE id = ?",
            (status, reminder_id),
        )


def trigger_call(reminder_id: int) -> None:
    with get_connection() as conn:
        reminder = conn.execute(
            "SELECT * FROM reminders WHERE id = ?",
            (reminder_id,),
        ).fetchone()

    if not reminder or reminder["status"] != "pending":
        return

    client = twilio_client()
    if client is None:
        mark_reminder_status(reminder_id, "failed_missing_twilio_config")
        app.logger.warning(
            "No se pudo llamar al recordatorio %s por configuración faltante de Twilio",
            reminder_id,
        )
        return

    try:
        callback_url = f"{TWILIO_BASE_URL.rstrip('/')}/voice/{reminder_id}"
        client.calls.create(
            to=reminder["phone_number"],
            from_=TWILIO_FROM_NUMBER,
            url=callback_url,
            method="POST",
        )
        mark_reminder_status(reminder_id, "called")
    except Exception as error:  # noqa: BLE001
        mark_reminder_status(reminder_id, "failed_call_error")
        app.logger.exception(
            "Error al marcar recordatorio %s: %s", reminder_id, error
        )


@app.route("/", methods=["GET"])
def index():
    with get_connection() as conn:
        reminders = conn.execute(
            "SELECT * FROM reminders ORDER BY scheduled_at ASC"
        ).fetchall()
    return render_template("index.html", reminders=reminders, timezone=APP_TIMEZONE)


@app.route("/schedule", methods=["POST"])
def schedule():
    name = request.form.get("name", "").strip()
    phone_number = request.form.get("phone_number", "").strip()
    message = request.form.get("message", "").strip()
    scheduled_at_local = request.form.get("scheduled_at", "").strip()

    if not all([name, phone_number, message, scheduled_at_local]):
        return redirect(url_for("index"))

    dt_local = datetime.fromisoformat(scheduled_at_local).replace(
        tzinfo=ZoneInfo(APP_TIMEZONE)
    )
    now = datetime.now(ZoneInfo(APP_TIMEZONE))

    if dt_local <= now:
        return redirect(url_for("index"))

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reminders (name, phone_number, scheduled_at, message, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (
                name,
                phone_number,
                dt_local.isoformat(),
                message,
                now.isoformat(),
            ),
        )
        reminder_id = cursor.lastrowid

    schedule_reminder_job(reminder_id, dt_local.isoformat())
    return redirect(url_for("index"))


@app.route("/voice/<int:reminder_id>", methods=["GET", "POST"])
def voice(reminder_id: int):
    with get_connection() as conn:
        reminder = conn.execute(
            "SELECT message FROM reminders WHERE id = ?",
            (reminder_id,),
        ).fetchone()

    response = VoiceResponse()
    if not reminder:
        response.say("No encontré el recordatorio solicitado.", language="es-MX")
    else:
        response.say(reminder["message"], language="es-MX")

    return str(response), 200, {"Content-Type": "application/xml"}


def boot_scheduler() -> None:
    with get_connection() as conn:
        pending = conn.execute(
            "SELECT id, scheduled_at FROM reminders WHERE status = 'pending'"
        ).fetchall()

    now = datetime.now(ZoneInfo(APP_TIMEZONE))
    for reminder in pending:
        run_at = datetime.fromisoformat(reminder["scheduled_at"])
        if run_at >= now:
            schedule_reminder_job(reminder["id"], reminder["scheduled_at"])
        else:
            mark_reminder_status(reminder["id"], "missed")

    if not scheduler.running:
        scheduler.start()


init_db()
boot_scheduler()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
