import os
from datetime import timedelta
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import Response, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import io

from database import engine, Base, get_db
from models import User, FileItem
import security
import encryption

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Secure File-Sharing App")

@app.on_event("startup")
def startup_event():
    db = next(get_db())
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        hashed_password = security.get_password_hash("adminpassword")
        private_pem, public_pem = security.generate_rsa_key_pair()
        admin_user = User(
            username="admin",
            hashed_password=hashed_password,
            role="admin",
            public_key=public_pem,
            private_key=private_pem
        )
        db.add(admin_user)
        db.commit()

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Dependency ---
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = security.jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    except security.jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

# --- Routes ---

@app.post("/register")
def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = security.get_password_hash(password)
    private_pem, public_pem = security.generate_rsa_key_pair()
    
    user = User(
        username=username,
        hashed_password=hashed_password,
        role="user",
        public_key=public_pem,
        private_key=private_pem
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"msg": "User registered successfully", "username": user.username}

@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Read file data
    file_data = await file.read()
    
    # Hybrid Encryption
    sym_key = encryption.generate_symmetric_key()
    encrypted_file_data = encryption.encrypt_file(file_data, sym_key)
    encrypted_sym_key = encryption.encrypt_symmetric_key(sym_key, current_user.public_key)
    
    # Ensure upload directory exists
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{current_user.id}_{file.filename}"
    
    with open(file_path, "wb") as f:
        f.write(encrypted_file_data)
        
    file_item = FileItem(
        filename=file.filename,
        file_path=file_path,
        encrypted_symmetric_key=encrypted_sym_key,
        owner_id=current_user.id
    )
    db.add(file_item)
    db.commit()
    db.refresh(file_item)
    
    return {"msg": "File uploaded and encrypted securely", "file_id": file_item.id}

@app.get("/files")
def list_files(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "admin":
        files = db.query(FileItem).all()
    else:
        files = db.query(FileItem).filter(FileItem.owner_id == current_user.id).all()
    return [{"id": f.id, "filename": f.filename, "owner_id": f.owner_id} for f in files]

@app.get("/download/{file_id}")
def download_file(file_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    file_item = db.query(FileItem).filter(FileItem.id == file_id).first()
    if not file_item:
        raise HTTPException(status_code=404, detail="File not found")
        
    if current_user.role != "admin" and file_item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this file")
        
    # We need the owner's private key to decrypt the symmetric key.
    # In our implementation, the admin can download the file because we have access to the owner's private key in the DB.
    owner = db.query(User).filter(User.id == file_item.owner_id).first()
    
    # Decrypt
    try:
        sym_key = encryption.decrypt_symmetric_key(file_item.encrypted_symmetric_key, owner.private_key)
        with open(file_item.file_path, "rb") as f:
            encrypted_file_data = f.read()
        decrypted_file_data = encryption.decrypt_file(encrypted_file_data, sym_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error decrypting file")
        
    return StreamingResponse(
        io.BytesIO(decrypted_file_data),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={file_item.filename}"}
    )

@app.post("/share/{file_id}")
def share_file(file_id: int, expires_in_seconds: int = 3600, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    file_item = db.query(FileItem).filter(FileItem.id == file_id).first()
    if not file_item:
        raise HTTPException(status_code=404, detail="File not found")
    if file_item.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to share this file")
        
    token = security.create_temporary_share_token(file_id, expires_in_seconds)
    return {"msg": "Share link generated", "link": f"/shared/{token}"}

@app.delete("/files/{file_id}")
def delete_file(file_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    file_item = db.query(FileItem).filter(FileItem.id == file_id).first()
    if not file_item:
        raise HTTPException(status_code=404, detail="File not found")
        
    if current_user.role != "admin" and file_item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this file")
        
    db.delete(file_item)
    db.commit()
    
    if os.path.exists(file_item.filepath):
        os.remove(file_item.filepath)
        
    return {"detail": "File deleted successfully"}

@app.get("/shared/{token}")
def download_shared_file(token: str, db: Session = Depends(get_db)):
    file_id = security.verify_temporary_share_token(token)
    if file_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
        
    file_item = db.query(FileItem).filter(FileItem.id == file_id).first()
    if not file_item:
        raise HTTPException(status_code=404, detail="File not found")
        
    owner = db.query(User).filter(User.id == file_item.owner_id).first()
    
    try:
        sym_key = encryption.decrypt_symmetric_key(file_item.encrypted_symmetric_key, owner.private_key)
        with open(file_item.file_path, "rb") as f:
            encrypted_file_data = f.read()
        decrypted_file_data = encryption.decrypt_file(encrypted_file_data, sym_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error decrypting file")
        
    return StreamingResponse(
        io.BytesIO(decrypted_file_data),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={file_item.filename}"}
    )
