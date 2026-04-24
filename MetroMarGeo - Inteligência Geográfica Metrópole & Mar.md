# MetroMarGeo - Inteligência Geográfica Metrópole & Mar

Este repositório contém um conjunto de scripts Python desenvolvidos para a
extração de dados geográficos e cadastrais de cidades da Metrópole (São Paulo) e
do Litoral Paulista, com foco em informações de lotes, logradouros, zoneamento
e, quando possível, dados de proprietários e débitos através de portais de
tributos. O MetroMarGeo atua como um CRM Imobiliário Interativo, fornecendo uma
base de dados robusta para análise e gestão.

## **Objetivo**

O objetivo principal é fornecer uma base de dados abrangente e detalhada de
imóveis, utilizando endpoints públicos de geoprocessamento (GeoServer, WFS) e,
em uma segunda fase, enriquecer esses dados com informações tributárias através
da automação de consultas em portais municipais, incluindo a quebra de CAPTCHAs
visuais.

## **Estrutura do Projeto**

O projeto está organizado da seguinte forma:

- `ocr_module.py`: Módulo Python responsável pela quebra de CAPTCHAs visuais
  utilizando a biblioteca `ddddocr`.
- `01_guaruja_geometrus.py`: Extrator de dados de Guarujá (Geometrus).
- `02_santos_massa_total.py`: Extrator de dados de Santos (massa total).
- `03_geosampa_total.py`: Extrator de dados de São Paulo (GeoSampa).
- `04_santos_mapeada.py`: Extrator de dados de Santos (versão mapeada).
- `05_praia_grande_total_v2.py`: Extrator aprimorado de Praia Grande, incluindo
  zoneamento.
- `06_peruibe_total_v2.py`: Extrator aprimorado de Peruíbe, com cruzamento
  espacial para logradouros.
- `07_bertioga_total.py`: Extrator de dados de Bertioga via DataGeo.
- `08_bertioga_fase2_ocr.py`: Extrator de Bertioga (Fase 2) com OCR para dados
  de débitos/proprietários.
- `09_peruibe_fase2_ocr.py`: Extrator de Peruíbe (Fase 2) com OCR para Ficha
  Cadastral.

## **Requisitos**

Para executar os scripts, você precisará ter o Python 3.11 ou superior
instalado, juntamente com as seguintes bibliotecas:

- `requests`: Para fazer requisições HTTP.
- `pandas`: Para manipulação e exportação de dados em json.
- `ddddocr`: Para reconhecimento óptico de caracteres (OCR) em CAPTCHAs.
- `opencv-python-headless`: Dependência do `ddddocr` para processamento de
  imagem.
- `Pillow`: Dependência do `ddddocr` para manipulação de imagem.

## **Instalação**

Para instalar as dependências, execute o seguinte comando no seu terminal:

```bash
sudo pip3 install requests pandas ddddocr opencv-python-headless Pillow
```

## **Uso dos Extratores**

Cada script é independente e pode ser executado individualmente. Recomenda-se
criar um diretório de saída para cada cidade antes de executar o script.

### **Fase 1: Extração de Base (Geográfica)**

Estes scripts extraem dados diretamente de serviços WFS (Web Feature Service) ou
APIs de geoprocessamento, focando em informações espaciais e cadastrais básicas.

- **`01_guaruja_geometrus.py` - Guarujá (Geometrus)**
  - **Descrição:** Extrai dados de lotes e suas geometrias do GeoServer de
    Guarujá.
  - **Como Executar:** `python3.11 01_guaruja_geometrus.py`
  - **Saída:** `extracao_guaruja/DADOS_GUARUJA_GERAL.json`

- **`02_santos_massa_total.py` - Santos (Massa Total)**
  - **Descrição:** Extrai uma grande massa de dados de lotes de Santos.
  - **Como Executar:** `python3.11 02_santos_massa_total.py`
  - **Saída:** `extracao_santos/DADOS_SANTOS_GERAL.json`

- **`03_geosampa_total.py` - São Paulo (GeoSampa)**
  - **Descrição:** Extrai dados de lotes e logradouros do GeoSampa.
  - **Como Executar:** `python3.11 03_geosampa_total.py`
  - **Saída:** `extracao_geosampa/DADOS_GEOSAMPA_GERAL.json`

- **`04_santos_mapeada.py` - Santos (Mapeada)**
  - **Descrição:** Versão mapeada do extrator de Santos, com foco em campos
    específicos.
  - **Como Executar:** `python3.11 04_santos_mapeada.py`
  - **Saída:** `extracao_santos_mapeada/DADOS_SANTOS_MAPEADA.json`

- **`05_praia_grande_total_v2.py` - Praia Grande (Aprimorado)**
  - **Descrição:** Extrai dados de lotes, logradouros, áreas e zoneamento de
    Praia Grande.
  - **Como Executar:** `python3.11 05_praia_grande_total_v2.py`
  - **Saída:** `extracao_praia_grande_v2/DADOS_PRAIA_GRANDE_COMPLETO.json`

- **`06_peruibe_total_v2.py` - Peruíbe (Aprimorado)**
  - **Descrição:** Extrai dados de lotes e realiza cruzamento espacial para
    obter logradouros completos.
  - **Como Executar:** `python3.11 06_peruibe_total_v2.py`
  - **Saída:** `extracao_peruibe_v2/DADOS_PERUIBE_COMPLETO.json`

- **`07_bertioga_total.py` - Bertioga (DataGeo)**
  - **Descrição:** Extrai dados geográficos de Bertioga e Riviera de São
    Lourenço via DataGeo (servidor estadual).
  - **Como Executar:** `python3.11 07_bertioga_total.py`
  - **Saída:** `extracao_bertioga/DADOS_BERTIOGA_GERAL.json`

### **Fase 2: Enriquecimento de Dados (Tributário com OCR)**

Estes scripts utilizam o módulo `ocr_module.py` para interagir com portais de
tributos que exigem CAPTCHA, buscando informações mais detalhadas como nomes de
proprietários, CPF/CNPJ (se disponível) e situação de débitos.

- **`08_bertioga_fase2_ocr.py` - Bertioga (Débitos e Proprietários)**
  - **Descrição:** Utiliza o OCR para consultar o portal de débitos de Bertioga
    e extrair informações de proprietários e situação fiscal por inscrição
    imobiliária.
  - **Como Executar:** `python3.11 08_bertioga_fase2_ocr.py`
  - **Saída:** `extracao_bertioga_fase2/DADOS_BERTIOGA_ENRIQUECIDOS.json`
  - **Observação:** Requer um arquivo json de entrada com as inscrições
    imobiliárias (gerado pela Fase 1).

- **`09_peruibe_fase2_ocr.py` - Peruíbe (Ficha Cadastral)**
  - **Descrição:** Utiliza o OCR para consultar a Ficha Cadastral de Peruíbe e
    extrair dados de proprietários e detalhes do imóvel.
  - **Como Executar:** `python3.11 09_peruibe_fase2_ocr.py`
  - **Saída:** `extracao_peruibe_fase2/DADOS_PERUIBE_ENRIQUECIDOS.json`
  - **Observação:** Requer um arquivo json de entrada com as inscrições
    imobiliárias (gerado pela Fase 1).

## **Módulo OCR (`ocr_module.py`)**

Este módulo é a chave para automatizar a interação com portais que utilizam
CAPTCHAs visuais. Ele é importado pelos scripts da Fase 2 e funciona da seguinte
forma:

1. **Download da Imagem:** O script baixa a imagem do CAPTCHA do portal.
2. **Processamento OCR:** A imagem é passada para o `ddddocr`, que a analisa e
   retorna o texto reconhecido.
3. **Envio da Solução:** O texto do CAPTCHA é então enviado de volta ao portal
   para validar a requisição.

## **Considerações Importantes**

- **Formato das Inscrições:** A inscrição imobiliária pode ter formatos
  diferentes entre os dados geográficos (GeoServer) e os portais de tributos. Os
  scripts da Fase 2 tentam padronizar, mas pode ser necessário ajustar a máscara
  de entrada conforme a cidade.
- **Limitações:** Alguns portais podem exigir login via Gov.br ou apresentar
  CAPTCHAs mais complexos que o `ddddocr` não consiga resolver com 100% de
  precisão. A instabilidade de servidores municipais também pode afetar a
  extração.
- **Extração em Massa:** Para extrair todos os registros, ajuste a variável
  `limit` dentro de cada script para um valor maior (ex: `limit = 1000000`).
- **Legalidade:** Certifique-se de que a extração e o uso dos dados estejam em
  conformidade com as leis locais e políticas de privacidade dos portais.

## **Próximos Passos (Sugestões)**

- **Novas Cidades:** Explorar e desenvolver extratores para outras cidades do
  litoral (Itanhaém, Mongaguá, São Vicente, Caraguatatuba, Ubatuba).
- **Monitoramento:** Implementar um sistema de monitoramento para verificar a
  disponibilidade dos endpoints e a validade dos CAPTCHAs.
- **Interface:** Desenvolver uma interface gráfica (GUI) para facilitar a
  execução e visualização dos dados.

---

**Desenvolvido por:** Manus AI **Data:** 05 de Abril de 2026
