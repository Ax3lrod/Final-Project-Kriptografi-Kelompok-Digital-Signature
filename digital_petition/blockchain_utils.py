import hashlib
import json
import time
import os

BLOCKCHAIN_FILE = 'blockchain.json'
USERS_DB_FILE = 'users.json'

def load_users_db():
    # Memuat database user dari file JSON.
    if not os.path.exists(USERS_DB_FILE):
        return {}
    with open(USERS_DB_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def calculate_hash(block):
    # Menghitung hash unik untuk sebuah blok.
    block_copy = block.copy()
    block_copy.pop('hash', None)
    block_string = json.dumps(block_copy, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()

def create_genesis_block():
    # Membuat blok pertama (genesis) blockchain.
    genesis_block = {
        'index': 0,
        'timestamp': time.time(),
        'transaction_type': 'GENESIS',
        'transaction_data': {},
        'previous_hash': '0',
        'hash': ''
    }
    genesis_block['hash'] = calculate_hash(genesis_block)
    return [genesis_block]

def load_blockchain():
    # Memuat atau membuat blockchain dari file.
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
    # Menyimpan state blockchain ke file JSON.
    with open(BLOCKCHAIN_FILE, 'w') as f:
        json.dump(chain, f, indent=2)

def get_last_block(chain):
    # Mengambil blok terakhir dari sebuah chain.
    return chain[-1]

def add_block(transaction_type, transaction_data):
    # Menambahkan blok transaksi baru ke chain.
    chain = load_blockchain()
    last_block = get_last_block(chain)

    new_block = {
        'index': last_block['index'] + 1,
        'timestamp': time.time(),
        'transaction_type': transaction_type,
        'transaction_data': transaction_data,
        'previous_hash': last_block['hash'],
        'hash': ''
    }
    new_block['hash'] = calculate_hash(new_block)
    chain.append(new_block)
    save_blockchain(chain)
    return new_block

def validate_chain(chain=None):
    # Memvalidasi integritas hash seluruh chain.
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
    # Memvalidasi semua tanda tangan dalam blockchain.
    chain = load_blockchain()
    users_db = load_users_db()

    if len(chain) <= 1:
        return True, "Tidak ada signature untuk diverifikasi."

    for i in range(1, len(chain)):
        block = chain[i]
        
        if block.get('transaction_type') == 'SIGN_PETITION':
            tx_data = block.get('transaction_data', {})
            username = tx_data.get('signer_username')
            petition_id = tx_data.get('petition_id')
            signature = tx_data.get('signature')

            if not all([username, petition_id, signature]):
                return False, f"Struktur transaksi tidak lengkap pada blok ke-{i}"

            public_key_str = users_db.get(username)
            if public_key_str is None:
                return False, f"Kunci publik untuk user '{username}' tidak ditemukan di registri pada blok ke-{i}"

            petition_text = load_petition_text(petition_id, chain)
            if petition_text is None:
                return False, f"Petisi {petition_id} tidak ditemukan untuk blok ke-{i}"

            message = petition_text + username

            if not verify_signature(message, signature, public_key_str):
                return False, f"Signature tidak valid pada blok ke-{i} oleh {username}"
    return True, "Semua signature valid."

def load_petition_text(pid, chain):
    # Helper: Ambil teks petisi dengan mencarinya di dalam blockchain.
    for block in chain:
        if block.get('transaction_type') == 'CREATE_PETITION':
            tx_data = block.get('transaction_data', {})
            if tx_data.get('petition_id') == pid:
                return tx_data.get('petition_text')
    return None
