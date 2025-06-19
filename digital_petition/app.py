import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime

from crypto_utils import generate_keys_in_memory, sign_data
from blockchain_utils import (
    load_blockchain,
    add_block,
    validate_chain,
    validate_signatures  # tambahkan ini
)


# --------------- Konstanta ---------------
PETITION_FILE = 'petition_data.json'
USERS_DB_FILE = 'users.json'


# --------------- Load Users ---------------
def load_users_db():
    if not os.path.exists(USERS_DB_FILE):
        with open(USERS_DB_FILE, 'w') as f:
            json.dump({}, f) # Buat file dengan objek JSON kosong
        return {}
        
    with open(USERS_DB_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {} # Jaga-jaga jika file korup
    
def save_users_db(db):
    with open(USERS_DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)

# --------------- UI Streamlit ---------------
st.set_page_config(page_title="Digital Petition", layout="centered")
st.title("🖋️ Digital Petition with Verified Signers")

if 'username' not in st.session_state:
    st.sidebar.error("⚠️ Silakan login terlebih dahulu")
    st.subheader("🔐 Login / Daftar")
    username_input = st.text_input("Masukkan Username")

    if st.button("Login / Daftar"):
        if not username_input.strip():
            st.warning("Username tidak boleh kosong.")
        else:
            # Logika untuk menyimpan kunci publik
            users_db = load_users_db()
            if username_input not in users_db:
                # Ini adalah user baru (pendaftaran)
                st.info(f"Username '{username_input}' belum terdaftar. Membuat akun baru...")
                private_key, public_key = generate_keys_in_memory()
                users_db[username_input] = public_key.export_key().decode()
                save_users_db(users_db)
                st.success(f"Akun baru untuk '{username_input}' berhasil dibuat!")
            else:
                # Ini adalah login user yang sudah ada
                private_key, public_key = generate_keys_in_memory()
                # FIX: Update public key di DB agar cocok dengan private key sesi ini
                users_db[username_input] = public_key.export_key().decode()
                save_users_db(users_db)

            st.session_state.username = username_input
            st.session_state.private_key = private_key
            st.session_state.public_key = public_key
            st.success(f"Login sebagai {username_input}")
            st.rerun()
    st.stop()

menu = st.sidebar.selectbox("Menu", [
    "Tandatangani Petisi",
    "Buat Petisi Baru",
    "Lihat Blockchain",
    "Validasi Chain",
    "📊 Statistik Petisi"
])

if 'username' in st.session_state:
    st.sidebar.markdown(f"👤 Login sebagai **{st.session_state.username}**")
    if st.sidebar.button("Logout"):
        # Hapus semua state saat logout
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

if menu == "Lihat Detail & Tanda Tangani Petisi":
    st.subheader("📜 Detail Petisi dan Penandatangan")
    
    chain = load_blockchain()
    users_db = load_users_db()
    
    petitions = {
        block['transaction_data']['petition_id']: {
            "text": block['transaction_data']['petition_text'],
            "creator": block['transaction_data'].get('creator', 'N/A')
        }
        for block in chain if block['transaction_type'] == 'CREATE_PETITION'
    }

    if not petitions:
        st.warning("Belum ada petisi yang tersedia. Silakan buat petisi baru.")
        st.stop()

    petition_titles = {
        f"[{pid}] {petitions[pid]['text'][:60]}{'...' if len(petitions[pid]['text']) > 60 else ''}": pid
        for pid in petitions
    }
    
    title_selected = st.selectbox("Pilih Petisi untuk Dilihat Detailnya", list(petition_titles.keys()))
    
    if title_selected:
        petition_id = petition_titles[title_selected]
        petition_data = petitions[petition_id]
        petition_text = petition_data['text']
        
        st.markdown("---")
        
        st.markdown(f"### Petisi: `{petition_id}`")
        st.markdown(f"**Dibuat oleh:** `{petition_data['creator']}`")
        with st.expander("Lihat Teks Lengkap Petisi"):
            st.text(petition_text)

        st.markdown("---")
        
        st.markdown("#### ✍️ Daftar Penandatangan")
        
        signers = []
        for block in chain:
            if block['transaction_type'] == 'SIGN_PETITION' and block['transaction_data'].get('petition_id') == petition_id:
                signers.append(block)

        if not signers:
            st.info("Belum ada yang menandatangani petisi ini.")
        else:
            display_data = []
            for block in signers:
                tx_data = block['transaction_data']
                signer_username = tx_data['signer_username']
                signature = tx_data['signature']
                
                public_key_str = users_db.get(signer_username)
                message_to_verify = petition_text + signer_username
                is_valid = verify_signature(message_to_verify, signature, public_key_str)
                
                status_icon = "✅ Valid" if is_valid else "❌ Tidak Valid"
                timestamp_formatted = datetime.fromtimestamp(block['timestamp']).strftime('%Y-%m-%d %H:%M:%S')

                display_data.append({
                    "Penandatangan": signer_username,
                    "Waktu Tanda Tangan": timestamp_formatted,
                    "Status Verifikasi": status_icon
                })
            
            df_signers = pd.DataFrame(display_data)
            st.table(df_signers)

        st.markdown("---")
        
        current_user = st.session_state.username
        signer_usernames = [s['transaction_data']['signer_username'] for s in signers]

        if current_user in signer_usernames:
            st.success("👍 Anda sudah menandatangani petisi ini.")
        else:
            st.write("Anda belum menandatangani petisi ini.")
            if st.button(f"Saya, {current_user}, Ingin Menandatangani Petisi Ini"):
                private_key = st.session_state.private_key
                message_to_sign = petition_text + current_user

                signature = sign_data(message_to_sign, private_key)

                new_block = add_block("SIGN_PETITION", {
                    "signer_username": current_user,
                    "petition_id": petition_id,
                    "signature": signature
                })
                
                st.success("Petisi berhasil ditandatangani! Halaman akan dimuat ulang.")
                st.json(new_block)
                st.rerun()

elif menu == "Lihat Blockchain":
    st.subheader("⛓️ Blockchain Data")
    chain = load_blockchain()

    for block in chain:
        with st.expander(f"Block {block['index']} - User: {block['transaction_data'].get('creator', 'Unknown')}"):
            st.json(block)

elif menu == "Validasi Chain":
    st.subheader("✅ Validasi Integritas Blockchain")
    with st.spinner("Memvalidasi..."):
        valid, msg = validate_chain()
        if valid:
            st.success(f"⛓️ Struktur Chain: {msg}")
        else:
            st.error(f"⛓️ Struktur Chain: {msg}")

        valid_sig, msg_sig = validate_signatures()
        if valid_sig:
            st.success(f"🔐 Signature: {msg_sig}")
        else:
            st.error(f"🔐 Signature: {msg_sig}")

elif menu == "📊 Statistik Petisi":
    st.subheader("📈 Statistik Jumlah Penandatangan per Petisi")
    #petitions = load_petitions()
    chain = load_blockchain()
    petitions = {
        block['transaction_data']['petition_id']: block['transaction_data']['petition_text']
        for block in chain if block['transaction_type'] == 'CREATE_PETITION'
    }
    signer_counts = {pid: 0 for pid in petitions.keys()}
    for block in chain:
        if block['transaction_type'] == 'SIGN_PETITION':
            pid = block['transaction_data'].get('petition_id')
            if pid in signer_counts:
                signer_counts[pid] += 1
    if not any(signer_counts.values()):
        st.info("Belum ada penandatangan.")
    else:
        import pandas as pd
        df = pd.DataFrame(list(signer_counts.items()), columns=["ID Petisi", "Jumlah Penandatangan"])
        df = df[df["Jumlah Penandatangan"] > 0]
        st.bar_chart(df.set_index("ID Petisi"))

elif menu == "Buat Petisi Baru":
    st.subheader("📝 Buat Petisi Baru")
    petition_id = st.text_input("ID Petisi (unik, misal: petisi1)")
    petition_text = st.text_area("Isi Lengkap Petisi")
    if st.button("Simpan Petisi"):
        if petition_id.strip() == "" or petition_text.strip() == "":
            st.warning("ID dan isi petisi tidak boleh kosong.")
        else:
            # Create a new block for the petition
            new_block = add_block("CREATE_PETITION", {
                "petition_id": petition_id,
                "petition_text": petition_text,
                "creator": st.session_state.username
            })
            st.success(f"Petisi '{petition_id}' berhasil ditambahkan.")
