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
    # Buscar locais e itens únicos do Firestore
    compras_docs = db.collection("compras").stream()
    locais_unicos = set()
    itens_unicos = set()

    for doc in compras_docs:
        data = doc.to_dict()
        local = data.get("local", "").strip()
        item = data.get("item", "").strip()
        if local:
            locais_unicos.add(local)
        if item:
            itens_unicos.add(item)

     data_atual = datetime.now().strftime("%Y-%m-%d")  # formato HTML5 date input


    return render_template(
        "index.html",
        categorias=CATEGORIAS,
        locais=sorted(locais_unicos),
        itens=sorted(itens_unicos)
        data_atual=data_atual  # <-- adiciona aqui
    )
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

        data_str = ""
        try:
            if isinstance(data_dt, datetime):
                data_str = data_dt.strftime('%Y-%m-%d')
            elif isinstance(data_dt, str):
                data_str = data_dt
        except Exception:
            data_str = ""

        data["data"] = data_str
        data["id"] = doc.id

        if filtro_item and filtro_item not in data.get("item", "").lower():
            continue
        if filtro_local and filtro_local not in data.get("local", "").lower():
            continue
        if filtro_data and data_str:
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

        # Coletar sugestões para datalists
        compras_docs = db.collection("compras").stream()
        locais_unicos = set()
        itens_unicos = set()
        categorias_unicas = set()

        for d in compras_docs:
            dados = d.to_dict()
            locais_unicos.add(dados.get("local", "").strip())
            itens_unicos.add(dados.get("item", "").strip())
            categorias_unicas.add(dados.get("categoria", "").strip())

        return render_template(
            "editar.html",
            compra=compra,
            locais=sorted(locais_unicos),
            itens=sorted(itens_unicos),
            categorias=sorted(categorias_unicas)
        )
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

    menores_ordenados = dict(sorted(menores.items()))
    return render_template("relatorio.html", menores=menores_ordenados)

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
                if produto in d["item"].lower():
                    resultados.append(d)

    return render_template("pesquisa.html", resultados=resultados, produto=produto)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
