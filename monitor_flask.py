import time
import requests
import subprocess

# Configurações
url = "http://127.0.0.1:5000"  # URL do servidor Flask
interval = 3200  # Intervalo de verificação em segundos
flask_command = ["python", "app.py"]  # Comando para rodar o Flask

def is_server_online():
    """Verifica se o servidor está online."""
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def restart_server():
    """Reinicia o servidor Flask."""
    print("Servidor offline. Reiniciando...")
    subprocess.Popen(flask_command)

if __name__ == "__main__":
    while True:
        if not is_server_online():
            restart_server()
        else:
            print("Servidor está online.")
        time.sleep(interval)
