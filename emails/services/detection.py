# services/detection.py
import anthropic, json, base64
import io, base64

from django.conf import settings
from emails.models import EmailData, RedactionBox
from PIL import Image


def detect_sensitive_regions(image_path):
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    img_b64 = prepare_image_for_api(image_path)

    msg = client.messages.create(
        model=settings.DETECTION_MODEL,     # <-- QUI, argomento nominale di create()
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}},
                {"type": "text", "text": (
                    "Individua volti umani e targhe veicolari visibili in questa foto. "
                    "Rispondi SOLO con JSON: "
                    '[{"type":"face"|"plate","x":0-1,"y":0-1,"w":0-1,"h":0-1,"confidence":0-1}]. '
                    "Coordinate normalizzate rispetto a larghezza/altezza immagine, x/y = angolo top-left. "
                    "Se non trovi nulla, rispondi []."
                )}
            ]
        }]
    )
    text = msg.content[0].text.strip().strip("```json").strip("```")
    return json.loads(text)

def detect_sensitive_regions_(image_path):
     client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

     with open(image_path, "rb") as f:
         img_b64 = base64.b64encode(f.read()).decode()

     msg = client.messages.create(
         model="claude-sonnet-4-6",
         max_tokens=1000,
         messages=[{
             "role": "user",
             "content": [
                 {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}},
                 {"type": "text", "text": (
                     "Individua volti umani e targhe veicolari visibili in questa foto. "
                     "Rispondi SOLO con JSON: "
                     '[{"type":"face"|"plate","x":0-1,"y":0-1,"w":0-1,"h":0-1,"confidence":0-1}]. '
                     "Coordinate normalizzate rispetto a larghezza/altezza immagine, x/y = angolo top-left. "
                     "Se non trovi nulla, rispondi []."
                 )}
             ]
         }]
     )
     text = msg.content[0].text.strip().strip("```json").strip("```")
     return json.loads(text)

def process_report_detection(email):
    email.status_int = EmailData.StatusInt.PROCESSING
    email.save(update_fields=['status_int'])

    if not email.image_file:
        email.status_int = EmailData.StatusInt.SKIPPED
        email.save(update_fields=['status_int'])
        return

    try:
        regions = detect_sensitive_regions(email.image_file.path)
    except Exception:
        email.status_int = EmailData.StatusInt.ERROR
        email.save(update_fields=['status_int'])
        return

    if regions:
        email.status_int = EmailData.StatusInt.FLAGGED
        send_flag_alert(email, regions)
    else:
        email.status_int = EmailData.StatusInt.PUBLISHED

    email.save(update_fields=['status_int'])

def process_report_detection_(report):
    report.status = EmailData.Status.PROCESSING
    report.save(update_fields=['status'])

    if not report.image:
        report.status = EmailData.Status.SKIPPED
        report.save(update_fields=['status'])
        return

    try:
        regions = detect_sensitive_regions(report.image.path)
    except Exception:
        report.status = EmailData.Status.ERROR
        report.save(update_fields=['status'])
        return

    for r in regions:
        RedactionBox.objects.create(
            report=report, box_type=r['type'],
            x=r['x'], y=r['y'], w=r['w'], h=r['h'],
            confidence=r.get('confidence', 1.0),
        )gg

    report.status = EmailData.Status.PENDING_REVIEW  # scelta (a) — vale anche con regions=[]
    report.save(update_fields=['status'])

def prepare_image_for_api(image_path, max_dimension=1024):
    """
    Ridimensiona l'immagine mantenendo le proporzioni, converte in JPEG,
    e ritorna il base64 pronto per l'API. Non tocca il file originale su disco.
    """
    img = Image.open(image_path)
    img = img.convert("RGB")  # necessario se l'originale è PNG con alpha o altro formato
    img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)  # non ingrandisce mai, solo riduce

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()
