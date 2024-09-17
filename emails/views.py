import imaplib
import email
import re
import ssl
import sqlite3
import logging
import os

import psycopg2
from psycopg2 import sql

from django.shortcuts import render
from django.utils import timezone

# Create your views here.
from django.http import HttpResponse

# new from AI
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.contrib import messages
from django.db.models import Count, Q

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
    mail = imaplib.IMAP4_SSL('in.citylog.cloud', port=993, ssl_context=context)
    mail.login('report@citylog.cloud', 'Blacking1')  # Sostituisci con le tue credenziali
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
    # Directory dove salvare le immagini temporaneamente
    temp_image_save_path = "./temp_images"

    if not os.path.exists(temp_image_save_path):
        os.makedirs(temp_image_save_path)

    text_content = ""  # Inizializziamo la variabile per memorizzare il contenuto di testo
    image_file_path = None  # Inizializza la variabile per il percorso del file immagine

    # Itera attraverso le parti dell'email
    for part in email_message.walk():
        content_type = part.get_content_type()

        if part.is_multipart():
            # Se la parte è multipart, continuiamo il loop
            continue

        if content_type == 'text/plain':
            # Gestione del testo
            text_content += part.get_payload(decode=True).decode('utf-8', errors='replace')
            text_content = text_content.replace('\r\n', '\n')

        elif content_type.startswith('image/'):  # Gestisce le immagini
            # Estrai il nome del file e il contenuto binario dell'immagine
            image_filename = part.get_filename()

            if not image_filename:
                # Genera un nome di file unico se il nome del file è mancante
                image_filename = f"image_{timezone.now().strftime('%Y%m%d%H%M%S')}.jpg"

            # Percorso completo per salvare l'immagine temporaneamente
            image_filepath = os.path.join(temp_image_save_path, image_filename)

            image_data = part.get_payload(decode=True)

            # Salva l'immagine temporaneamente
            with open(image_filepath, 'wb') as f:
                f.write(image_data)

            print(f"Immagine salvata temporaneamente: {image_filepath}")

            # Salva l'immagine utilizzando il modello Django
            image_instance = EmailData()
            image_instance.image_file.save(image_filename, open(image_filepath, 'rb'), save=False)
            image_file_path = image_instance.image_file

    # Analisi del contenuto di testo per estrarre informazioni
    if text_content:
        print("Text Content:\n", text_content)

        # Utilizza le espressioni regolari per trovare le coordinate e l'indirizzo
        latitude = re.search(r'Latitude:\s*([\d\.\-]+)', text_content)
        longitude = re.search(r'Longitude:\s*([\d\.\-]+)', text_content)
        city = re.search(r'\*\*City:\*\*\s*(.+)', text_content)
        address = re.search(r'\*\*Address:\*\*\s*(.+)', text_content)
        #typo = re.search(r'\*\*Typo:\*\*\s*(.+)', text_content)
        image_time = timezone.now()
        image_id = re.search(r'\*\*ImageID:\*\*\s*([a-f0-9\-]+)', text_content)
        image_url = re.search(r'https?://[^\s]+', text_content)

        # Aggiorna le informazioni dell'istanza dell'immagine
        image_instance.latitude = latitude.group(1) if latitude else None
        image_instance.longitude = longitude.group(1) if longitude else None
        image_instance.city = city.group(1) if city else None
        image_instance.address = address.group(1) if address else None
        #typo_instance.address = typo.group(1) if typo else None
        image_instance.image_time = image_time
        image_instance.image_id = image_id.group(1) if image_id else None

        # **Importante**: Assegna l'URL dell'immagine generato da Django al campo `image_url`
        image_instance.image_url = image_instance.image_file.url

        # Salva l'istanza del modello nel database
        image_instance.save()

        print("Dati salvati nel database.")

        return {
            'latitude': image_instance.latitude,
            'longitude': image_instance.longitude,
            'city': image_instance.city,
            'address': image_instance.address,
            #'typo': image_instance.typo,
            'image_time': image_instance.image_time,
            'image_id': image_instance.image_id,
            'image_url': image_instance.image_url,  # URL dell'immagine salvata
            'image_file': image_instance.image_file.url
        }

    return None

def parse_email_content___(email_message):
    # Directory dove salvare le immagini temporaneamente
    temp_image_save_path = "./temp_images"

    if not os.path.exists(temp_image_save_path):
        os.makedirs(temp_image_save_path)

    text_content = ""  # Inizializziamo la variabile per memorizzare il contenuto di testo
    image_file_path = None  # Inizializza la variabile per il percorso del file immagine

    # Itera attraverso le parti dell'email
    for part in email_message.walk():
        content_type = part.get_content_type()

        if part.is_multipart():
            # Se la parte è multipart, continuiamo il loop
            continue

        if content_type == 'text/plain':
            # Gestione del testo
            text_content += part.get_payload(decode=True).decode('utf-8', errors='replace')
            text_content = text_content.replace('\r\n', '\n')

        elif content_type.startswith('image/'):  # Gestisce le immagini
            # Estrai il nome del file e il contenuto binario dell'immagine
            image_filename = part.get_filename()

            if not image_filename:
                # Genera un nome di file unico se il nome del file è mancante
                image_filename = f"image_{timezone.now().strftime('%Y%m%d%H%M%S')}.jpg"

            # Percorso completo per salvare l'immagine temporaneamente
            image_filepath = os.path.join(temp_image_save_path, image_filename)

            image_data = part.get_payload(decode=True)

            # Salva l'immagine temporaneamente
            with open(image_filepath, 'wb') as f:
                f.write(image_data)

            print(f"Immagine salvata temporaneamente: {image_filepath}")

            # Salva l'immagine utilizzando il modello Django
            image_instance = EmailData()
            image_instance.image_file.save(image_filename, open(image_filepath, 'rb'), save=False)
            image_file_path = image_instance.image_file

    # Analisi del contenuto di testo per estrarre informazioni
    if text_content:
        print("Text Content:\n", text_content)

        # Utilizza le espressioni regolari per trovare le coordinate e l'indirizzo
        latitude = re.search(r'Latitude:\s*([\d\.\-]+)', text_content)
        longitude = re.search(r'Longitude:\s*([\d\.\-]+)', text_content)
        city = re.search(r'\*\*City:\*\*\s*(.+)', text_content)
        address = re.search(r'\*\*Address:\*\*\s*(.+)', text_content)
        #typo = re.search(r'\*\*Typo:\*\*\s*(.+)', text_content)
        image_time = timezone.now()
        image_id = re.search(r'\*\*ImageID:\*\*\s*([a-f0-9\-]+)', text_content)
        image_url = re.search(r'https?://[^\s]+', text_content)

        # Aggiorna le informazioni dell'istanza dell'immagine
        image_instance.latitude = latitude.group(1) if latitude else None
        image_instance.longitude = longitude.group(1) if longitude else None
        image_instance.city = city.group(1) if city else None
        image_instance.address = address.group(1) if address else None
        #image_instance.typo = typo.group(1) if typo else None
        image_instance.image_time = image_time
        image_instance.image_id = image_id.group(1) if image_id else None
        image_instance.image_url = image_url.group(0) if image_url else None

        # Salva l'istanza del modello nel database
        image_instance.save()

        print("Dati salvati nel database.")

        return {
            'latitude': image_instance.latitude,
            'longitude': image_instance.longitude,
            'city': image_instance.city,
            'address': image_instance.address,
            #'typo': image_instance.typo,
            'image_time': image_instance.image_time,
            'image_id': image_instance.image_id,
            'image_url': image_instance.image_url,
            'image_file': image_instance.image_file.url
        }

    return None

def parse_email_content__(email_message):
    # Directory dove salvare le immagini
    image_save_path = "./downloaded_images"

    if not os.path.exists(image_save_path):
        os.makedirs(image_save_path)

    text_content = ""  # Inizializziamo la variabile per memorizzare il contenuto di testo

    # Itera attraverso le parti dell'email
    for part in email_message.walk():
        content_type = part.get_content_type()

        if part.is_multipart():
            # Se la parte è multipart, continuiamo il loop
            continue

        if content_type == 'text/plain':
            # Gestione del testo
            text_content += part.get_payload(decode=True).decode('utf-8', errors='replace')
            text_content = text_content.replace('\r\n', '\n')

        elif content_type.startswith('image/'):  # Gestisce le immagini
            # Estrai il nome del file e il contenuto binario dell'immagine
            image_filename = part.get_filename()

            if not image_filename:
                # Genera un nome di file unico se il nome del file è mancante
                image_filename = f"image_{timezone.now().strftime('%Y%m%d%H%M%S')}.jpg"

            # Percorso completo per salvare l'immagine
            image_filepath = os.path.join(image_save_path, image_filename)

            image_data = part.get_payload(decode=True)

            # Salva l'immagine o fai ulteriori elaborazioni
            with open(image_filepath, 'wb') as f:
                f.write(image_data)

            print(f"Immagine salvata: {image_filepath}")

    # Analisi del contenuto di testo per estrarre informazioni
    if text_content:
        print("Text Content:\n", text_content)

        # Utilizza le espressioni regolari per trovare le coordinate e l'indirizzo
        latitude = re.search(r'Latitude:\s*([\d\.\-]+)', text_content)
        longitude = re.search(r'Longitude:\s*([\d\.\-]+)', text_content)
        city = re.search(r'\*\*City:\*\*\s*(.+)', text_content)
        address = re.search(r'\*\*Address:\*\*\s*(.+)', text_content)
        #typo = re.search(r'\*\*Typo:\*\*\s*(.+)', text_content)
        image_time = timezone.now()
        image_id = re.search(r'\*\*ImageID:\*\*\s*([a-f0-9\-]+)', text_content)
        image_url = re.search(r'https?://[^\s]+', text_content)
        image_file = re.search(r'- ImageFocus:\s*(.*)', text_content)

        # Salva i dati nel database
        save_to_postgresql(
            latitude.group(1) if latitude else None,
            longitude.group(1) if longitude else None,
            city.group(1) if city else None,
            address.group(1) if address else None,
            typo.group(1) if typo else None,
            image_time,
            image_id.group(1) if image_id else None,
            image_url.group(0) if image_url else None,
            image_file.group(1) if image_file else None
        )

        return {
            'latitude': latitude.group(1) if latitude else None,
            'longitude': longitude.group(1) if longitude else None,
            'city': city.group(1) if city else None,
            'address': address.group(1) if address else None,
            #'typo': typo.group(1) if typo else None,
            'image_time': image_time,
            'image_id': image_id.group(1) if image_id else None,
            'image_url': image_url.group(0) if image_url else None,
            'image_file': image_file.group(1) if image_file else None
        }

    return None

# Funzione per analizzare il contenuto del testo e estrarre i dati
def parse_email_content_(email_message):
    for part in email_message.walk():
        content_type = part.get_content_type()
        #if content_type == 'text/plain':

        if part.get_content_type() == 'text/plain':
            text_content = part.get_payload(decode=True).decode('utf-8', errors='replace')
            text_content = text_content.replace('\r\n', '\n')
            print(f'{text_content}')

            # Utilizza le espressioni regolari per trovare le coordinate e l'indirizzo
            latitude = re.search(r'Latitude:\s*([\d\.\-]+)', text_content)
            longitude = re.search(r'Longitude:\s*([\d\.\-]+)', text_content)
            city = re.search(r'\*\*City:\*\*\s*(.+)', text_content)
            address = re.search(r'\*\*Address:\*\*\s*(.+)', text_content)
            #typo = re.search(r'\*\*Typo:\*\*\s*(.+)', text_content)
            image_time = timezone.now()
            image_id = re.search(r'\*\*ImageID:\*\*\s*([a-f0-9\-]+)', text_content)
            image_url = re.search(r'- ImageURL:\s*\n', text_content)
            #image_file = re.search(r'- ImageFocus:\s*(.+)', text_content)
            #image_file = re.search(r'- ImageFocus:\s*(.*)', text_content)
            image_file = re.findall(r'- ImageFocus:/images/\d+/(\w+.jpg)', text_content)

            # Salva i dati nel database
            save_to_postgresql(latitude.group(1) if latitude else None,
                           longitude.group(1) if longitude else None,
                           city.group(1) if city else None,
                           address.group(1) if address else None,
                           #typo.group(1) if typo else None,
                           image_time,
                           image_id.group(1) if image_id else None,
                           image_url.group(1) if image_url else None,
                           image_file.group(1) if image_file else None)

            return {
                'latitude': latitude.group(1) if latitude else None,
                'longitude': longitude.group(1) if longitude else None,
                'city': city.group(1) if city else None,
                'address': address.group(1) if address else None,
                #'typo': typo.group(1) if typo else None,
                'image_time': image_time,
                'image_id': image_id.group(1) if image_id else None,
                'image_url': image_url.group(1) if image_url else None,
                'image_file': image_file.group(1) if image_file else None
            }

        #elif content_type.startswith('image/'):  # Gestisce le immagini
            # Estrai il nome del file e il contenuto binario dell'immagine
        #    image_filename = part.get_filename()

        #    if not image_filename:
                # Genera un nome di file unico se il nome del file è mancante
        #        image_filename = f"image_{timezone.now().strftime('%Y%m%d%H%M%S')}.jpg"

            # Percorso completo per salvare l'immagine
        #    image_filepath = os.path.join(image_save_path, image_filename)

        #    image_data = part.get_payload(decode=True)

            # Salva l'immagine o fai ulteriori elaborazioni
        #    with open(image_filepath, 'wb') as f:
        #        f.write(image_data)

        #    print(f"Immagine salvata: {image_filepath}")

    return None

def save_to_postgresql(latitude, longitude, city, address, image_time, image_id, image_url, image_file):
    try:
        # Connessione a PostgreSQL
        conn = psycopg2.connect(
            dbname="geodumbmail",
            user="postgres",
            password="",
            host="192.168.1.65",
            port="5432"
        )
        c = conn.cursor()

        # Creazione della tabella se non esiste
        c.execute('''
            CREATE TABLE IF NOT EXISTS emails_emaildata (
                id SERIAL PRIMARY KEY,
                latitude REAL,
                longitude REAL,
                city TEXT,
                address TEXT,
                image_time DATE,
                image_id TEXT UNIQUE,
                image_url TEXT,
                image_file TEXT
            )
        ''')

        # Verifica duplicati
        c.execute("SELECT * FROM emails_emaildata WHERE image_id = %s", (image_id,))
        row = c.fetchone()
        print(f'ROW: {row}')

        if row:
            print(f"Duplicate ImageID detected: {image_id}")
        else:
            c.execute('''
                INSERT INTO emails_emaildata (latitude, longitude, city, address, image_time, image_id, image_url, image_file)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (latitude, longitude, city, address, image_time, image_id, image_url, image_file))
            conn.commit()

            print("Insert a new record on database {row}")

    except psycopg2.Error as e:
        print(f"An error occurred while interacting with PostgreSQL: {e}")
    finally:
        # Chiudere il cursore e la connessione anche in caso di errore
        if c:
            c.close()
        if conn:
            conn.close()

# Funzione per salvare i dati in SQLite
def save_to_sqlite(latitude, longitude, city, address, image_id, image_url):
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
            INSERT INTO email_data (latitude, longitude, city, address, image_id, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (latitude, longitude, city, address, image_id, image_url))
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

def process_emails(request):
    mail, email_ids, unread_emails = fetch_unread_emails()

    if not unread_emails:
        # Aggiorna il messaggio per indicare che i nuovi dati sono stati memorizzati
        messages.warning(request, "No new unread emails found. App is idle, waiting for new emails...")
        # Verifica le segnalazioni dopi nel database
        check_and_update_database()

    # Itera su ogni email e relativo email_id
    for idx, email_message in enumerate(unread_emails):
        logger.info("Parsing email content...")
        extracted_data = parse_email_content(email_message)

        if extracted_data:
            logger.info("Data successfully extracted:")
            logger.info(f"Latitude: {extracted_data['latitude']}")
            logger.info(f"Longitude: {extracted_data['longitude']}")
            logger.info(f"City: {extracted_data['city']}")
            logger.info(f"Address: {extracted_data['address']}")
            #logger.info(f"Typo: {extracted_data['typo']}")
            logger.info(f"ImageTime: {extracted_data['image_time']}")
            logger.info(f"ImageID: {extracted_data['image_id']}")
            logger.info(f"ImageURL: {extracted_data['image_url']}")
            logger.info(f"ImageFile: {extracted_data['image_file']}")

            ## Messaggio di stato quando vengono trovate nuove email
            if idx == 0:
                messages.info(request, f"Found {len(unread_emails)} new unread emails. Processing...")

            # Normalizza l'indirizzo per evitare discrepanze (spazi in più, maiuscole/minuscole)
            normalized_address = extracted_data['address'].strip().lower()
            logger.info(f"Normalize:{normalized_address}")
            logger.info(f"Old Extracdata:{extracted_data['city']}")

            # Verifica se esiste già un record con lo stesso indirizzo normalizzato
            #existing_email_data = EmailData.objects.filter(
            #    latitude__iexact=normalized_address
            #).first()

            # Verifica se esiste già un record con lo stesso indirizzo e numero civico
            existing_lat_long = EmailData.objects.filter(
                latitude=extracted_data['latitude']
            ).filter(longitude=extracted_data['longitude']).first()

            if existing_lat_long:
                # Aggiorna lo stato se esiste già
                existing_lat_long.status = 'In elaborazione'
                existing_lat_long.save()
                logger.info(f"Record updated: {existing_lat_long}")
            else:
                # Crea un nuovo record se non esiste
                new_email_data = EmailData(
                    latitude=extracted_data['latitude'],
                    longitude=extracted_data['longitude'],
                    city=extracted_data['city'],
                    address=extracted_data['address'],
                    #typo=extracted_data['typo'],
                    image_time=extracted_data['image_time'],
                    image_id=extracted_data['image_id'],
                    image_url=extracted_data['image_url'],
                    image_file=extracted_data['image_file'],
                    status='Nuovo'
                )
                new_email_data.save()
                logger.info(f"New record created: {new_email_data}")

        else:
            logger.error("No data extracted.")
            email_id = email_ids[idx].decode('utf-8')
            if email_id:
                mark_as_unread(mail, email_id)
                messages.warning(request, f"Marked as unread: {mail}_{email_id}")
            else:
                logger.error(f"Invalid email ID: {email_id}")
                logger.debug(f"Email content:\n{email_message}")
                messages.error(request, f"Invalid email_id: {email_id}.")

    mail.logout()
    # Recupera i dati dal database per visualizzarli nella pagina
    emails = EmailData.objects.all().order_by('-image_time').values()
    return render(request, 'emails/email_list.html', {'emails': emails})

# Vista principale per elaborare le email
def process_emails_(request):
    mail, email_ids, unread_emails = fetch_unread_emails()

    if not unread_emails:
        # Aggiorna il messaggio per indicare che i nuovi dati sono stati memorizzati
        messages.warning(request, "No new unread emails found. App is idle, waiting for new emails...")
        # Controllo duplicati anche e non ci sono nuove email
        check_and_update_database()

    # Itera su ogni email e relativo email_id
    for idx, email_message in enumerate(unread_emails):
        logger.info("Parsing email content...")
        extracted_data = parse_email_content(email_message)

        if extracted_data:
            logger.info("Data successfully extracted:")
            logger.info(f"Latitude: {extracted_data['latitude']}")
            logger.info(f"Longitude: {extracted_data['longitude']}")
            logger.info(f"City: {extracted_data['city']}")
            logger.info(f"Address: {extracted_data['address']}")
            #logger.info(f"Typo: {extracted_data['typo']}")
            logger.info(f"ImageTime: {extracted_data['image_time']}")
            logger.info(f"ImageID: {extracted_data['image_id']}")
            logger.info(f"ImageURL: {extracted_data['image_url']}")
            logger.info(f"ImageFile: {extracted_data['image_file']}")

            ## Messaggio di stato quando vengono trovate nuove email
            if idx == 0:
                messages.info(request, f"Found {len(unread_emails)} new unread emails. Processing...")
        else:
            logger.error("No data extracted.")
            email_id = email_ids[idx].decode('utf-8')
            if email_id:
                mark_as_unread(mail, email_id)
                messages.warning(request, "Mark as unread {mail}_{email_id}..")
            else:
                logger.error(f"Invalid email ID: {email_id}")
                logger.debug(f"Email content:\n{email_message}")
                messages.error(request, "Invalid email_id: {email_id}..")

    mail.logout()
    # Recupera i dati dal database per visualizzarli nella pagina
    emails = EmailData.objects.all()
    return render(request, 'emails/email_list.html', {'emails': emails})

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

def check_and_update_database_():
    """
    Funzione per controllare e aggiornare i record nel database basati su duplicati di latitude e longitude.
    """
    # Trova duplicati basati su latitudine e longitudine
    duplicates = (
        EmailData.objects
        .values('latitude', 'longitude')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
    )

    for duplicate in duplicates:
        lat = duplicate['latitude']
        lon = duplicate['longitude']

        # Ottieni tutti i record con la stessa latitudine e longitudine
        duplicate_records = EmailData.objects.filter(latitude=lat, longitude=lon)

        # Imposta il primo record come 'In elaborazione' e il resto come 'Duplicato'
        first_record = True
        for record in duplicate_records:
            if first_record:
                record.status = 'In elaborazione'
                first_record = False
            else:
                record.status = 'Duplicato'

            # Salva il record aggiornato
            record.save()
            logger.info(f"Updated record {record.id} with status: {record.status}")

    logger.info("Database check and update completed.")

def check_and_update_database():
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

def search_emails_list(request):
    query = request.GET.get('q')  # Recupera il parametro di ricerca dalla query string
    emails = EmailData.objects.all()

    if query:
        # Filtra i risultati in base alla query di ricerca
        emails = emails.filter(
            Q(city__icontains=query) |
            Q(address__icontains=query)
        )

    return render(request, 'emails/email_list.html', {'emails': emails, 'query': query})
