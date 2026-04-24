package com.metromargeo.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.metromargeo.model.Imovel;
import com.metromargeo.repository.ImovelRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;
import java.util.List;

/**
 * [O MESTRE DE OBRAS]: Esta classe cuida da LÓGICA do sistema. 
 * Ela lê o arquivo JSON e manda salvar tudo no Banco de Dados JPA de uma vez só!
 */
@Service // Avisa ao Spring: "Isto aqui é um Serviço Profissional que gerencia dados"
public class ImovelService {

    @Autowired // MÁGICA GFT: Pedimos ao Spring para "Injetar" (entregar pronta) a conexão com o Banco
    private ImovelRepository imovelRepository;

    private final String JSON_PATH = "../../data/output/dados_santos_enriquecido.json";
    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * FUNÇÃO DE SINCRONIA: Lê o seu arquivo do robô Python e injeta no Banco de Dados.
     */
    public String sincronizarJsonComBanco() throws IOException {
        File file = new File(JSON_PATH);
        if (!file.exists()) return "Erro: O arquivo JSON do Robô não foi encontrado ainda!";

        // 1. Lê a lista gigante de imóveis da memória do JSON
        List<Imovel> listaLida = objectMapper.readValue(file, new TypeReference<List<Imovel>>() {});

        // 2. Antes de salvar, ensinamos cada 'Economia' (Filho) quem é o seu 'Imovel' (Pai)
        for (Imovel imovel : listaLida) {
            if (imovel.getEconomias() != null) {
                imovel.getEconomias().forEach(economia -> economia.setImovel(imovel));
            }
        }

        // 3. COMANDO MÁGICO DO JPA: Salva tudo no banco H2 (ou PostgreSQL se configurado)
        imovelRepository.saveAll(listaLida);

        return "Sucesso! Foram importados " + listaLida.size() + " prédios para o Banco de Dados JPA!";
    }

    /**
     * BUSCA NO BANCO: Recupera todos os dados direto do Banco de Dados (mais rápido que o JSON).
     */
    public List<Imovel> listarTodosDoBanco() {
        return imovelRepository.findAll();
    }
}
