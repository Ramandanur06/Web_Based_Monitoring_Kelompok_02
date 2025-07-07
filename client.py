import socket
import psutil
import requests
import time

SERVER = 'http://192.168.1.13/update'  # IP HAProxy
DEVICE_ID = 'client-04'  # Ganti sesuai nama client

def kirim_data():
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except:
        ip = '0.0.0.0'

    cpu = f"{psutil.cpu_percent()}%"
    ram = f"{psutil.virtual_memory().percent}%"

    data = {
        "id": DEVICE_ID,
        "ip": ip,
        "hostname": hostname,
        "cpu": cpu,
        "ram": ram,
        "status": "online"
    }

    try:
        res = requests.post(SERVER, json=data)
        print(f"[INFO] Data terkirim: {res.status_code}")
    except Exception as e:
        print("[ERROR]", e)

while True:
    kirim_data()
    time.sleep(5)
