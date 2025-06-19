# Final Project Kriptografi - Digital Signature

## Anggota Kelompok 2

| No | Nama Anggota                 | NRP        | Job Description                              |
|----|------------------------------|------------|----------------------------------------------|
| 1. | Karissa Maheswari Sasikirana | 5048221013 | Penulisan Dokumentasi dan Laporan Akhir      |
| 2. | Achmad Rayhan Purnomo        | 5048221018 | Integrator UI-to-Blockchain                  |
| 3. | Aryasatya Alaauddin          | 5027231082 | Manajer Identitas dan Kunci Publik           |
| 4. | Fiorenza Adelia Nalle        | 5027231053 | Arsitek Sesi dan Kunci Privat                |
| 5. | Harwinda                     | 5027231079 | Designer Tampilan Visual dan Verifikasi      |
| 6. | Kevin Anugerah Faza          | 5027231027 | Designer Struktur Transaksi Blockchain       |
| 7. | Muhammad Faqih Husain        | 5027231023 | Arsitektur Awal Proyek dan Membangun Fondasi |
| 8. | Adlya Isriena Aftarisya      | 5027231066 | Pengembangan Fitur Analitik dan Profil       |
| 9. | Falisha Tazkia               | 5027231076 | Pengembangan Halaman dan Detail Verifikasi   |

# Digital Petition: Sistem Tanda Tangan Petisi Digital
Digital Petition merupakan aplikasi web yang menyediakan alur kerja menyeluruh untuk membuat, menandatangani dan memverifikasi tanda tangan petisi secara digital. Pengguna dapat membuat akun dan menghasilkan pasangan kunci RSA, membuat petisi, serta memberikan dukungan dengan menandatangani petisi secara digital. Setiap transaksi yang dilakukan akan dicatat ke dalam blockchain lokal yang aman, sehingga menjamin integritas dan transparansi data secara menyeluruh.

**Fitur verifikasi memungkinkan siapapun untuk memeriksa:**
- Keaslian tanda tangan digital
- Validasi struktur blockchain
- Riwayat dukungan petisi secara publik (transparan)

## Deskripsi Proyek
Di era modern ini, hampir semua aktivitas dilakukan secara digital, kebutuhan akan sistem yang aman, transparan, dan terpercaya menjadi sangat krusial karena dibutuhkan untuk membangun kepercayaan dalam proses pengumpulan dukungan publik. Dimana tantangannya adalah memastikan bahwa setiap tanda tangan berasal dari orang yang sah dan petisi tersebut tidak dimanipulasi. Proyek Digital Petition ini menjadi jawaban untuk tantangan tersebut dengan menghadirkan platform yang memungkinkan pengguna untuk:
- **Membuat Identitas Digital**: Pengguna otomatis menghasilkan pasangan kunci RSA (Public & Private) yang unik sebagai identitas mereka, yang digunakan untuk proses penandatangan secara aman dan terenkripsi.
- **Menandatangani Petisi**: Menandatangani petisi secara digital dengan menggunakan kunci privat, sehingga menghasilkan tanda tangan digital yang tidak dapat dimanipulasi.
- **Mencatat Transaksi di Blcokchain**: setiap aksi yang dilakukan, baik itu membuat petisi atau menandatangani petisi, akan dicatat dalam sebuah blockchain lokal.
- **Memverifikasi Keaslian Tanda Tangan**: Memverifikasi keaslian tanda tangan digital pengguna dengan menggunakan kunci publik yang terdaftar.

## Arsitektur Aplikasi
- `Streamlit UI`: Interface pengguna untuk login, membuat dan menandatangani petisi, serta melihat blockchain aplikasi.
- `Pycryptodome`: Library kriptografi yang digunakan untuk implementasi RSA dan SHA-256.
- `Blockchain.json`: Menyimpan data blockchain secara lokal dalam format JSON.
- `users.json`: Menyimpan data-data dan kunci publik dari semua pengguna.

## Algoritma RSA dan SHA-256
Aplikasi ini menggunakan sistem keamanan yang berupa kombinasi dari fungsi hash **SHA-256** dan algoritma kriptografi asimetris **RSA (Rivest-Shamir-Adleman)**, yang dimana:

- **RSA (Rivest-SHamir-Adleman)**
>- **Kunci Publik RSA**: Digunakan untuk memverifikasi tanda tangan digital.
>- **Kunci Private RSA**: Digunakan untuk membuat tanda tangan digital.

- **(Secure Hash Algorithm) SHA-256**: Mengubah data berukuran berapapun menjadi hash sepanjang 256-bit (64 karakter hex), dimana sangat sensitif terhadap perubahan data sekecil apapun.

## Proses Penandatanganan (Signing Process)
Ketika seseorang menandatangani suatu petisi pada aplikasi, maka proses berikut akan terjadi:
**1. Membetuk Pesan**
>Sistem akan membentuk pesan unik yang terdiri dari gabungan teks lengkap petisi dan username penandatangan.
**2. Hasing**
>Pesan akan di-hash dengan menggunakan algoritma SHA-256 untuk menghasilkan message digest.
**3. Eknripsi Hash**
>Hash akan dienkripsi dengan menggunakan **kunci privat** pengguna dengan algoritma RSA, yang dimana hasil enkripsi ini adalah *Digital Signature*.
**4. Pencatatan Transaksi**
> Tanda tangan ini, bersama dengan username dan petition ID akan dicatat sebagai blok transaksi dalam blockchain.

## Proses Verifikasi (Verification Process)
**1. Pengambilan Data**
> Mengambil data tanda tangan, username, dan petition ID dari blok transaksi dalam blockchain.
**2. Pengambilan Kunci Publik**
> Kunci publik penandatangan diambil dari `users.json` berdasarkan username penandatangan.
**3. Pembentukan Ulang Pesan**
> Sistem akan membentuk ulang pesan yang sama persis dengan penandatangan.
**4. Verifikasi Tanda Tangan**
> Menghitung hash dari pesan yang dibentuk ulang, menggunakan kunci publik untuk mendekripsi tanda tangan digital dan mendapatkan hash asli, lalu membandingkan kedua has, jika identik maka dinyatakan *valid*, jika tidak maka *tidak valid*.

## Integritas Blockchain
Blockchain dapat menjamin integritas data dengan melalui mekanisme **chained-hashing**, yang dimana:
- Setiap blok dalam blockchain berisi hash dari blok sebelumnya
- Hash setiap blok dihitung berdasarkan seluruh konten blok tersebut, temasuk hash sebelumnya.
- Terdapat fungsi `validate_chain` yang dapat mengintegrasi seluruh rantai dan memeriksa apakah hash sebelumnya di setiap blok benar-benar cocok dengan hash dari blok sebelumnya. Jika ada satu data saja yang berubah maka rantai hash akan "putus", sehingga terdeteksi sebagai tidak valid.

# Cara Menjalankan Aplikasi
**Prasyarat:**
- Pandas
- Streamlit
- Pycryptodome
- Plotly

## 1. Jalankan Backend
```bash
cd digital_petition
pip install -r requirements.txt
```
> Download `requirements.txt`

## 2. Jalankan Frontend
```bash
streamlit run app.py
```
Frontend akan berjalan di: **http://localhost:8501/**

# Cara Menggunakan Aplikasi
## 1. Halaman utama user login
User disambut di halaman login, untuk login dapat memasukan username. Jika belum memiliki akun, akan dibuat secara otomatis oleh sistem.
![image](https://github.com/user-attachments/assets/563c9e20-b2fd-4d77-a31b-36fb8ddb8f53)

## 2. Halaman Daftar Petisi
Setelah user login, akan memasuki halaman yang berisi daftar-daftar petisi.
![image](https://github.com/user-attachments/assets/7f5fc2a6-6271-4759-b5ac-6a487c571f3a)

## 4. Halaman Membuat Petisi
User dapat mengakses halaman untuk membuat petisi melalui menu navigasi yang berada di sebelah kiri layar. Pada halaman ini, user diminta untuk memasukkan ID petisi dan isi lengkap (deskripsi) petisi. Untuk publikasi petisin dapat menekan tombol "simpan dan publikasi petisi".
![image](https://github.com/user-attachments/assets/01553054-d3ab-4c36-a52e-90758a3ac706)

## 5. Halaman Pencarian Petisi
User dapat mencari petisi pada halaman ini dengan mencari ID petisi-nya.
![image](https://github.com/user-attachments/assets/204123a4-cc43-45d4-b4b6-121958cfa92d)

> User juga dapat melihat petisi pada halaman **Daftar Petisi**
> ![image](https://github.com/user-attachments/assets/1ee0bfee-6a99-4a25-9cf9-76c1f7526acf)

## 6. Menandatangani Petisi
User dapat kembali ke halaman "Lihat dan Tandatangani Petisi" untuk menandatangani petisi. Caranya dengan menekan tombol "Tandatangani Petisi Ini Sekarang!".
![image](https://github.com/user-attachments/assets/357ab6c7-bd36-410b-a11b-afa20b4be742)

Jika sudah menekan tombol tersebut, akan menampilkan hasil seperti berikut.
![image](https://github.com/user-attachments/assets/9018a975-35d4-4072-a53f-0d8c0218611c)

## 7. Halaman Statistik Petisi
User dapat memantau data jumlah penandatangan dan jumlah petisi dalam bentuk distribusi penandatangan, piechart, dan tren waktu.
![image](https://github.com/user-attachments/assets/ce0a16db-dba4-4cb0-a98c-ca8be58d831c)

## 8. Halaman Lihat Blockchain
User dapat melihat transaksi yang dilakukan oleh semua pengguna pada halaman blockchain. Halaman ini berfungsi sebagai bentuk keamanan dan transparansi tanda tangan dengan menampilkan data mentah blockchain.
![image](https://github.com/user-attachments/assets/1a05c13f-b7a2-4543-8e9b-bdf50138f2a7)

## 9. Halaman Validasi Blockchain
User dapat melakukan validasi blockchain, dimana berfungsi untuk memeriksa integritas data. Halaman ini dapat menampilkan jika seluruh struktur chain dan tanda tangan berupa valid atau tidak valid.
![image](https://github.com/user-attachments/assets/82f765ee-0459-4572-a63e-fb874f691d36)

## 10. Halaman Profil Saya
User dapat melihat aktivitasnya pada halaman ini. Halaman ini berisi berapa banyak petisi yang dibuat dan ditandatangani oleh user, serta list petisi-nya.
![image](https://github.com/user-attachments/assets/8e83d177-4535-43d8-a37f-0f7d89534036)
