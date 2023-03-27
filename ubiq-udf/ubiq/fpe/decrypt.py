import base64
from typing import Dict, List, Any

from .algo import ff1

from .common import fmtInput, strConvertRadix, decKeyNumber, fmtOutput
from .common import fetchKey

class Decryption:
    def __init__(self, secret_crypto_access_key: str, ubiq_ffs_params: Dict[str, Any], ubiq_key_params: Dict[str, Any]) -> None:
        if not secret_crypto_access_key:
            raise RuntimeError("secret crypto access key not set")

        self._srsa = secret_crypto_access_key
        self._ffs = ubiq_ffs_params
        self._udkey = base64.b64decode(fetchKey(ubiq_key_params, secret_crypto_access_key))

    def Cipher(self, ct: str, twk = None) -> str:
        pth = self._ffs['passthrough']
        ics = self._ffs['input_character_set']
        ocs = self._ffs['output_character_set']

        fmt, ct = fmtInput(ct, pth, ocs, ics)
        ct, _ = decKeyNumber(ct, ocs, self._ffs['msb_encoding_bits'])
        
        if self._ffs['encryption_algorithm'] == 'FF1':
            self._ctx = ff1.Context(
                self._udkey,
                base64.b64decode(self._ffs['tweak']),
                self._ffs['tweak_min_len'], self._ffs['tweak_max_len'],
                len(ics), ics)
        else:
            raise RuntimeError('unsupported algorithm: ' +
                                self._ffs['encryption_algorithm'])
        
        ct = strConvertRadix(ct, ocs, ics)

        pt = self._ctx.Decrypt(ct, twk)

        return fmtOutput(fmt, pt, pth)

def Decrypt(
    secret_crypto_access_key: str, 
    ubiq_ffs_params: Dict[str, Any], 
    ubiq_key_params: Dict[str, Any], 
    cipher_text_strings: List[str], 
    twk = None) -> List[str]:
    
    # Initialize the decryption algorithm for the given secret crypto access key, 
    # FSS and FPE key (note that this assumes that the same key is used for all 
    # data in the current batch)
    # NOTE: If key is rotated, this will fail to decrypt older encrypted strings.
    decryption = Decryption(secret_crypto_access_key, ubiq_ffs_params, ubiq_key_params)
    
    # Iteratively decrypt all cipher text data
    return [decryption.Cipher(cipher_text, twk) for cipher_text in cipher_text_strings]
