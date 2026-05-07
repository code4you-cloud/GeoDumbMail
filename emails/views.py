import imaplib
import email
import re
import ssl
import sqlite3
import logging
import os
import requests
import datetime

import psycopg2
from psycopg2 import sql

from django.shortcuts import render
from django.utils import timezone

# Create your views here.
from django.http import HttpResponse

# new from AI
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Count, Q
from django.db import transaction
from django.conf import settings

from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseRedirect

from .models import EmailData  # Importa il modello se hai definito uno in models.py

# Configura il logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Funzione per collegarsi al server IMAP e recuperare tutte le email non lette
def fetch_unread_emails():
    # Connessione con SSL/TLS usando porta 993
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)  # Solo per alcune versioni di Python
    context.set_ciphers('HIGH:!DH:!aNULL')

    # Connessione al server IMAP
    mail = imaplib.IMAP4_SSL(settings.SERVER_IMAP, port=993, ssl_context=context)
    #mail = imaplib.IMAP4_SSL('in.citylog.cloud', port=993, ssl_context=context)
    mail.login(settings.MAIL_TO_GET_REPORT, settings.PWD_TO_GET_REPORT)  # Sostituisci con le tue credenziali
    mail.select('inbox')

    # Cerca tutte le email non lette
    status, messages = mail.search(None, 'UNSEEN')

    # Controlla se ci sono messaggi non letti
    email_ids = messages[0].split() if messages[0] else []

    unread_emails = []

    # Itera su tutte le email non lette
    for email_id in email_ids:
        status, msg_data = mail.fetch(email_id, '(RFC822)')
        raw_email = msg_data[0][1]

        # Decodifica l'email
        email_message = email.message_from_bytes(raw_email)
        unread_emails.append(email_message)

    return mail, email_ids, unread_emails

def parse_email_content(email_message):
    text_content = ""
    image_file_path = None
    image_instance = EmailData()  # Prepara l'istanza

    for part in email_message.walk():
        content_type = part.get_content_type()

        if part.is_multipart():
            continue

        if content_type == 'text/plain':
            text_content += part.get_payload(decode=True).decode('utf-8', errors='replace')
            text_content = text_content.replace('\r\n', '\n')

        elif content_type.startswith('image/'):
            image_filename = part.get_filename()
            if not image_filename:
                image_filename = f"image_{timezone.now().strftime('%Y%m%d%H%M%S')}.jpg"

            image_data = part.get_payload(decode=True)

            # Usa ContentFile invece di scrivere su disco
            content_file = ContentFile(image_data, name=image_filename)

            # Salva direttamente sul modello usando lo storage configurato
            image_instance.image_file.save(image_filename, content_file, save=False)

    import sys
    sys.stderr.write("\n========== DEBUG TEXT_CONTENT ==========\n")
    sys.stderr.write(repr(text_content))
    sys.stderr.write("\n========================================\n")
    sys.stderr.write(f"Contains 'DateTime'? {'DateTime' in text_content}\n")
    sys.stderr.write(f"Contains '**DateTime**'? {'**DateTime**' in text_content}\n")

    if text_content:
        # Parsing delle informazioni
        latitude = re.search(r'Latitude:\s*([\d\.\-]+)', text_content)
        longitude = re.search(r'Longitude:\s*([\d\.\-]+)', text_content)
        city = re.search(r'\*\*City:\*\*\s*(.+)', text_content)
        address = re.search(r'\*\*Address:\*\*\s*(.+)', text_content)
        image_id = re.search(r'\*\*ImageID:\*\*\s*([a-f0-9\-]+)', text_content)
        logger.debug(f"Corpo email (primi 500 char): {text_content[:500]}")
        logger.debug(f"Contains DateTime? {'DateTime' in text_content}")
        logger.debug(f"Position: {text_content.find('DateTime')}")

        # --- Rilettura email datate e conversione data
        # --- Estrazione image_time con debug ---
        image_time = None  # inizializza
        if 'DateTime' in text_content:
            pos = text_content.find('DateTime')
            snippet = text_content[pos:pos+80]
            logger.debug(f"REPR snippet: {repr(snippet)}")

            # Regex che ignora qualsiasi carattere non-digit tra DateTime e la data
            match = re.search(r'DateTime[^0-9]*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', text_content)
            if match:
                image_time_str = match.group(1)
                logger.debug(f"✅ Data estratta (stringa): {image_time_str}")
                # Conversione da stringa a datetime naive
                try:
                    naive_dt = datetime.datetime.strptime(image_time_str, '%Y-%m-%d %H:%M:%S')
                    # Rendi timezone-aware usando il fuso orario di default (es. settings.TIME_ZONE)
                    image_time = timezone.make_aware(naive_dt)
                    logger.debug(f"✅ Data convertita (aware): {image_time}")
                except ValueError as e:
                    logger.error(f"Errore conversione data '{image_time_str}': {e}")
                    image_time = None
            else:
                # Fallback: cerca qualsiasi data nel testo
                fallback = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', text_content)
                if fallback:
                    image_time_str = fallback.group(1)
                    logger.debug(f"✅ Data trovata con fallback: {image_time_str}")
                    try:
                        naive_dt = datetime.datetime.strptime(image_time_str, '%Y-%m-%d %H:%M:%S')
                        image_time = timezone.make_aware(naive_dt)
                        logger.debug(f"✅ Data convertita (aware): {image_time}")
                    except ValueError as e:
                        logger.error(f"Errore conversione data (fallback) '{image_time_str}': {e}")
                        image_time = None
                else:
                    logger.debug("❌ Nessuna data trovata nel testo")
        else:
            logger.debug("❌ 'DateTime' non trovato nel corpo")

        # Assegnazione al modello (assicurati che image_instance esista)
        #image_time = re.search(r'DateTime[^:]*:?\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', text_content)
        #image_time = re.search(r'\*\*DateTime\*\*:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', text_content)
        ###
        user_id = re.search(r'\*\*UserID:\*\*\s*([^\n\r]+)', text_content) #intercept both authentication
        #user_id = re.search(r'\*\*UserID:\*\*\s*(\d+)', text_content) #intercept only facebook user_id

        image_instance.latitude = latitude.group(1) if latitude else None
        image_instance.longitude = longitude.group(1) if longitude else None
        image_instance.city = city.group(1) if city else None
        image_instance.address = address.group(1) if address else None
        logger.debug(f"IMAGE_TIME: {image_time}")
        image_instance.image_time = image_time
        #image_instance.image_time = image_time.group(1) if image_time else None
        #image_instance.image_time = timezone.now()
        image_instance.image_id = image_id.group(1) if image_id else None
        ###
        raw_user_id = user_id.group(1).strip() if user_id else None #bothe F anf G
        #facebook_id = user_id.group(1).strip() if user_id else None #bothe F anf G
        #facebook_id = user_id.group(1) if user_id else None #facebook only
        #image_instance.user_id = user_id.group(1) if user_id else None

        # Salvo solo l'ID interno nel DB Django
        #image_instance.user_id = user_id_int
        logger.debug(f"RAW USER ID: {raw_user_id}")
        # ---- identificazione tipologia utente facebook | google
        user_id_int = None

        if raw_user_id:
            provider = "google" if raw_user_id.isdigit() and len(raw_user_id) > 18 else "facebook"
            logger.debug(f"Provider rilevato: {provider}")

            try:
                url = f"{settings.FASTAPI_BASE_URL}/{provider}/{raw_user_id}"
                resp = requests.get(url, timeout=5)

                logger.debug(f"REQUEST URL: {url}")
                logger.debug(f"STATUS: {resp.status_code}")
                logger.debug(f"RESPONSE: {resp.text}")

                if resp.status_code == 200:
                    data = resp.json()
                    user_id_int = data.get("id")

                    if user_id_int:
                        logger.debug(f"User id int: {user_id_int}")
                    else:
                        logger.debug(f"ID non trovato nella risposta: {data}")
                else:
                    logger.debug(f"FastAPI error: {resp.status_code} {resp.text}")

            except Exception as e:
                logger.debug(f"Errore chiamata FastAPI: {e}")

        image_instance.user_id = user_id_int

        # Solo se l'immagine è presente
        if image_instance.image_file:
            image_instance.image_url = image_instance.image_file.url

        image_instance.save()

        return {
            'latitude': image_instance.latitude,
            'longitude': image_instance.longitude,
            'city': image_instance.city,
            'address': image_instance.address,
            'image_time': image_instance.image_time,
            'image_id': image_instance.image_id,
            'image_url': image_instance.image_url,
            'image_file': image_instance.image_file.url if image_instance.image_file else None,
            ###
            #'user_id': image_instance.user_id
        }

    return None

# ORM django compatibile
def save_to_postgresql(latitude, longitude, city, address, image_id, image_time, image_url, image_file=None, status=0):
    """
    Salva o aggiorna un record nel database PostgreSQL usando l'ORM di Django.

    Argomenti:
        - image_time: datetime object (timezone-aware) o stringa convertibile
        - image_file: percorso/URL del file (opzionale)
        - status: intero (default 0)
    """
    # Se image_time è una stringa, convertirla in datetime aware
    if isinstance(image_time, str):
        from datetime import datetime
        naive = datetime.strptime(image_time, '%Y-%m-%d %H:%M:%S')
        image_time = timezone.make_aware(naive)

    obj, created = EmailData.objects.update_or_create(
        image_id=image_id,
        defaults={
            'latitude': latitude,
            'longitude': longitude,
            'city': city,
            'address': address,
            'image_time': image_time,
            'image_url': image_url,
            'image_file': image_file,
            'status': status,
        }
    )
    action = "creato" if created else "aggiornato"
    print(f"Record {action} per image_id {image_id} (PK={obj.pk})")
    return obj


# Funzione per salvare i dati in SQLite
def save_to_sqlite(latitude, longitude, city, address, image_id, image_time, image_url, db_path='emails.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS email_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL,
            longitude REAL,
            city TEXT,
            address TEXT,
            image_id TEXT,
            image_time TEXT,
            image_url TEXT
        )
    ''')
    # Usa INSERT OR REPLACE: se image_id esiste, aggiorna tutte le colonne
    c.execute('''
        INSERT OR REPLACE INTO email_data
        (id, latitude, longitude, city, address, image_id, image_time, image_url)
        VALUES (
            COALESCE((SELECT id FROM email_data WHERE image_id = ?), NULL),
            ?, ?, ?, ?, ?, ?, ?
        )
    ''', (image_id, latitude, longitude, city, address, image_id, image_time, image_url))
    conn.commit()
    conn.close()

# Funzione per salvare i dati in SQLite
def save_to_sqlite__(latitude, longitude, city, address, image_id, image_time, image_url, db_path='emails.db'):
    """
    Salva i dati in SQLite.
    - db_path: percorso del database (default 'emails.db'; usa ':memory:' per test in RAM)
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS email_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL,
            longitude REAL,
            city TEXT,
            address TEXT,
            image_id TEXT,
            image_time TEXT,
            image_url TEXT
        )
    ''')

    c.execute("SELECT * FROM email_data WHERE image_id = ?", (image_id,))
    row = c.fetchone()
    if row:
        print(f"Duplicate ImageID detected: {image_id}")
    else:
        # Usa INSERT OR REPLACE: se image_id esiste, aggiorna tutte le colonne
        c.execute('''
            INSERT OR REPLACE INTO email_data
            (id, latitude, longitude, city, address, image_id, image_time, image_url)
            VALUES (
                COALESCE((SELECT id FROM email_data WHERE image_id = ?), NULL),
                ?, ?, ?, ?, ?, ?, ?
            )
        ''', (image_id, latitude, longitude, city, address, image_id, image_time, image_url))

        #c.execute('''
        #    INSERT INTO email_data (latitude, longitude, city, address, image_id, image_time, image_url)
        #    VALUES (?, ?, ?, ?, ?, ?, ?)
        #''', (latitude, longitude, city, address, image_id, image_time, image_url))
        conn.commit()
    conn.close()

# Funzione per salvare i dati in SQLite
def save_to_sqlite_(latitude, longitude, city, address, image_id, image_time, image_url):
    conn = sqlite3.connect('emails.db')
    c = conn.cursor()

    # Creazione della tabella se non esiste
    c.execute('''
        CREATE TABLE IF NOT EXISTS email_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL,
            longitude REAL,
            city TEXT,
            address TEXT,
            image_id TEXT,
            image_time TEXT,
            image_url TEXT
        )
    ''')

    # Verifica valore ImageID
    c.execute("SELECT * FROM email_data WHERE image_id=?", (image_id,))
    row = c.fetchone()
    print(f'ROW: {row}')

    if row:
        print(f"Duplicate ImageID detected: {'image_id'}")
    else:
        c.execute('''
            INSERT INTO email_data (latitude, longitude, city, address, image_id, image_time, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (latitude, longitude, city, address, image_id, image_time, image_url))
        conn.commit()

    conn.close()

# Funzione per marcare le email come non lette se non sono stati estratti dati
def mark_as_unread(mail, email_id):
    if email_id:
        email_id_str = str(email_id)
        logger.debug(f"Marking email ID {email_id_str} as unread")
        mail.store(email_id_str, '-FLAGS', '\\Seen')
    else:
        logger.error("Cannot mark email as unread: invalid or empty email ID")


# Test richiamo endpoint FastAPI per elaborare le email
def process_emails(request):
    """
    Processa le email non lette:
    1. Recupera email dal server IMAP
    2. Salva i dati nel DB Django
    3. Invia i nuovi record a FastAPI tramite service-login
    """

    # --- Step 0: inizializza variabili e logging ---
    try:
        mail, email_ids, unread_emails = fetch_unread_emails()
    except Exception as e:
        logger.error(f"Errore durante il fetch delle email: {str(e)}", exc_info=True)
        return redirect('update_in_progress')

    if not unread_emails:
        messages.warning(request, "No new unread emails found. App is idle, waiting for new emails...")
        check_and_update_database()

        # 🔽 MOSTRA COMUNQUE I DATI
        emails = EmailData.objects.all().order_by('-image_time', 'id').values()
        paginator = Paginator(emails, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'emails/email_list.html', {'emails': emails, 'page_obj': page_obj})

    # --- Step 1: Salvataggio email nel DB Django ---
    new_records = []
    for idx, email_message in enumerate(unread_emails):
        logger.info(f"Parsing email {idx+1}/{len(unread_emails)}...")
        try:
            extracted_data = parse_email_content(email_message)
        except Exception as e:
            logger.error(f"Errore parsing email {idx}: {e}")
            continue

        if not extracted_data:
            logger.warning(f"Nessun dato estratto dall'email {idx}")
            continue

        existing = EmailData.objects.filter(
            latitude=extracted_data['latitude'],
            longitude=extracted_data['longitude']
        ).first()

        if existing:
            existing.status = 'In elaborazione'
            existing.status_int = EmailData.StatusInt.PROCESSING   # 10
            existing.save()
            logger.info(f"Aggiornato record esistente ID {existing.id}")
        else:
            new_email = EmailData(
                latitude=extracted_data['latitude'],
                longitude=extracted_data['longitude'],
                city=extracted_data['city'],
                address=extracted_data['address'],
                image_time=extracted_data['image_time'],
                image_id=extracted_data['image_id'],
                image_url=extracted_data['image_url'],
                image_file=extracted_data['image_file'],
                status='Nuovo',
                status_int = EmailData.StatusInt.NEW
                ##
                ##image_file=extracted_data['user_id'],
            )
            new_email.save()
            new_records.append(new_email)
            logger.info(f"Creato nuovo record ID {new_email.id}")

    mail.logout()

    if not new_records:
        logger.info("Nessun nuovo record da inviare a FastAPI")
        messages.info(request, "Non ci sono nuovi record da inviare a FastAPI.")

        # 🔽 MOSTRA I DATI
        emails = EmailData.objects.all().order_by('-image_time', 'id').values()
        paginator = Paginator(emails, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'emails/email_list.html', {'emails': emails, 'page_obj': page_obj})

    # --- Step 2: Autenticazione servizio Django → FastAPI ---
    try:
        auth_response = requests.post(
            f"{settings.FASTAPI_BASE_URL}/auth/service-login"
        )
        auth_response.raise_for_status()
        token = auth_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        logger.info("Autenticazione FastAPI avvenuta con successo")
    except Exception as e:
        logger.error(f"Autenticazione FastAPI fallita: {e}")
        messages.error(request, "Autenticazione FastAPI fallita.")
        return redirect('update_in_progress')

    # --- Step 3: Invio nuovi record a FastAPI ---
    for record in new_records:
        payload = {
            "latitude": record.latitude,
            "longitude": record.longitude,
            "city": record.city,
            "address": record.address,
            "image_id": record.image_id,
            "image_url": record.image_url,
            "status": record.status
        }
        try:
            response = requests.post(
                f"{settings.FASTAPI_BASE_URL}/rifiuti/",
                json=payload,
                headers=headers
            )
            if response.status_code == 201:
                logger.info(f"✅ Record ID {record.id} creato su FastAPI")
            else:
                logger.error(f"❌ Errore creazione record ID {record.id}: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Errore invio record ID {record.id} a FastAPI: {e}")

    messages.success(request, f"Elaborazione completata. {len(new_records)} record inviati a FastAPI.")

    # 🔽 🔽 🔽 BLOCCO FINALE CHE TI SERVIVA
    emails = EmailData.objects.all().order_by('-image_time').values()
    paginator = Paginator(emails, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'emails/email_list.html', {'emails': emails, 'page_obj': page_obj})

    # ==========================================================
    # 📊 QUI STA IL PEZZO CHE TI MANCAVA → POPOLA IL TEMPLATE
    # ==========================================================
    emails = EmailData.objects.all().order_by('-image_time').values()

    paginator = Paginator(emails, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'emails/email_list.html',
        {'emails': emails, 'page_obj': page_obj}
    )


def save_image_from_email(email_message):
    for part in email_message.walk():
        if part.get_content_type().startswith('image'):
            image_name = part.get_filename()
            image_content = part.get_payload(decode=True)

            if image_content:
                # Salva l'immagine nel campo ImageField
                email_data = EmailData.objects.create(
                    latitude=None,  # Inserisci altri dati se disponibili
                    longitude=None,
                    city=None,
                    address=None,
                    #typo=None,
                    image_time=timezone.now(),
                    image_id=None,
                    image_url=None,
                    image_file=None,
                )
                email_data.image_file.save(image_name, ContentFile(image_content))
                email_data.save()
                logger.info(f"Image saved successfully: {image_name}")
            else:
                logger.error("Image content could not be decoded.")

def check_and_update_database():
    """
    Trova record con stesso indirizzo, marca il primo (o il migliore) come 'NEW',
    gli altri come 'DUPLICATE'. Usa status_int.
    """
    # Trova gli indirizzi duplicati
    duplicates = (
        EmailData.objects.values('address')
        .annotate(cnt=Count('id'))
        .filter(cnt__gt=1)
    )

    if not duplicates:
        logger.info("Nessun indirizzo duplicato trovato.")
        return

    for dup in duplicates:
        address = dup['address']
        # Recupera i record per questo indirizzo, ordinati per id (o per data, o per presenza immagine)
        records = EmailData.objects.filter(address=address).order_by('id')

        # Decidi quale record tenere come "principale" (es. quello con immagine valida, o il più recente)
        best = None
        for rec in records:
            # Esempio: meglio un record con image_url non vuoto e status non già duplicato
            if rec.image_url and not rec.status_int == EmailData.StatusInt.DUPLICATE:
                best = rec
                break
        if not best:
            best = records.first()  # fallback: il più vecchio

        # Aggiorna tutti i record in una singola transazione
        with transaction.atomic():
            # Imposta il migliore come NEW (0) se non lo è già
            if best.status_int != EmailData.StatusInt.NEW:
                best.status_int = EmailData.StatusInt.NEW
                best.save(update_fields=['status_int'])
                logger.info(f"Record {best.id} (address={address}) → NEW")

            # Tutti gli altri diventano DUPLICATE (40)
            others = records.exclude(id=best.id)
            updated = others.update(status_int=EmailData.StatusInt.DUPLICATE)
            logger.info(f"{updated} record marcati come DUPLICATE per address {address}")

    logger.info("Controllo duplicati per indirizzo completato.")

def check_and_update_database_():
    """
    Funzione per controllare e aggiornare i record nel database anche quando non ci sono nuove email da leggere.
    """
    # Ottieni tutti i record dal database
    all_emails = EmailData.objects.all()

    # Verifica se ci sono record duplicati basati sull'indirizzo
    duplicates = (
        EmailData.objects
        .values('address')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
    )

    for duplicate in duplicates:
        address = duplicate['address']

        # Ottieni tutti i record con lo stesso indirizzo
        duplicate_records = EmailData.objects.filter(address=address)

        # Imposta il primo record come 'In elaborazione' e il resto come 'Duplicato'
        first_record = True
        for record in duplicate_records:
            if first_record:
                record.status = '0'
                first_record = False
            else:
                record.status = '1'

            # Salva il record aggiornato
            record.save()
            logger.info(f"Updated record {record.id} with status: {record.status}")

    logger.info("Database check and update completed.")

# ricerca condizioni
def search_emails_list(request):
    query = request.GET.get('q', '').strip()
    emails = EmailData.objects.all()

    if query:
        # Costruisci i filtri con OR tra tutti i campi
        filters = (
            Q(city__icontains=query) |
            Q(address__icontains=query) |
            Q(status__icontains=query) |
            Q(typo__icontains=query)
        )
        # Per ID: ricerca esatta se query è un numero
        if query.isdigit():
            filters |= Q(id=int(query))

        emails = emails.filter(filters)

    # Ordinamento stabile (se hai image_time)
    emails = emails.order_by('-image_time', 'id')

    # Log della query SQL generata (solo se DEBUG=True)
    logger.debug(f"QUERY EMAILS: {str(emails.query)}")

    # Attenzione: dopo .order_by(), emails è ancora una QuerySet non valutata.
    # Se vuoi vedere anche il conteggio dei risultati:
    logger.debug(f"COUNT: {emails.count()}")  # questo valuta la query

    return render(request, 'emails/email_list.html', {'emails': emails, 'query': query})

def search_emails_list_(request):
    query = request.GET.get('q')  # Recupera il parametro di ricerca dalla query string
    emails = EmailData.objects.all()

    if query:
        # Filtra i risultati in base alla query di ricerca
        emails = emails.filter(
            Q(city__icontains=query) |
            Q(address__icontains=query)
        )

    return render(request, 'emails/email_list.html', {'emails': emails, 'query': query})

def update_typo(request, email_id):
    if request.method == 'POST':
        email = get_object_or_404(EmailData, id=email_id)

	# Aggiorna il campo typo con il valore inviato dal form
        email.typo = request.POST.get('typo')

	# Controllo se l'utente ha selezionato "Rimuovi"
        if email.typo == 'rimuovi':
            if email.image_file and email.image_file.storage.exists(email.image_file.name):
                try:
                    email.image_file.delete(save=False)
                except NotImplementedError:
                    pass
            # Rimuovi il file immagine associato, se esiste su path tradizionale media/
            #if email.image_file and os.path.isfile(email.image_file.path):
                #os.remove(email.image_file.path)

            # Elimina la segnalazione
            email.delete()
            #messages.success(request, f"Segnalazione e immagine associate rimosse con successo.")
            messages.success(request, f"Segnalazione per {email.city} ({email.status}) e immagine con ID {email.image_id} rimosse con successo.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        email.save()
        # Reindirizza alla pagina precedente o a una pagina specifica
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

def update_in_progress(request):
        return render(request, 'emails/update_in_progress.html')
