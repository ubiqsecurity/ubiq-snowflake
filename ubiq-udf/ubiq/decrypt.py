import base64
import struct
import cryptography.exceptions as crypto_exceptions
import cryptography.hazmat.primitives as crypto
from cryptography.hazmat.primitives.hashes import Hash, SHA1, SHA256
from cryptography.hazmat.backends import default_backend as crypto_backend
from typing import Dict, Any
from .algorithm import algorithm

class decryption:
    def __init__(self, secret_crypto_access_key: str, ubiq_params: Dict[str, Any]):
        """Initialize the encryption object

        secret_crypto_access_key:
            The client's secret RSA encryption key/password (used to decrypt
            the client's RSA key from the server). This key is not retained
            by this object.
        ubiq_params:
            The contents of the repsonse from the Ubiq decryption endpoint.
        """

        self._key = {}
        self._key['session'] = ubiq_params['encryption_session']
        self._key['finger_print'] = ubiq_params['key_fingerprint']
        self._key['encrypted_private_key'] = ubiq_params['encrypted_private_key']
        self._key['wrapped_data_key'] = ubiq_params['wrapped_data_key']

        if not secret_crypto_access_key:
            raise RuntimeError("secret crypto access key not set")

        self._srsa = secret_crypto_access_key

    def begin(self):
        """Begin the decryption process

        returns:
            any plain text produced by the call
        """

        # this interface does not take any cipher text in its arguments
        # in an attempt to maintain an API that corresponds to the
        # encryption object. in doing so, the work that can take place
        # in this function is limited. without any data, there is no
        # way to determine which key is in use or decrypt any data.
        #
        # this function simply throws an error if starting an decryption
        # while one is already in progress, and initializes the internal
        # buffer, otherwise

        if 'dec' in self._key:
            raise RuntimeError("decryption already in progress")

        self._buf = b''
        return b''

    def update(self, data):
        """Decrypt cipher text

        Cipher text must be passed to this function in the order in
        which it was output from the encryption.update function.

        data:
            (A portion of) the cipher text to be decrypted.  data
            value has to be contained in a bytes, bytearray or memoryview object.

        returns:
            any plain text produced by the call
        """

        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise RuntimeError("Data must be bytes, bytearray, or memoryview objects")

        #
        # each encryption has a header on it that identifies the algorithm
        # used  and an encryption of the data key that was used to encrypt
        # the original plain text. there is no guarantee how much of that
        # data will be passed to this function or how many times this
        # function will be called to process all of the data. to that end,
        # this function buffers data internally, when it is unable to
        # process it.
        #
        # the function buffers data internally until the entire header is
        # received. once the header has been received, the encrypted data
        # key is sent to the server for decryption. after the header has
        # been successfully handled, this function always decrypts all of
        # the data in its internal buffer *except* for however many bytes
        # are specified by the algorithm's tag size. see the end() function
        # for details.
        #

        self._buf += data
        pt = b''

        # if there is no key or 'dec' member of key, then the code
        # is still trying to build a complete header

        if not 'dec' in self._key:
            fmt = '!BBBBH'
            fmtlen = struct.calcsize(fmt)

            # does the buffer contain enough of the header to
            # determine the lengths of the initialization vector
            # and the key?

            if len(self._buf) >= fmtlen:
                ver, flags, alg, veclen, keylen = struct.unpack(
                    fmt, self._buf[:fmtlen])

                # For VER 0, lsb of indicates AAD or not
                if (ver != 0) or (flags & ~algorithm.UBIQ_HEADER_V0_FLAG_AAD):
                    raise RuntimeError('invalid encryption header')

                # does the buffer contain the entire header?

                if len(self._buf) >= fmtlen + veclen + keylen:

                    # Get the Header for AAD purposes.  Only needed if
                    # version != 0, but get it now anyways
                    aad = self._buf[:fmtlen + veclen + keylen]
                    # extract the initialization vector and the key
                    vec = self._buf[fmtlen:fmtlen + veclen]
                    key = self._buf[fmtlen + veclen:fmtlen + veclen + keylen]

                    # remove the header from the buffer
                    self._buf = self._buf[fmtlen + veclen + keylen:]

                    # generate a local identifier for the key
                    sha = Hash(SHA256(), backend=crypto_backend())
                    sha.update(key)
                    client_id = sha.finalize()
                    
                    self._key['algo']      = algorithm(alg)
                    
                    # the client's id for recognizing key reuse
                    self._key['client_id'] = client_id

                    # decrypt the client's private key (sent
                    # by the server)
                    prvkey = crypto.serialization.load_pem_private_key(
                        self._key['encrypted_private_key'].encode('utf-8'),
                        self._srsa.encode('utf-8'),
                        crypto_backend())
                    # use the private key to decrypt the data key
                    self._key['raw'] = prvkey.decrypt(
                        base64.b64decode(self._key['wrapped_data_key']),
                        crypto.asymmetric.padding.OAEP(
                            mgf=crypto.asymmetric.padding.MGF1(
                                algorithm=SHA1()),
                            algorithm=SHA1(),
                            label=None))

                    # this key hasn't been used (yet)
                    self._key['uses'] = 0

                    # Create a new decryptor with the initialization vector 
                    # from the header and the decrypted key (which is either 
                    # new from the server or cached from the previous decryption). 
                    # In either case, increment the key usage
                    self._key['dec'] = self._key['algo'].decryptor(
                        self._key['raw'], vec)
                    self._key['uses'] += 1

                    if (flags & algorithm.UBIQ_HEADER_V0_FLAG_AAD):
                        self._key['dec'].authenticate_additional_data(aad)

        # if the object has a decryptor, then decrypt whatever data is 
        # in the buffer, less any data that needs to be saved to
        # serve as the tag.
        if 'dec' in self._key:
            sz = len(self._buf) - self._key['algo'].len['tag']
            if sz > 0:
                pt = self._key['dec'].update(self._buf[:sz])
                self._buf = self._buf[sz:]

        return pt

    def end(self):
        """Finish a decryption

        returns:
            any plain text produced by the call
        """
        # the update function always maintains tag-size bytes in
        # the buffer because this function provides no data parameter.
        # by the time the caller calls this function, all data must
        # have already been input to the decryption object.

        pt = b''

        try:
            # determine how much of the buffer contains data
            # and how much of it contains the tag
            sz = len(self._buf) - self._key['algo'].len['tag']

            if sz < 0:
                # there's not enough data in the buffer for a complete tag
                raise crypto_exceptions.InvalidTag
            elif sz == 0:
                # the buffer contains exactly the right amount of data
                # for a complete tag. if the tag length is zero, just
                # finalize the decryption
                if self._key['algo'].len['tag'] == 0:
                    pt = self._key['dec'].finalize()
                else:
                    pt = self._key['dec'].finalize_with_tag(self._buf)
            else:
                # this is a logic error that can't occur based
                # on the logic in the update function. the update
                # function never leaves more data than the tag
                # size in the buffer once the header has been
                # successfully parsed.
                raise AssertionError
        finally:
            del self._key['dec']
            del self._buf

        return pt

def decrypt(data: Any, secret_crypto_access_key: str, ubiq_params: Dict[str, Any]):
    """Simple decryption interface

    data:
        A byte string containing the cipher text to be decrypted
    secret_crypto_access_key:
        The client's secret RSA encryption key/password (used to decrypt
        the client's RSA key from the server).    
    ubiq_params:
        The contents of the response from the Ubiq decryption endpoint.

    returns:
        the entire cipher text that can be passed to the decrypt function
    """
    dec = decryption(secret_crypto_access_key, ubiq_params)
    return dec.begin() + dec.update(data) + dec.end()
