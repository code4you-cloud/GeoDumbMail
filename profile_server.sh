##!/bin/bash
#
## Abilita il debugging
#set -x
#
## Variabili di configurazione
#CMD_POETRY="/root/.local/bin/poetry"
#PROJECT_DIR="/home/remote/GeoDumbMail"
#LOGFILE="$PROJECT_DIR/django_server.log"
#MAIL_RECIPIENT="system@code4you.cloud"
#
##cd /home/remote/GeoDumbMail
#SERVER_CMD="$CMD_POETRY run python manage.py runserver 0.0.0.0:8000 &"
#
#echo "Avviando il server Django..."
#if eval "$SERVER_CMD"; then
#    echo "Server Django avviato correttamente."
#else
#    echo "Errore: impossibile avviare il server Django con Poetry." >&2
#    exit 1
#fi
#
## Funzione per avviare il server Django
#start_django_server() {
#    echo "Starting Django server..."
#    cd "$PROJECT_DIR" || exit
#    nohup $SERVER_CMD > $LOGFILE 2>&1 &
#}
#
## Funzione per verificare se il server Django è in esecuzione
#is_django_running() {
#    pgrep -f "manage.py runserver" > /dev/null
#}
#
## Funzione per inviare una mail se il server non è in esecuzione
#send_alert_email() {
#    echo "Django server is down! Attempting to restart..." | mail -s "Test Subject" "$MAIL_RECIPIENT"
#}
#
## Controlla se il server Django è in esecuzione, altrimenti avvialo e manda una mail
#if is_django_running; then
#    echo "Django image.citylog.cloud server is running."
#    send_alert_email
#else
#    echo "Django image.citylog.cloud server is NOT running."
#    send_alert_email
#    start_django_server
#fi
#
## Disabilita il debugging
#set +x
#

#!/bin/bash
set -x

SERVICE_NAME="runserver"
PORT=8000
PROJECT_DIR="/home/remote/GeoDumbMail"
VENV_PATH="/home/remote/venv"  # <-- Modifica se usi un virtualenv o poetry shell
NOTIFY_EMAIL="system@code4you.cloud"
LOG_FILE="/var/log/django_monitor.log"
ERR_LOG_FILE="/var/log/django_monitor_error.log"

HOSTNAME=$(hostname)
IP_ADDRESS=$(hostname -I | awk '{print $1}')
CURRENT_DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Controlla se qualcosa è in ascolto sulla porta
if ! ss -ltn | grep -q ":$PORT"; then
    echo "$CURRENT_DATE: $SERVICE_NAME non è attivo su $HOSTNAME ($IP_ADDRESS). Riavvio..." >> "$LOG_FILE"

    cd "$DJANGO_PROJECT_DIR" || {
        echo "$CURRENT_DATE: ERRORE: Impossibile accedere a $DJANGO_PROJECT_DIR" >> "$ERR_LOG_FILE"
        exit 1
    }

    # Attiva l’ambiente virtuale
    source "$VENV_PATH/bin/activate"

    # Avvia il server e cattura eventuali errori
    nohup python manage.py runserver 0.0.0.0:$PORT >> "$LOG_FILE" 2>> "$ERR_LOG_FILE" &

    sleep 5  # aspetta un attimo per dare tempo al server di partire

    # Controlla di nuovo se è partito correttamente
    if ss -ltn | grep -q ":$PORT"; then
        echo "$CURRENT_DATE: Il servizio Django è stato avviato con successo sulla porta $PORT." >> "$LOG_FILE"
        echo -e "Data: $CURRENT_DATE\nHostname: $HOSTNAME\nIP Address: $IP_ADDRESS\nIl servizio Django è stato riavviato correttamente." \
            | mail -s "Django runserver riavviato" "$NOTIFY_EMAIL"
    else
        echo "$CURRENT_DATE: ERRORE: Fallito il riavvio del servizio Django!" >> "$ERR_LOG_FILE"
        echo -e "Data: $CURRENT_DATE\nHostname: $HOSTNAME\nIP Address: $IP_ADDRESS\n**ATTENZIONE**: Django non si è avviato correttamente." \
            | mail -s "ERRORE: Django non si è riavviato" "$NOTIFY_EMAIL"
    fi
else
    echo "$CURRENT_DATE: $SERVICE_NAME è attivo su $HOSTNAME ($IP_ADDRESS)." >> "$LOG_FILE"
fi

set +x

