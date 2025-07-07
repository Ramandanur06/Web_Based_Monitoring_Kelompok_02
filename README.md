# Web-Based Monitoring System with HAProxy Failover

Proyek monitoring client menggunakan Flask, SQLite dan HAProxy. Mendukung failover otomatis dari server utama ke backup.

## Struktur

- `app.py` → Backend Flask (run di server utama & backup)
- `client.py` → Script pengirim data dari client (CPU, RAM)
- `data.json` → Penyimpanan sementara untuk dashboard
- `monitoring.db` → Log data histori (SQLite)
- `templates/` → File HTML dashboard dan histori
- `haproxy.cfg` → Konfigurasi load balancer HAProxy

## Jalankan Server

```bash
python3 app.py 5000  # Server utama
python3 app.py 5001  # Server backup
