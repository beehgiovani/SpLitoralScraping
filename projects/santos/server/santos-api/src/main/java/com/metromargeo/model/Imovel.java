package com.metromargeo.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.persistence.*;
import lombok.Data;
import java.util.List;

/**
 * [PAI DO LOTE]: Esta classe se conecta com a tabela de Prédios no Banco de Dados.
 */
@Data
@Entity // Avisa ao Spring: "Crie uma tabela chamada 'imoveis' para esta classe"
@Table(name = "imoveis")
@JsonIgnoreProperties(ignoreUnknown = true)
public class Imovel {

    @Id // O Lote (Número) é a nossa Chave Primária
    private String lote;
    
    private String logradouro;
    private String numero;
    private String bairro;
    
    // --- MÁGICA DO JPA: RELACIONAMENTO ---
    // Um Prédio tem MUITOS (@OneToMany) apartamentos (economias).
    // O 'CascadeAll' faz com que, ao cadastrar um prédio, o banco já salve todos os vizinhos.
    @OneToMany(mappedBy = "imovel", cascade = CascadeType.ALL, fetch = FetchType.EAGER)
    @JsonProperty("economias")
    private List<Economia> economias;
}
