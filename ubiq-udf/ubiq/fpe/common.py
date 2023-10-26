import base64

from .algo import ffx

import cryptography.hazmat.primitives as crypto
from cryptography.hazmat.backends import default_backend as crypto_backend
from typing import Dict, Any, Tuple

def strConvertRadix(s: str, ics: str, ocs: str) -> str:
    return ffx.NumberToString(len(ocs), ocs,
                              ffx.StringToNumber(len(ics), ics, s),
                              len(s))

def fmtInput(s: str, pth: str, ics: str, ocs: str) -> Tuple[str, str]:
    fmt = ''
    trm = ''
    for c in s:
        if c in pth:
            fmt += c
        else:
            fmt += ocs[0]
            if c in ics:
                trm += c
            else:
                raise RuntimeError("invalid input character '%s' (valid characters: %s | valid passthrough characters: %s)" %(c, ics, pth))
    return fmt, trm

def encKeyNumber(s: str, ocs: str, n: str, sft: int) -> str:
    return ocs[ocs.find(s[0]) + (int(n) << sft)] + s[1:]

def decKeyNumber(s: str, ocs: str, sft: int) -> Tuple[str, int]:
    charBuf = s[0]
    encoded_value = ocs.find(charBuf)
    key_num = encoded_value >> sft

    return ocs[encoded_value - (key_num << sft)] + s[1:], key_num

def fmtOutput(fmt, s: str, pth: str) -> str:
    o = ''
    for c in fmt:
        if c not in pth:
            o, s = o + s[0], s[1:]
        else:
            o += c

    if len(s) > 0:
        raise RuntimeError('mismatched format and output strings')

    return o

def fetchKey(key: Dict[str, Any], srsa: str) -> str:
    prvkey = crypto.serialization.load_pem_private_key(
        key['encrypted_private_key'].encode(), srsa.encode(),
        crypto_backend())

    unwrapped_data_key = prvkey.decrypt(
        base64.b64decode(key['wrapped_data_key']),
        crypto.asymmetric.padding.OAEP(
            mgf=crypto.asymmetric.padding.MGF1(
                algorithm=crypto.hashes.SHA1()),
            algorithm=crypto.hashes.SHA1(),
            label=None))

    return base64.b64encode(unwrapped_data_key).decode()
