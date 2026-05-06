import pytest
import re
import sqlite3
import shutil
import tempfile

from django.test import TestCase
from unittest.mock import patch
from email.message import EmailMessage as StdEmailMessage  # libreria standard, NON Django
from emails.models import EmailData

from .views import fetch_unread_emails, parse_email_content, save_to_sqlite, save_to_postgresql, mark_as_unread

class ReprocessPreservesOriginalDateTimeTestPSQL(TestCase):
    def test_reprocess_updates_image_time(self):
        # 1. Simula un record già esistente (con una data vecchia o None)
        existing = EmailData.objects.create(
            image_id="test-123",
            latitude=45.0,
            longitude=9.0,
            city="Test",
            address="Via Test",
            image_time=None,   # oppure una data vecchia
            status=0
        )

        # 2. Costruisci la stessa email con la data originale (più vecchia)
        email_body = """...
        - **ImageID:** 7af36900-92d2-4d80-8147-d10c52d0d4b6
        - **DateTime:** 2026-03-13 09:15:00
        ..."""
        msg = StdEmailMessage()
        msg.set_content(email_body, subtype='plain')

        # 3. Rielabora l'email (funzione che aggiorna il record esistente)
        parsed = parse_email_content(msg)   # deve restituire anche image_time
        # Salva o aggiorna il record nel DB (deve farlo con .update_or_create)
        obj, created = EmailData.objects.update_or_create(
            image_id=parsed['image_id'],
            defaults={
                'latitude': parsed['latitude'],
                'longitude': parsed['longitude'],
                'city': parsed['city'],
                'address': parsed['address'],
                'image_time': parsed['image_time'],   # chiave
                'image_url': parsed.get('image_url')
            }
        )

        # 4. Verifica che image_time sia la data originale
        self.assertEqual(obj.image_time, parsed['image_time'])
        self.assertEqual(obj.image_time.strftime('%Y-%m-%d %H:%M:%S'), "2026-03-13 09:15:00")

class ReprocessingPreservesOriginalDateTimeTestSQLite(TestCase):
    """
    Verifica che rielaborando la stessa email (es. dopo averla segnata come non letta)
    il campo DateTime rimanga quello originale e non venga sostituito con la data corrente.
    """

    def test_original_datetime_survives_reprocessing(self):
        # Crea una copia temporanea del database reale
        db_copy = tempfile.NamedTemporaryFile(suffix='.db')
        shutil.copy2('emails.db', db_copy.name)  # sostituisci con il percorso corretto

        # 1. Crea un email fittizia con una data originale (13 marzo)
        original_body = """**Description Audit:**
        Here is the photo taken at the following location:

        - **ImageID:** 7b0aa0eb-0fb4-4fee-a906-1018e3b63338
        - **UserID:** 104165751464563590205

        - **Coordinates:**
        - Latitude: 45.51313709
        - Longitude: 10.13730802

        - **City:** Castel Mella
        - **Address:** Via Renolda, 14, 25030 Castel Mella BS, Italia
        - **DateTime:** 2026-03-13 09:15:00   # Data originale

        **Map Citylog Preview:**
        https://maps.citylog.cloud/hot/15/17306/11721.png
        """

        msg = StdEmailMessage()
        msg.set_content(original_body, subtype='plain')

        # 2. Estrai i dati (inclusa la data)
        extracted = parse_email_content(msg)
        self.assertIn('image_time', extracted, "parse_email_content deve restituire 'image_time'")
        original_date = extracted['image_time']

        # 3. Prepara un database SQLite di test (in memoria)
        test_db_path = db_copy.name
        #test_db_path = ":memory:"

        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude REAL,
                longitude REAL,
                city TEXT,
                address TEXT,
                image_id TEXT UNIQUE,
                image_time TEXT,
                image_url TEXT
            )
        ''')
        conn.commit()
        conn.close()

        # 4. Primo salvataggio
        save_to_sqlite(
            latitude=extracted['latitude'],
            longitude=extracted['longitude'],
            city=extracted['city'],
            address=extracted['address'],
            image_id=extracted['image_id'],
            image_url=extracted.get('image_url', ''),
            image_time=original_date,
            db_path=test_db_path
        )

        # 5. Simula una rielaborazione (stessa email, stesso parsing)
        #    In un caso reale, questa seconda chiamata avviene dopo aver rimesso l'email in stato "unread"
        extracted_again = parse_email_content(msg)   # stessa data dall'email
        second_date = extracted_again['image_time']

        # Secondo salvataggio (aggiornerà il record se usi INSERT OR REPLACE)
        save_to_sqlite(
            latitude=extracted_again['latitude'],
            longitude=extracted_again['longitude'],
            city=extracted_again['city'],
            address=extracted_again['address'],
            image_id=extracted_again['image_id'],
            image_url=extracted_again.get('image_url', ''),
            image_time=second_date,
            db_path=test_db_path
        )

        # 6. Verifica che nel database sia ancora presente la data originale (13 marzo)
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT image_time FROM email_data WHERE image_id = ?", (extracted['image_id'],))
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row, "Nessun record trovato nel database di test")
        stored_date = row[0]
        self.assertEqual(stored_date, original_date,
                         f"La data memorizzata è {stored_date}, ma doveva essere {original_date} (originale). "
                         "Il bug potrebbe aver sostituito la data con quella di rielaborazione.")

class EmailFetchTestCase(TestCase):
    @patch('imaplib.IMAP4_SSL')
    def test_fetch_unread_emails(self, mock_imap):
        """Verifica il recupero delle email non lette da IMAP."""
        instance = mock_imap.return_value
        instance.login.return_value = ('OK', [b'Logged in'])
        instance.select.return_value = ('OK', [b'INBOX'])
        instance.search.return_value = ('OK', [b'1'])          # un solo ID per coerenza
        instance.fetch.return_value = ('OK', [(b'1 (RFC822 {3420}', b'raw email content here')])

        mail, email_ids, unread_emails = fetch_unread_emails()

        self.assertEqual(len(unread_emails), 1)
        self.assertEqual(email_ids, [b'1'])

class EmailContentParsingTestCase(TestCase):
    def test_parse_email_content(self):
        # Corpo email reale (quello che arriva realmente)
        raw_body = """**Description Audit:**
        Here is the photo taken at the following location:

        - **ImageID:** 7b0aa0eb-0fb4-4fee-a906-1018e3b63338
        - **UserID:** 104165751464563590205

        - **Coordinates:**
        - Latitude: 45.51313709
        - Longitude: 10.13730802

        - **City:** Castel Mella
        - **Address:** Via Renolda, 14, 25030 Castel Mella BS, Italia
        - **DateTime:** 2026-04-22 13:23:39

        **Map Citylog Preview:**
        https://maps.citylog.cloud/hot/15/17306/11721.png?lang=en-US&ll=10.13730802,45.51313709&z=15&l=map&size=400,300&pt=10.13730802,45.51313709,pm2rdm

        - **Warning Transmission Image:**
        - ImageID: 7b0aa0eb-0fb4-4fee-a906-1018e3b63338
        - FocusImage:"""

        msg = StdEmailMessage()
        msg.set_content(raw_body, subtype='plain')
        extracted_data = parse_email_content(msg)

        self.assertEqual(extracted_data['latitude'], '45.51313709')
        self.assertEqual(extracted_data['longitude'], '10.13730802')
        self.assertEqual(extracted_data['city'], 'Castel Mella')
        self.assertEqual(extracted_data['address'], 'Via Renolda, 14, 25030 Castel Mella BS, Italia')
        self.assertEqual(extracted_data['image_id'], '7b0aa0eb-0fb4-4fee-a906-1018e3b63338')
        # L'URL potrebbe essere quello della mappa o un altro; controlla la tua funzione
        # Se la tua funzione estrae il primo URL, questo è quello:
        #self.assertEqual(extracted_data['image_url'], 'https://maps.citylog.cloud/hot/15/17306/11721.png?lang=en-US&ll=10.13730802,45.51313709&z=15&l=map&size=400,300&pt=10.13730802,45.51313709,pm2rdm')


class DatabaseSavingTestCase(TestCase):
    def test_save_to_sqlite_in_memory(self):
        # Usa un database temporaneo in RAM
        save_to_sqlite(
            latitude=45.51313709,
            longitude=10.13730802,
            city="Castel Mella",
            address="Via Renolda, 14",
            image_id="test-123",
            image_url="http://example.com/img.jpg",
            db_path=":memory:"
        )
        # Per verificare, devi eseguire una query diretta o usare una funzione di lettura.
        # Puoi creare una funzione helper read_from_sqlite(db_path) oppure verificare tramite una seconda connessione.
        conn = sqlite3.connect(":memory:")
        c = conn.cursor()
        c.execute("SELECT * FROM email_data WHERE image_id = ?", ("test-123",))
        row = c.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], 45.51313709)  # latitude

class DatabaseSavingTestCase(TestCase):
    @pytest.mark.skip(reason=(
        "save_to_sqlite scrive direttamente su file emails.db, non usa il modello ORM Django. "
        "Per testarlo modificare la funzione per usare EmailData.objects.create() oppure riscrivere il test."
    ))
    def test_save_to_sqlite(self):
        """Test attualmente saltato – da rivedere l'implementazione di save_to_sqlite."""
        save_to_sqlite('45.123', '9.123', 'TestCity', 'TestAddress', '12345-abcde', 'http://example.com/image.jpg')
        email_data = EmailData.objects.get(image_id='12345-abcde')
        self.assertEqual(email_data.latitude, 45.123)
        self.assertEqual(email_data.longitude, 9.123)
        self.assertEqual(email_data.city, 'TestCity')
        self.assertEqual(email_data.address, 'TestAddress')
        self.assertEqual(email_data.image_url, 'http://example.com/image.jpg')


class MarkAsUnreadTestCase(TestCase):
    @patch('imaplib.IMAP4_SSL')
    def test_mark_as_unread(self, mock_imap):
        """Verifica che l'email venga segnata come 'non letta'."""
        instance = mock_imap.return_value
        mark_as_unread(instance, '1')
        instance.store.assert_called_with('1', '-FLAGS', '\\Seen')
