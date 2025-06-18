import streamlit as st
import json
import os

from crypto_utils import generate_keys, load_keys, sign_data, verify_signature
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

menu = st.sidebar.selectbox("Menu", [
    "Tandatangani Petisi",
    "Buat Petisi Baru",
    "Lihat Blockchain",
    "Validasi Chain",
    "📊 Statistik Petisi"
])


if menu == "Tandatangani Petisi":
    petitions = load_petitions()

    if not petitions:
        st.warning("Belum ada petisi yang tersedia.")
    else:
        username = st.text_input("Nama Anda", key="name_input")
        # Buat mapping: "Judul Petisi" -> ID
        petition_titles = {
            f"[{pid}] {petitions[pid][:60]}{'...' if len(petitions[pid]) > 60 else ''}": pid
            for pid in petitions
        }
        title_selected = st.selectbox("Pilih Petisi", list(petition_titles.keys()))
        petition_id = petition_titles[title_selected]


        if st.button("Tandatangani"):
            if username.strip() == "":
                st.error("Nama tidak boleh kosong.")
            else:
                # Generate key jika belum ada
                priv_path = f'keys/{username}_private.pem'
                if not os.path.exists(priv_path):
                    generate_keys(username)
                    st.success("RSA key baru dibuat.")

                private_key, public_key = load_keys(username)

                # Ambil teks petisi
                petition_text = petitions[petition_id]

                # Hash isi petisi + nama
                message = petition_text + username
                signature = sign_data(message, private_key)

                # Cegah user menandatangani petisi sama lebih dari sekali
                chain = load_blockchain()
                for block in chain:
                    if block['username'] == username and block['petition_id'] == petition_id:
                        st.warning("Anda sudah menandatangani petisi ini sebelumnya.")
                        st.stop()


                # Tambahkan ke blockchain
                new_block = add_block(username, petition_id, signature, public_key.export_key().decode())

                st.success("Petisi berhasil ditandatangani!")
                st.json(new_block)

elif menu == "Lihat Blockchain":
    st.subheader("⛓️ Blockchain Data")
    chain = load_blockchain()
    for block in chain:
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

