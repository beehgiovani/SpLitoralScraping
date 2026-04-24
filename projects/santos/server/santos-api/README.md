# Spring Boot API - MetroMarGeo Santos

Esta pasta contém o **Coração Comercial** (Backend) do seu sistema de dados. É aqui que os dados extraídos pelo robô Python são entregues para o mundo exterior.

## Por que Spring Boot?
O Spring Boot (Java) é o padrão ouro para **Sistemas Bancários e de Gestão de Dados**. Ele garante que sua API seja sempre rápida, segura e escalonável.

## Como funciona?
- **Controller**: O `ImovelController` gerencia as rotas (URLs) que o usuário acessa.
- **Model**: O `Imovel.java` define o contrato de dados. Ele lê o arquivo JSON e o transforma em um objeto Java pronto para ser pesquisado.

## Endpoints (Rotas da API)
Ao rodar este servidor localmente ou na nuvem, você teria acesso a:
- `GET /api/imoveis`: Listagem completa.
- `GET /api/imoveis/busca?nome=TANIA`: Filtro instantâneo por proprietário.

## Estrutura do Projeto
- `pom.xml`: Gerencia bibliotecas (Lombok, Jackson, Spring Web).
- `src/main/java/com/metromargeo`: O código-fonte Java profissionalmente organizado.

---
*Parte do Sistema Integrado MetroMarGeo*
