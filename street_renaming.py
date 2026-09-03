# test_simulazione.py (nella root del progetto)
import os
import django

# 1. Inizializza le impostazioni di Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GeoDumbMail.settings')  # Sostituisci con il nome reale
django.setup()

# 2. Importa il modello e la funzione dal tuo path reale
from emails.models import EmailData
from emails.services.street_renaming import build_report_code

def simula():
    print("=== AVVIO SIMULAZIONE DI RINOMINAZIONE (DRY-RUN) ===\n")

    # Legge un campione di 20 record senza toccare il DB
    campione = EmailData.objects.all()[:20]

    for s in campione:
        # Recupera i campi reali (adatta se i nomi dei campi differiscono)
        address = getattr(s, 'indirizzo', getattr(s, 'address', None))
        image_id = getattr(s, 'image_id', None)

        # Genera il nome simulato
        nuovo_codice = build_report_code(address, image_id)

        print(f"ID: {s.pk:<5} | Indirizzo: {str(address):<30} | Simulato: {nuovo_codice}")

if __name__ == '__main__':
    simula()
