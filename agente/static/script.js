const chat = document.getElementById("chatMessages");
const input = document.getElementById("userInput");
const modal = document.getElementById("chartModal");
const closeModalBtn = document.getElementById("closeChartModal");
const downloadBtn = document.getElementById("downloadChart");
const conversationList = document.getElementById("conversationList");
let fullscreenChartInstance = null;
let currentChartData = null;
let currentConversationId = null;

const API_URL = "https://unreproachable-hybridisable-maggie.ngrok-free.dev";

loadConversations();

async function loadConversations() {
    try {
        const response = await fetch(`${API_URL}/conversations`);
        const conversations = await response.json();
        renderConversations(conversations);
    } catch (e) {
        console.error("Failed to load conversations", e);
    }
}

function renderConversations(conversations) {
    conversationList.innerHTML = "";
    conversations.forEach(c => {
        const div = document.createElement("div");
        div.className = `conversation-item ${c.id === currentConversationId ? 'active' : ''}`;
        div.onclick = () => loadConversation(c.id);

        const title = document.createElement("div");
        title.className = "conversation-title";
        title.textContent = c.title;

        const date = document.createElement("div");
        date.className = "conversation-date";
        date.textContent = new Date(c.created_at).toLocaleDateString();

        const actions = document.createElement("div");
        actions.className = "conversation-actions";

        const renameBtn = document.createElement("button");
        renameBtn.className = "action-btn";
        renameBtn.title = "Renomear";
        renameBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z" /></svg>';
        renameBtn.onclick = (e) => {
            e.stopPropagation();
            renameConversation(c.id, c.title);
        };

        const deleteBtn = document.createElement("button");
        deleteBtn.className = "action-btn";
        deleteBtn.title = "Excluir";
        deleteBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z" /></svg>';
        deleteBtn.onclick = (e) => {
            e.stopPropagation();
            deleteConversation(c.id);
        };

        actions.appendChild(renameBtn);
        actions.appendChild(deleteBtn);

        div.appendChild(title);
        div.appendChild(date);
        div.appendChild(actions);
        conversationList.appendChild(div);
    });
}

async function loadConversation(id) {
    currentConversationId = id;
    chat.innerHTML = "";

    const items = document.querySelectorAll('.conversation-item');
    items.forEach(item => item.classList.remove('active'));
    loadConversations();

    try {
        const response = await fetch(`${API_URL}/conversations/${id}/messages`);
        const messages = await response.json();

        if (messages.length === 0) {
            addMessage("Olá! Sou seu analista financeiro. Envie sua pergunta para começar.", "in");
        } else {
            messages.forEach(msg => {
                addMessage(msg.content, msg.sender === 'user' ? 'out' : 'in');
                if (msg.chart_data) {
                    renderChart(msg.chart_data);
                }
            });
        }
    } catch (e) {
        console.error("Failed to load messages", e);
        addMessage("Erro ao carregar histórico.", "in");
    }
}

function startNewChat() {
    currentConversationId = null;
    chat.innerHTML = "";
    addMessage("Olá! Sou seu analista financeiro. Envie sua pergunta para começar.", "in");
    loadConversations();
}

function addMessage(text, sender = "in") {
    const div = document.createElement("div");
    div.className = "msg msg-" + sender;

    const textSpan = document.createElement("span");
    textSpan.textContent = text;
    div.appendChild(textSpan);

    if (sender === "in") {
        const audioBtn = document.createElement("button");
        audioBtn.className = "audio-btn";
        audioBtn.title = "Ouvir";
        audioBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M14,3.23V5.29C16.89,6.15 19,8.83 19,12C19,15.17 16.89,17.84 14,18.7V20.77C18,19.86 21,16.28 21,12C21,7.72 18,4.14 14,3.23M16.5,12C16.5,10.23 15.5,8.71 14,7.97V16.02C15.5,15.29 16.5,13.76 16.5,12M3,9V15H7L12,20V4L7,9H3Z" /></svg>';
        audioBtn.onclick = () => playAudio(text, audioBtn);
        div.appendChild(audioBtn);
    }

    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

async function playAudio(text, btn) {
    if (btn.classList.contains('audio-loading')) return;

    const parent = btn.parentElement;
    const originalContent = btn.innerHTML;

    btn.classList.add('audio-loading');
    btn.innerHTML = '<svg viewBox="0 0 24 24" class="spinning"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none" stroke-dasharray="31.4 31.4" stroke-linecap="round"/></svg>';
    btn.title = "Carregando áudio...";

    try {
        const voice = document.getElementById('voiceSelect').value;
        const response = await fetch(`${API_URL}/tts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, voice: voice })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
            throw new Error(errorData.detail || `Erro ${response.status}`);
        }

        const blob = await response.blob();
        if (blob.size === 0) throw new Error('Áudio vazio recebido');

        const audioUrl = URL.createObjectURL(blob);

        const audio = document.createElement('audio');
        audio.controls = true;
        audio.src = audioUrl;
        audio.style.marginTop = "8px";
        audio.style.display = "block";
        audio.style.maxWidth = "100%";
        audio.style.height = "40px";

        // Hide the button and append the audio player
        btn.style.display = 'none';
        parent.appendChild(audio);

        await audio.play();

    } catch (e) {
        console.error('Erro no TTS:', e);
        btn.classList.remove('audio-loading');
        btn.classList.add('audio-error');
        btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12,2C6.48,2 2,6.48 2,12C2,17.52 6.48,22 12,22C17.52,22 22,17.52 22,12C22,6.48 17.52,2 12,2M13,17H11V15H13V17M13,13H11V7H13V13Z"/></svg>';
        btn.title = `Erro: ${e.message}`;

        const errorMsg = document.createElement('div');
        errorMsg.className = 'audio-error-toast';
        errorMsg.textContent = `❌ ${e.message}`;
        document.body.appendChild(errorMsg);

        setTimeout(() => {
            errorMsg.classList.add('fade-out');
            setTimeout(() => errorMsg.remove(), 300);
        }, 3000);

        setTimeout(() => {
            btn.classList.remove('audio-error');
            btn.innerHTML = originalContent;
            btn.title = "Ouvir";
        }, 3000);
    }
}

function renderChart(chartData) {
    if (chartData && Object.keys(chartData).length > 0) {
        currentChartData = chartData;

        const bubble = document.createElement("div");
        bubble.className = "chart-bubble";

        const canvas = document.createElement("canvas");
        bubble.appendChild(canvas);
        chat.appendChild(bubble);
        chat.scrollTop = chat.scrollHeight;

        new Chart(canvas.getContext("2d"), {
            type: chartData.type,
            data: chartData.data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: getChartColors() }
                    }
                },
                scales: chartData.type !== 'pie' && chartData.type !== 'doughnut' ? {
                    x: { ticks: { color: getChartColors() } },
                    y: { ticks: { color: getChartColors() } }
                } : {}
            }
        });

        bubble.addEventListener("click", () => openChartModal());
    }
}

function getChartColors() {
    const isDark = document.body.classList.contains('dark-mode');
    return isDark ? '#e9edef' : '#111111';
}

async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, "out");
    input.value = "";

    const loadingMsg = document.createElement("div");
    loadingMsg.className = "msg msg-in";
    loadingMsg.textContent = "Analisando...";
    chat.appendChild(loadingMsg);
    chat.scrollTop = chat.scrollHeight;

    try {
        const response = await fetch(
            `${API_URL}/conta-corrente`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    pergunta: text,
                    tipo_conta: "conta-corrente",
                    conversation_id: currentConversationId
                })
            }
        );

        const data = await response.json();
        loadingMsg.remove();

        if (!currentConversationId && data.conversation_id) {
            currentConversationId = data.conversation_id;
            loadConversations();
        }

        addMessage(data.analise_texto || "Sem resposta.", "in");

        if (data.grafico && Object.keys(data.grafico).length > 0) {
            renderChart(data.grafico);
        }
    } catch (e) {
        loadingMsg.remove();
        addMessage("Erro ao consultar API.", "in");
        console.error(e);
    }
}

function openChartModal() {
    if (!currentChartData) return;

    modal.style.display = "flex";

    const ctx = document.getElementById("fullscreenChart").getContext("2d");

    if (fullscreenChartInstance) {
        fullscreenChartInstance.destroy();
    }

    fullscreenChartInstance = new Chart(ctx, {
        type: currentChartData.type,
        data: currentChartData.data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: getChartColors(), font: { size: 14 } }
                }
            },
            scales: currentChartData.type !== 'pie' && currentChartData.type !== 'doughnut' ? {
                x: { ticks: { color: getChartColors() } },
                y: { ticks: { color: getChartColors() } }
            } : {}
        }
    });
}

function closeChartModal() {
    modal.style.display = "none";
    if (fullscreenChartInstance) {
        fullscreenChartInstance.destroy();
        fullscreenChartInstance = null;
    }
}

closeModalBtn.addEventListener("click", closeChartModal);

modal.addEventListener("click", (e) => {
    if (e.target === modal) closeChartModal();
});

downloadBtn.addEventListener("click", () => {
    const canvas = document.getElementById("fullscreenChart");
    const isDark = document.body.classList.contains('dark-mode');
    const bgColor = isDark ? '#202c33' : '#ffffff';

    const tmpCanvas = document.createElement("canvas");
    const ctx = tmpCanvas.getContext("2d");
    tmpCanvas.width = canvas.width;
    tmpCanvas.height = canvas.height;

    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, tmpCanvas.width, tmpCanvas.height);
    ctx.drawImage(canvas, 0, 0);

    const url = tmpCanvas.toDataURL("image/png");
    const a = document.createElement("a");
    a.href = url;
    a.download = "grafico-analise-financeira.png";
    a.click();
});

input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
});

const toggle = document.getElementById("theme-toggle");

function setTheme(mode) {
    document.body.classList.toggle("dark-mode", mode === "dark");
    localStorage.setItem("theme", mode);
}

toggle.onclick = () => {
    const newMode = document.body.classList.contains("dark-mode") ? "light" : "dark";
    setTheme(newMode);
};

setTheme(localStorage.getItem("theme") || "light");

async function renameConversation(id, currentTitle) {
    const newTitle = prompt("Novo nome da conversa:", currentTitle);
    if (newTitle && newTitle !== currentTitle) {
        try {
            await fetch(`${API_URL}/conversations/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            });
            loadConversations();
        } catch (e) {
            console.error("Failed to rename conversation", e);
            alert("Erro ao renomear conversa.");
        }
    }
}

async function deleteConversation(id) {
    if (confirm("Tem certeza que deseja excluir esta conversa?")) {
        try {
            await fetch(`${API_URL}/conversations/${id}`, {
                method: 'DELETE'
            });
            if (currentConversationId === id) {
                startNewChat();
            } else {
                loadConversations();
            }
        } catch (e) {
            console.error("Failed to delete conversation", e);
            alert("Erro ao excluir conversa.");
        }
    }
}
