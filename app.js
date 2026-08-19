const API_URL = "";

let authToken = localStorage.getItem('authToken');
let currentUsername = localStorage.getItem('username');
let activeShares = [];
let globalTimerInterval = null;

const authSection = document.getElementById('auth-section');
const dashboardSection = document.getElementById('dashboard-section');
const userInfo = document.getElementById('user-info');
const usernameDisplay = document.getElementById('username-display');
const authError = document.getElementById('auth-error');
const filesList = document.getElementById('files-list');

function init() {
    if (authToken) {
        showDashboard();
    } else {
        showAuth();
    }
}

function showAuth() {
    authSection.classList.remove('hidden');
    dashboardSection.classList.add('hidden');
    userInfo.classList.add('hidden');
}

function showDashboard() {
    authSection.classList.add('hidden');
    dashboardSection.classList.remove('hidden');
    userInfo.classList.remove('hidden');
    usernameDisplay.textContent = `Logged in as: ${currentUsername}`;
    fetchFiles();
}

document.getElementById('login-btn').addEventListener('click', async () => {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    authError.textContent = "";

    try {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const res = await fetch(`${API_URL}/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });

        if (!res.ok) throw new Error("Login failed");

        const data = await res.json();
        authToken = data.access_token;
        currentUsername = username;
        localStorage.setItem('authToken', authToken);
        localStorage.setItem('username', currentUsername);
        showDashboard();
    } catch (e) {
        authError.textContent = e.message;
    }
});

document.getElementById('register-btn').addEventListener('click', async () => {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    authError.textContent = "";

    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const res = await fetch(`${API_URL}/register`, {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Registration failed");
        }
        
        alert("Registration successful. Please login.");
    } catch (e) {
        authError.textContent = e.message;
    }
});

document.getElementById('logout-btn').addEventListener('click', () => {
    authToken = null;
    currentUsername = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('username');
    
    activeShares = [];
    if (globalTimerInterval) {
        clearInterval(globalTimerInterval);
        globalTimerInterval = null;
    }
    const container = document.getElementById('active-shares-list');
    if (container) {
        container.innerHTML = '<p style="font-size: 0.875rem; color: var(--text-muted);">No active share links.</p>';
    }
    
    showAuth();
});

document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('file-input');
    const msg = document.getElementById('upload-message');
    msg.textContent = "Uploading...";

    if (fileInput.files.length === 0) return;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const res = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` },
            body: formData
        });

        if (!res.ok) throw new Error("Upload failed");
        
        msg.textContent = "File uploaded securely!";
        fileInput.value = "";
        fetchFiles();
    } catch (e) {
        msg.textContent = "Error: " + e.message;
    }
});

async function fetchFiles() {
    try {
        const res = await fetch(`${API_URL}/files`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!res.ok) {
            if (res.status === 401) {
                document.getElementById('logout-btn').click();
                return;
            }
            throw new Error("Failed to fetch files");
        }

        const files = await res.json();
        renderFiles(files);
    } catch (e) {
        console.error(e);
    }
}

function renderFiles(files) {
    filesList.innerHTML = "";
    files.forEach(f => {
        const escapedFilename = f.filename.replace(/'/g, "\\'");
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${f.id}</td>
            <td>${f.filename}</td>
            <td>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    <button class="btn btn-primary" onclick="downloadFile(${f.id}, '${escapedFilename}')">Download</button>
                    <div style="display: flex; gap: 0.25rem; align-items: center;">
                        <input type="number" id="expiry-${f.id}" value="3600" style="width: 70px; padding: 0.25rem; border: 1px solid var(--border-color); border-radius: 4px;" title="Expiry in seconds">
                        <span style="font-size: 0.75rem; color: var(--text-muted);">sec</span>
                        <button class="btn btn-secondary" onclick="shareFile(${f.id}, '${escapedFilename}')">Share</button>
                    </div>
                    <button class="btn btn-primary" style="background-color: var(--error-color);" onclick="deleteFile(${f.id})">Delete</button>
                </div>
            </td>
        `;
        filesList.appendChild(tr);
    });
}

window.downloadFile = async (id, filename) => {
    try {
        const res = await fetch(`${API_URL}/download/${id}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!res.ok) throw new Error("Download failed");

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
    } catch (e) {
        alert(e.message);
    }
};

window.deleteFile = async (id) => {
    try {
        const res = await fetch(`${API_URL}/files/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!res.ok) throw new Error("Failed to delete file");
        
        fetchFiles();
    } catch (e) {
        alert(e.message);
    }
};

function updateTimersInDOM() {
    activeShares.forEach(share => {
        const timerSpan = document.getElementById(`timer-${share.id}`);
        if (timerSpan) {
            if (share.timeRemaining <= 0) {
                timerSpan.textContent = "Expired";
                timerSpan.style.color = "var(--text-muted)";
            } else {
                const mins = Math.floor(share.timeRemaining / 60);
                const secs = share.timeRemaining % 60;
                timerSpan.textContent = `Expires in: ${mins}m ${secs}s`;
            }
        }
    });
}

function renderActiveShares() {
    const container = document.getElementById('active-shares-list');
    if (activeShares.length === 0) {
        container.innerHTML = '<p style="font-size: 0.875rem; color: var(--text-muted);">No active share links.</p>';
        return;
    }
    
    container.innerHTML = "";
    activeShares.forEach(share => {
        const div = document.createElement('div');
        div.style.border = "1px solid var(--border-color)";
        div.style.padding = "0.75rem";
        div.style.marginBottom = "0.5rem";
        div.style.borderRadius = "4px";
        
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <strong>${share.filename}</strong>
                <span id="timer-${share.id}" style="font-size: 0.875rem; font-weight: bold; color: var(--error-color);"></span>
            </div>
            <div style="display: flex; gap: 0.5rem;">
                <input type="text" id="link-${share.id}" readonly value="${share.link}" onclick="this.select()" style="cursor: pointer; width: 100%; border: 1px solid var(--border-color); border-radius: 4px; padding: 0.5rem;">
                <button id="copy-btn-${share.id}" class="btn btn-secondary" style="white-space: nowrap;" onclick="copyLink('${share.id}')">Copy Link</button>
            </div>
        `;
        container.appendChild(div);
    });
    updateTimersInDOM();
}

window.copyLink = (id) => {
    const input = document.getElementById(`link-${id}`);
    const btn = document.getElementById(`copy-btn-${id}`);
    if (input && btn) {
        input.select();
        input.setSelectionRange(0, 99999);
        try {
            document.execCommand('copy');
            const originalText = btn.textContent;
            btn.textContent = 'Copied!';
            btn.classList.remove('btn-secondary');
            btn.classList.add('btn-primary');
            setTimeout(() => {
                btn.textContent = originalText;
                btn.classList.remove('btn-primary');
                btn.classList.add('btn-secondary');
            }, 2000);
        } catch (e) {
            console.error('Failed to copy', e);
        }
    }
};

function startGlobalTimer() {
    if (globalTimerInterval) return;
    globalTimerInterval = setInterval(() => {
        let needsRender = false;
        activeShares.forEach(share => {
            if (share.timeRemaining > 0) {
                share.timeRemaining--;
                needsRender = true;
            }
        });
        if (needsRender) {
            updateTimersInDOM();
        }
    }, 1000);
}

window.shareFile = async (id, filename) => {
    try {
        const expiryInput = document.getElementById(`expiry-${id}`);
        let expiry = expiryInput ? parseInt(expiryInput.value) : 3600;
        if (isNaN(expiry) || expiry <= 0) {
            expiry = 3600;
        }

        const res = await fetch(`${API_URL}/share/${id}?expires_in_seconds=${expiry}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!res.ok) throw new Error("Failed to generate share link");

        const data = await res.json();
        const fullLink = window.location.origin + data.link;
        
        activeShares.push({
            id: Date.now() + Math.random(),
            filename: filename || `File #${id}`,
            link: fullLink,
            timeRemaining: expiry
        });
        
        renderActiveShares();
        startGlobalTimer();
        
    } catch (e) {
        alert(e.message);
    }
};

init();
