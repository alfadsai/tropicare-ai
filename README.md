# TropiCare AI

Chatbot edukasi tentang penyakit menular tropis menggunakan Python, Streamlit, dan Gemini API.

## Fitur

- Chat interaktif dengan Gemini.
- Input Gemini API key melalui sidebar.
- Dukungan pertanyaan tentang malaria, demam berdarah, gejala, pencegahan, penularan, dan penanganan secara edukatif.
- Guardrail agar chatbot tidak mendiagnosis atau memberikan dosis obat personal.
- Rujukan ke halaman resmi [Profil Kesehatan Kemenkes](https://www.kemkes.go.id/id/category/profil-kesehatan).
- Penanganan API key, error jaringan, kuota, dan percakapan per sesi.

## Local deployment

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

Masukkan Gemini API key melalui sidebar saat aplikasi berjalan. Alternatifnya, buat `.streamlit/secrets.toml` secara lokal:

```toml
GEMINI_API_KEY = "your-api-key"
```

File tersebut sudah masuk `.gitignore` dan tidak boleh di-commit.

## Deploy ke Streamlit Community Cloud

1. Push repository ke GitHub tanpa `.streamlit/secrets.toml` atau file `.env`.
2. Buat aplikasi baru di Streamlit Community Cloud.
3. Pilih repository dan file utama `app.py`.
4. Di pengaturan **Secrets**, tambahkan:

```toml
GEMINI_API_KEY = "your-api-key"
```

5. Deploy dan uji pertanyaan sederhana sebelum membagikan URL aplikasi.

## Batasan sumber 

Halaman Profil Kesehatan Kemenkes merupakan indeks publikasi resmi, bukan dashboard kasus harian. Aplikasi tidak boleh mengarang angka kasus terkini. Untuk laporan terbaru, periksa publikasi dan sumber resmi terkait, lalu cantumkan tanggal serta tautannya.

Jawaban chatbot bersifat edukatif dan bukan pengganti pemeriksaan atau nasihat tenaga kesehatan. Jangan masukkan identitas pribadi atau data medis sensitif ke dalam chat.
