#!/bin/bash

LOG_FILE="/var/log/update_crafty.log"

# Redirect all following output to the log file AND show it in the terminal
exec > >(tee -a "$LOG_FILE") 2>&1

PROJECT_DIR="/home/debian/crafty/docker"
DATA_DIR="/home/debian/crafty"

# Move to the directory
cd "$PROJECT_DIR" || exit 1

# Pull and capture the status message
# We use '2>&1' to catch errors and standard output together
PULL_RESULT=$(sudo docker compose pull 2>&1)

# Check if the result contains the 'newer image' string
if [[ "$PULL_RESULT" == *"Downloaded newer image"* ]]; then
    # Recreate container with updated image
    sudo docker compose up -d

    # Clean up old image layers
    sudo docker image prune -f

    # Ensure permissions remain correct
    sudo chown -R 1000:1000 "$DATA_DIR"
    sudo chmod -R 775 "$DATA_DIR"
fi

# Wait before health check..."
sleep 15

# --- Health Check Section ---
# -k: Ignore SSL warnings
# -s: Silent mode
# -o /dev/null: Don't print the HTML output
# -w: Print the HTTP status code
HTTP_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" "$PANEL_URL")

if [ "$HTTP_STATUS" -eq 200 ] || [ "$HTTP_STATUS" -eq 302 ]; then
    echo "Health Check: OK $HTTP_STATUS"
else
    echo "Health Check: FAILED $HTTP_STATUS"
    echo "Check logs with: sudo docker compose logs --tail=20"
fi
