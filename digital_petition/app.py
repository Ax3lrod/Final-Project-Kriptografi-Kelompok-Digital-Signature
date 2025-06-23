# digital_petition/app.py

import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import time

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

# --------------- Helper Functions untuk Analitik ---------------
def get_petition_stats():
    """Mendapatkan statistik lengkap petisi"""
    chain = load_blockchain()
    petitions = {}
    signers_data = []
    
    # Ambil data petisi
    for block in chain:
        if block['transaction_type'] == 'CREATE_PETITION':
            petition_id = block['transaction_data']['petition_id']
            petitions[petition_id] = {
                'text': block['transaction_data']['petition_text'],
                'creator': block['transaction_data'].get('creator', 'N/A'),
                'created_at': block['timestamp'],
                'signers': 0,
                'signatures': []
            }
    
    # Hitung penandatangan
    for block in chain:
        if block['transaction_type'] == 'SIGN_PETITION':
            petition_id = block['transaction_data'].get('petition_id')
            if petition_id in petitions:
                petitions[petition_id]['signers'] += 1
                petitions[petition_id]['signatures'].append({
                    'signer': block['transaction_data']['signer_username'],
                    'timestamp': block['timestamp']
                })
                signers_data.append({
                    'petition_id': petition_id,
                    'signer': block['transaction_data']['signer_username'],
                    'timestamp': block['timestamp'],
                    'date': datetime.fromtimestamp(block['timestamp']).date()
                })
    
    return petitions, signers_data

def search_petitions(query):
    """Mencari petisi berdasarkan ID atau teks"""
    chain = load_blockchain()
    results = []
    
    for block in chain:
        if block['transaction_type'] == 'CREATE_PETITION':
            petition_id = block['transaction_data']['petition_id']
            petition_text = block['transaction_data']['petition_text']
            
            if (query.lower() in petition_id.lower() or 
                query.lower() in petition_text.lower()):
                results.append({
                    'id': petition_id,
                    'text': petition_text,
                    'creator': block['transaction_data'].get('creator', 'N/A'),
                    'timestamp': block['timestamp']
                })
    
    return results

def get_user_activity(username):
    """Mendapatkan aktivitas user (petisi yang dibuat dan ditandatangani)"""
    chain = load_blockchain()
    created_petitions = []
    signed_petitions = []
    
    for block in chain:
        if block['transaction_type'] == 'CREATE_PETITION':
            if block['transaction_data'].get('creator') == username:
                created_petitions.append({
                    'id': block['transaction_data']['petition_id'],
                    'text': block['transaction_data']['petition_text'],
                    'timestamp': block['timestamp']
                })
        
        elif block['transaction_type'] == 'SIGN_PETITION':
            if block['transaction_data'].get('signer_username') == username:
                signed_petitions.append({
                    'petition_id': block['transaction_data']['petition_id'],
                    'timestamp': block['timestamp']
                })
    
    return created_petitions, signed_petitions

# --------------- UI Streamlit ---------------
st.set_page_config(page_title="Petisi Digital", layout="wide")
st.title("Petisi Digital dengan Tanda Tangan Terverifikasi")

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
                 # Username belum ada → buat akun baru dengan pasangan key baru
                    st.info(f"Username '{username_input}' belum terdaftar. Membuat akun baru...", icon="✨")
                    private_key, public_key = generate_keys_in_memory()
                    users_db[username_input] = public_key.export_key().decode()
                    save_users_db(users_db)
                else:
                    # Username sudah ada → ambil public key dari database
                    public_key_pem = users_db[username_input]
                    public_key = public_key_pem.encode()

                    # Buat private key baru hanya untuk sesi ini (⚠ tidak cocok untuk verifikasi signature lama)
                    private_key, _ = generate_keys_in_memory()
                
                st.session_state.username = username_input
                st.session_state.private_key = private_key
                st.session_state.public_key = public_key
                st.success(f"Login berhasil sebagai {username_input}!", icon="🎉")
                st.rerun()
    st.stop()

# --- Navigasi Sidebar Setelah Login ---
st.sidebar.success(f"👤 Login sebagai **{st.session_state.username}**")
st.sidebar.header("Menu Navigasi")

# Check redirect SEBELUM radio button
if st.session_state.get('redirect_to_petition', False):
    st.session_state['redirect_to_petition'] = False
    menu = "Lihat & Tandatangani Petisi"
    
    # Tetap tampilkan sidebar untuk navigasi
    st.sidebar.info("📍 Menampilkan hasil pencarian", icon="🔍")
    st.sidebar.radio(
        "Navigasi:",
        (
            "Lihat & Tandatangani Petisi",
            "🔍 Pencarian Petisi", 
            "Buat Petisi Baru",
            "📊 Statistik Petisi",
            "👤 Profil Saya",
            "Lihat Blockchain",
            "Validasi Chain"
        ),
        index=0,  # Auto-select current page
        disabled=False,
        key="sidebar_after_redirect"
    )
else:
    menu = st.sidebar.radio(
        "Pilih Halaman:",
        (
            "Lihat & Tandatangani Petisi",
            "🔍 Pencarian Petisi",
            "Buat Petisi Baru",
            "📊 Statistik Petisi",
            "👤 Profil Saya",
            "Lihat Blockchain",
            "Validasi Chain"
        ),
        captions=[
            "Lihat daftar petisi yang ada.",
            "Cari petisi berdasarkan ID atau teks.",
            "Mulai petisi Anda sendiri.",
            "Visualisasi data penandatangan.",
            "Aktivitas petisi Anda.",
            "Inspeksi data mentah blockchain.",
            "Periksa integritas data."
        ]
    )

if st.sidebar.button("Logout", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- Konten Halaman ---
if menu == "🔍 Pencarian Petisi":
    st.subheader("🔍 Pencarian Petisi")
    
    with st.container(border=True):
        search_query = st.text_input(
            "Masukkan kata kunci pencarian:",
            placeholder="Cari berdasarkan ID petisi atau teks petisi...",
            help="Pencarian akan mencari di ID petisi dan isi teks petisi"
        )
        
        if search_query:
            results = search_petitions(search_query)
            
            if not results:
                st.info(f"Tidak ditemukan petisi yang cocok dengan '{search_query}'", icon="🔍")
            else:
                st.success(f"Ditemukan {len(results)} petisi yang cocok:", icon="✅")
                
                for result in results:
                    with st.expander(f"📋 [{result['id']}] {result['text'][:50]}..."):
                        st.markdown(f"**ID Petisi:** `{result['id']}`")
                        st.markdown(f"**Dibuat oleh:** {result['creator']}")
                        st.markdown(f"**Tanggal:** {datetime.fromtimestamp(result['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                        st.markdown("**Teks Lengkap:**")
                        st.text(result['text'])
                        
                        if st.button(f"Lihat Detail & Tandatangani", key=f"view_{result['id']}"):
                            # Set session state untuk redirect
                            st.session_state['selected_petition_from_search'] = result['id']
                            st.session_state['redirect_to_petition'] = True
                            st.session_state['came_from_search'] = True
                            st.rerun()

elif menu == "Lihat & Tandatangani Petisi":
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
    
    # Check if petition selected from search
    selected_from_search = st.session_state.get('selected_petition_from_search')
    just_signed_petition = st.session_state.get('just_signed_petition')
    
    if selected_from_search and selected_from_search in petition_titles.values():
        default_index = list(petition_titles.values()).index(selected_from_search)
        st.session_state.pop('selected_petition_from_search', None)
        st.session_state['maintain_petition_selection'] = selected_from_search
        
        st.info(f"📍 Menampilkan petisi hasil pencarian: **{selected_from_search}**", icon="🔍")
    elif just_signed_petition and just_signed_petition in petition_titles.values():
        default_index = list(petition_titles.values()).index(just_signed_petition)
        st.session_state.pop('just_signed_petition', None)
        st.success(f"✅ Tanda tangan berhasil ditambahkan untuk petisi: **{just_signed_petition}**", icon="🎉")
    elif st.session_state.get('maintain_petition_selection') and st.session_state.get('maintain_petition_selection') in petition_titles.values():
        default_index = list(petition_titles.values()).index(st.session_state['maintain_petition_selection'])
    else:
        default_index = 0
    
    title_selected = st.selectbox("Pilih Petisi untuk Dilihat Detailnya", list(petition_titles.keys()), index=default_index)
    
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

        with st.expander("Lihat Teks Lengkap Petisi", expanded=True):
            st.text(petition_text)
        
        st.markdown("---")
        
        # Reload data untuk yang terbaru
        chain = load_blockchain()
        users_db = load_users_db()
        
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
                    if public_key_str:
                        message_to_verify = petition_text + signer_username
                        is_valid = verify_signature(message_to_verify, signature, public_key_str)
                        status_icon = "✅ Valid" if is_valid else "❌ Tidak Valid"
                    else:
                        status_icon = "❌ Public Key Tidak Ditemukan"
                    
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
            
            # Button key yang stabil, tidak berubah setiap render
            if 'button_click_count' not in st.session_state:
                st.session_state.button_click_count = 0
            
            button_key = f"sign_{petition_id}_{current_user}"
            
            if st.button(f"Tandatangani Petisi Ini Sekarang!", type="primary", use_container_width=True, key=button_key):
                private_key = st.session_state.private_key
                message_to_sign = petition_text + current_user
                signature = sign_data(message_to_sign, private_key)

                block_data = {
                    "signer_username": current_user,
                    "petition_id": petition_id,
                    "signature": signature
                }

                with st.spinner("Menambahkan tanda tangan Anda ke blockchain..."):
                    success = add_block("SIGN_PETITION", block_data)
                
                if success:
                    st.session_state['just_signed_petition'] = petition_id
                    st.session_state['maintain_petition_selection'] = petition_id
                    
                    st.success("Petisi berhasil ditandatangani! Halaman akan dimuat ulang.", icon="🎉")
                    st.balloons()
                    
                    time.sleep(2)  # Berikan waktu lebih untuk melihat pesan
                    st.rerun()
                else:
                    st.error("Gagal menambahkan tanda tangan ke blockchain.")

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

elif menu == "👤 Profil Saya":
    st.subheader(f"👤 Profil: {st.session_state.username}")
    
    created_petitions, signed_petitions = get_user_activity(st.session_state.username)
    
    # Statistik ringkas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Petisi yang Dibuat", len(created_petitions))
    with col2:
        st.metric("Petisi yang Ditandatangani", len(signed_petitions))
    with col3:
        st.metric("Total Aktivitas", len(created_petitions) + len(signed_petitions))
    
    st.markdown("---")
    
    # Tab untuk memisahkan petisi yang dibuat dan ditandatangani
    tab1, tab2 = st.tabs(["📝 Petisi yang Saya Buat", "✍️ Petisi yang Saya Tandatangani"])
    
    with tab1:
        if not created_petitions:
            st.info("Anda belum membuat petisi apapun.", icon="📝")
        else:
            st.write(f"Anda telah membuat **{len(created_petitions)}** petisi:")
            for petition in created_petitions:
                with st.expander(f"📋 [{petition['id']}] {petition['text'][:50]}..."):
                    st.markdown(f"**ID:** `{petition['id']}`")
                    st.markdown(f"**Dibuat pada:** {datetime.fromtimestamp(petition['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                    st.markdown("**Teks Lengkap:**")
                    st.text(petition['text'])
    
    with tab2:
        if not signed_petitions:
            st.info("Anda belum menandatangani petisi apapun.", icon="✍️")
        else:
            st.write(f"Anda telah menandatangani **{len(signed_petitions)}** petisi:")
            
            # Ambil detail petisi yang ditandatangani
            chain = load_blockchain()
            petition_details = {}
            for block in chain:
                if block['transaction_type'] == 'CREATE_PETITION':
                    petition_details[block['transaction_data']['petition_id']] = block['transaction_data']['petition_text']
            
            for signed in signed_petitions:
                petition_text = petition_details.get(signed['petition_id'], 'Teks tidak ditemukan')
                with st.expander(f"✍️ [{signed['petition_id']}] {petition_text[:50]}..."):
                    st.markdown(f"**ID Petisi:** `{signed['petition_id']}`")
                    st.markdown(f"**Ditandatangani pada:** {datetime.fromtimestamp(signed['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                    st.markdown("**Teks Petisi:**")
                    st.text(petition_text)

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
    st.subheader("Statistik dan Analitik Petisi")
    
    petitions, signers_data = get_petition_stats()
    
    if not petitions:
        st.info("Belum ada petisi untuk ditampilkan statistiknya.", icon="📊")
    else:
        # Statistik Overview
        total_petitions = len(petitions)
        total_signatures = sum(p['signers'] for p in petitions.values())
        most_popular = max(petitions.items(), key=lambda x: x[1]['signers']) if petitions else None
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Petisi", total_petitions)
        with col2:
            st.metric("Total Tanda Tangan", total_signatures)
        with col3:
            if most_popular:
                st.metric("Petisi Terpopuler", f"{most_popular[0]} ({most_popular[1]['signers']} ttd)")
        
        st.markdown("---")
        
        # Tab untuk berbagai visualisasi
        tab1, tab2, tab3 = st.tabs(["Distribusi Penandatangani", "Pie Chart", "Tren Waktu"])
        
        with tab1:
            st.markdown("#### Jumlah Penandatangani per Petisi")
            if any(p['signers'] for p in petitions.values()):
                df_data = []
                for pid, data in petitions.items():
                    short_title = data['text'][:30] + '...' if len(data['text']) > 30 else data['text']
                    df_data.append({
                        "Petisi": f"[{pid}] {short_title}", 
                        "Jumlah Penandatangani": data['signers']
                    })
                
                df = pd.DataFrame(df_data)
                st.bar_chart(df.set_index("Petisi"))
                
                # Tabel detail
                st.markdown("#### Detail Statistik")
                detail_data = []
                for pid, data in petitions.items():
                    detail_data.append({
                        "ID Petisi": pid,
                        "Judul": data['text'][:50] + '...' if len(data['text']) > 50 else data['text'],
                        "Dibuat oleh": data['creator'],
                        "Tanggal Dibuat": datetime.fromtimestamp(data['created_at']).strftime('%Y-%m-%d'),
                        "Jumlah Penandatangani": data['signers']
                    })
                
                st.dataframe(pd.DataFrame(detail_data), use_container_width=True)
            else:
                st.info("Belum ada penandatangan pada petisi manapun.", icon="🚶‍♀️")
        
        with tab2:
            st.markdown("#### Distribusi Penandatangani (Pie Chart)")
            if any(p['signers'] for p in petitions.values()):
                pie_data = []
                for pid, data in petitions.items():
                    if data['signers'] > 0:  # Hanya tampilkan yang memiliki penandatangan
                        pie_data.append({
                            "Petisi": pid,
                            "Label": pid,  # Hanya ID petisi tanpa deskripsi
                            "Penandatangani": data['signers']
                        })
                
                if pie_data:
                    fig = px.pie(
                        pie_data, 
                        values='Penandatangani', 
                        names='Label',
                        title="Distribusi Penandatangani per Petisi"
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Tidak ada data untuk pie chart karena belum ada penandatangan.", icon="🥧")
            else:
                st.info("Belum ada penandatangan untuk ditampilkan dalam pie chart.", icon="🥧")
        
        with tab3:
            st.markdown("#### 📈 Tren Penandatangganan dari Waktu ke Waktu")
            if signers_data:
                # Konversi ke DataFrame untuk analisis time series
                df_time = pd.DataFrame(signers_data)
                df_time['datetime'] = pd.to_datetime(df_time['timestamp'], unit='s')
                df_time['date'] = df_time['datetime'].dt.date
                df_time['time'] = df_time['datetime'].dt.strftime('%H:%M:%S')
                
                # Pilihan agregasi
                aggregation_option = st.radio(
                    "Pilih tingkat detail:",
                    ["Per Jam", "Per Hari", "Detail per Tanda Tangan"],
                    horizontal=True
                )
                
                if aggregation_option == "Detail per Tanda Tangan":
                    # Tampilkan setiap tanda tangan individual
                    df_time_sorted = df_time.sort_values('datetime')
                    df_time_sorted['cumulative'] = range(1, len(df_time_sorted) + 1)
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=df_time_sorted['datetime'],
                        y=df_time_sorted['cumulative'],
                        mode='lines+markers',
                        name='Total Tanda Tangan',
                        line=dict(color='blue'),
                        hovertemplate='<b>%{x}</b><br>Total: %{y}<br>Petisi: %{customdata}<extra></extra>',
                        customdata=df_time_sorted['petition_id']
                    ))
                    
                    fig.update_layout(
                        title="Tren Kumulatif Penandatanganan (Detail)",
                        xaxis_title="Waktu",
                        yaxis_title="Total Kumulatif Tanda Tangan",
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Tabel detail
                    st.markdown("#### 📋 Detail Setiap Tanda Tangan")
                    detail_table = df_time_sorted[['datetime', 'signer', 'petition_id']].copy()
                    detail_table['datetime'] = detail_table['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    detail_table.columns = ['Waktu', 'Penandatanggan', 'ID Petisi']
                    st.dataframe(detail_table.sort_values('Waktu', ascending=False), use_container_width=True)
                
                elif aggregation_option == "Per Jam":
                    # Aggregate by hour
                    df_time['hour'] = df_time['datetime'].dt.floor('H')
                    hourly_signatures = df_time.groupby('hour').size().reset_index(name='signatures')
                    hourly_signatures['cumulative'] = hourly_signatures['signatures'].cumsum()
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=hourly_signatures['hour'],
                        y=hourly_signatures['signatures'],
                        mode='lines+markers',
                        name='Tanda Tangan per Jam',
                        line=dict(color='blue')
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=hourly_signatures['hour'],
                        y=hourly_signatures['cumulative'],
                        mode='lines+markers',
                        name='Kumulatif Tanda Tangan',
                        line=dict(color='red'),
                        yaxis='y2'
                    ))
                    
                    fig.update_layout(
                        title="Tren Penandatangani per Jam",
                        xaxis_title="Waktu (Per Jam)",
                        yaxis_title="Tanda Tangan per Jam",
                        yaxis2=dict(
                            title="Kumulatif Tanda Tangan",
                            overlaying='y',
                            side='right'
                        ),
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Tabel aktivitas per jam
                    st.markdown("#### ⏰ Aktivitas per Jam")
                    hourly_signatures['hour'] = hourly_signatures['hour'].dt.strftime('%Y-%m-%d %H:%M')
                    hourly_signatures.columns = ['Jam', 'Tanda Tangan Baru', 'Total Kumulatif']
                    st.dataframe(hourly_signatures.sort_values('Jam', ascending=False), use_container_width=True)
                
                else:  # Per Hari
                    # Aggregate by date (existing code)
                    daily_signatures = df_time.groupby('date').size().reset_index(name='signatures')
                    daily_signatures['cumulative'] = daily_signatures['signatures'].cumsum()
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=daily_signatures['date'],
                        y=daily_signatures['signatures'],
                        mode='lines+markers',
                        name='Tanda Tangan Harian',
                        line=dict(color='blue')
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=daily_signatures['date'],
                        y=daily_signatures['cumulative'],
                        mode='lines+markers',
                        name='Kumulatif Tanda Tangan',
                        line=dict(color='red'),
                        yaxis='y2'
                    ))
                    
                    fig.update_layout(
                        title="Tren Penandatanganan per Hari",
                        xaxis_title="Tanggal",
                        yaxis_title="Tanda Tangan Harian",
                        yaxis2=dict(
                            title="Kumulatif Tanda Tangan",
                            overlaying='y',
                            side='right'
                        ),
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Tabel aktivitas harian
                    st.markdown("#### 📅 Aktivitas Harian")
                    daily_signatures_display = daily_signatures.copy()
                    daily_signatures_display['date'] = daily_signatures_display['date'].astype(str)
                    daily_signatures_display.columns = ['Tanggal', 'Tanda Tangan Baru', 'Total Kumulatif']
                    st.dataframe(daily_signatures_display.sort_values('Tanggal', ascending=False), use_container_width=True)
            else:
                st.info("Belum ada data tanda tangan untuk analisis tren waktu.", icon="📈")