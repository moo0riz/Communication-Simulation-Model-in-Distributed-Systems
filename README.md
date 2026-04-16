
# (RR vs PubSub vs RPC)

=======

# Communication Simulation Model in Distributed Systems (RR vs PubSub vs RPC)


Simulasi GUI interaktif untuk memvisualisasikan dan membandingkan tiga model komunikasi pada sistem terdistribusi:

- **Request–Response (RR)**
- **Publish–Subscribe (PubSub)**
- **Remote Procedure Call (RPC)**

Aplikasi menampilkan topologi node, aliran pesan (token bergerak), serta metrik seperti jumlah pesan terkirim/terkirim-sampai/hilang, latency end-to-end, dan throughput.

## Fitur

- Visualisasi node dan link sesuai model (RR / PubSub / RPC)
- Simulasi **latency per hop** dan **loss per hop**
- Tombol eksekusi tiap model + mode auto untuk PubSub
- Panel metrik + order log (urutan event send/deliver/drop)

## Struktur File

- `main.py` — entrypoint menjalankan GUI.
- `app_tk.py` — GUI Tkinter (`DistributedCommsSimulator`), render scene, animasi token, panel metrik & log.
- `comm_actions.py` — skenario komunikasi RR / PubSub / RPC (alur pesan per model).
- `node_registry.py` — definisi topologi node per model.
- `models.py` — `Node`, `MessageToken`.
- `metrics.py` — class `Metrics`.

## Prasyarat

- Python **3.10+** (disarankan **3.12**)
- Tkinter (Tk/Tcl)

> Program ini tidak memakai library eksternal (hanya standard library Python).

## Cara Menjalankan

Jalankan dari folder project:

### Windows

```powershell
python main.py
# atau
py main.py
```

### macOS

```zsh
python3 main.py
```

Jika Tkinter pada `python3` tidak kompatibel/bermasalah, gunakan Python yang menyertakan Tk yang sesuai (misalnya `python3.12`):

```zsh
python3.12 main.py
```

<<<<<<< HEAD

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

=======

## Cara Menggunakan

- Klik tombol:
  - **Jalankan RR (Send Request)**
  - **Jalankan PubSub (Publish Event)**
  - **Jalankan RPC (Remote Call)**
- Atur slider:
  - **Latency per hop (ms)**
  - **Loss per hop (%)**
  - **Rate (event/detik)** (untuk auto PubSub)
- Centang **Auto run** untuk publish event PubSub berkala.

## Catatan Metrik (ringkas)

- **Sent/Delivered/Dropped** dihitung **per-hop**.
- **Avg latency (e2e)** adalah rata-rata waktu end-to-end (mis. RR: request+response + processing).
- **Throughput** dihitung sebagai delivered per detik.
