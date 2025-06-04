from flask import Flask, render_template, request, redirect
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

app = Flask(__name__)

import os
import json

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
    return render_template("tabela.html")


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

@app.route("/relatorio")
def relatorio():
    compras = db.collection("compras").stream()
    precos = {}
    for c in compras:
        d = c.to_dict()
        item = d["item"].lower()
        if item not in precos:
            precos[item] = []
        precos[item].append((d["local"], d["valor"]))

    menores = {}
    for item, valores in precos.items():
        menores[item] = min(valores, key=lambda x: x[1])

    return render_template("relatorio.html", menores=menores)

@app.route("/lista", methods=["GET", "POST"])
def lista():
    sugestoes = {}
    if request.method == "POST":
        lista_itens = request.form["itens"].split(",")
        compras = db.collection("compras").stream()
        historico = {}
        for c in compras:
            d = c.to_dict()
            nome = d["item"].lower()
            if nome not in historico:
                historico[nome] = []
            historico[nome].append((d["local"], d["valor"]))

        for item in lista_itens:
            item = item.strip().lower()
            if item in historico:
                sugestoes[item] = min(historico[item], key=lambda x: x[1])
            else:
                sugestoes[item] = ("Sem dados", 0.0)

    return render_template("lista.html", sugestoes=sugestoes, lista_itens=request.form.get("itens", ""))

@app.route("/pesquisa", methods=["GET", "POST"])
def pesquisa():
    resultados = []
    produto = ""

    if request.method == "POST":
        produto = request.form.get("produto", "").strip().lower()
        if produto:
            compras = db.collection("compras").stream()
            for c in compras:
                d = c.to_dict()
                # Comparar com o nome do produto (minusculo)
                if d["item"].lower() == produto:
                    resultados.append(d)

    return render_template("pesquisa.html", resultados=resultados, produto=produto)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
