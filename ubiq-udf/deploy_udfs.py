import fire
import pandas as pd
from typing import Iterable, Tuple
from snowflake.snowpark import Session
from snowflake.snowpark.types import PandasDataFrame, PandasSeries
from snowflake.snowpark.functions import pandas_udf
from typing import Dict
import ubiq
import ubiq.fpe as ubiqfpe


def deploy_functions(
    account: str,
    user: str,
    password: str,
    warehouse: str,
    database: str,
    schema: str,
    role="ACCOUNTADMIN",
    stage="ubiq_package_stage",
) -> None:
    """
    Creates a new Snowflake session, uploads Ubiq pacakge to the Snowflake
    stage, and deploys Ubiq encrypt/decrypt functions.

    Args:
        account: snowflake account name (excluding https:// prefix)
        user: snowflake username
        password: snowflake password
        warehouse: name of the Snowflake warehouse
        database: name of the Snowflake database in which to create Ubiq UDFs
        schema: name of the schema in which to create Ubiq UDFs
        stage: name of the Snowflake stage in which to serialize Ubiq library
            (defaults to ubiq_package_stage)
    """

    # Create the Snowflake session
    session = Session.builder.configs(
        {
            "account": account,
            "user": user,
            "password": password,
            "warehouse": warehouse,
            "database": database,
            "schema": schema,
            "role": role,
        }
    ).create()

    # Create the stage in which to store Ubiq client library code
    session.sql(f"create stage if not exists {stage}").collect()

    # Add the ubiq package to the session
    session.add_import("ubiq")

    # Register data key decryption function on Snowflake
    session.udf.register(
        ubiq_fetch_data_key,
        name="_ubiq_fetch_data_key",
        session=session,
        packages=["cryptography"],
        is_permanent=True,
        stage_location=stage,
        replace=True,
    )

    # Register standard/FPE encryption and decryption user-defined functions
    # (UDFs) on Snowflake
    session.udf.register(
        ubiq_encrypt,
        name="_ubiq_encrypt",
        session=session,
        packages=["cryptography"],
        is_permanent=True,
        stage_location=stage,
        replace=True,
    )
    session.udf.register(
        ubiq_encrypt_for_search,
        name="_ubiq_encrypt_for_search_array",
        session=session,
        packages=["cryptography"],
        is_permanent=True,
        stage_location=stage,
        replace=True,
    )
    session.udtf.register(
        EncryptForSearch,
        ["encrypted_data"],
        name="_ubiq_encrypt_for_search_table",
        is_permanent=True,
        replace=True,
        stage_location=stage,
        packages=["cryptography"]
    )
    session.udf.register(
        ubiq_decrypt,
        name="_ubiq_decrypt",
        session=session,
        packages=["cryptography"],
        is_permanent=True,
        stage_location=stage,
        replace=True,
    )

    # Used pandas_udf function to deploy as vectorized function
    pandas_udf(
        ubiq_encrypt_batch,
        name="_ubiq_encrypt_batch",
        session=session,
        packages=["cryptography"],
        is_permanent=True,
        stage_location=stage,
        replace=True,
    )
    # Used pandas_udf function to deploy as vectorized function
    pandas_udf(
        ubiq_decrypt_batch,
        name="_ubiq_decrypt_batch",
        session=session,
        packages=["cryptography"],
        is_permanent=True,
        stage_location=stage,
        replace=True,
    )


def ubiq_fetch_data_key(
    ffs_name: str, secret_crypto_access_key: str, ubiq_ffs_key_cache: Dict
) -> Dict:
    """ """
    dataset_names = ffs_name.split(',')
    for name in dataset_names:
        ubiq_ffs_key_cache[name]["keys"] = [
            ubiqfpe.common.fetchKey(
                {
                    "encrypted_private_key": ubiq_ffs_key_cache[name][
                        "encrypted_private_key"
                    ],
                    "wrapped_data_key": encrypted_key,
                },
                secret_crypto_access_key,
            )
            for encrypted_key in ubiq_ffs_key_cache[name]["keys"]
        ]

    return ubiq_ffs_key_cache

'''
Currently Deprecated
Users should use cache rather than passing/pulling at run time
'''
# def ubiq_encrypt(
#     df: PandasDataFrame[str, str, Dict, Dict],
# ) -> PandasSeries[str]:
#     """
#     Encrypts the given batch of plain text data using the Ubiq-provided key and
#     Field Format Specification (FFS).

#     Args:
#         df: data frame containing four columns of data at the following indices:
#             0. plain-text string data to be encrypted
#             1. The client's secret RSA encryption key/password (used to decrypt
#                 the client's RSA key from the server)
#             2. Ubiq field format specification (FFS) parameters
#             3. Ubiq format preserving encryption (FPE) endpoint response, including
#                 Ubiq encryption key

#     Returns:
#         Vector of encrypted cipher text for the given plain text strings.
#     """
#     return pd.Series(
#         ubiqfpe.Encrypt(df[1].iloc[0], df[2].iloc[0], df[3].iloc[0], df[0])
#     )

'''
Currently Deprecated
Users should use cache rather than passing/pulling at run time
'''
# def ubiq_decrypt(
#     df: PandasDataFrame[str, str, Dict, Dict],
# ) -> PandasSeries[str]:
#     """
#     Decrypts the given batch of cipher text strings using the Ubiq-provided key
#     and Field Format Specification (FFS).

#     Args:
#         df:
#             0: cipher-text string data to be decrypted
#             1: the client's secret RSA encryption key/password (used to decrypt
#                 the client's RSA key from the server)
#             2: Ubiq field format specification (FFS) parameters
#             3: Ubiq format preserving encryption (FPE) endpoint response,
#                 including Ubiq encryption key

#     Returns:
#         Vector of decrypted plain text for the given cipher text strings.
#     """
#     return pd.Series(
#         ubiqfpe.Decrypt(df[1].iloc[0], df[2].iloc[0], df[3].iloc[0], df[0])
#     )


def ubiq_encrypt(
    plain_text: str,
    ffs_name: str,
    ubiq_ffs_key_cache: Dict,
) -> str:
    """
    Encrypts the given plain text data using a Ubiq-provided key and Field
    Format Specification (FFS) cache dictionary of multiple FFS and possible keys.

    Args:
        plain_text: plain-text string data to be encrypted
        secret_crypto_access_key: The client's secret RSA encryption key/password
            (used to decrypt the client's RSA key from the server)
        ubiq_ffs_key_cache: Ubiq field format specification (FFS) parameters and
            Ubiq format preserving encryption (FPE) keys including Ubiq encryption
            keys

    Returns:
        Encrypted cipher text for the given plain-text string.
    """
    return ubiqfpe.EncryptCache(
        ffs_name, ubiq_ffs_key_cache, plain_text
    )


def ubiq_encrypt_for_search(
    plain_text: str,
    ffs_name: str,
    ubiq_ffs_key_cache: Dict,
) -> list:
    """
    Encrypts the given plain text data using a Ubiq-provided key and Field
    Format Specification (FFS) cache dictionary of multiple FFS and possible keys.

    Args:
        plain_text: plain-text string data to be encrypted
        secret_crypto_access_key: The client's secret RSA encryption key/password
            (used to decrypt the client's RSA key from the server)
        ubiq_ffs_key_cache: Ubiq field format specification (FFS) parameters and
            Ubiq format preserving encryption (FPE) keys including Ubiq encryption
            keys

    Returns:
        A list of encrypted cipher texts for the given plain-text string
    """
    return ubiqfpe.EncryptForSearchCache(
        ffs_name, ubiq_ffs_key_cache, plain_text
    )


class EncryptForSearch:
    def process(self,
                plain_text: str,
                ffs_name: str,
                ubiq_ffs_key_cache: Dict) -> Iterable[Tuple[str]]:
        res = ubiqfpe.EncryptForSearchCache(
            ffs_name, ubiq_ffs_key_cache, plain_text
        )
        for encrypted in res:
            yield (encrypted, )


def ubiq_decrypt(
    cipher_text: str,
    ffs_name: str,
    ubiq_ffs_key_cache: Dict,
) -> str:
    """
    Decrypts the given cipher text data using a Ubiq-provided key and Field
    Format Specification (FFS) cache dictionary of multiple FFS and possible keys.

    Args:
        cipher_text: cipher-text string data to be decrypted
        secret_crypto_access_key: The client's secret RSA encryption key/password
            (used to decrypt the client's RSA key from the server)
        ubiq_ffs_key_cache: Ubiq field format specification (FFS) parameters and
            Ubiq format preserving encryption (FPE) keys including Ubiq encryption
            keys

    Returns:
        Decrypted plain-text for the given cipher text string.
    """
    return ubiqfpe.DecryptCache(
        ffs_name, ubiq_ffs_key_cache, cipher_text
    )


def ubiq_encrypt_batch(
    df: PandasDataFrame[str, str, str, Dict],
) -> PandasSeries[str]:
    """
    Encrypts the given plain text data using a Ubiq-provided key and Field
    Format Specification (FFS) cache dictionary of multiple FFS and possible keys.

    Args:
        df:
            0: plain-text string data to be encrypted
            1: the client's secret RSA encryption key/password (used to decrypt
                the client's RSA key from the server)
            2: Ubiq field format specification (FFS) format preserving encryption (FPE)
                cache in one Dictionary
    Returns:
        Encrypted cipher text for the given plain-text string.
    """
    return pd.Series(
        ubiqfpe.EncryptCacheBatch(
            df[1].iloc[0], df[2].iloc[0], df[3].iloc[0], df[0])
    )


def ubiq_decrypt_batch(
    df: PandasDataFrame[str, str, str, Dict],
) -> PandasSeries[str]:
    """
    Decrypts the given cipher text data using a Ubiq-provided key and Field
    Format Specification (FFS) cache dictionary of multiple FFS and possible keys.

    Args:
        df:
            0: cipher-text string data to be decrypted
            1: the client's secret RSA encryption key/password (used to decrypt
                the client's RSA key from the server)
            2: Ubiq field format specification (FFS) format preserving encryption (FPE)
                cache in one Dictionary

    Returns:
        Decrypted plain-text for the given cipher text string.
    """
    return pd.Series(
        ubiqfpe.DecryptCacheBatch(
            df[1].iloc[0], df[2].iloc[0], df[3].iloc[0], df[0])
    )


if __name__ == "__main__":
    fire.Fire(deploy_functions)
