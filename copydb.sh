#!/bin/bash
# Simple script to copy a file from Google Cloud VM to local directory (no backups, no timestamp)

# === Configuration ===
PROJECT="antan-discord-bot"      # Your GCP project ID
ZONE="us-central1-a"             # Your VM zone
VM_NAME="discord-bot-vm"         # Your VM name

# === Input validation ===
if [ -z "$1" ]; then
  echo "Usage: $0 <remote_file_path>"
  echo "Example: $0 ~/swath-movers/swath_movers.db"
  exit 1
fi

REMOTE_PATH="$1"
FILENAME=$(basename "$REMOTE_PATH")
LOCAL_FILE="./$FILENAME"

echo "📦 Copying from VM..."
echo "   VM:        $VM_NAME"
echo "   Remote:    $REMOTE_PATH"
echo "   Local:     $LOCAL_FILE"
echo ""

# === Run gcloud scp ===
gcloud compute scp \
  --project="$PROJECT" \
  --zone="$ZONE" \
  "$VM_NAME:$REMOTE_PATH" \
  "$LOCAL_FILE"

if [ $? -eq 0 ]; then
  echo "✅ File copied successfully to $LOCAL_FILE"
else
  echo "❌ Copy failed."
  exit 1
fi