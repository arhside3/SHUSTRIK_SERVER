let ws;
let monitorWs;
let isMonitoring = false;

function connect() {
    ws = new WebSocket("ws://localhost:8765");
    ws.onopen = () => {
        console.log("WebSocket подключен");
        fetchCards();
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log("Received:", data);
            
            if (data.command === "list_cards" && data.status === "success") {
                updateTable(data.cards);
            } else if (data.command === "upload_image") {
                document.getElementById('uploadStatus').innerHTML = 
                    `<p style="color: ${data.status === 'success' ? 'green' : 'red'}">${data.message}</p>`;
                if (data.status === 'success') {
                    fetchCards();
                    document.getElementById('uploadForm').reset();
                }
            } else if (data.type === "card_scanned") {
                displayCurrentCard(data);
            } else if (data.status === "error") {
                console.error("Ошибка от сервера:", data.message);
            }
        } catch (e) {
            console.error("Ошибка парсинга JSON:", e);
        }
    };

    ws.onclose = () => {
        console.log("WebSocket закрыт, переподключение через 3 секунды");
        setTimeout(connect, 3000);
    };

    ws.onerror = (error) => {
        console.error("WebSocket ошибка:", error);
    };
}

function connectMonitor() {
    monitorWs = new WebSocket("ws://localhost:8765");
    
    monitorWs.onopen = () => {
        console.log("Monitor WebSocket подключен");
        document.getElementById('monitorStatus').textContent = 'Подключен';
        document.getElementById('monitorStatus').className = 'status-connected';
        document.getElementById('startMonitor').disabled = true;
        document.getElementById('stopMonitor').disabled = false;
        isMonitoring = true;
        
        monitorWs.send(JSON.stringify({
            command: "start_serial_monitor"
        }));
    };
    
    monitorWs.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === "serial_data") {
                addMonitorMessage(data.message, data.direction, data.timestamp);
                
                if (data.direction === "incoming" && data.message.includes('cardData')) {
                    processCardDataMessage(data.message);
                }
            } else if (data.type === "card_scanned") {
                displayCurrentCard(data);
            } else if (data.status === "error") {
                console.error("Ошибка в мониторе:", data.message);
            }
        } catch (e) {
            console.error("Ошибка парсинга данных монитора:", e);
        }
    };
    
    monitorWs.onclose = () => {
        console.log("Monitor WebSocket закрыт");
        if (isMonitoring) {
            document.getElementById('monitorStatus').textContent = 'Переподключение...';
            document.getElementById('monitorStatus').className = 'status-connecting';
            setTimeout(connectMonitor, 3000);
        }
    };
    
    monitorWs.onerror = (error) => {
        console.error("Monitor WebSocket ошибка:", error);
    };
}

function processCardDataMessage(message) {
    try {
        const data = JSON.parse(message);
        if (data.type === "cardData" && data.cardUID) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    command: "get_card_details_by_uid",
                    uid: data.cardUID
                }));
            }
        }
    } catch (e) {
        console.error("Ошибка обработки данных карты:", e);
    }
}

function displayCurrentCard(data) {
    const display = document.getElementById('currentCardDisplay');
    const imageContainer = document.getElementById('currentCardImage');
    const cardType = document.getElementById('currentCardType');
    const cardUid = document.getElementById('currentCardUid');
    const cardAccess = document.getElementById('currentCardAccess');
    const cardTime = document.getElementById('currentCardTime');
    
    cardType.textContent = data.cardType || 'UNKNOWN';
    cardUid.textContent = data.cardUID || '-';
    cardAccess.textContent = data.accessGranted ? 'Разрешён' : 'Запрещён';
    cardAccess.className = data.accessGranted ? 'access-granted' : 'access-denied';
    cardTime.textContent = new Date().toLocaleTimeString();
    
    if (data.hasImage && data.imageUrl) {
        imageContainer.innerHTML = `<img src="${data.imageUrl}" alt="Изображение карты" />`;
    } else {
        imageContainer.innerHTML = '<div class="no-image">Нет изображения</div>';
    }
    
    display.style.display = 'block';
    
    setTimeout(() => {
        display.style.display = 'none';
    }, 10000);
}

function addMonitorMessage(message, direction, timestamp) {
    const messagesContainer = document.getElementById('monitorMessages');
    const messageElement = document.createElement('div');
    messageElement.className = `monitor-message ${direction}`;
    
    const time = new Date(timestamp).toLocaleTimeString();
    const directionText = direction === 'incoming' ? '← ВХОДЯЩЕЕ' : '→ ИСХОДЯЩЕЕ';
    
    messageElement.innerHTML = `
        <span class="message-time">[${time}]</span>
        <span class="message-direction">${directionText}:</span>
        <span class="message-content">${message}</span>
    `;
    
    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function startMonitor() {
    connectMonitor();
}

function stopMonitor() {
    isMonitoring = false;
    if (monitorWs) {
        monitorWs.close();
    }
    document.getElementById('monitorStatus').textContent = 'Отключен';
    document.getElementById('monitorStatus').className = 'status-disconnected';
    document.getElementById('startMonitor').disabled = false;
    document.getElementById('stopMonitor').disabled = true;
}

function clearMonitor() {
    document.getElementById('monitorMessages').innerHTML = '';
}

function fetchCards() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ command: "list_cards" }));
    } else {
        console.error("WebSocket не подключен");
        setTimeout(connect, 1000);
    }
}

function updateTable(cards) {
    const tbody = document.querySelector("#cardsTable tbody");
    tbody.innerHTML = "";

    if (cards.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Нет карт в базе данных</td></tr>';
        return;
    }

    cards.forEach((card, idx) => {
        const tr = document.createElement("tr");
        
        const hasImage = card.image_filename || card.has_image;
        const imageCell = hasImage ? 
            `<img src="http://localhost:8080/media/${card.image_filename}" class="thumbnail" alt="Card image">` : 
            'Нет изображения';
        
        tr.innerHTML = `
            <td>${idx + 1}</td>
            <td>${card.card_type}</td>
            <td>${card.uid}</td>
            <td>${card.date_added}</td>
            <td>${imageCell}</td>
            <td>
                <button class="action-btn view-btn" onclick="viewCardDetails('${card.card_type}', '${card.uid}')">
                    Просмотр
                </button>
                <button class="action-btn upload-btn" onclick="quickUpload('${card.card_type}', '${card.uid}')">
                    Загрузить фото
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

document.getElementById('uploadForm').addEventListener('submit', function(e) {
    e.preventDefault();

    const cardType = document.getElementById('uploadCardType').value.trim();
    const uid = document.getElementById('uploadUid').value.trim();
    const fileInput = document.getElementById('imageFile');

    if (!cardType || !uid) {
        alert('Пожалуйста, заполните тип карты и UID');
        return;
    }

    if (!fileInput.files[0]) {
        alert('Пожалуйста, выберите файл');
        return;
    }

    const file = fileInput.files[0];
    const reader = new FileReader();

    reader.onload = function(e) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            document.getElementById('uploadStatus').innerHTML = '<p>Загрузка...</p>';
            
            const uploadData = {
                command: "upload_image",
                card_type: cardType,
                uid: uid,
                image_data: e.target.result,
                filename: file.name
            };
            console.log("Sending upload command:", uploadData);
            ws.send(JSON.stringify(uploadData));
        } else {
            alert('WebSocket не подключен. Попробуйте обновить страницу.');
            console.error("WebSocket не подключен, состояние:", ws?.readyState);
        }
    };

    reader.onerror = function() {
        alert('Ошибка чтения файла');
    };

    reader.readAsDataURL(file);
});

function quickUpload(cardType, uid) {
    document.getElementById('uploadCardType').value = cardType;
    document.getElementById('uploadUid').value = uid;
    document.getElementById('imageFile').focus();
}

function viewCardDetails(cardType, uid) {
    window.open(`card-viewer.html?card_type=${encodeURIComponent(cardType)}&uid=${encodeURIComponent(uid)}`, '_blank');
}

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('startMonitor').addEventListener('click', startMonitor);
    document.getElementById('stopMonitor').addEventListener('click', stopMonitor);
    document.getElementById('clearMonitor').addEventListener('click', clearMonitor);
    
    setTimeout(startMonitor, 1000);
});

connect();