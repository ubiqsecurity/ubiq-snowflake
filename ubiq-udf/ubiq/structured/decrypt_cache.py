import base64
from typing import Dict, List, Any

from .algo import ff1

from .common import fmtInput, strConvertRadix, decKeyNumber, fmtOutput
from .common import fetchKey

class DecryptionWithCache:
    def __init__(self, dataset_name: str, ubiq_cache: Dict[str, Any]) -> None:
        self._cache = ubiq_cache[dataset_name]

        try:
            self._cache = ubiq_cache[dataset_name]
        except KeyError as e:
            raise RuntimeError("Definition for dataset name \"%s\" not found in provided Cache.", dataset_name)
        
        self._dataset = self._cache['ffs']

    def Cipher(self, ct: str, twk = None) -> str:
        pth = self._dataset['passthrough']
        ics = self._dataset['input_character_set']
        ocs = self._dataset['output_character_set']

        fmt, ct = fmtInput(ct, pth, ocs, ics)
        ct, n = decKeyNumber(ct, ocs, self._dataset['msb_encoding_bits'])

        key = base64.b64decode(self._cache['keys'][n])
        
        if self._dataset['encryption_algorithm'] == 'FF1':
            self._ctx = ff1.Context(
                key,
                base64.b64decode(self._dataset['tweak']),
                self._dataset['tweak_min_len'], self._dataset['tweak_max_len'],
                len(ics), ics)
        else:
            raise RuntimeError('unsupported algorithm: ' +
                                self._dataset['encryption_algorithm'])
        
        ct = strConvertRadix(ct, ocs, ics)

        pt = self._ctx.Decrypt(ct, twk)

        return fmtOutput(fmt, pt, pth)

def DecryptCache(
    dataset_name: str, 
    ubiq_cache: Dict[str, Any], 
    cipher_text: str, 
    twk=None) -> List[str]:

    return DecryptionWithCache(dataset_name, ubiq_cache).Cipher(cipher_text, twk)

def DecryptCacheBatch(
    dataset_name: str, 
    ubiq_cache: Dict[str, Any], 
    cipher_text_strings: List[str], 
    twk=None) -> List[str]:

    # Initialize the decryption algorithm for the given secret crypto access key, 
    # Dataset and Keys
    decryption = DecryptionWithCache(dataset_name, ubiq_cache)
    
    # Iteratively decrypt all plain text data
    return [decryption.Cipher(cipher_text, twk) for cipher_text in cipher_text_strings]
