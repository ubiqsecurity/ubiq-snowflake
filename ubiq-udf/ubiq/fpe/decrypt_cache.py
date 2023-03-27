import base64
from typing import Dict, List, Any

from .algo import ff1

from .common import fmtInput, strConvertRadix, decKeyNumber, fmtOutput
from .common import fetchKey

class DecryptionWithCache:
    def __init__(self, ffs_name: str, ubiq_ffs_key_cache: Dict[str, Any]) -> None:
        self._cache = ubiq_ffs_key_cache[ffs_name]

        try:
            self._cache = ubiq_ffs_key_cache[ffs_name]
        except KeyError as e:
            raise RuntimeError("Definition for ffs name \"%s\" not found in provided Cache.", ffs_name)
        
        self._ffs = self._cache['ffs']

    def Cipher(self, ct: str, twk = None) -> str:
        pth = self._ffs['passthrough']
        ics = self._ffs['input_character_set']
        ocs = self._ffs['output_character_set']

        fmt, ct = fmtInput(ct, pth, ocs, ics)
        ct, n = decKeyNumber(ct, ocs, self._ffs['msb_encoding_bits'])

        key = base64.b64decode(self._cache['keys'][n])
        
        if self._ffs['encryption_algorithm'] == 'FF1':
            self._ctx = ff1.Context(
                key,
                base64.b64decode(self._ffs['tweak']),
                self._ffs['tweak_min_len'], self._ffs['tweak_max_len'],
                len(ics), ics)
        else:
            raise RuntimeError('unsupported algorithm: ' +
                                self._ffs['encryption_algorithm'])
        
        ct = strConvertRadix(ct, ocs, ics)

        pt = self._ctx.Decrypt(ct, twk)

        return fmtOutput(fmt, pt, pth)

def DecryptCache(
    ffs_name: str, 
    ubiq_ffs_key_cache: Dict[str, Any], 
    cipher_text: str, 
    twk=None) -> List[str]:

    return DecryptionWithCache(ffs_name, ubiq_ffs_key_cache).Cipher(cipher_text, twk)

def DecryptCacheBatch(
    ffs_name: str, 
    ubiq_ffs_key_cache: Dict[str, Any], 
    cipher_text_strings: List[str], 
    twk=None) -> List[str]:

    # Initialize the decryption algorithm for the given secret crypto access key, 
    # FSS and FPE key
    decryption = DecryptionWithCache(ffs_name, ubiq_ffs_key_cache)
    
    # Iteratively decrypt all plain text data
    return [decryption.Cipher(cipher_text, twk) for cipher_text in cipher_text_strings]
