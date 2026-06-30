"""Seed database from quiniela CSV and match schedule."""

import csv
import os
import re
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import admin_email_set, get_settings
from app.models import Match, Prediction, User
from app.scoring import recalculate_all_scores
from app.teams import MATCH_KICKOFFS_UTC, get_flag_code, stage_from_match_number

settings = get_settings()

# Optional local/dev seed only — never required for container start
CSV_CANDIDATES = [
    Path(__file__).resolve().parent.parent / "data" / "quiniela.csv",  # backend/data
    Path(__file__).resolve().parents[2] / "data" / "quiniela.csv",      # repo data/ (must be a file)
    Path(__file__).resolve().parents[2] / "quinierla.csv",
]


def _dir_is_writable(directory: Path) -> bool:
    """True if we can create/write a file in directory (mkdir alone is not enough on RO mounts)."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / f".write_probe_{os.getpid()}"
        probe.write_bytes(b"ok")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _quiniela_candidate_dirs() -> list[Path]:
    """Ordered dirs to try for admin uploads. QUINIELA_DATA_DIR wins when set."""
    dirs: list[Path] = []
    env = (os.environ.get("QUINIELA_DATA_DIR") or "").strip()
    if env:
        dirs.append(Path(env))
    dirs.extend(
        [
            Path("/app/data"),
            Path(__file__).resolve().parent.parent / "data",
            Path(tempfile.gettempdir()),
            Path("/tmp"),
        ]
    )
    seen: set[str] = set()
    out: list[Path] = []
    for d in dirs:
        key = str(d.resolve()) if d.exists() else str(d)
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


def quiniela_upload_filename(original_filename: str | None = None) -> str:
    """One-shot upload name: never reused (uuid suffix)."""
    uid = uuid.uuid4().hex
    stem = "quiniela"
    if original_filename:
        base = Path(original_filename).stem
        base = re.sub(r"[^\w.\-]+", "_", base).strip("._")[:40]
        if base:
            stem = base
    return f"{stem}_{uid}.csv"


def find_csv() -> Path | None:
    """Optional bootstrap CSV for first-time seed in local/dev; not required in production."""
    for p in CSV_CANDIDATES:
        try:
            if p.is_file():
                return p
        except OSError:
            continue
    return None


def _normalize_quiniela_bytes(content: bytes | str) -> bytes:
    if isinstance(content, str):
        data = content.encode("utf-8")
    else:
        data = content
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    if not data.strip():
        raise ValueError("Archivo vacío")
    try:
        head = data[:4000].decode("utf-8", errors="replace")
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo: {e}") from e
    if "Partido" not in head and "partido" not in head.lower():
        raise ValueError("El archivo no parece una quiniela (faltan columnas Partido …)")
    return data


def save_uploaded_quiniela(content: bytes | str, filename: str | None = None) -> Path:
    """
    Persist one admin upload as a new file (quiniela_<uuid>.csv). Never overwrites previous uploads.
    """
    data = _normalize_quiniela_bytes(content)
    name = quiniela_upload_filename(filename)
    errors: list[str] = []
    for d in _quiniela_candidate_dirs():
        if not _dir_is_writable(d):
            continue
        dest = d / name
        try:
            dest.write_bytes(data)
            return dest
        except OSError as e:
            errors.append(f"{dest}: {e}")
            continue
    try:
        fd, tmp_name = tempfile.mkstemp(prefix="quiniela_", suffix=f"_{uuid.uuid4().hex}.csv")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return Path(tmp_name)
    except OSError as e:
        detail = "; ".join(errors) if errors else str(e)
        raise OSError(
            f"No hay directorio escribible para subir quiniela (Railway suele montar /app de solo lectura). "
            f"Define QUINIELA_DATA_DIR o usa volumen en /app/data. Intentos: {detail}"
        ) from e


def parse_score(value: str) -> tuple[int, int] | None:
    value = (value or "").strip()
    if not value:
        return None
    m = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", value)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def parse_match_header(header: str) -> tuple[int, str, str, bool]:
    """Returns match_number, home, away, is_placeholder."""
    m = re.match(r"Partido\s+(\d+):\s*(.+)", header.strip())
    if not m:
        return 0, "", "", True
    num = int(m.group(1))
    rest = m.group(2).strip()
    if "Por Definir" in rest:
        return num, rest, rest, True
    if "-" in rest:
        parts = rest.split("-", 1)
        return num, parts[0].strip(), parts[1].strip(), False
    return num, rest, "", False


def _read_csv_tables(csv_path: Path) -> tuple[list[str], list[list[str]], list[tuple[int, int, str, str, bool]]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)

    match_cols: list[tuple[int, int, str, str, bool]] = []
    for col_idx, header in enumerate(headers):
        if not header.startswith("Partido"):
            continue
        num, home, away, ph = parse_match_header(header)
        if num:
            match_cols.append((col_idx, num, home, away, ph))
    return headers, rows, match_cols


def _ensure_matches_from_cols(
    db: Session,
    match_cols: list[tuple[int, int, str, str, bool]],
) -> dict[int, Match]:
    """Create missing Match rows from CSV headers; do not overwrite existing teams/scores."""
    match_by_num: dict[int, Match] = {
        m.match_number: m for m in db.query(Match).all()
    }
    created = 0
    for _, num, home, away, ph in match_cols:
        if num in match_by_num:
            continue
        kickoff_str = MATCH_KICKOFFS_UTC.get(num)
        kickoff = datetime.fromisoformat(kickoff_str) if kickoff_str else None
        stage = stage_from_match_number(num, f"{home}-{away}")
        m = Match(
            match_number=num,
            home_team=home,
            away_team=away,
            home_flag=get_flag_code(home),
            away_flag=get_flag_code(away),
            kickoff=kickoff,
            stage=stage,
            is_placeholder=ph,
        )
        db.add(m)
        match_by_num[num] = m
        created += 1
    if created:
        db.flush()
    return match_by_num


def import_quiniela_predictions(
    db: Session,
    *,
    update_existing: bool = True,
    csv_path: Path | None = None,
) -> dict:
    """
    Import / re-sync predictions from quiniela.csv into an existing DB.

    - Creates users and missing matches as needed.
    - If update_existing=True, overwrites prediction scores from the sheet (for people
      who updated outside the app).
    - If update_existing=False, only inserts missing predictions (original seed behaviour).
    - Does NOT touch official Match results (home_score/away_score/is_finished).
    - Recalculates all points at the end.
    """
    path = csv_path or find_csv()
    if not path:
        return {
            "ok": False,
            "error": "Falta el archivo CSV (sube uno en Admin; no se reutiliza un quiniela.csv fijo).",
        }

    _, rows, match_cols = _read_csv_tables(path)
    if not match_cols:
        return {"ok": False, "error": "No Partido columns in CSV", "csv": str(path)}

    match_by_num = _ensure_matches_from_cols(db, match_cols)

    users_created = 0
    preds_created = 0
    preds_updated = 0
    preds_skipped = 0

    for row in rows:
        if len(row) < 2:
            continue
        email = (row[1] or "").strip().lower()
        if not email or "@" not in email:
            continue
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, name=email.split("@")[0])
            db.add(user)
            db.flush()
            users_created += 1

        for col_idx, num, _, _, _ in match_cols:
            if col_idx >= len(row):
                continue
            score = parse_score(row[col_idx])
            if not score:
                continue
            match = match_by_num.get(num)
            if not match:
                continue
            existing = (
                db.query(Prediction)
                .filter(Prediction.user_id == user.id, Prediction.match_id == match.id)
                .first()
            )
            if existing:
                if not update_existing:
                    preds_skipped += 1
                    continue
                if existing.home_score == score[0] and existing.away_score == score[1]:
                    preds_skipped += 1
                    continue
                existing.home_score = score[0]
                existing.away_score = score[1]
                existing.updated_at = datetime.utcnow()
                preds_updated += 1
            else:
                db.add(
                    Prediction(
                        user_id=user.id,
                        match_id=match.id,
                        home_score=score[0],
                        away_score=score[1],
                    )
                )
                preds_created += 1

    _ensure_admin(db)
    db.commit()
    recalculate_all_scores(db)
    db.commit()

    return {
        "ok": True,
        "csv": str(path),
        "update_existing": update_existing,
        "users_created": users_created,
        "predictions_created": preds_created,
        "predictions_updated": preds_updated,
        "predictions_unchanged_or_skipped": preds_skipped,
        "matches": db.query(Match).count(),
        "users": db.query(User).count(),
    }


def seed_if_empty(db: Session) -> dict:
    match_count = db.query(Match).count()
    if match_count > 0:
        return {"seeded": False, "matches": match_count, "users": db.query(User).count()}

    csv_path = find_csv()
    if not csv_path:
        # Create matches from schedule only
        _seed_matches_only(db)
        _ensure_admin(db)
        return {"seeded": True, "matches": db.query(Match).count(), "users": db.query(User).count(), "csv": None}

    _, rows, match_cols = _read_csv_tables(csv_path)

    match_by_num: dict[int, Match] = {}
    for _, num, home, away, ph in match_cols:
        kickoff_str = MATCH_KICKOFFS_UTC.get(num)
        kickoff = datetime.fromisoformat(kickoff_str) if kickoff_str else None
        stage = stage_from_match_number(num, f"{home}-{away}")
        m = Match(
            match_number=num,
            home_team=home,
            away_team=away,
            home_flag=get_flag_code(home),
            away_flag=get_flag_code(away),
            kickoff=kickoff,
            stage=stage,
            is_placeholder=ph,
        )
        db.add(m)
        match_by_num[num] = m
    db.flush()

    for row in rows:
        if len(row) < 2:
            continue
        email = (row[1] or "").strip().lower()
        if not email or "@" not in email:
            continue
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, name=email.split("@")[0])
            db.add(user)
            db.flush()

        for col_idx, num, _, _, _ in match_cols:
            if col_idx >= len(row):
                continue
            score = parse_score(row[col_idx])
            if not score:
                continue
            match = match_by_num.get(num)
            if not match:
                continue
            existing = (
                db.query(Prediction)
                .filter(Prediction.user_id == user.id, Prediction.match_id == match.id)
                .first()
            )
            if existing:
                continue
            pred = Prediction(
                user_id=user.id,
                match_id=match.id,
                home_score=score[0],
                away_score=score[1],
            )
            db.add(pred)

    _ensure_admin(db)
    db.commit()
    recalculate_all_scores(db)
    db.commit()

    return {
        "seeded": True,
        "matches": db.query(Match).count(),
        "users": db.query(User).count(),
        "csv": str(csv_path),
    }


def _seed_matches_only(db: Session) -> None:
    for num in range(1, 105):
        kickoff_str = MATCH_KICKOFFS_UTC.get(num)
        kickoff = datetime.fromisoformat(kickoff_str) if kickoff_str else None
        ph = num > 72
        home = away = "Por Definir" if ph else f"Team{num}A"
        m = Match(
            match_number=num,
            home_team=home,
            away_team=away,
            home_flag=get_flag_code(home),
            away_flag=get_flag_code(away),
            kickoff=kickoff,
            stage=stage_from_match_number(num, home),
            is_placeholder=ph,
        )
        db.add(m)
    db.flush()


def _ensure_admin(db: Session) -> None:
    """Promote / create all configured admin emails (all environments)."""
    for email in admin_email_set():
        admin = db.query(User).filter(User.email == email).first()
        if not admin:
            label = "Super Admin" if email == settings.super_admin_email.lower() else email.split("@")[0]
            admin = User(email=email, name=label, is_admin=True)
            db.add(admin)
        else:
            admin.is_admin = True
    # Anyone already in DB with a configured admin email gets the flag (e.g. seeded from CSV)
    for u in db.query(User).filter(User.email.in_(list(admin_email_set()))).all():
        u.is_admin = True
    db.flush()


def refresh_kickoffs_from_schedule(db: Session) -> dict:
    """Re-apply MATCH_KICKOFFS_UTC onto existing rows (safe; does not wipe scores).

    Call on every startup so schedule fixes ship without DB reset.
    Always overwrites stored kickoff when it differs from the code schedule so fixes
    like #39 Cabo Verde–Uruguay (real 21 Jun 22:00 UTC, not 22 Jun 16:00) propagate.
    """
    from app.teams import SCHEDULE_REVISION

    updated = 0
    for m in db.query(Match).all():
        kickoff_str = MATCH_KICKOFFS_UTC.get(m.match_number)
        if not kickoff_str:
            continue
        new_ko = datetime.fromisoformat(kickoff_str)
        if m.kickoff == new_ko:
            continue
        m.kickoff = new_ko
        updated += 1
    if updated:
        db.flush()
    return {"kickoffs_updated": updated, "schedule_revision": SCHEDULE_REVISION}
