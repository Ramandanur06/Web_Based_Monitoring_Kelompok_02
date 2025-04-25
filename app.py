from flask import Flask, render_template, request, jsonify, send_file
import json, time, datetime, sqlite3, csv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
DATA_FILE = 'data.json'

@app.route('/')
def index():
    with open(DATA_FILE) as f:
        data = json.load(f)

    now = datetime.datetime.now()
    for d in data.values():
        try:
            t = datetime.datetime.strptime(d['timestamp'], "%Y-%m-%d %H:%M:%S")
            delta = (now - t).total_seconds()
            d['status'] = "online" if delta <= 30 else "offline"
        except:
            d['status'] = "offline"

    return render_template('index.html', devices=data)

@app.route('/update', methods=['POST'])
def update():
    payload = request.json
    payload['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")

    with open(DATA_FILE, 'r+') as f:
        try:
            data = json.load(f)
        except:
            data = {}

        data[payload['id']] = payload
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()

    # Simpan ke database
    conn = sqlite3.connect('monitoring.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO logs (client_id, ip, hostname, cpu, ram, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        payload['id'],
        payload['ip'],
        payload['hostname'],
        payload['cpu'],
        payload['ram'],
        payload['status'],
        payload['timestamp']
    ))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})

@app.route('/data')
def data():
    with open(DATA_FILE) as f:
        data = json.load(f)

    now = datetime.datetime.now()
    for d in data.values():
        try:
            t = datetime.datetime.strptime(d['timestamp'], "%Y-%m-%d %H:%M:%S")
            delta = (now - t).total_seconds()
            d['status'] = "online" if delta <= 30 else "offline"
        except:
            d['status'] = "offline"

    return jsonify(data)

@app.route('/histori/<client_id>')
def histori(client_id):
    conn = sqlite3.connect('monitoring.db')
    c = conn.cursor()
    c.execute("SELECT timestamp, cpu, ram FROM logs WHERE client_id=? ORDER BY timestamp DESC LIMIT 20", (client_id,))
    rows = c.fetchall()
    conn.close()

    rows.reverse()
    timestamps = [row[0] for row in rows]
    cpu = [float(row[1].replace('%','')) for row in rows]
    ram = [float(row[2].replace('%','')) for row in rows]

    return render_template("histori.html", client_id=client_id, timestamps=timestamps, cpu=cpu, ram=ram)

@app.route('/export')
def export():
    conn = sqlite3.connect('monitoring.db')
    c = conn.cursor()
    c.execute("SELECT * FROM logs")
    rows = c.fetchall()
    conn.close()

    with open('export.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Client ID', 'IP', 'Hostname', 'CPU', 'RAM', 'Status', 'Timestamp'])
        for row in rows:
            writer.writerow(row)

    return send_file('export.csv', as_attachment=True)

@app.route('/export-pdf')
def export_pdf():
    conn = sqlite3.connect('monitoring.db')
    c = conn.cursor()
    c.execute("SELECT * FROM logs ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()

    filename = "monitoring_report.pdf"
    pdf = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 50, "Monitoring Report")

    pdf.setFont("Helvetica", 10)
    y = height - 80
    pdf.drawString(50, y, "ID | Client ID | IP | Hostname | CPU | RAM | Status | Timestamp")
    y -= 15

    for row in rows:
        row_text = " | ".join(str(x) for x in row)
        pdf.drawString(50, y, row_text[:130])
        y -= 15
        if y < 50:
            pdf.showPage()
            y = height - 50

    pdf.save()
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
