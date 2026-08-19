# Secure File Sharing Application

A fully secure, lightweight file-sharing application built with Python (FastAPI) and Vanilla JavaScript/CSS. 

This application provides a highly secure way to upload, store, and share files. It uses a robust hybrid encryption system (RSA + Fernet) to ensure files are encrypted before they ever touch the disk, and allows authenticated users to generate temporary, self-destructing share links.

## ✨ Features
* **Hybrid Encryption**: Files are encrypted with Fernet symmetric keys on upload. Those symmetric keys are then encrypted with the user's RSA public key.
* **Temporary Share Links**: Generate unique, time-limited download links for any file.
* **Multi-timer UI**: Share multiple files simultaneously; each generated link has an independent, active visual countdown timer in the dashboard.
* **Role-based Access Control**: Standard users can only view, download, and share their own files. An `admin` account is automatically provisioned and has global delete privileges.
* **Copy to Clipboard**: One-click copying of generated share links.
* **Modern UI**: A responsive, clean, minimalistic interface free of unnecessary bloat.

## 🚀 Tech Stack
* **Backend**: Python, FastAPI, SQLAlchemy, PyJWT, Cryptography (Fernet/RSA), bcrypt
* **Database**: SQLite
* **Frontend**: Vanilla HTML, CSS, JavaScript (No heavy frameworks)

## 🛠️ Setup Instructions

### 1. Requirements
* Python 3.9+
* `pip` (Python package manager)

### 2. Installation
1. Navigate to the project directory:
   ```bash
   cd secure_file_sharing
   ```
2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```
3. Install the required dependencies:
   ```bash
   pip install fastapi uvicorn sqlalchemy pyjwt cryptography bcrypt python-multipart
   ```

### 3. Running the Server
Start the FastAPI server using Uvicorn:
```bash
python -m uvicorn main:app --port 8000 --reload
```
The application will be accessible at: `http://127.0.0.1:8000`

### 4. Admin Account
When the server starts for the very first time, it automatically provisions an admin account:
* **Username**: `admin`
* **Password**: `adminpassword`

You can use this account to manage and delete any files uploaded to the server.

## 🔐 Security Architecture Overview
1. **User Registration**: When a user registers, a unique 2048-bit RSA key pair is generated.
2. **File Upload**: A unique Fernet symmetric key is generated for the file. The file is encrypted using this Fernet key. 
3. **Key Storage**: The Fernet key is then encrypted using the user's RSA public key and stored in the database. 
4. **File Download**: The encrypted Fernet key is decrypted using the user's RSA private key, which is then used to decrypt the file in memory before streaming it to the user.
5. **Share Links**: Secure JSON Web Tokens (JWTs) are generated containing the `file_id` and an expiration timestamp. The API validates these tokens before allowing anonymous downloads.

## 📂 Project Structure
* `main.py` - FastAPI entry point and core routing.
* `security.py` - Encryption, hashing, and JWT logic.
* `models.py` - SQLAlchemy database models.
* `database.py` - SQLite connection factory.
* `static/` - Contains the frontend logic (`app.js`), styling (`style.css`), and main page (`index.html`).
* `uploads/` - The directory where encrypted binary files are stored securely.
