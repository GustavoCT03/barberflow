
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings
from django.core import signing
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

signer = TimestampSigner(salt="barberflow-links")

def firmar(payload: str) -> str:
    return signer.sign(payload)

def verificar(token: str, max_age=60*60*3): 
    try:
        data = signer.unsign(token, max_age=max_age)
        return data
    except (BadSignature, SignatureExpired):
        return None



def generar_token_waitlist(entry_id: int) -> str:
    return signing.dumps({'wl': entry_id})

def validar_token_waitlist(token: str):
    try:
        data = signing.loads(token, max_age=900)  # 15 min
        return data.get('wl')
    except (signing.BadSignature, signing.SignatureExpired):
        return None

def firmar(payload: str) -> str:
    """Genera token firmado para cualquier payload"""
    return signing.dumps(payload)

def verificar_firma(token: str, max_age: int = 3600) -> str:
    """Verifica token firmado y devuelve payload original"""
    try:
        return signing.loads(token, max_age=max_age)
    except (signing.BadSignature, signing.SignatureExpired):
        return None
def enviar_notificacion(user_id, tipo, mensaje, data=None):
    """Envía notificación push vía WebSocket"""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'user_{user_id}',
        {
            'type': 'notificacion_nueva',
            'tipo': tipo,
            'mensaje': mensaje,
            'data': data or {}
        }
    )