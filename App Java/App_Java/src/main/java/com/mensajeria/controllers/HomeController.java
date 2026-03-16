/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mensajeria.controllers;

/**
 *
 * @author Raquel Sanabria R
 */

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.*;

@Controller
public class HomeController {


    // Muestra la página principal
    @GetMapping("/")
    public String inicio() {
        return "index";
    }

}
