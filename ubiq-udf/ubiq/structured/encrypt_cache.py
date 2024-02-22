import base64
from typing import Dict, List, Any
import json

from .algo import ff1

from .common import fmtInput, strConvertRadix, encKeyNumber, fmtOutput
from .common import fetchKey

class EncryptionWithCache:
    def __init__(self, dataset_name: str, ubiq_cache: Dict[str, Any]) -> None:
        try:
            self._cache = ubiq_cache[dataset_name]
        except KeyError as e:
            raise RuntimeError("Definition for dataset name \"%s\" not found in provided Cache.", dataset_name)
        # ubiq_get_encrypt_key reduces the cache `.keys` to only contain the current key to cut down on keys transferred
        if self._cache.get('current_key_only'):
            self._key = {
                'key_number': self._cache['current_key_number'],
                'unwrapped_data_key': base64.b64decode(self._cache["keys"][0])
            }
        else:
            self._key = {
                'key_number': self._cache['current_key_number'],
                'unwrapped_data_key': base64.b64decode(self._cache["keys"][int(self._cache['current_key_number'])])
            }

        self._dataset = self._cache['ffs']

        if self._dataset['encryption_algorithm'] == 'FF1':
            self._algo = ff1.Context(
                self._key['unwrapped_data_key'],
                base64.b64decode(self._dataset['tweak']),
                self._dataset['tweak_min_len'], self._dataset['tweak_max_len'],
                len(self._dataset['input_character_set']),
                self._dataset['input_character_set'])
        else:
            raise RuntimeError('unsupported algorithm: ' +
                               self._dataset['encryption_algorithm'])
    
    def Cipher(self, pt: str, twk=None) -> str:
        pth = self._dataset['passthrough']
        ics = self._dataset['input_character_set']
        ocs = self._dataset['output_character_set']

        fmt, pt = fmtInput(pt, pth, ics, ocs)

        ct = self._algo.Encrypt(pt, twk)

        ct = strConvertRadix(ct, ics, ocs)
        ct = encKeyNumber(ct, ocs,
                          self._key['key_number'],
                          self._dataset['msb_encoding_bits'])
        return fmtOutput(fmt, ct, pth)
    
    def CipherForSearch(self, pt, twk=None) -> list:
        if self._cache.get('current_key_only'):
            raise Exception('Encrypting for Search requires more than just the current key. Please check your configuration.')
        
        pth = self._dataset['passthrough']
        ics = self._dataset['input_character_set']
        ocs = self._dataset['output_character_set']
        fmt, pt = fmtInput(pt, pth, ics, ocs)

        searchCipher = []
        for key_num, key in enumerate(self._cache['keys']):
            algo = ff1.Context(
                base64.b64decode(key),
                base64.b64decode(self._dataset['tweak']),
                self._dataset['tweak_min_len'], self._dataset['tweak_max_len'],
                len(ics),
                ics)
            ct = algo.Encrypt(pt, twk)
            ct = strConvertRadix(ct, ics, ocs)
            ct = encKeyNumber(ct, ocs, key_num, self._dataset['msb_encoding_bits'])
            searchCipher.append(fmtOutput(fmt, ct, pth))

        return searchCipher

def EncryptCache(
    dataset_name: str, 
    ubiq_cache: Dict[str, Any], 
    plain_text: str, 
    twk=None) -> str:  

    return EncryptionWithCache(dataset_name, ubiq_cache).Cipher(plain_text, twk)

def EncryptCacheBatch(
    dataset_name: str, 
    ubiq_cache: Dict[str, Any], 
    plain_text_strings: List[str], 
    twk=None) -> List[str]:

    """
        For use with the Snowflake Batch API
    """
    # Initialize the encryption algorithm for the given secret crypto access key, 
    # Dataset and Keys
    encryption = EncryptionWithCache(dataset_name, ubiq_cache)

    # Iteratively encrypt all plain text data
    return [encryption.Cipher(plain_text, twk) for plain_text in plain_text_strings]

def EncryptForSearchCache(
        dataset_name: str,
        ubiq_cache: Dict[str, Any],
        plain_text: str,
        twk=None) -> list:
    encryption = EncryptionWithCache(dataset_name, ubiq_cache)

    return encryption.CipherForSearch(plain_text, twk)
