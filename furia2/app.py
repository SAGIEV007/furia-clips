"""FURIA 2 — o servidor da bancada.

Enquanto o desenho está sendo montado tela a tela, isto aqui não faz nada além
de entregar a bancada. O motor do Furia 1 (transcrição, análise, seleção,
corte) entra depois que as telas estiverem aprovadas — ele já foi conferido e
importa sozinho, sem depender de nada da interface velha.

Roda na porta 5001 de propósito: o Furia 1 roda na 5000, e a combinação foi os
dois abertos lado a lado, para comparar.
"""

from pathlib import Path

from flask import Flask, render_template

PORTA = 5001

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)


@app.route("/")
def bancada():
    return render_template("bancada.html")


if __name__ == "__main__":
    print(f"Furia 2 — bancada em http://127.0.0.1:{PORTA}")
    # 127.0.0.1 e não 0.0.0.0: o programa é da máquina dele e não tem por que
    # ficar escutando a rede da casa.
    app.run(host="127.0.0.1", port=PORTA, debug=False)
