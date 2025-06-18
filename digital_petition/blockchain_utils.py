import hashlib
import json
import time
import os

BLOCKCHAIN_FILE = 'blockchain.json'
USERS_DB_FILE = 'users.json'

def load_users_db():
    if not os.path.exists(USERS_DB_FILE):
        return {}
    with open(USERS_DB_FILE, 'r') as f:
        return json.load(f)

def calculate_hash(block):
    block_string = f"{block['index']}{block['timestamp']}{block['username']}{block['petition_id']}{block['signature']}{block['previous_hash']}"
    return hashlib.sha256(block_string.encode()).hexdigest()

def create_genesis_block():
    genesis_block = {
        'index': 0,
        'timestamp': time.time(),
        'username': 'genesis',
        'petition_id': '0',
        'signature': '',
        'previous_hash': '0',
        'hash': ''
    }
    genesis_block['hash'] = calculate_hash(genesis_block)
    return [genesis_block]

def load_blockchain():
    if not os.path.exists(BLOCKCHAIN_FILE):
        chain = create_genesis_block()
        save_blockchain(chain)
        return chain

    with open(BLOCKCHAIN_FILE, 'r') as f:
        try:
            chain = json.load(f)
            if not chain:
                chain = create_genesis_block()
                save_blockchain(chain)
            return chain
        except json.JSONDecodeError:
            chain = create_genesis_block()
            save_blockchain(chain)
            return chain

def save_blockchain(chain):
    with open(BLOCKCHAIN_FILE, 'w') as f:
        json.dump(chain, f, indent=2)

def get_last_block(chain):
    return chain[-1]

def add_block(username, petition_id, signature):
    chain = load_blockchain()
    last_block = get_last_block(chain)

    new_block = {
        'index': last_block['index'] + 1,
        'timestamp': time.time(),
        'username': username,
        'petition_id': petition_id,
        'signature': signature,
        'previous_hash': last_block['hash'],
        'hash': ''
    }
    new_block['hash'] = calculate_hash(new_block)
    chain.append(new_block)
    save_blockchain(chain)
    return new_block

def validate_chain(chain=None):
    if chain is None:
        chain = load_blockchain()

    for i in range(1, len(chain)):
        prev = chain[i-1]
        curr = chain[i]
        if curr['previous_hash'] != prev['hash']:
            return False, f"Block {i} has invalid previous hash"
        if curr['hash'] != calculate_hash(curr):
            return False, f"Block {i} has invalid current hash"
    return True, "Blockchain is valid"


from crypto_utils import verify_signature

def validate_signatures():
    chain = load_blockchain()
    users_db = load_users_db()

    if len(chain) <= 1:
        return True, "Tidak ada signature untuk diverifikasi."

    for i in range(1, len(chain)):
        block = chain[i]
        username = block['username']
        petition_id = block['petition_id']
        signature = block['signature']

        public_key_str = users_db.get(username)
        if public_key_str is None:
            return False, f"Kunci publik untuk user '{username}' tidak ditemukan di registri pada blok ke-{i}"

        petition_text = load_petition_text(petition_id)
        if petition_text is None:
            return False, f"Petisi {petition_id} tidak ditemukan untuk blok ke-{i}"

        message = petition_text + username

        if not verify_signature(message, signature, public_key_str):
            return False, f"Signature tidak valid pada blok ke-{i} oleh {username}"
    return True, "Semua signature valid."

# Helper: ambil teks petisi dari file
def load_petition_text(pid):
    if not os.path.exists("petition_data.json"):
        return None
    with open("petition_data.json", "r") as f:
        petitions = json.load(f)
    return petitions.get(pid, None)

