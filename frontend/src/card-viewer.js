const urlParams = new URLSearchParams(window.location.search);
const cardType = urlParams.get('card_type');
const uid = urlParams.get('uid');

let ws;

function connect() {
ws = new WebSocket("ws://localhost:8765");

ws.onopen = () => {
    console.log("WebSocket подключен");
    loadCardDetails();
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("Received:", data);
    
    if (data.command === "get_card_details" && data.status === "success") {
    displayCardDetails(data.card);
    } else if (data.command === "get_card_details" && data.status === "error") {
    document.getElementById('imageContainer').innerHTML = 
        '<div class="no-image">Ошибка загрузки данных карты</div>';
    }
};

ws.onclose = () => {
    console.log("WebSocket закрыт, переподключение через 3 секунды");
    setTimeout(connect, 3000);
};
}

function loadCardDetails() {
if (ws && ws.readyState === WebSocket.OPEN && cardType && uid) {
    ws.send(JSON.stringify({
    command: "get_card_details",
    card_type: cardType,
    uid: uid
    }));
}
}

function displayCardDetails(card) {
document.getElementById('infoCardType').textContent = card.card_type;
document.getElementById('infoUid').textContent = `[${card.uid.join(', ')}]`;
document.getElementById('infoDateAdded').textContent = card.date_added;
document.getElementById('infoDateUploaded').textContent = card.date_uploaded || 'Не загружено';

const imageContainer = document.getElementById('imageContainer');

if (card.has_image && card.image_filename) {
    imageContainer.innerHTML = `
    <img src="http://localhost:8080/media/${card.image_filename}" 
            alt="Изображение карты ${card.card_type}" 
            class="card-image">
    <p><small>Файл: ${card.image_filename}</small></p>
    `;
} else {
    imageContainer.innerHTML = '<div class="no-image">Для этой карты нет изображения</div>';
}
}

function goBack() {
window.close();
}

if (cardType && uid) {
connect();
} else {
document.getElementById('imageContainer').innerHTML = 
    '<div class="no-image">Не указаны параметры карты</div>';
}