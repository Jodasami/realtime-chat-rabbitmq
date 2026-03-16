/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mensajeria.controllers;

import com.mensajeria.Mensaje;
import com.mensajeria.service.ChatService;
import java.util.List;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.bind.annotation.RestController;

/**
 *
 * @author Raquel Sanabria R
 */

@RestController
@RequestMapping("/api")
public class ChatRestController {
    
    @Autowired
    private ChatService chatService;
    
    @PostMapping("/enviar")
    @ResponseBody
    public String enviarMensaje(@RequestBody Mensaje mensaje) {
        
    chatService.enviarMensaje(mensaje);
    
    return "OK";
    }
    
    @GetMapping("/historial")
    public List<Mensaje> obtenerHistorial() {
        return chatService.obtenerHistorialSQL();
    }
    
}
