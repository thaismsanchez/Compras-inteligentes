from flask import Flask, render_template, request, redirect
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os
import json

app = Flask(__name__)

# Inicialização do Firebase a partir de variável de ambiente
firebase_config = json.loads(os.environ["FIREBASE_CONFIG"])
cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Lista de categorias usadas no formulário
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

        # Garantir que data seja string 'YYYY-MM-DD'
        data_raw = data.get('data')

        data_str = ""
        try:
            if isinstance(data_raw, str):
                data_str = data_raw
            elif hasattr(data_raw, 'strftime'):
                data_str = data_raw.strftime('%Y-%m-%d')
            elif hasattr(data_raw, 'to_datetime'):
                data_str = data_raw.to_datetime().strftime('%Y-%m-%d')
        except Exception:
            data_str = ""

        data['data'] = data_str

        # Aplicar filtros
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

    # Ordenar por data decrescente (string no formato YYYY-MM-DD)
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
                # Busca parcial: verifica se o termo digitado está contido no nome do produto
                if produto in d["item"].lower():
                    resultados.append(d)

    return render_template("pesquisa.html", resultados=resultados, produto=produto)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
