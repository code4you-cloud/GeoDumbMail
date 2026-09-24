from django.conf import settings

def imap_server_info(request):
    """
    Notifica il server IMAP in uso
    """
    return {"IMAP_SERVER_LABEL": getattr(settings, "IMAP_SERVER_LABEL", settings.SERVER_IMAP)}
