# digital_petition/app.py

import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime

# Mengimpor fungsi yang diperlukan, termasuk perbaikan bug 'verify_signature' not defined
from crypto_utils import generate_keys_in_memory, sign_data, verify_signature
from blockchain_utils import (
    load_blockchain,
    add_block,
    validate_chain,
    validate_signatures
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
st.set_page_config(page_title="Petisi Digital", layout="wide")
st.title("🖋️ Petisi Digital dengan Tanda Tangan Terverifikasi")

# --- Bagian Login ---
if 'username' not in st.session_state:
    st.sidebar.warning("⚠️ Silakan login untuk melanjutkan.")
    
    with st.container(border=True):
        st.subheader("🔐 Login / Pendaftaran Akun")
        username_input = st.text_input("Masukkan Username Anda", help="Jika username belum ada, akun baru akan dibuat secara otomatis.")

        if st.button("Login / Daftar", type="primary", use_container_width=True):
            if not username_input.strip():
                st.warning("Username tidak boleh kosong.", icon="❗")
            else:
                users_db = load_users_db()
                if username_input not in users_db:
                    st.info(f"Username '{username_input}' belum terdaftar. Membuat akun baru...", icon="✨")
                    private_key, public_key = generate_keys_in_memory()
                    users_db[username_input] = public_key.export_key().decode()
                    save_users_db(users_db)
                    st.success(f"Akun baru untuk '{username_input}' berhasil dibuat!")
                else:
                    private_key, public_key = generate_keys_in_memory()
                    # FIX: Update public key di DB agar cocok dengan private key sesi ini
                    users_db[username_input] = public_key.export_key().decode()
                    save_users_db(users_db)
                
                st.session_state.username = username_input
                st.session_state.private_key = private_key
                st.session_state.public_key = public_key
                st.success(f"Login berhasil sebagai {username_input}!", icon="🎉")
                st.rerun()
    st.stop()


# --- Navigasi Sidebar Setelah Login ---
st.sidebar.success(f"👤 Login sebagai **{st.session_state.username}**")
st.sidebar.header("Menu Navigasi")
menu = st.sidebar.radio(
    "Pilih Halaman:",
    (
        "Lihat & Tandatangani Petisi",
        "Buat Petisi Baru",
        "📊 Statistik Petisi",
        "Lihat Blockchain",
        "Validasi Chain"
    ),
    captions=[
        "Lihat daftar petisi yang ada.",
        "Mulai petisi Anda sendiri.",
        "Visualisasi data penandatangan.",
        "Inspeksi data mentah blockchain.",
        "Periksa integritas data."
    ]
)

if st.sidebar.button("Logout", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# --- Konten Halaman ---

# Perbaikan bug: Menyamakan nama menu di list dan di kondisi if
if menu == "Lihat & Tandatangani Petisi":
    st.subheader("📜 Daftar Petisi Publik")
    
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
        st.warning("Belum ada petisi yang tersedia. Silakan buat petisi baru.", icon="🕊️")
        st.stop()

    petition_titles = {
        f"[{pid}] {petitions[pid]['text'][:60]}{'...' if len(petitions[pid]['text']) > 60 else ''} (Oleh: {petitions[pid]['creator']})": pid
        for pid in petitions
    }
    
    title_selected = st.selectbox("Pilih Petisi untuk Dilihat Detailnya", list(petition_titles.keys()))
    
    if title_selected:
        petition_id = petition_titles[title_selected]
        petition_data = petitions[petition_id]
        petition_text = petition_data['text']
        
        st.markdown("---")
        
        # Menggunakan st.columns dan st.metric untuk layout yang lebih baik
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="ID Petisi", value=petition_id)
        with col2:
            st.metric(label="Dibuat oleh", value=petition_data['creator'])

        with st.expander("Lihat Teks Lengkap Petisi"):
            st.text(petition_text)
        
        st.markdown("---")
        
        # Bagian Penandatangan
        with st.container(border=True):
            st.markdown("#### ✍️ Daftar Penandatangan")
            
            signers = [b for b in chain if b['transaction_type'] == 'SIGN_PETITION' and b['transaction_data'].get('petition_id') == petition_id]

            if not signers:
                st.info("Belum ada yang menandatangani petisi ini.", icon="🚶")
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
                st.dataframe(df_signers, use_container_width=True)

        st.markdown("---")
        
        # Bagian Aksi untuk User
        current_user = st.session_state.username
        signer_usernames = [s['transaction_data']['signer_username'] for s in signers]

        if current_user in signer_usernames:
            st.success("👍 Anda sudah menandatangani petisi ini.", icon="✔️")
        else:
            st.write(f"Anda, **{current_user}**, belum menandatangani petisi ini.")
            if st.button(f"Tandatangani Petisi Ini Sekarang!", type="primary"):
                private_key = st.session_state.private_key
                message_to_sign = petition_text + current_user
                signature = sign_data(message_to_sign, private_key)

                with st.spinner("Menambahkan tanda tangan Anda ke blockchain..."):
                    add_block("SIGN_PETITION", {
                        "signer_username": current_user,
                        "petition_id": petition_id,
                        "signature": signature
                    })
                
                st.success("Petisi berhasil ditandatangani! Halaman akan dimuat ulang.", icon="🎉")
                st.balloons()
                st.rerun()

elif menu == "Buat Petisi Baru":
    st.subheader("📝 Buat Petisi Baru")
    # Menggunakan container untuk mengelompokkan form
    with st.container(border=True):
        petition_id = st.text_input("ID Petisi (unik, misal: selamatkan-badak)", help="Gunakan huruf kecil dan tanda hubung (-).")
        petition_text = st.text_area("Isi Lengkap Petisi", height=200)
        
        if st.button("Simpan dan Publikasikan Petisi", use_container_width=True, type="primary"):
            if not petition_id.strip() or not petition_text.strip():
                st.warning("ID dan isi petisi tidak boleh kosong.", icon="⚠️")
            else:
                with st.spinner("Menambahkan petisi ke blockchain..."):
                    add_block("CREATE_PETITION", {
                        "petition_id": petition_id,
                        "petition_text": petition_text,
                        "creator": st.session_state.username
                    })
                st.success(f"Petisi '{petition_id}' berhasil ditambahkan ke blockchain!", icon="✅")

elif menu == "Lihat Blockchain":
    st.subheader("⛓️ Tampilan Detail Blockchain")
    st.info("Setiap 'block' merepresentasikan sebuah transaksi yang tercatat secara permanen. Blok terbaru ditampilkan di paling atas.", icon="ℹ️")
    chain = load_blockchain()

    # Menampilkan dari blok terbaru
    for block in reversed(chain):
        creator_info = block['transaction_data'].get('creator') or block['transaction_data'].get('signer_username', 'N/A')
        expander_title = f"📦 **Block #{block['index']}** | Tipe: **{block['transaction_type']}** | Oleh: **{creator_info}**"
        
        with st.expander(expander_title):
            st.markdown(f"**Timestamp:** `{datetime.fromtimestamp(block['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}`")
            st.markdown(f"**Hash Block Ini:**")
            st.code(block['hash'], language='text')
            st.markdown(f"**Hash Block Sebelumnya:**")
            st.code(block['previous_hash'], language='text')

            st.markdown("---")
            st.markdown("**Data Transaksi:**")
            
            tx_data = block.get('transaction_data')
            if tx_data:
                display_data = tx_data.copy()
                # Memotong signature yang panjang agar tampilan lebih rapi
                if 'signature' in display_data and isinstance(display_data['signature'], str):
                    sig = display_data['signature']
                    display_data['signature'] = f"{sig[:20]}..."
                st.json(display_data)
            else:
                st.write("Tidak ada data transaksi (Genesis Block).")

elif menu == "Validasi Chain":
    st.subheader("✅ Validasi Integritas Blockchain")
    st.write("Proses ini memeriksa apakah struktur hash antar blok masih utuh dan semua tanda tangan digital valid.")
    
    if st.button("Mulai Validasi", use_container_width=True, type="primary"):
        with st.spinner("Memeriksa integritas dan validitas tanda tangan..."):
            valid_chain, msg_chain = validate_chain()
            valid_sig, msg_sig = validate_signatures()

            # Menggunakan st.columns untuk layout berdampingan
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 🔗 Validasi Struktur Chain")
                if valid_chain:
                    st.success(f"**Status:** {msg_chain}", icon="✅")
                else:
                    st.error(f"**Status:** {msg_chain}", icon="❌")

            with col2:
                st.markdown("#### ✍️ Validasi Tanda Tangan")
                if valid_sig:
                    st.success(f"**Status:** {msg_sig}", icon="✅")
                else:
                    st.error(f"**Status:** {msg_sig}", icon="❌")

elif menu == "📊 Statistik Petisi":
    st.subheader("📈 Statistik Jumlah Penandatangan per Petisi")
    chain = load_blockchain()
    petitions = {
        block['transaction_data']['petition_id']: block['transaction_data']['petition_text']
        for block in chain if block['transaction_type'] == 'CREATE_PETITION'
    }
    
    if not petitions:
        st.info("Belum ada petisi untuk ditampilkan statistiknya.", icon="📊")
    else:
        signer_counts = {pid: 0 for pid in petitions.keys()}
        for block in chain:
            if block['transaction_type'] == 'SIGN_PETITION':
                pid = block['transaction_data'].get('petition_id')
                if pid in signer_counts:
                    signer_counts[pid] += 1
        
        if not any(signer_counts.values()):
            st.info("Belum ada penandatangan pada petisi manapun.", icon="🚶‍♀️")
        else:
            df_data = []
            for pid, count in signer_counts.items():
                # Menampilkan judul petisi yang lebih pendek untuk label grafik
                short_title = petitions[pid][:30] + '...' if len(petitions[pid]) > 30 else petitions[pid]
                df_data.append({"Petisi": f"[{pid}] {short_title}", "Jumlah Penandatangan": count})

            df = pd.DataFrame(df_data)
            st.bar_chart(df.set_index("Petisi"))