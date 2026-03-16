/* 
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Other/javascript.js to edit this template
 */

let stompClient = null;
let ultimoMensajeLocal = null;

window.onload = function () {
    conectarWebSocket();// Se conecta al websocket
    cargarHistorial(); // Carga los mensajes desde la bd
};

function conectarWebSocket() {

    const socket = new SockJS('/chat');
    stompClient = Stomp.over(socket);

    stompClient.connect({}, function () {

        console.log("Conectado al WebSocket");

        // Escuchar mensajes del servidor
        stompClient.subscribe('/topic/chat', function (mensaje) {
                const sms = JSON.parse(mensaje.body);
                console.log("Mensaje recibido:", sms);
                mostrarMensaje(sms);
        });

    });
}

async function enviar() {

    let texto = document.getElementById("mensaje").value;
    if (!texto) return;

    ultimoMensajeLocal = texto;
    crearBurbuja("Tú", texto, new Date());

    await fetch("/api/enviar", {
        method: "POST",
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: texto })
    });

    document.getElementById("mensaje").value = "";
}


function mostrarMensaje(mensaje) {

    if (!mensaje) return;

    // evitar duplicado del propio mensaje
    if (mensaje.sender === "Java" &&
        mensaje.message === ultimoMensajeLocal) {
        ultimoMensajeLocal = null;
        return;
    }

    const sender =
        mensaje.sender === "Java" ? "Tú" : "Python";

    const texto = mensaje.message;

    const fecha = mensaje.timestamp
        ? new Date(mensaje.timestamp)
        : new Date();

    crearBurbuja(sender, texto, fecha);

}

function crearBurbuja(sender, texto, fecha) {

    const chat = document.getElementById("chat");

    const hora = fecha.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit'
    });

    const div = document.createElement("div");
    div.classList.add("message");
    div.classList.add(sender === "Tú" ? "you" : "python");

    div.innerHTML = `
        <div class="message-header">
            <span>${sender}</span>
            <span>${hora}</span>
        </div>
        <div class="message-body">${texto}</div>
    `;

    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

async function cargarHistorial() {

    let res = await fetch("/api/historial");
    let mensajes = await res.json();

    const chat = document.getElementById("chat");
    chat.innerHTML = "";

    mensajes.forEach(m => mostrarMensaje(m));
}

document.getElementById("mensaje") // Esto es para el "Enter"
    .addEventListener("keypress", function(e) {
        if (e.key === "Enter") {
            enviar();
        }
});
