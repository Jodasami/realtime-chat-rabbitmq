/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mensajeria.service;

/**
 *
 * @author Raquel Sanabria R
 */
import com.mensajeria.Mensaje;
import com.rabbitmq.client.*;
import org.springframework.stereotype.Service;
import java.nio.charset.StandardCharsets;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import org.springframework.messaging.simp.SimpMessagingTemplate;

@Service
public class ChatService {
    
    private Channel channel;
    private Connection connection;
    
    // --------------------------------------------------------- PARAMETROS RABBITMQ ---------------------------------------------------------
    
    private final static String QUEUE_SEND = "java_to_python_queue";
    private final static String QUEUE_RECEIVE = "python_to_java_queue";
    
    // ---------------------------------------------------------------------------------------------------------------------------------------
    
    
    // --------------------------------------------------------- PARAMETROS SQL SERVER ---------------------------------------------------------
    
    private final String DB_URL = "jdbc:sqlserver://localhost:1433;databaseName=Chat_DB;encrypt=false;trustServerCertificate=true;";
    private final String DB_USER = "sa";
    private final String DB_PASS = "1234";
    
    // ---------------------------------------------------------------------------------------------------------------------------------------
    
    
    // --------------------------------------------------------- PARAMETRO WebSocket ---------------------------------------------------------
    
    private final SimpMessagingTemplate messagingTemplate;
    
    // ---------------------------------------------------------------------------------------------------------------------------------------
    

    public ChatService(SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
        try {
            ConnectionFactory factory = new ConnectionFactory();
            factory.setHost("localhost");

            this.connection = factory.newConnection();
            this.channel = connection.createChannel();

            // Declarar colas
            channel.queueDeclare(QUEUE_SEND, false, false, false, null);
            channel.queueDeclare(QUEUE_RECEIVE, false, false, false, null);

            // Este es el listener
            DeliverCallback deliverCallback = (consumerTag, delivery) -> {

                String msg = new String(delivery.getBody(), StandardCharsets.UTF_8);

                System.out.println("Mensaje recibido de PYTHON: " + msg);

                Mensaje mensaje = new Mensaje();
                mensaje.setSender("Python");
                mensaje.setReceiver("Java");
                mensaje.setMessage(msg);
                mensaje.setTimestamp(java.time.LocalDateTime.now());

                guardarMensaje(mensaje);
                
            };

            channel.basicConsume(QUEUE_RECEIVE, true, deliverCallback, consumerTag -> {});

        } catch (Exception e) {
            e.printStackTrace();
        }
                
    }

    public void enviarMensaje(Mensaje mensaje) {
    try {
        
        mensaje.setSender("Java");
        mensaje.setReceiver("Python");
        mensaje.setTimestamp(java.time.LocalDateTime.now());

        // Se comunica por la cola del RabbitMQ y envía el mensaje
        channel.basicPublish("", QUEUE_SEND, null, mensaje.getMessage().getBytes(StandardCharsets.UTF_8)
        );

        System.out.println("Mensaje enviado a PYTHON: " + mensaje.getMessage());

        guardarMensaje(mensaje);

    } catch (Exception e) {
        e.printStackTrace();
    }
    }
    

    private void guardarMensaje(Mensaje mensaje) {
    
// enviar a websocket
    messagingTemplate.convertAndSend("/topic/chat", mensaje);

    // guardar en SQL Server
    try (java.sql.Connection conn =
            DriverManager.getConnection(DB_URL, DB_USER, DB_PASS)) {

        String sql = """
            INSERT INTO messages (sender, receiver, message, timestamp)
            VALUES (?, ?, ?, ?)
        """;

        PreparedStatement stmt = conn.prepareStatement(sql);

        stmt.setString(1, mensaje.getSender());
        stmt.setString(2, mensaje.getReceiver());
        stmt.setString(3, mensaje.getMessage());
        stmt.setTimestamp(
                4,
                java.sql.Timestamp.valueOf(mensaje.getTimestamp())
        );

        stmt.executeUpdate();

    } catch (SQLException e) {
        e.printStackTrace();
    }
    }
    
    public List<Mensaje> obtenerHistorialSQL() {

        List<Mensaje> historial = new ArrayList<>();

        String sql = """
            SELECT id, sender, receiver, message, timestamp
            FROM messages
            ORDER BY id ASC
        """;

        try (java.sql.Connection conn =
             DriverManager.getConnection(DB_URL, DB_USER, DB_PASS);
             PreparedStatement stmt = conn.prepareStatement(sql);
             ResultSet rs = stmt.executeQuery()) {

            while (rs.next()) {

                Mensaje m = new Mensaje();

                m.setId(rs.getInt("id"));
                m.setSender(rs.getString("sender"));
                m.setReceiver(rs.getString("receiver"));
                m.setMessage(rs.getString("message"));

                java.sql.Timestamp ts = rs.getTimestamp("timestamp");
                if (ts != null)
                    m.setTimestamp(ts.toLocalDateTime());

                historial.add(m);
            }

        } catch (SQLException e) {
            e.printStackTrace();
        }

        return historial;
    }
}
