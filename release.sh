#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── 1. Load credentials ──────────────────────────────────────────────
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  echo "ERROR: .env file not found. Copy .env.example and fill in credentials."
  exit 1
fi
# shellcheck source=.env
source "$SCRIPT_DIR/.env"

# ── 2. Commit & push ─────────────────────────────────────────────────
MSG="${1:-build: release $(date '+%Y-%m-%d')}"
cd "$SCRIPT_DIR"
git add -A
git commit -m "$MSG" || echo "(nothing to commit)"
git push origin rust-version

# ── 3. Build ─────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/data-export/ink-density-tool-rs"
cargo build --release --target x86_64-pc-windows-gnu

# ── 4. Zip ───────────────────────────────────────────────────────────
ZIP="target/InkDensityTool.zip"
rm -f "$ZIP"
zip -j "$ZIP" target/x86_64-pc-windows-gnu/release/ink-density-tool.exe
echo "Zipped: $ZIP"

# ── 5. Upload to Google Drive & email link ────────────────────────────
DRIVE_FOLDER="InkDensityTool-builds"
rclone copy "$ZIP" "gdrive:$DRIVE_FOLDER/"
DOWNLOAD_URL=$(rclone link "gdrive:$DRIVE_FOLDER/InkDensityTool.zip")
echo "Drive link: $DOWNLOAD_URL"

python3 - "$SMTP_USER" "$SMTP_PASS" "$SMTP_TO" "$DOWNLOAD_URL" <<'PYEOF'
import sys, smtplib
from email.mime.text import MIMEText

user, pw, to, url = sys.argv[1:]

msg = MIMEText(
    f"Latest InkDensityTool build is ready on Google Drive:\n\n{url}\n\n"
    "(Sign in with your personal Google account to download.)",
    'plain'
)
msg['From'] = user
msg['To'] = to
msg['Subject'] = "InkDensityTool build ready"

with smtplib.SMTP('smtp.gmail.com', 587) as s:
    s.ehlo()
    s.starttls()
    s.login(user, pw)
    s.sendmail(user, to, msg.as_string())
    print(f"Sent to {to}")
PYEOF
