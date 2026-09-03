# services/redaction.py
from PIL import Image, ImageFilter

def apply_redaction(report):
    img = Image.open(report.image.path).convert("RGB")
    w, h = img.size

    for box in report.boxes.filter(confirmed=True):
        x1, y1 = int(box.x * w), int(box.y * h)
        x2, y2 = int((box.x + box.w) * w), int((box.y + box.h) * h)
        region = img.crop((x1, y1, x2, y2))
        # pixelation più robusta del blur contro re-identificazione
        small = region.resize((max(1, (x2-x1)//10), max(1, (y2-y1)//10)))
        pixelated = small.resize((x2-x1, y2-y1), Image.NEAREST)
        img.paste(pixelated, (x1, y1))

    output_path = report.image.path.replace('originals', 'redacted')
    img.save(output_path, quality=90)
    report.redacted_image.name = output_path.replace(settings.MEDIA_ROOT, '').lstrip('/')
    report.status = 'reviewed'
    report.save()
