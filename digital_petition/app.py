import streamlit as st
import json
import os

from crypto_utils import generate_keys_in_memory, load_keys, sign_data, verify_signature
from blockchain_utils import (
    load_blockchain,
    add_block,
    validate_chain,
    validate_signatures  # tambahkan ini
)


# --------------- Konstanta ---------------
PETITION_FILE = 'petition_data.json'

# --------------- Load Petisi ---------------
def load_petitions():
    if not os.path.exists(PETITION_FILE):
        return {}
    with open(PETITION_FILE, 'r') as f:
        return json.load(f)

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
            from crypto_utils import generate_keys_in_memory
            private_key, public_key = generate_keys_in_memory()
            st.session_state.username = username_input
            st.session_state.private_key = private_key
            st.session_state.public_key = public_key
            st.success(f"Login sebagai {username_input}")
            st.rerun()
    st.stop()  # hentikan semua eksekusi kecuali login

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
        st.session_state.clear()
        st.rerun()

if menu == "Tandatangani Petisi":
    petitions = load_petitions()

    if not petitions:
        st.warning("Belum ada petisi yang tersedia.")
    else:
        username = st.session_state.username
        private_key = st.session_state.private_key
        public_key = st.session_state.public_key

        chain = load_blockchain()
        signed_petitions = {
            block['petition_id'] for block in chain if block['username'] == username
        }

        hide_signed = st.checkbox("Sembunyikan petisi yang sudah saya tandatangani.", value=True)

        filtered_petitions = {
            pid: text for pid, text in petitions.items()
            if not (hide_signed and pid in signed_petitions)
        }

        if not filtered_petitions:
            st.info("Tidak ada petisi yang tersedia untuk ditandatangani.")
            st.stop()

        petition_titles = {
            f"[{pid}] {filtered_petitions[pid][:60]}{'...' if len(filtered_petitions[pid]) > 60 else ''}": pid
            for pid in filtered_petitions
        }
        title_selected = st.selectbox("Pilih Petisi", list(petition_titles.keys()))
        petition_id = petition_titles[title_selected]


        if st.button("Tandatangani"):
                # Ambil teks petisi
                petition_text = petitions[petition_id]

                # Hash isi petisi + nama
                message = petition_text + username
                signature = sign_data(message, private_key)

                # Cegah user menandatangani petisi sama lebih dari sekali
                if petition_id in signed_petitions:
                    st.warning("Anda sudah menandatangani petisi ini.")
                    st.stop()
                    
                # Tambahkan ke blockchain
                new_block = add_block(username, petition_id, signature, public_key.export_key().decode())

                st.success("Petisi berhasil ditandatangani!")
                st.json(new_block)

elif menu == "Lihat Blockchain":
    st.subheader("⛓️ Blockchain Data")
    username = st.session_state.username
    chain = load_blockchain()

    # Tambahkan toggle pilihan filter
    filter_mode = st.radio("Tampilkan blok:", ["Semua", "Hanya Saya"], horizontal=True)

    if filter_mode == "Hanya Saya":
        filtered_chain = [block for block in chain if block['username'] == username]
    else:
        filtered_chain = chain

    if not filtered_chain:
        st.info("Tidak ada data blockchain yang tersedia.")
    else:
        for block in filtered_chain:
            with st.expander(f"Block {block['index']}"):
                st.json(block)

elif menu == "Validasi Chain":
    st.subheader("✅ Validasi Integritas Blockchain")
    valid, msg = validate_chain()
    st.write("⛓️ Struktur Chain:", msg)

    valid_sig, msg_sig = validate_signatures()
    if valid_sig:
        st.success(f"🔐 Signature: {msg_sig}")
    else:
        st.error(f"🔐 Signature: {msg_sig}")

    if valid:
        st.success(msg)
    else:
        st.error(msg)

elif menu == "📊 Statistik Petisi":
    st.subheader("📈 Statistik Jumlah Penandatangan per Petisi")

    petitions = load_petitions()
    chain = load_blockchain()

    # Hitung signer per petition_id
    signer_counts = {}
    for pid in petitions.keys():
        signer_counts[pid] = 0

    for block in chain[1:]:  # skip genesis
        pid = block['petition_id']
        if pid in signer_counts:
            signer_counts[pid] += 1

    if not any(signer_counts.values()):
        st.info("Belum ada penandatangan.")
    else:
        import pandas as pd
        df = pd.DataFrame(list(signer_counts.items()), columns=["Petisi", "Jumlah Penandatangan"])
        st.bar_chart(df.set_index("Petisi"))
elif menu == "Buat Petisi Baru":
    st.subheader("📝 Buat Petisi Baru")

    petition_id = st.text_input("ID Petisi (unik, misal: petisi1)")
    petition_text = st.text_area("Isi Lengkap Petisi")

    if st.button("Simpan Petisi"):
        if petition_id.strip() == "" or petition_text.strip() == "":
            st.warning("ID dan isi petisi tidak boleh kosong.")
        else:
            # Cek apakah file petisi sudah ada
            if os.path.exists(PETITION_FILE):
                with open(PETITION_FILE, "r") as f:
                    data = json.load(f)
            else:
                data = {}

            if petition_id in data:
                st.error("ID petisi sudah digunakan. Coba ID lain.")
            else:
                data[petition_id] = petition_text
                with open(PETITION_FILE, "w") as f:
                    json.dump(data, f, indent=4)
                st.success(f"Petisi '{petition_id}' berhasil ditambahkan.")

