import json
import hashlib
import time
import os

BLOCKCHAIN_FILE = 'blockchain.json'

def load_blockchain():
    """Memuat blockchain dari file atau membuat genesis block"""
    if not os.path.exists(BLOCKCHAIN_FILE):
        # Buat genesis block
        genesis_block = {
            "index": 0,
            "timestamp": time.time(),
            "transaction_type": "GENESIS",
            "transaction_data": {"message": "Genesis Block"},
            "previous_hash": "0",
            "hash": ""
        }
        genesis_block['hash'] = hash_block(genesis_block)
        
        # Simpan ke file
        with open(BLOCKCHAIN_FILE, 'w') as f:
            json.dump([genesis_block], f, indent=2)
        
        return [genesis_block]
    
    try:
        with open(BLOCKCHAIN_FILE, 'r') as f:
            chain = json.load(f)
            return chain if chain else []
    except (json.JSONDecodeError, FileNotFoundError):
        # Jika file corrupt, buat ulang genesis block
        genesis_block = {
            "index": 0,
            "timestamp": time.time(),
            "transaction_type": "GENESIS",
            "transaction_data": {"message": "Genesis Block"},
            "previous_hash": "0",
            "hash": ""
        }
        genesis_block['hash'] = hash_block(genesis_block)
        
        with open(BLOCKCHAIN_FILE, 'w') as f:
            json.dump([genesis_block], f, indent=2)
        
        return [genesis_block]

def hash_block(block):
    """Membuat hash untuk sebuah blok"""
    # Membuat copy block tanpa hash untuk di-hash
    block_copy = block.copy()
    if 'hash' in block_copy:
        del block_copy['hash']
    
    block_string = json.dumps(block_copy, sort_keys=True)
    return hashlib.sha256(block_string.encode()).hexdigest()

def add_block(transaction_type, transaction_data):
    """Menambahkan blok baru ke blockchain"""
    try:
        # Load blockchain current
        chain = load_blockchain()
        
        # Membuat blok baru
        new_block = {
            "index": len(chain),
            "timestamp": time.time(),
            "transaction_type": transaction_type,
            "transaction_data": transaction_data,
            "previous_hash": chain[-1]['hash'] if chain else "0",
            "hash": ""
        }
        
        # Membuat hash untuk blok baru
        new_block['hash'] = hash_block(new_block)
        
        # Menambahkan ke chain
        chain.append(new_block)
        
        # Menyimpan ke file dengan backup
        try:
            # Backup file lama jika ada
            if os.path.exists(BLOCKCHAIN_FILE):
                backup_file = f"{BLOCKCHAIN_FILE}.backup"
                with open(BLOCKCHAIN_FILE, 'r') as f_old:
                    old_data = f_old.read()
                with open(backup_file, 'w') as f_backup:
                    f_backup.write(old_data)
            
            # Simpan data baru
            with open(BLOCKCHAIN_FILE, 'w') as f:
                json.dump(chain, f, indent=2)
            
            # Verifikasi data tersimpan
            with open(BLOCKCHAIN_FILE, 'r') as f:
                saved_chain = json.load(f)
                
            return True
            
        except Exception as save_error:
            return False
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False

def validate_chain():
    """Memvalidasi integritas hash blockchain"""
    try:
        chain = load_blockchain()
        
        for i in range(1, len(chain)):
            current_block = chain[i]
            previous_block = chain[i-1]
            
            # Cek hash block sebelumnya
            if current_block['previous_hash'] != previous_block['hash']:
                return False, f"Hash tidak valid pada blok {i}"
            
            # Cek hash block saat ini
            expected_hash = hash_block(current_block)
            if current_block['hash'] != expected_hash:
                return False, f"Hash blok {i} tidak sesuai"
        
        return True, f"Blockchain valid dengan {len(chain)} blok"
    
    except Exception as e:
        return False, f"Error validasi: {str(e)}"

def validate_signatures():
    """Memvalidasi semua tanda tangan digital dalam blockchain"""
    try:
        from crypto_utils import verify_signature
        
        chain = load_blockchain()
        
        # Load users database
        users_file = 'users.json'
        if os.path.exists(users_file):
            with open(users_file, 'r') as f:
                users_db = json.load(f)
        else:
            return False, "Database pengguna tidak ditemukan"
        
        valid_signatures = 0
        total_signatures = 0
        
        for block in chain:
            if block['transaction_type'] == 'SIGN_PETITION':
                total_signatures += 1
                tx_data = block['transaction_data']
                
                signer_username = tx_data['signer_username']
                signature = tx_data['signature']
                petition_id = tx_data['petition_id']
                
                # Cari teks petisi
                petition_text = None
                for b in chain:
                    if (b['transaction_type'] == 'CREATE_PETITION' and 
                        b['transaction_data']['petition_id'] == petition_id):
                        petition_text = b['transaction_data']['petition_text']
                        break
                
                if petition_text and signer_username in users_db:
                    message_to_verify = petition_text + signer_username
                    public_key_str = users_db[signer_username]
                    
                    if verify_signature(message_to_verify, signature, public_key_str):
                        valid_signatures += 1
        
        if total_signatures == 0:
            return True, "Tidak ada tanda tangan untuk divalidasi"
        
        return (valid_signatures == total_signatures, 
                f"{valid_signatures}/{total_signatures} tanda tangan valid")
    
    except Exception as e:
        return False, f"Error validasi tanda tangan: {str(e)}"
