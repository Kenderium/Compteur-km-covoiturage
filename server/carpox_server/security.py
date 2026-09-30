"""Mots de passe et jetons.

- Mots de passe : scrypt (bibliothèque standard), sel aléatoire par
  utilisateur, comparaison en temps constant.
- Jetons de session, de boîtier et personnels (Home Assistant) : aléatoires,
  seule leur empreinte SHA-256 est stockée en base (une fuite de la base ne
  donne pas accès aux comptes).
"""

import base64
import hashlib
import hmac
import secrets

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
MIN_PASSWORD_LENGTH = 10


def _b64(data):
    return base64.b64encode(data).decode()


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
                            maxmem=64 * 1024 * 1024, dklen=32)
    return "scrypt$%d$%d$%d$%s$%s" % (SCRYPT_N, SCRYPT_R, SCRYPT_P, _b64(salt), _b64(digest))


def verify_password(password, stored):
    try:
        algo, n, r, p, salt, digest = stored.split("$")
        if algo != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r),
                                p=int(p), maxmem=64 * 1024 * 1024, dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# Empreinte factice : on la vérifie quand l'utilisateur n'existe pas, pour que
# la réponse prenne le même temps (on ne révèle pas quels comptes existent).
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def new_token():
    return secrets.token_urlsafe(32)


API_TOKEN_PREFIX = "cpx_"


def new_api_token():
    """Jeton personnel : préfixe reconnaissable (utile si on le retrouve dans un fichier)."""
    return API_TOKEN_PREFIX + secrets.token_urlsafe(32)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def new_ble_pin():
    return "%06d" % secrets.randbelow(1000000)


def new_device_id():
    return "box-" + secrets.token_hex(4)


def check_password_strength(password):
    """Retourne un message d'erreur, ou None si le mot de passe convient."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return "Le mot de passe doit faire au moins %d caractères." % MIN_PASSWORD_LENGTH
    if len(password) > 256:
        return "Mot de passe trop long."
    if len(set(password)) < 5:
        return "Mot de passe trop simple."
    return None
