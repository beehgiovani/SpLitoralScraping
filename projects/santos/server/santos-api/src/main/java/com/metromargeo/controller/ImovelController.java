package com.metromargeo.controller;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.metromargeo.model.Imovel;
import com.metromargeo.service.ImovelService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.stream.Collectors;

/**
 * [O PORTEIRO DA API]: Agora o porteiro gerencia tanto o arquivo JSON quanto o Banco de Dados.
 */
@RestController
@RequestMapping("/api/imoveis")
public class ImovelController {

    @Autowired // Pedimos ao Spring o serviço de Banco de Dados que criamos
    private ImovelService imovelService;

    private final String JSON_PATH = "../../data/output/dados_santos_enriquecido.json";
    private final ObjectMapper objectMapper = new ObjectMapper();

    // --- ROTA 1: BUSCA TRADICIONAL (VIA ARQUIVO JSON) ---
    @GetMapping("/json/busca")
    public List<Map<String, Object>> buscarNoJson(@RequestParam(required = false, defaultValue = "") String nome) {
        try {
            File file = new File(JSON_PATH);
            if (!file.exists()) return Collections.emptyList();
            
            // Tenta ler o arquivo. Se o robô Python estiver salvando agora, pode dar erro.
            List<Imovel> todos = objectMapper.readValue(file, new TypeReference<List<Imovel>>() {});
            return achatarResultados(todos, nome.toUpperCase());
            
        } catch (IOException e) {
            // Se o arquivo estiver travado pelo robô, avisamos ao invés de dar erro 500
            Map<String, Object> erro = new LinkedHashMap<>();
            erro.put("aviso", "O robô Python está salvando dados no arquivo agora. Tente de novo em 5 segundos!");
            return List.of(erro);
        }
    }

    // --- ROTA 2: SINCRONIZAR (MANDA DO JSON PARA O BANCO) ---
    @GetMapping("/sync")
    public String sincronizar() throws IOException {
        // Esta função pega os dados do robô Python e injeta no JPA
        return imovelService.sincronizarJsonComBanco();
    }

    // --- ROTA 3: BUSCA MODERNA (VIA BANCO DE DATA JPA) ---
    @GetMapping("/db/busca")
    public List<Map<String, Object>> buscarNoBanco(@RequestParam(required = false, defaultValue = "") String nome) {
        // Aqui, o Spring busca direto nas tabelas do H2, sem ler arquivos!
        List<Imovel> doBanco = imovelService.listarTodosDoBanco();
        return achatarResultados(doBanco, nome.toUpperCase());
    }

    /**
     * FUNÇÃO AUXILIAR: Transforma a árvore (Imovel > Unidades) em uma lista 
     * simplificada de unidades individuais para facilitar a leitura no navegador.
     */
    private List<Map<String, Object>> achatarResultados(List<Imovel> lista, String nomeBusca) {
        return lista.stream()
                // Verificação de segurança: Ignora prédios que não tem 'economias' (unidades)
                .filter(predio -> predio.getEconomias() != null)
                .flatMap(predio -> predio.getEconomias().stream()
                        .filter(u -> u.getProprietario() != null && u.getProprietario().contains(nomeBusca))
                        .map(u -> {
                            Map<String, Object> map = new LinkedHashMap<>();
                            map.put("logradouro", predio.getLogradouro());
                            map.put("numero", predio.getNumero());
                            map.put("bairro", predio.getBairro());
                            map.put("unidade", u.getLoteCompleto());
                            map.put("dono", u.getProprietario());
                            map.put("cpf", u.getCpfCnpj());
                            return map;
                        }))
                .collect(Collectors.toList());
    }
}
