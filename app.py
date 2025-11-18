from flask import Flask, render_template, request
from anonimizador import anonimizar_texto

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        lei = request.form.get("lei")
        texto = request.form.get("prompt", "")
        if not lei:
            return render_template("index.html", original=None, erro="Selecione uma legislação antes de continuar.")
        texto_anon = anonimizar_texto(texto, lei)
        return render_template("index.html", original=texto, anonimizado=texto_anon)
    return render_template("index.html", original=None)

if __name__ == "__main__":
    app.run(debug=True)
