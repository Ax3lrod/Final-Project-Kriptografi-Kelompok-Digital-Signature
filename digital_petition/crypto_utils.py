from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import os
import base64

def generate_keys_in_memory():
    key = RSA.generate(2048)
    private_key = key
    public_key = key.publickey()
    return private_key, public_key

def load_keys(username):
    with open(f'keys/{username}_private.pem', 'rb') as f:
        private_key = RSA.import_key(f.read())
    with open(f'keys/{username}_public.pem', 'rb') as f:
        public_key = RSA.import_key(f.read())
    return private_key, public_key

def sign_data(data: str, private_key):
    hash_obj = SHA256.new(data.encode('utf-8'))
    signature = pkcs1_15.new(private_key).sign(hash_obj)
    return base64.b64encode(signature).decode()

def verify_signature(message, signature, public_key_str):
    try:
        public_key = RSA.import_key(public_key_str)
        hash_obj = SHA256.new(message.encode())
        signature_bytes = base64.b64decode(signature)
        pkcs1_15.new(public_key).verify(hash_obj, signature_bytes)
        return True
    except (ValueError, TypeError):
        return False
