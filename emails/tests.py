from django.test import TestCase

# Create your tests here

from django.test import TestCase
from unittest.mock import patch, Mock
from .views import fetch_unread_emails, parse_email_content, save_to_sqlite, mark_as_unread, check_image_relevance

class EmailFetchTestCase(TestCase):
    @patch('imaplib.IMAP4_SSL')
    def test_fetch_unread_emails(self, mock_imap):
        # Configura il mock per il server IMAP
        instance = mock_imap.return_value
        instance.login.return_value = ('OK', [b'Logged in'])
        instance.select.return_value = ('OK', [b'INBOX'])
        instance.search.return_value = ('OK', [b'1 2 3'])

        # Simula il fetch delle email
        instance.fetch.return_value = ('OK', [(b'1 (RFC822 {3420}', b'raw email content here')])

        mail, email_ids, unread_emails = fetch_unread_emails()

        # Assicurati che le email siano state correttamente lette
        self.assertEqual(len(unread_emails), 1)
        self.assertEqual(email_ids, [b'1', b'2', b'3'])

class EmailContentParsingTestCase(TestCase):
    def test_parse_email_content(self):
        # Crea un messaggio email simulato
        email_message = EmailMessage()
        email_message.set_content("Latitude: 45.123\nLongitude: 9.123\n**City:** TestCity\n**Address:** TestAddress\n**ImageID:** 12345-abcde\n- ImageURL: http://example.com/image.jpg")

        # Analizza il contenuto dell'email
        extracted_data = parse_email_content(email_message)

        # Verifica che i dati siano stati estratti correttamente
        self.assertEqual(extracted_data['latitude'], '45.123')
        self.assertEqual(extracted_data['longitude'], '9.123')
        self.assertEqual(extracted_data['city'], 'TestCity')
        self.assertEqual(extracted_data['address'], 'TestAddress')
        self.assertEqual(extracted_data['image_id'], '12345-abcde')
        self.assertEqual(extracted_data['image_url'], 'http://example.com/image.jpg')

class DatabaseSavingTestCase(TestCase):
    def test_save_to_sqlite(self):
        # Chiama la funzione per salvare i dati nel database
        save_to_sqlite('45.123', '9.123', 'TestCity', 'TestAddress', '12345-abcde', 'http://example.com/image.jpg')

        # Verifica che il record sia stato creato correttamente
        email_data = EmailData.objects.get(image_id='12345-abcde')
        self.assertEqual(email_data.latitude, 45.123)
        self.assertEqual(email_data.longitude, 9.123)
        self.assertEqual(email_data.city, 'TestCity')
        self.assertEqual(email_data.address, 'TestAddress')
        self.assertEqual(email_data.image_url, 'http://example.com/image.jpg')


class MarkAsUnreadTestCase(TestCase):
    @patch('imaplib.IMAP4_SSL')
    def test_mark_as_unread(self, mock_imap):
        # Configura il mock per il server IMAP
        instance = mock_imap.return_value

        # Simula la marcatura di una email come non letta
        mark_as_unread(instance, '1')

        # Verifica che il metodo IMAP 'store' sia stato chiamato correttamente
        instance.store.assert_called_with('1', '-FLAGS', '\\Seen')

class CheckImageRelevanceTestCase(TestCase):
    @patch('requests.get')
    def test_check_image_relevance(self, mock_get):
        # Configura il mock per la risposta HTTP
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.content = b'image data'

        # Chiama la funzione da testare
        result = check_image_relevance('http://example.com/image.jpg')

        # Verifica che l'immagine sia stata considerata rilevante
        self.assertTrue(result)
