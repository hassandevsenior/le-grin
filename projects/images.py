"""
Traitement des captures d'écran envoyées par les membres.

On ne stocke jamais le fichier reçu tel quel : il est ouvert, vérifié, réduit
puis réencodé en WebP. Ça écarte les faux fichiers image, supprime les
métadonnées, et allège les pages pour les connexions lentes.
"""

import uuid
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

MAX_WIDTH = 1440
MAX_RATIO = 1.6  # hauteur maximale = 1,6 x la largeur : on garde le haut d'une longue page
MAX_SOURCE_PIXELS = 40_000_000
MIN_WIDTH = 320


def process_screenshot(upload):
    """Valide `upload` et renvoie un ContentFile WebP prêt à être enregistré."""
    if upload.size > settings.MAX_SCREENSHOT_BYTES:
        raise ValidationError("Cette image est trop lourde (5 Mo maximum).")
    try:
        upload.seek(0)
        image = Image.open(upload)
        if image.width * image.height > MAX_SOURCE_PIXELS:
            raise ValidationError("Cette image est trop grande.")
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValidationError("Ce fichier n'est pas une image lisible (PNG, JPEG ou WebP).")

    if image.width < MIN_WIDTH:
        raise ValidationError("Cette capture est trop petite pour être lisible.")

    image = image.convert("RGB")
    max_height = int(image.width * MAX_RATIO)
    if image.height > max_height:
        image = image.crop((0, 0, image.width, max_height))
    if image.width > MAX_WIDTH:
        image = image.resize((MAX_WIDTH, round(image.height * MAX_WIDTH / image.width)), Image.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, "WEBP", quality=80, method=4)
    return ContentFile(buffer.getvalue(), name=f"{uuid.uuid4().hex}.webp")
