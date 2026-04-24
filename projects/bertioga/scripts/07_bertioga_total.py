import requests
import ddddocr
from bs4 import BeautifulSoup
import urllib3
import os
import json
import time

# Desativa avisos de conexões inseguras
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BertiogaExtractor:
    """
    Extrator para a Prefeitura de Bertioga (Sistema SMARAPD) com saída formatada.
    """
    def __init__(self):
        self.base_url = "https://sistemas-smarapd.bertioga.sp.gov.br"
        self.session = requests.Session()
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        })

    def solve_captcha(self):
        """Baixa e resolve a imagem do CAPTCHA."""
        captcha_url = f"{self.base_url}/tbw/getCaptcha.jpg"
        try:
            r = self.session.get(f"{captcha_url}?{int(time.time()*1000)}", verify=False, timeout=15)
            if r.status_code == 200:
                return self.ocr.classification(r.content)
        except Exception as e:
            print(f"[-] Erro ao resolver captcha: {e}")
        return None

    def query_imovel(self, inscricao):
        """Realiza a consulta do imóvel usando a inscrição imobiliária."""
        print(f"[*] Consultando imóvel: {inscricao}")
        
        init_url = f"{self.base_url}/tbw/loginWeb.jsp?execobj=i20ServicosWebPesqImovel"
        try:
            r = self.session.get(init_url, verify=False, timeout=20)
            soup = BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            print(f"[-] Erro de conexão: {e}")
            return None

        form_data = {}
        for input_tag in soup.find_all("input"):
            name = input_tag.get("name")
            value = input_tag.get("value", "")
            if name:
                form_data[name] = value

        captcha_text = self.solve_captcha()
        if not captcha_text:
            return None
        print(f"[+] Captcha resolvido: {captcha_text}")

        form_data.update({
            "i20inscricao": inscricao,
            "i20captchafield": captcha_text,
            "cmd": "finalizar",
            "parametros": "execObj,I05PesquisaDebitoWEB"
        })

        post_url = f"{self.base_url}/tbw/servlet/controle"
        
        try:
            self.session.headers.update({"Referer": init_url})
            r = self.session.post(post_url, data=form_data, verify=False, timeout=30)
            
            if "Captcha incorreto" in r.text:
                print("[-] Captcha incorreto, tentando novamente...")
                return self.query_imovel(inscricao)
            
            if "Ocorreu um erro inesperado" in r.text and "não encontrado" in r.text.lower():
                print(f"[-] Imóvel {inscricao} não encontrado.")
                return None

            return self.parse_results(r.text, inscricao)

        except Exception as e:
            print(f"[-] Erro durante a requisição: {e}")
        return None

    def parse_results(self, html, inscricao):
        """Analisa o HTML e retorna os dados no formato solicitado pelo usuário."""
        soup = BeautifulSoup(html, "html.parser")
        
        # Mapeamento interno para facilitar a busca
        extracted_data = {}
        labels_map = {
            "Proprietário": "proprietario",
            "Endereço": "logradouro",
            "Bairro": "bairro",
            "Cidade": "cidade",
            "CEP": "cep",
            "Área Terreno": "area_terreno",
            "Área Construída": "area_construida",
            "Valor Venal": "valor_venal_total"
        }

        for span in soup.find_all(["span", "td", "label"]):
            txt = span.get_text(strip=True)
            for label, key in labels_map.items():
                if label in txt:
                    nxt = span.find_next(["span", "td"])
                    if nxt and nxt.get_text(strip=True) != txt:
                        extracted_data[key] = nxt.get_text(strip=True)

        # Formatação para o JSON final solicitado
        # O campo 'lote' costuma ser a inscrição sem pontos/traços
        lote_clean = inscricao.replace(".", "").replace("-", "")
        
        # Estrutura base solicitada
        result = {
            "lote": lote_clean,
            "idlog": None,
            "logradouro": extracted_data.get("logradouro", ""),
            "numero": None, # Geralmente precisa de um split do logradouro se vier junto
            "bairro": extracted_data.get("bairro", ""),
            "idtnp": 0,
            "nivelprotecao": "",
            "idacabamento": None,
            "dlacabamento": None,
            "idbai": None,
            "idutilizacao": None,
            "dlutilizacao": None,
            "stsantoscriativa": None,
            "stusomisto": 0,
            "id_unico": f"bertioga.{lote_clean}",
            "coord_x": None,
            "coord_y": None,
            "economias": [
                {
                    "lote_completo_11": lote_clean[:11] if len(lote_clean) >= 11 else lote_clean,
                    "proprietario": extracted_data.get("proprietario"),
                    "cpf_cnpj": None, # SMARAPD raramente mostra CPF/CNPJ completo por LGPD
                    "complemento": None,
                    "apto_sala": None,
                    "valor_venal_total": extracted_data.get("valor_venal_total"),
                    "valor_venal_construcao": None,
                    "valor_venal_terreno": extracted_data.get("area_terreno")
                }
            ]
        }

        # Tentar extrair número do logradouro se estiver no formato "Rua X, 123"
        if "," in result["logradouro"]:
            parts = result["logradouro"].split(",")
            result["logradouro"] = parts[0].strip()
            num_part = parts[1].strip().split(" ")[0]
            if num_part.isdigit():
                result["numero"] = int(num_part)

        return result

if __name__ == "__main__":
    extractor = BertiogaExtractor()
    
    # Exemplo de teste
    test_inscricao = "01.01.001.0001.001"
    result = extractor.query_imovel(test_inscricao)
    
    if result:
        print("\n[+] Resultado Formatado:")
        print(json.dumps(result, indent=4, ensure_ascii=False))
        
        # Salva o resultado
        output_dir = "data/extracao_bertioga"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"bertioga_formatado_{test_inscricao.replace('.', '_')}.json"
        with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        print(f"\n[+] Dados salvos em {os.path.join(output_dir, filename)}")