Para Poder ejecutar el programa se deben cambiar las siguientes líneas de código por credenciales de SQLServer:

Clase: ChatService.java

 // ---------------------------------------------------- PARAMETROS SQL ERVER ---------------------------------------------------------
    
    private final String DB_URL = "jdbc:sqlserver://localhost:1433;databaseName=Chat_DB;encrypt=false;trustServerCertificate=true;";
    private final String DB_USER = "sa";
    private final String DB_PASS = "SQL2019";
    
    // ---------------------------------------------------------------------------------------------------------------------------------------
    
Adicionalmente es necesario tener instalado el servicio de RabbitMQ.

Se recomienda utilizar JDK 21 o mas.