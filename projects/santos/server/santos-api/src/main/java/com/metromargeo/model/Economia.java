package com.metromargeo.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.persistence.*;
import lombok.Data;

/**
 * [FILHO DO IMÓVEL]: Esta classe representa uma unidade individual no Banco de Dados.
 */
@Data
@Entity // Avisa ao Spring: "Crie uma tabela chamada 'economia' para esta classe"
@Table(name = "economias")
@JsonIgnoreProperties(ignoreUnknown = true)
public class Economia {

    @Id // Define que este campo é a Chave Primária (o ID único)
    @JsonProperty("lote_completo_11")
    private String loteCompleto;
    
    private String proprietario;
    
    @JsonProperty("cpf_cnpj")
    private String cpfCnpj;
    
    @JsonProperty("apto_sala")
    private String aptoSala;
    
    @JsonProperty("valor_venal_total")
    private String valorVenalTotal;

    // --- RELACIONAMENTO JPA ---
    // Muitas economias pertencem a UM ÚNICO imóvel pai (prédio)
    @ManyToOne 
    @JoinColumn(name = "imovel_lote") // Nome da coluna que liga as duas tabelas
    @JsonIgnore // Evita que o JSON entre em loop infinito ao carregar
    private Imovel imovel;
}
