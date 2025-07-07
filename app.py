from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO
from flask_cors import CORS
import json, time, datetime, sqlite3, csv, os, sys
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

DATA_FILE = 'data.json'

def read_data_file():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except:
        return {}

def write_data_file(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error writing to data.json: {e}")
        return False
    return True

@app.route('/')
def index():
    data = read_data_file()
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

    data = read_data_file()
    data[payload['id']] = payload
    if not write_data_file(data):
        return jsonify({"status": "error", "message": "Failed to write data.json"}), 500

    try:
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
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    socketio.emit('alert', {'message': f"📡 Data updated from {payload['hostname']}"})
    return jsonify({"status": "ok"})

@app.route('/data')
def data():
    data = read_data_file()
    now = datetime.datetime.now()
    for d in data.values():
        try:
            t = datetime.datetime.strptime(d['timestamp'], "%Y-%m-%d %H:%M:%S")
            delta = (now - t).total_seconds()
            d['status'] = "online" if delta <= 30 else "offline"
        except:
            d['status'] = "offline"
    return jsonify(data)

@app.route('/ping')
def ping():
    return 'pong', 200

@app.route('/histori/<client_id>')
def histori(client_id):
    selected_date = request.args.get('date')
    conn = sqlite3.connect('monitoring.db')
    c = conn.cursor()

    if selected_date:
        start = f"{selected_date} 00:00:00"
        end = f"{selected_date} 23:59:59"
        c.execute("""
            SELECT timestamp, cpu, ram FROM logs 
            WHERE client_id=? AND timestamp BETWEEN ? AND ? 
            ORDER BY timestamp DESC
        """, (client_id, start, end))
    else:
        c.execute("""
            SELECT timestamp, cpu, ram FROM logs 
            WHERE client_id=? ORDER BY timestamp DESC
        """, (client_id,))

    rows = c.fetchall()
    conn.close()

    rows.reverse()
    timestamps = [row[0] for row in rows]
    cpu = [float(row[1].replace('%', '')) for row in rows]
    ram = [float(row[2].replace('%', '')) for row in rows]

    return render_template("histori.html", client_id=client_id, timestamps=timestamps, cpu=cpu, ram=ram, selected_date=selected_date)

@app.route('/export')
def export():
    conn = sqlite3.connect('monitoring.db')
    c = conn.cursor()
    c.execute("SELECT * FROM logs")
    rows = c.fetchall()
    conn.close()

    filename = f"export_{int(time.time())}.csv"
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Client ID', 'IP', 'Hostname', 'CPU', 'RAM', 'Status', 'Timestamp'])
        writer.writerows(rows)

    return send_file(filename, as_attachment=True)

@app.route('/export-pdf')
def export_pdf():
    conn = sqlite3.connect('monitoring.db')
    c = conn.cursor()
    c.execute("SELECT * FROM logs ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()

    filename = f"monitoring_report_{int(time.time())}.pdf"
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

@socketio.on('connect')
def handle_connect():
    print('Client connected via WebSocket')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except:
            pass
    print(f"🚀 Server running on port {port} (primary if 5000, backup if 5001)")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
