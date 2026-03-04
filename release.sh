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

# ── 4. Zip (rename .exe → .bin so Gmail doesn't block the attachment) ─
ZIP="target/InkDensityTool.zip"
BIN="target/ink-density-tool.bin"
cp target/x86_64-pc-windows-gnu/release/ink-density-tool.exe "$BIN"
rm -f "$ZIP"
zip -j "$ZIP" "$BIN"
echo "Zipped: $ZIP"

# ── 5. Email with attachment ──────────────────────────────────────────
python3 - "$SMTP_USER" "$SMTP_PASS" "$SMTP_TO" "$ZIP" <<'PYEOF'
import sys, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os

user, pw, to, zip_path = sys.argv[1:]

msg = MIMEMultipart()
msg['From'] = user
msg['To'] = to
msg['Subject'] = "InkDensityTool build ready"
msg.attach(MIMEText(
    "Latest build attached.\n\n"
    "The exe is renamed to .bin to get past Gmail.\n"
    "On Windows: extract, then rename ink-density-tool.bin → ink-density-tool.exe",
    'plain'
))

with open(zip_path, 'rb') as f:
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="InkDensityTool.zip"')
    msg.attach(part)

with smtplib.SMTP('smtp.gmail.com', 587) as s:
    s.ehlo()
    s.starttls()
    s.login(user, pw)
    s.sendmail(user, to, msg.as_string())
    print(f"Sent to {to}")
PYEOF
