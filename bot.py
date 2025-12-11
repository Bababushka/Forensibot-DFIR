import asyncio  # Python's asynchronous I/O framework; enables async functions used by the bot
import logging  # Standard logging for visibility into bot actions (case creation, file saves, analysis)
import os  # Access environment variables loaded from .env
import uuid  # Generate random unique case IDs
from pathlib import Path  # Modern path handling for files/folders
from typing import Optional  # Type hint for functions that may return a Path or None
from zipfile import ZipFile  # Used to extract uploaded .zip archives

from dotenv import load_dotenv  # Loads environment variables from .env (e.g., TELEGRAM_BOT_TOKEN)
from telegram import Update  # Telegram update object representing incoming messages/commands
from telegram.constants import ChatAction  # Chat actions like TYPING/UPLOAD_DOCUMENT for UX feedback
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Analysis modules
# Import the core DFIR processing functions from our analysis package. These perform hashing,
# metadata extraction, log parsing, browser history parsing, timeline building, and report writing.
from analysis import (
    compute_hashes_for_case,
    extract_metadata_for_case,
    parse_logs_for_case,
    parse_browser_history,
    build_timeline,
    write_report,
)


# Configure logging early; INFO provides helpful runtime feedback without being verbose
# Format includes time, level, and message for quick debugging.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# Base directories
BASE_DIR = Path(__file__).parent  # Project root directory
CASES_DIR = BASE_DIR / "cases"  # Where per-case evidence is stored
REPORTS_DIR = BASE_DIR / "reports"  # Where generated Markdown reports are saved


def _ensure_dirs() -> None:
    """Ensure runtime directories exist for cases and reports.

    Creating these at startup guarantees uploads and reports can be written.
    """
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _generate_case_id() -> str:
    """Generate a short case ID using the first 8 characters of a UUID4.

    Short IDs are easy to read and reference in chat, while remaining unique.
    """
    return uuid.uuid4().hex[:8]


def _safe_extract_zip(zip_path: Path, dest_dir: Path) -> int:
    """Safely extract a ZIP archive into dest_dir, preventing path traversal.

    Path traversal protection ensures files from the archive cannot escape
    the case folder by using malicious paths like '../../outside'.

    Returns the number of extracted members.
    """
    count = 0
    with ZipFile(zip_path) as zf:
        for member in zf.infolist():
            # Skip directories
            if member.is_dir():
                continue
            # Normalize member path and prevent traversal outside dest_dir
            member_path = Path(member.filename)
            # Join and resolve to ensure containment
            target_path = (dest_dir / member_path).resolve()
            if not str(target_path).startswith(str(dest_dir.resolve())):
                # Skip dangerous member
                continue
            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, target_path.open("wb") as dst:
                dst.write(src.read())
                count += 1
    return count


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start: send a welcome message with usage instructions.

    This primes the user on the key commands and the workflow for case setup
    and evidence analysis.
    """
    text = (
        "Welcome to DFIR Case Automation Bot!\n\n"
        "Use /newcase to create a case.\n"
        "After creating a case, upload evidence files or a .zip.\n"
        "Then run /analyze to process the evidence and receive a Markdown report."
    )
    await update.message.reply_text(text)


async def newcase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /newcase: create a per-user case directory and store the case_id.

    Each user gets their own current case, tracked via context.user_data.
    """
    case_id = _generate_case_id()
    case_path = CASES_DIR / case_id
    case_path.mkdir(parents=True, exist_ok=True)

    # Store case_id in user-specific context
    context.user_data["case_id"] = case_id

    logger.info("Created new case %s at %s for user %s", case_id, case_path, update.effective_user.id)
    await update.message.reply_text(
        f"New case created: {case_id}\n"
        f"Upload evidence files or a .zip to this chat; they will be saved to cases/{case_id}."
    )


async def _save_document(update: Update, context: ContextTypes.DEFAULT_TYPE, case_path: Path) -> Optional[Path]:
    """Save an uploaded Telegram Document to the case directory.

    Telegram 'document' messages cover generic files, including ZIP archives.
    Returns the saved file path, or None if saving fails.
    """
    if not update.message or not update.message.document:
        return None

    doc = update.message.document
    file = await doc.get_file()
    filename = doc.file_name or f"document_{doc.file_unique_id}"
    dest = case_path / filename
    await file.download_to_drive(custom_path=str(dest))
    logger.info("Saved document to %s", dest)
    return dest


async def _save_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, case_path: Path) -> Optional[Path]:
    """Save an uploaded Telegram photo (choose the highest resolution variant).

    Photos arrive as multiple sizes; we pick the last (highest resolution) for analysis.
    """
    if not update.message or not update.message.photo:
        return None
    photo = update.message.photo[-1]
    file = await photo.get_file()
    # Photos may not have filenames; use a generated name
    dest = case_path / f"photo_{photo.file_unique_id}.jpg"
    await file.download_to_drive(custom_path=str(dest))
    logger.info("Saved photo to %s", dest)
    return dest


async def handle_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle file/photo uploads: save to the current case and extract ZIPs.

    If a case is not set, the user is guided to create one first.
    ZIP archives are extracted and the original archive is removed to reduce clutter.
    """
    case_id = context.user_data.get("case_id")
    if not case_id:
        await update.message.reply_text("Create a case first with /newcase.")
        return
    case_path = CASES_DIR / case_id
    case_path.mkdir(parents=True, exist_ok=True)

    await update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)

    saved_path: Optional[Path] = None
    if update.message.document:
        saved_path = await _save_document(update, context, case_path)
    elif update.message.photo:
        saved_path = await _save_photo(update, context, case_path)

    if not saved_path:
        await update.message.reply_text("No file found in the message.")
        return

    # If the uploaded file is a ZIP, extract it and delete the archive
    if saved_path.suffix.lower() == ".zip":
        try:
            count = _safe_extract_zip(saved_path, case_path)
            saved_path.unlink(missing_ok=True)
            logger.info("Extracted %d files from %s", count, saved_path.name)
            await update.message.reply_text(f"Zip extracted: {count} files added to case {case_id}.")
        except Exception as e:
            logger.exception("Failed to extract ZIP: %s", e)
            await update.message.reply_text("Failed to extract ZIP archive.")
    else:
        await update.message.reply_text(f"Saved file to case {case_id}: {saved_path.name}")


async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /analyze: run the analysis pipeline and send back a Markdown report.

    The pipeline: hashing -> metadata -> logs -> browser -> timeline -> report.
    """
    case_id = context.user_data.get("case_id")
    if not case_id:
        await update.message.reply_text("Create a case first with /newcase.")
        return

    case_path = CASES_DIR / case_id
    if not case_path.exists():
        await update.message.reply_text("Case folder not found; create a new case with /newcase.")
        return

    logger.info("Starting analysis for case %s", case_id)
    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        # Hashing
        hashes = compute_hashes_for_case(case_path)

        # Metadata extraction
        metadata = extract_metadata_for_case(case_path)

        # Logs parsing
        log_events = parse_logs_for_case(case_path)

        # Browser history parsing
        browser_events = parse_browser_history(case_path)

        # Timeline build
        events = log_events + browser_events
        timeline = build_timeline(events)

        # Report generation
        report_path = write_report(
            case_id=case_id,
            case_path=case_path,
            hashes=hashes,
            metadata=metadata,
            timeline=timeline,
            reports_dir=REPORTS_DIR,
        )

        # Send report back to the user
        await update.message.reply_document(document=report_path.open("rb"), caption="DFIR Report")
        logger.info("Analysis complete for case %s; report at %s", case_id, report_path)
    except Exception as e:
        logger.exception("Analysis failed: %s", e)
        await update.message.reply_text("Analysis failed due to an internal error.")


def main() -> None:
    """Entrypoint: load token, ensure dirs, and start the bot application.

    This wires commands and message handlers, then uses polling to receive updates.
    """
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env")

    _ensure_dirs()

    app = ApplicationBuilder().token(token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newcase", newcase))
    app.add_handler(CommandHandler("analyze", analyze))

    # Upload handlers: documents and photos
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_upload))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()