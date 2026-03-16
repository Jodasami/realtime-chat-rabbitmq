# Realtime Chat System with RabbitMQ

Sistema de mensajería en tiempo real utilizando RabbitMQ para la comunicación entre servicios.

El sistema implementa un modelo de mensajería distribuida donde múltiples servicios se comunican mediante colas de mensajes.

Este proyecto fue desarrollado como parte de un proyecto académico.

---

## Tecnologías utilizadas

Backend
- Java
- Python

Mensajería
- RabbitMQ

Base de datos
- PostgreSQL

Otros
- WebSockets

---

## Características principales

- Chat en tiempo real
- Comunicación entre servicios mediante colas de mensajes
- Arquitectura distribuida
- Persistencia de mensajes en base de datos
- Comunicación asíncrona mediante RabbitMQ

---

## Arquitectura del sistema


Cliente → WebSocket → Chat Service
Chat Service → RabbitMQ → Message Processor
Message Processor → PostgreSQL


---

## Nota

Proyecto desarrollado como parte de formación académica en Ingeniería en Sistemas.

---
