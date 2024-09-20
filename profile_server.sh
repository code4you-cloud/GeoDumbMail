#!/bin/bash

# Abilita il debugging
set -x

# Variabili di configurazione
PROJECT_DIR="/home/remote/GeoDumbMail"
LOGFILE="$PROJECT_DIR/django_server.log"
MAIL_RECIPIENT="system@code4you.cloud"
SERVER_CMD="poetry run python manage.py runserver 0.0.0.0:8000"

# Funzione per avviare il server Django
start_django_server() {
    echo "Starting Django server..."
    cd "$PROJECT_DIR" || exit
    nohup $SERVER_CMD > $LOGFILE 2>&1 &
}

# Funzione per verificare se il server Django è in esecuzione
is_django_running() {
    pgrep -f "manage.py runserver" > /dev/null
}

# Funzione per inviare una mail se il server non è in esecuzione
send_alert_email() {
    echo "Django server is down! Attempting to restart..." | msmtp --debug -a default "$MAIL_RECIPIENT"
}

# Controlla se il server Django è in esecuzione, altrimenti avvialo e manda una mail
if is_django_running; then
    echo "Django server is running."
else
    echo "Django server is NOT running."
    send_alert_email
    start_django_server
fi

# Disabilita il debugging
set +x

