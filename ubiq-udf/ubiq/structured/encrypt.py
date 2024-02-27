import base64
from typing import Dict, List, Any

from .algo import ff1

from .common import fmtInput, strConvertRadix, encKeyNumber, fmtOutput
from .common import fetchKey

class Encryption:
    def __init__(self, secret_crypto_access_key: str, ubiq_dataset_params: Dict[str, Any], ubiq_key_params: Dict[str, Any]) -> None:
        if not secret_crypto_access_key:
            raise RuntimeError("secret crypto access key not set")

        self._dataset = ubiq_dataset_params
        self._udkey = base64.b64decode(fetchKey(ubiq_key_params, secret_crypto_access_key))
        self._keyNum = ubiq_key_params['key_number']

        if self._dataset['encryption_algorithm'] == 'FF1':
            self._algo = ff1.Context(
                self._udkey,
                base64.b64decode(self._dataset['tweak']),
                self._dataset['tweak_min_len'], self._dataset['tweak_max_len'],
                len(self._dataset['input_character_set']),
                self._dataset['input_character_set'])
        else:
            raise RuntimeError('unsupported algorithm: ' +
                               self._dataset['encryption_algorithm'])

    def Cipher(self, pt: str, twk = None) -> str:
        pth = self._dataset['passthrough']
        ics = self._dataset['input_character_set']
        ocs = self._dataset['output_character_set']

        fmt, pt = fmtInput(pt, pth, ics, ocs)

        ct = self._algo.Encrypt(pt, twk)

        ct = strConvertRadix(ct, ics, ocs)
        ct = encKeyNumber(ct, ocs,
                          self._keyNum['key_number'],
                          self._dataset['msb_encoding_bits'])
        return fmtOutput(fmt, ct, pth)

def Encrypt(
    secret_crypto_access_key: str, 
    ubiq_dataset_params: Dict[str, Any], 
    ubiq_key_params: Dict[str, Any], 
    plain_text_strings: List[str], 
    twk = None) -> List[str]:
    
    # Initialize the encryption algorithm for the given secret crypto access key, 
    # Dataset and Keys (note that this assumes that the same key is used for all 
    # data in the current batch)
    encryption = Encryption(secret_crypto_access_key, ubiq_dataset_params, ubiq_key_params)    
    
    # Iteratively encrypt all plain text data
    return [encryption.Cipher(plain_text, twk) for plain_text in plain_text_strings]
