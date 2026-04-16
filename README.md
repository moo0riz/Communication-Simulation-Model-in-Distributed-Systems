# Simulasi Interaktif Model Komunikasi dalam Sistem Terdistribusi (RR vs PubSub vs RPC)

Tugas: **Sister – Tugas 2**

## 1. Tujuan

Aplikasi ini membantu memahami dampak **model komunikasi yang berbeda** pada sistem terdistribusi melalui simulasi visual interaktif:

1. **Request–Response (RR)**

   - _Client_ mengirim request ke _Server_.
   - _Server_ memproses lalu mengirim response kembali.
   - Karakteristik: sinkron, one-to-one, kuat ketergantungan pada server.

2. **Publish–Subscribe (PubSub)**

   - _Publisher_ menerbitkan event ke _Broker_.
   - _Broker_ melakukan fan-out ke semua _Subscriber_.
   - Karakteristik: event-driven, loose coupling, one-to-many.

3. **Remote Procedure Call (RPC)**
   - _Client_ melakukan pemanggilan prosedur/fungsi ke _Server_ (call) lalu menerima nilai balik (return).
   - Karakteristik: abstraksi “pemanggilan fungsi remote”, umumnya sinkron; mirip RR tetapi menekankan semantik call/return dan waktu eksekusi di server.

Simulasi memperlihatkan **aliran pesan** di link (garis) serta memperlihatkan dampak **latency** dan **loss** terhadap metrik.

## 2. Komponen Sistem

## 2.a Struktur File (Modular)

Kode sudah dipecah agar tidak menumpuk di satu file:

- `main.py` — entrypoint untuk menjalankan GUI.
- `app_tk.py` — kelas GUI `DistributedCommsSimulator` (layout, render node/link, animasi token, metrik UI).
- `comm_actions.py` — skenario komunikasi RR / PubSub / RPC (logika alur pesan per model).
- `node_registry.py` — definisi topologi node per model + helper lookup node.
- `models.py` — dataclass `Node`, `MessageToken`.
- `metrics.py` — class `Metrics`.

Cadangan versi monolitik ada di:
- `main_old_monolith.py`


Komponen yang divisualisasikan sebagai node:

- **Client**: pengirim request RR.
- **Server**: penerima request RR dan pengirim response.
- **Publisher**: penerbit event PubSub.
- **Broker**: perantara; menerima event dari publisher lalu mendistribusikan.
- **Subscriber A/B/C**: penerima event dari broker.

Link yang disimulasikan:

- RR: `Client → Server` dan `Server → Client`
- PubSub: `Publisher → Broker` dan `Broker → Subscriber(i)`

## 3. Cara Menjalankan

## 3.a Prasyarat (yang perlu di-install)

Aplikasi ini **tidak memakai library eksternal** (murni Python standard library), namun butuh:

- **Python 3.10+** (disarankan 3.12)
- **Tkinter (Tk/Tcl)** untuk GUI
- (opsional) **Git** untuk push ke GitHub

### macOS (disarankan)

Karena Tkinter bisa berbeda-beda tergantung instalasi Python, gunakan Python yang **pasti** punya Tkinter yang kompatibel.

### Windows

#### Prasyarat

- Install **Python 3.10+** dari https://www.python.org/downloads/
- Saat instalasi, centang:
  - **Add python.exe to PATH**
  - **tcl/tk and IDLE** (biar Tkinter ikut terpasang)

#### Menjalankan

Buka Command Prompt / PowerShell, lalu:

```powershell
cd path\ke\folder\Tugas2
python main.py
```

Jika perintah `python` tidak ditemukan, coba:

```powershell
py main.py
```

#### Opsi 1: Homebrew Python 3.12 + Tk

Pastikan paket berikut ada (Homebrew):

- `python@3.12`
- `tcl-tk`
- `python-tk@3.12`

Lalu jalankan dari folder project:

```zsh
python3.12 main.py
```

#### Opsi 2: Python bawaan macOS (jika Tk-nya tidak crash)

Jalankan dari folder project:

```zsh
python3 main.py
```

#### Troubleshooting singkat

- Jika menjalankan `python3 main.py` tetapi tidak muncul apa-apa, pastikan **bukan** memakai Homebrew Python 3.14 (`/opt/homebrew/bin/python3`) karena pada beberapa konfigurasi Tk dapat crash/abort.
- Cek Tkinter dulu:

```zsh
python3.12 -c "import tkinter as tk; r=tk.Tk(); r.after(300, r.destroy); r.mainloop(); print('tk ok')"
```

## 3.b Push ke GitHub (ringkas)

1. Buat repo di GitHub.
2. Di folder project:

```zsh
git init
git add .
git commit -m "Initial commit"
```

3. Tambahkan remote lalu push (ganti URL sesuai repo kamu):

```zsh
git remote add origin https://github.com/<username>/<repo>.git
git branch -M main
git push -u origin main
```

> File `.gitignore` sudah disediakan untuk mengabaikan `__pycache__`, `.venv`, `.DS_Store`, dll.

## 4. Cara Menggunakan (Interaksi Pengguna)

### Tombol

- **Jalankan RR (Send Request)**: menjalankan satu transaksi RR (request + response).
- **Jalankan PubSub (Publish Event)**: menjalankan satu event PubSub (publish + fan-out).
- **Jalankan RPC (Remote Call)**: menjalankan satu transaksi RPC (call + return, termasuk waktu eksekusi di server).
- **Reset metrik & log**: menghapus token aktif, metrik, dan order log.

### Slider

- **Latency per hop (ms)**: delay jaringan per hop.
- **Loss per hop (%)**: probabilitas pesan hilang per hop.
- **Rate (event/detik)**: kecepatan publish saat mode auto PubSub.

### Checkbox

- **Auto run (publish berkala)**: PubSub publish otomatis berdasarkan nilai rate.

## 5. Representasi Visual

- Node ditampilkan sebagai lingkaran dengan label.
- Link antar node ditampilkan sebagai garis.
- Pesan ditampilkan sebagai **token/gelembung** yang bergerak dari sumber ke tujuan.

## 6. Mekanisme Perbandingan (Metrik)

Panel metrik menampilkan RR, PubSub, dan RPC secara bersamaan:

- **Sent**: jumlah pengiriman per hop.
- **Delivered**: jumlah yang sampai.
- **Dropped**: jumlah yang hilang (drop) karena loss.
- **Avg latency (e2e)**: rata-rata delay end-to-end.
- **Throughput**: delivered per detik.
- **Order log**: urutan kejadian send/deliver/drop untuk membantu observasi.

### Cara interpretasi cepat

- Pada **RR**, satu transaksi terdiri dari **2 hop** (client→server, server→client). Jadi loss per hop mengakumulasi peluang drop.
- Pada **RPC**, satu transaksi juga terdiri dari **2 hop** (call client→server, return server→client) + waktu eksekusi di server. Secara probabilistik mirip RR, tetapi e2e cenderung sedikit lebih tinggi karena ada exec delay.
- Pada **PubSub**, satu event terdiri dari **1 hop ke broker + fan-out** ke setiap subscriber. Jadi sent/delivered biasanya lebih banyak karena one-to-many, dan bisa terjadi _partial delivery_ (sebagian subscriber menerima, sebagian drop).

## 7. Catatan Implementasi

- Simulasi berjalan di event loop Tkinter dan memakai scheduler `after()`.
- RR dan PubSub dapat berjalan bersamaan (concurrent) tanpa perlu thread tambahan.
- Parameter loss diterapkan per hop secara probabilistik.

## 8. Checklist Rubrik (Ringkas)

- ✅ 3 model komunikasi (RR, PubSub, RPC)
- ✅ Komponen sistem jelas (client/server/publisher/broker/subscriber)
- ✅ Logika interaksi akurat (hop-by-hop, latency, loss)
- ✅ Representasi visual (node, link, token bergerak)
- ✅ Interaksi pengguna (tombol, slider, auto)
- ✅ Mekanisme perbandingan (metrik + order log)
- ✅ Dokumentasi (README ini)
# -Communication-Simulation-Model-in-Distributed-Systems
# Communication-Simulation-Model-in-Distributed-Systems
