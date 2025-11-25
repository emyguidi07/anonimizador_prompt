from flask import Flask, render_template, request
from anonimizador import anonimizar_texto

import requests
import os
import json
bin_key = os.environ['BIN_KEY']
bin_url = 'https://api.jsonbin.io/v3/b/6925a2e1d0ea881f40ff3959'

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():

    #get contador
    response = requests.get(
        bin_url,
        headers = {
            'X-Master-Key':bin_key
        }
    )
    data = response.json()
    
    #update contador
    data['record']['contador_acessos'] += 1
    response = requests.put(
        bin_url,
        headers = {
            'Content-Type': 'application/json',
            'X-Master-Key':bin_key
        },
        data = json.dumps(data['record'])
    )
    contador = data['record']['contador_acessos']

    if request.method == "POST":
        lei = request.form.get("lei")
        texto = request.form.get("prompt", "")
        if not lei:
            return render_template("index.html", original=None, erro="Selecione uma legislação antes de continuar.", contador=contador)
        texto_anon = anonimizar_texto(texto, lei)
        return render_template("index.html", original=texto, anonimizado=texto_anon, contador=contador)
    return render_template("index.html", original=None, contador=contador)

if __name__ == "__main__":
    app.run(debug=True)
