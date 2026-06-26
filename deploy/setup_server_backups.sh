#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/astrobot/app"
DB_PATH="$APP_DIR/astrobot.db"
BACKUP_DIR="/opt/astrobot/backups"
BACKUP_SCRIPT="/usr/local/bin/backup-astrobot-db"
SERVICE_PATH="/etc/systemd/system/astrobot-backup.service"
TIMER_PATH="/etc/systemd/system/astrobot-backup.timer"

if ! id astrobot >/dev/null 2>&1; then
  echo "User astrobot not found. Run the server setup first." >&2
  exit 1
fi

if [ ! -d "$APP_DIR" ]; then
  echo "App directory not found: $APP_DIR" >&2
  exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y sqlite3

install -d -m 700 -o astrobot -g astrobot "$BACKUP_DIR"

cat > "$BACKUP_SCRIPT" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

DB_PATH="/opt/astrobot/app/astrobot.db"
BACKUP_DIR="/opt/astrobot/backups"
KEEP_DAYS="${KEEP_DAYS:-14}"

if [ ! -f "$DB_PATH" ]; then
  echo "Database not found: $DB_PATH" >&2
  exit 1
fi

install -d -m 700 -o astrobot -g astrobot "$BACKUP_DIR"

timestamp="$(date +%F-%H%M%S)"
tmp_path="$BACKUP_DIR/astrobot-$timestamp.db.tmp"
backup_path="$BACKUP_DIR/astrobot-$timestamp.db"

sqlite3 "$DB_PATH" ".backup '$tmp_path'"
mv "$tmp_path" "$backup_path"
chown astrobot:astrobot "$backup_path"
chmod 600 "$backup_path"

find "$BACKUP_DIR" -type f -name 'astrobot-*.db' -mtime "+$KEEP_DAYS" -delete

echo "backup_created=$backup_path"
EOF

chmod 700 "$BACKUP_SCRIPT"

cat > "$SERVICE_PATH" <<'EOF'
[Unit]
Description=Backup Astrobot SQLite database

[Service]
Type=oneshot
ExecStart=/usr/local/bin/backup-astrobot-db
EOF

cat > "$TIMER_PATH" <<'EOF'
[Unit]
Description=Daily Astrobot database backup

[Timer]
OnCalendar=*-*-* 03:30:00
Persistent=true
RandomizedDelaySec=10m

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now astrobot-backup.timer
systemctl start astrobot-backup.service

systemctl is-active astrobot-backup.timer
systemctl --no-pager --full status astrobot-backup.service || true
systemctl list-timers --all --no-pager | grep astrobot-backup || true
ls -lh "$BACKUP_DIR"
