/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mensajeria;

/**
 *
 * @author Raquel Sanabria R
 */
import com.mensajeria.service.ChatService;
import java.sql.DriverManager;
import java.sql.SQLException;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = "com.mensajeria")
public class AppMensajeria {

    public static void main(String[] args) throws Exception {
        ConfigurableApplicationContext context = SpringApplication.run(AppMensajeria.class, args);
        ChatService chatService = context.getBean(ChatService.class);
    }
}