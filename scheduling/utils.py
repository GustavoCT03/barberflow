
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings

signer = TimestampSigner(salt="barberflow-links")

def firmar(payload: str) -> str:
    return signer.sign(payload)

def verificar(token: str, max_age=60*60*3): 
    try:
        data = signer.unsign(token, max_age=max_age)
        return data
    except (BadSignature, SignatureExpired):
        return None

from django.core import signing

def generar_token_waitlist(entry_id: int) -> str:
    return signing.dumps({'wl': entry_id})

def validar_token_waitlist(token: str):
    try:
        data = signing.loads(token, max_age=900)  # 15 min
        return data.get('wl')
    except (signing.BadSignature, signing.SignatureExpired):
        return None