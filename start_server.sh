#!/bin/bash

# Enable debugging
set -x

# Configuration variables
PROJECT_DIR="/home/remote/GeoDumbMail"
LOGFILE="$PROJECT_DIR/django_server.log"
MAIL_RECIPIENT="system@code4you.cloud"
SERVER_CMD="poetry run python manage.py runserver 0.0.0.0:8000"

# Function to start the Django server
start_django_server() {
    echo "Starting Django server..."
    cd "$PROJECT_DIR" || exit
    nohup $SERVER_CMD > $LOGFILE 2>&1 &
}

# Function to check if the Django server is running
is_django_running() {
    pgrep -f "manage.py runserver" > /dev/null
}

# Function to send an alert email if the server is not running
send_alert_email() {
    SUBJECT="Django Server Alert"
    BODY="Django server is down! Attempting to restart..."
    echo "$BODY" | mail -s "$SUBJECT" -r "report@citylog.cloud" "$MAIL_RECIPIENT"
}

# Check if the Django server is running, otherwise start it and send an email
if is_django_running; then
    echo "Django server is running."
else
    echo "Django server is NOT running."
    send_alert_email
    start_django_server
fi

# Disable debugging
set +x
