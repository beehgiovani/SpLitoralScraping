package com.metromargeo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * [O PONTO DE PARTIDA]: Esta é a classe que "liga" todo o motor da sua API.
 * Sem ela, o Java não saberia por onde começar.
 */
@SpringBootApplication // Este comando faz o Spring configurar o servidor Tomcat e as rotas automaticamente.
public class MetromargeoApiApplication {
    public static void main(String[] args) {
        // Inicializa o Java, configura as conexões e abre a porta 8080 para o seu navegador.
        SpringApplication.run(MetromargeoApiApplication.class, args);
    }
}
