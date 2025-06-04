from flask import Flask, render_template, request, redirect
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os
import json
from google.cloud.firestore_v1 import _helpers  # Import para tipo Timestamp do Firestore

app = Flask(__name__)

# Inicialização do Firebase a partir de variável de ambiente
firebase_config = json.loads(os.environ["FIREBASE_CONFIG"])
cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred)
db = firestore.client()

CATEGORIAS = [
    "Laticínios", "Hortifruti", "Carnes", "Mercearia",
    "Limpeza", "Higiene", "Bebidas", "Pet"
]

@app.route("/")
def index():
    return render_template("index.html", categorias=CATEGORIAS)

@app.route('/tabela')
def tabela():
    filtro_item = request.args.get("item", "").lower()
    filtro_local = request.args.get("local", "").lower()
    filtro_data = request.args.get("data", "")

    compras_ref = db.collection('compras')
    compras_docs = compras_ref.stream()

    compras = []
    for doc in compras_docs:
        data = doc.to_dict()

        data_raw = data.get('data')

        # Converter Timestamp do Firestore para datetime padrão
        if isinstance(data_raw, _helpers.Timestamp):
            data_dt = data_raw.ToDatetime()
        else:
            data_dt = data_raw

        data_str = ""
        try:
            if isinstance(data_dt, datetime):
                data_str = data_dt.strftime('%Y-%m-%d')
            elif isinstance(data_dt, str):
                data_str = data_dt
        except Exception:
            data_str = ""

        data['data'] = data_str

        if filtro_item and filtro_item not in data.get('item', '').lower():
            continue
        if filtro_local and filtro_local not in data.get('local', '').lower():
            continue
        if filtro_data and data_str:
            try:
                data_compra = datetime.strptime(data_str, '%Y-%m-%d').date()
                filtro_data_obj = datetime.strptime(filtro_data, '%Y-%m-%d').date()
                if data_compra != filtro_data_obj:
                    continue
            except Exception:
                continue

        compras.append(data)

    compras.sort(key=lambda x: x.get('data', ''), reverse=True)

    return render_template('tabela.html', compras=compras)

@app.route("/adicionar", methods=["POST"])
def adicionar():
    item = request.form["item"]
    categoria = request.form["categoria"]
    valor = float(request.form["valor"].replace(",", "."))
    local = request.form["local"]
    data = datetime.strptime(request.form["data"], "%Y-%m-%d")

    db.collection("compras").add({
