# Per inviare i dati di 1 solo sensore:
# curl -X POST -H "Content-Type: application/json" -d '{"sensors": {"sensor1": 15}}' http://localhost:5000/data
# Per inviare i dati di più sensori (es: 3):
# curl -X POST -H "Content-Type: application/json" -d '{"sensors": {"sensor1": 10, "sensor2": 20, "sensor3": 30}}' http://localhost:5000/data

import sqlite3
from flask import Flask, request, jsonify, send_file
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import io
import numpy as np

app = Flask(__name__)

# Dizionario per memorizzare i dati per ciascun sensore in memoria
sensor_data = {}
sensor_data_filepath = "data/sensor_data.db"

# Connessione al database SQLite e inizializzazione della tabella
def init_db():
    conn = sqlite3.connect(sensor_data_filepath)
    c = conn.cursor()
    # Creazione della tabella se non esiste
    c.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_name TEXT,
            value REAL,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Salvataggio dei dati nel database
def save_to_db(sensor, value, timestamp):
    conn = sqlite3.connect(sensor_data_filepath)
    c = conn.cursor()
    c.execute('INSERT INTO sensor_data (sensor_name, value, timestamp) VALUES (?, ?, ?)',
              (sensor, value, timestamp))
    conn.commit()
    conn.close()

# Caricamento dei dati dal database all'avvio
def load_data_from_db():
    global sensor_data
    conn = sqlite3.connect(sensor_data_filepath)
    c = conn.cursor()
    c.execute('SELECT sensor_name, value, timestamp FROM sensor_data')
    rows = c.fetchall()
    conn.close()

    # Inserire i dati estratti nella struttura in memoria
    for row in rows:
        sensor, value, timestamp_str = row
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        if sensor not in sensor_data:
            sensor_data[sensor] = []
        sensor_data[sensor].append({'timestamp': timestamp, 'value': value})

# Endpoint per ricevere i dati di più sensori
@app.route('/data', methods=['POST'])
def receive_data():
    global sensor_data
    try:
        # Ottieni i dati dei sensori dal JSON ricevuto (deve essere un dizionario con valori)
        data_input = request.json.get('sensors')
        if not data_input:
            return jsonify({"status": "error", "message": "Dati dei sensori mancanti!"}), 400
        
        # Aggiungi i dati di ciascun sensore con il timestamp corrente
        timestamp = datetime.now()
        for sensor, value in data_input.items():
            if sensor not in sensor_data:
                sensor_data[sensor] = []
            sensor_data[sensor].append({'timestamp': timestamp, 'value': value})

            # Salva i dati nel database
            save_to_db(sensor, value, timestamp)

        return jsonify({"status": "success", "message": "Dati dei sensori aggiunti e salvati con successo!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint per visualizzare il grafico
@app.route('/', methods=['GET'])
def plot_data():
    if not sensor_data:
        return jsonify({"status": "error", "message": "Nessun dato da visualizzare!"}), 400

    # Impostare il tema scuro
    plt.style.use('dark_background')

    # Creare il grafico a linee con mappa di colori
    plt.figure(figsize=(10, 5))
    cmap = plt.get_cmap('plasma')

    # Traccia ogni sensore separatamente
    color_idx = np.linspace(0, 1, len(sensor_data))  # Genera un colore diverso per ogni sensore
    for i, (sensor, data_entries) in enumerate(sensor_data.items()):
        timestamps = [entry['timestamp'] for entry in data_entries]
        values = [entry['value'] for entry in data_entries]
        
        # Disegna la linea per ciascun sensore con un colore distinto
        plt.plot(timestamps, values, marker='o', color=cmap(color_idx[i]), linestyle='-', label=f'Sensore {sensor}')
    
    plt.title("Dati dei sensori", color='white')
    plt.xlabel("Timestamp", color='white')
    plt.ylabel("Valore", color='white')

    # Formatta l'asse X per mostrare le date in modo leggibile
    plt.gcf().autofmt_xdate()
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())

    # Imposta il colore della griglia e delle etichette degli assi
    plt.grid(True, color='gray')
    plt.gca().tick_params(axis='x', colors='white')
    plt.gca().tick_params(axis='y', colors='white')
    
    # Aggiungi una legenda una sola volta per ciascun sensore
    plt.legend()

    # Salvare il grafico in un buffer temporaneo
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    
    # Restituire il grafico come immagine
    return send_file(img, mimetype='image/png')

# Inizializzazione del database e caricamento dei dati all'avvio del server
init_db()
load_data_from_db()

# Avvio del server Flask
if __name__ == '__main__':
    app.run(debug=True)

