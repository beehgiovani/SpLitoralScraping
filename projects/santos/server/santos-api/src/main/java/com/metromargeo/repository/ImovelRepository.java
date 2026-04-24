package com.metromargeo.repository;

import com.metromargeo.model.Imovel;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * [MÁGICA DO REPOSITORY]: Esta interface ensina ao Spring como conversar com o banco H2.
 * O 'JpaRepository' já vem com todos os comandos prontos para a gente usar (CRUD).
 */
@Repository // Avisa ao Spring: "Gerencie este serviço de Banco de Dados para mim"
public interface ImovelRepository extends JpaRepository<Imovel, String> {
    // Aqui, podemos adicionar buscas personalizadas se precisarmos amanhã!
}
