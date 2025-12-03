from flask import Flask, render_template, request, session
from anonimizador import anonimizar_texto

import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()

from datetime import timedelta
import threading
import tempfile

app = Flask(__name__)
app.secret_key = "qualquercoisa"
app.permanent_session_lifetime = timedelta(days=365)

# Caminho absoluto dentro da pasta do app (evita problemas de cwd)
ARQUIVO_CONTADOR = os.path.join(app.root_path, "contador.json")

# Lock para evitar corrupção se várias threads acessarem ao mesmo tempo
_contador_lock = threading.Lock()

BIN_ID = os.getenv('BIN_ID')
BIN_KEY = os.getenv('BIN_KEY')    
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
bin_headers = {
    "X-Master-Key": BIN_KEY,
    "Content-Type": "application/json"
}

def carregar_contador():
    get_response = requests.get(JSONBIN_URL, headers=bin_headers)
    data = get_response.json()
    counter = data["record"].get("contador", 0)
    return counter

    return
    """Carrega o contador do arquivo JSON. Se não existir, cria com zero."""
    with _contador_lock:
        if not os.path.exists(ARQUIVO_CONTADOR):
            print(f"[contador] arquivo não encontrado. Criando: {ARQUIVO_CONTADOR}")
            try:
                with open(ARQUIVO_CONTADOR, "w", encoding="utf-8") as f:
                    json.dump({"visitas": 0}, f)
            except Exception as e:
                print(f"[contador] erro ao criar arquivo: {e}")
                raise

        try:
            with open(ARQUIVO_CONTADOR, "r", encoding="utf-8") as f:
                data = json.load(f)
            visitas = int(data.get("visitas", 0))
        except (json.JSONDecodeError, ValueError) as e:
            # Se arquivo estiver corrompido, reseta para 0
            print(f"[contador] JSON inválido em {ARQUIVO_CONTADOR}: {e}. Resetando para 0.")
            visitas = 0
            salvar_contador(visitas)
        except Exception as e:
            print(f"[contador] erro ao ler arquivo: {e}")
            visitas = 0

        print(f"[contador] carregar_contador -> {visitas}")
        return visitas


def salvar_contador(valor):
    BIN_ID = os.getenv('BIN_ID')
    BIN_KEY = os.getenv('BIN_KEY')
        
    JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"

    bin_headers = {
        "X-Master-Key": BIN_KEY,
        "Content-Type": "application/json"
    }
    update_response = requests.put(
        JSONBIN_URL,
        headers=bin_headers,
        json={"contador": valor}
    )
    data = update_response.json()
    counter = data["record"].get("contador", 0)
    return counter
    return
    """Salva o contador no arquivo JSON de forma atômica."""
    with _contador_lock:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(ARQUIVO_CONTADOR))
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmpf:
                json.dump({"visitas": int(valor)}, tmpf)
                tmpf.flush()
                os.fsync(tmpf.fileno())
            # substitui atomically o arquivo antigo
            os.replace(tmp_path, ARQUIVO_CONTADOR)
            print(f"[contador] salvo -> {valor}")
        except Exception as e:
            # tenta limpar o temp se der ruim
            print(f"[contador] erro ao salvar contador: {e}")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            raise


# carrega contador ao iniciar servidor
contador_total = carregar_contador()


@app.route("/", methods=["GET", "POST"])
def index():
    global contador_total

    # Garante que um visitante conte apenas uma vez por sessão (1 ano)
    #if not session.get("contou"):
    #    try:
    #        contador_total += 1
    #        session["contou"] = True
    #        salvar_contador(contador_total)   # grava permanentemente
    #    except Exception as e:
    #        print(f"[contador] falha ao incrementar/salvar: {e}")

    #Contador pelo bin.io
    salvar_contador(contador_total+1)


    if request.method == "POST":
        lei = request.form.get("lei")
        texto = request.form.get("prompt", "")

        if not lei:
            return render_template(
                "index.html",
                original=None,
                erro="Selecione uma legislação antes de continuar.",
                contador=contador_total
            )

        texto_anon = anonimizar_texto(texto, lei)

        return render_template(
            "index.html",
            original=texto,
            anonimizado=texto_anon,
            contador=contador_total
        )

    return render_template("index.html", original=None, contador=contador_total)


if __name__ == "__main__":
    app.run(debug=False)
