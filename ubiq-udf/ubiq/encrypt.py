import struct
import base64
import cryptography.hazmat.primitives as crypto
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.backends import default_backend as crypto_backend
from typing import Dict, Any
from ubiq.algorithm import algorithm

class encryption:
    """Ubiq Platform Encryption object

    This object represents a single data encryption key and can be used
    to encrypt several separate plain texts using the same key
    """

    def __init__(self, secret_crypto_access_key: str, ubiq_params: Dict[str, Any]):
        """Initialize the encryption object

        secret_crypto_access_key:
            The client's secret RSA encryption key/password (used to decrypt
            the client's RSA key from the server). This key is not retained
            by this object.
        ubiq_params:
            The contents of the repsonse from the Ubiq encryption endpoint.
        """

        self._key = {}
        self._key['id'] = ubiq_params['key_fingerprint']
        self._key['session'] = ubiq_params['encryption_session']
        self._key['security_model'] = ubiq_params['security_model']
        self._key['algorithm'] = self._key['security_model']['algorithm'].lower()
        self._key['max_uses'] = ubiq_params['max_uses']
        self._key['uses'] = 0

        #
        # decrypt the client's private key. if the decryption fails,
        # the function raises a ValueError which is propagated up.
        #
        prvkey = load_pem_private_key(
            ubiq_params['encrypted_private_key'].encode('utf-8'), secret_crypto_access_key.encode('utf-8'),
            crypto_backend())

        #
        # use the client's private key to decrypt the data key to
        # be used for encryption
        #
        self._key['raw'] = prvkey.decrypt(
            base64.b64decode(ubiq_params['wrapped_data_key']),
            crypto.asymmetric.padding.OAEP(
                mgf=crypto.asymmetric.padding.MGF1(
                    algorithm=crypto.hashes.SHA1()),
                algorithm=crypto.hashes.SHA1(),
                label=None))

        #
        # the service also returns the encryption key encrypted by
        # its own master key. this value is attached to each cipher
        # text created by this object
        #
        self._key['encrypted'] = base64.b64decode(ubiq_params['encrypted_data_key'])

        self._algo = algorithm(self._key['algorithm'])


    def begin(self):
        """Begin the encryption process

        When this function is called, the encryption object increments
        the number of uses of the key and creates a new internal context
        to be used to encrypt the data.
        """
        if hasattr(self, '_enc'):
            raise RuntimeError("encryption already in progress")

        if self._key['uses'] >= self._key['max_uses']:
            raise RuntimeError("maximum key uses exceeded")
        self._key['uses'] += 1

        # create a new encryption context
        self._enc, iv = self._algo.encryptor(self._key['raw'])

        # VER 0, Flags 1 bit means AAD
        hdr = struct.pack('!BBBBH',
                          0, algorithm.UBIQ_HEADER_V0_FLAG_AAD,
                          self._algo.id,
                          len(iv), len(self._key['encrypted']));
        hdr += iv + self._key['encrypted']
        self._enc.authenticate_additional_data(hdr)

        # create and return the header for the cipher text
        return (hdr)

    def update(self, data: Any):
        """Encrypt some plain text -
        plain text value has to be contained in a bytes, bytearray or memoryview object.

        Any cipher text produced by the operation is returned
        """

        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise RuntimeError("Data must be bytes, bytearray, or memoryview objects")

        return self._enc.update(data)

    def end(self):
        """Finalize an encryption

        This function finalizes the encryption (producing the final
        cipher text for the encryption, if necessary) and adds any
        authentication information (if required by the algorithm).
        Any data produced is returned by the function.

        This function also resets the internal context, so that the
        caller can start a new encryption using the begin() function.
        """
        res = self._enc.finalize()
        if not self._algo.len['tag'] == 0:
            res += self._enc.tag

        del self._enc
        return res

def encrypt(data: Any, secret_crypto_access_key: str, ubiq_params: Dict[str, Any]):
    """Simple encryption interface

    data:
        A byte string containing the plain text to be encrypted
    secret_crypto_access_key:
        The client's secret RSA encryption key/password (used to decrypt
        the client's RSA key from the server).
    ubiq_params:
        The contents of the response from the Ubiq encryption endpoint.

    returns:
        the entire cipher text that can be passed to the decrypt function
    """
    enc = encryption(secret_crypto_access_key, ubiq_params)
    return enc.begin() + enc.update(data) + enc.end()
