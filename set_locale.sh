
#!/bin/bash
# Guaranteed locale fix

# Set to C.UTF-8 (always available)
sudo update-locale LANG=C.UTF-8 LC_ALL=C.UTF-8 LANGUAGE=C

# Apply to current session
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export LANGUAGE=C

echo "✅ Locale fixed! Warnings will be gone in new terminals."
echo "Current settings:"
locale
EOF
