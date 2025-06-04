from flask import Flask, render_template, request, redirect, url_for
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os
import json
from google.cloud.firestore_v1 import _helpers  # Timestamp do Firestore

app = Flask(__name__)

# Inicialização do Firebase
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

@app.route("/tabela")
def tabela():
    filtro_item = request.args.get("item", "").lower()
    filtro_local = request.args.get("local", "").lower()
    filtro_data = request.args.get("data", "")

    compras_ref = db.collection("compras")
    compras_docs = compras_ref.stream()

    compras = []
    for doc in compras_docs:
        data = doc.to_dict()
        data_raw = data.get("data")

        # Conversão de data
        if isinstance(data_raw, _helpers.Timestamp):
            data_dt = data_raw.ToDatetime()
        else:
            data_dt = data_raw

        try:
            if isinstance(data_dt, datetime):
                data_str = data_dt.strftime('%Y-%m-%d')
            else:
                data_str = data_dt
        except Exception:
            data_str = ""

        data["data"] = data_str
        data["id"] = doc.id

        if filtro_item and filtro_item not in data.get("item", "").lower():
            continue
        if filtro_local and filtro_local not in data.get("local", "").lower():
            continue
        if filtro_data:
            try:
                data_compra = datetime.strptime(data_str, "%Y-%m-%d").date()
                filtro_data_obj = datetime.strptime(filtro_data, "%Y-%m-%d").date()
                if data_compra != filtro_data_obj:
                    continue
            except Exception:
                continue

        compras.append(data)

    compras.sort(key=lambda x: x.get("data", ""), reverse=True)
    return render_template("tabela.html", compras=compras)

@app.route("/editar/<id>", methods=["GET", "POST"])
def editar(id):
    doc_ref = db.collection("compras").document(id)

    if request.method == "POST":
        doc_ref.update({
            "item": request.form["item"],
            "categoria": request.form["categoria"],
            "valor": float(request.form["valor"].replace(",", ".")),
            "local": request.form["local"],
            "data": datetime.strptime(request.form["data"], "%Y-%m-%d")
        })
        return redirect(url_for("tabela"))

    doc = doc_ref.get()
    if doc.exists:
        compra = doc.to_dict()
        compra["id"] = doc.id
        if isinstance(compra.get("data"), datetime):
            compra["data"] = compra["data"].strftime("%Y-%m-%d")
        return render_template("editar.html", compra=compra, categorias=CATEGORIAS)
    else:
        return "Compra não encontrada", 404

@app.route("/adicionar", methods=["POST"])
def adicionar():
    item = request.form["item"]
    categoria = request.form["categoria"]
    valor = float(request.form["valor"].replace(",", "."))
    local = request.form["local"]
    data = datetime.strptime(request.form["data"], "%Y-%m-%d")

    db.collection("compras").add({
        "item": item,
        "categoria": categoria,
        "valor": valor,
        "local": local,
        "data": data
    })
    return redirect("/")

# ... demais rotas permanecem iguais ...

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
