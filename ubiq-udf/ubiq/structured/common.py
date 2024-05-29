import base64

from .algo import ffx

import cryptography.hazmat.primitives as crypto
from cryptography.hazmat.backends import default_backend as crypto_backend
from typing import Dict, Any, Tuple

def strConvertRadix(s: str, ics: str, ocs: str) -> str:
    return ffx.NumberToString(len(ocs), ocs,
                              ffx.StringToNumber(len(ics), ics, s),
                              len(s))

def fmtInput(s: str, pth: str, ics: str, ocs: str, rules = []) -> Tuple[str, str, list]:
    fmt = ''
    trm = '%s'%(s)
    
    # Check if there's a passthrough rule. If not, create for legacy passthrough.
    if not any(rule.get('type') == 'passthrough' for rule in rules):
        rules.insert(0, {'type': 'passthrough', 'value': pth, 'priority': 1})
        
    # Sort the rules by priority
    rules.sort(key=lambda x: x['priority'])
    for idx, rule in enumerate(rules):
        if(rule['type'] == 'passthrough'):
            pth = rule['value']
            o = ''
            for c in trm:
                if c in pth:
                    fmt += c
                else:
                    fmt += ocs[0]
                    o += c
            trm = o
        elif(rule['type'] == 'prefix'):
            rules[idx]['buffer'] = trm[:rule['value']]
            trm = trm[rule['value']:]
        elif(rule['type'] == 'suffix'):
            rules[idx]['buffer'] = trm[(-1 * rule['value']):]
            trm = trm[:(-1 * rule['value'])]
        else:
            raise RuntimeError('Ubiq Python Library does not support rule type "%s" at this time.'%(rule['type']))

    # Validate final string contains only allowed characters.
    if not all((c in ics) for c in trm):
        raise RuntimeError('Invalid input string character(s)')

    return fmt, trm, rules

def encKeyNumber(s: str, ocs: str, n: str, sft: int) -> str:
    return ocs[ocs.find(s[0]) + (int(n) << sft)] + s[1:]

def decKeyNumber(s: str, ocs: str, sft: int) -> Tuple[str, int]:
    charBuf = s[0]
    encoded_value = ocs.find(charBuf)
    key_num = encoded_value >> sft

    return ocs[encoded_value - (key_num << sft)] + s[1:], key_num

def fmtOutput(fmt, s: str, pth: str, rules = []) -> str:
    # Sort the rules by decreasing priority
    rules.sort(key=lambda x: x['priority'], reverse=True)

    for rule in rules:
        if(rule['type'] == 'passthrough'):
            o = ''
            for c in fmt:
                if c not in pth:
                    o, s = o + s[0], s[1:]
                else:
                    o += c
                
            if len(s) > 0:
                raise RuntimeError('mismatched format and output strings')
            s = o
        elif(rule['type'] == 'prefix'):
            s = rule['buffer'] + s
        elif(rule['type'] == 'suffix'):
            s = s + rule['buffer']
        else:
            raise RuntimeError('Ubiq Python Library does not support rule type "%s" at this time.'%(rule['type']))

    return s

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
