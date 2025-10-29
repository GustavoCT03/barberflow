
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

