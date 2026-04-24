# MetroMarGeo - Inteligência Geográfica Metrópole & Mar
import requests
import pandas as pd
import ddddocr
import urllib3
from bs4 import BeautifulSoup
import os
import time
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BertiogaFase2Extractor:
    def __init__(self):
        self.base_url = "https://sistemas-smarapd.bertioga.sp.gov.br"
        self.session = requests.Session()
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def solve_captcha(self):
        captcha_url = f"{self.base_url}/tbw/getCaptcha.jpg"
        try:
            r = self.session.get(captcha_url, verify=False, timeout=20)
            if r.status_code == 200:
                return self.ocr.classification(r.content)
        except: pass
        return None

    def query_imovel(self, inscricao):
        # 1. Acessar a página inicial para pegar cookies
        init_url = f"{self.base_url}/tbw/loginWeb.jsp?execobj=i20ServicosWebPesqImovel"
        self.session.get(init_url, verify=False)
        
        # 2. Resolver captcha
        captcha_text = self.solve_captcha()
        if not captcha_text: return None
        
        # 3. Enviar a consulta
        # O SMARAPD costuma usar um fluxo de POST que redireciona para o resultado
        data = {
            "i20inscricao": inscricao,
            "i20captchafield": captcha_text,
            "i20btnConsultar": "Consultar"
        }
        
        try:
            r = self.session.post(init_url, data=data, verify=False, timeout=30)
            if r.status_code == 200:
                if "Captcha incorreto" in r.text:
                    return self.query_imovel(inscricao)
                
                # Se o resultado não estiver no HTML, pode ser que precise de um GET subsequente
                # Vamos procurar por redirecionamentos ou mensagens de erro
                if "Proprietário" not in r.text:
                    # Tentar acessar a página de débitos diretamente se o POST foi bem sucedido
                    debitos_url = f"{self.base_url}/tbw/loginWeb.jsp?execobj=i20ServicosWebPesqDebitosImovel"
                    r_deb = self.session.get(debitos_url, verify=False)
                    soup = BeautifulSoup(r_deb.text, 'html.parser')
                else:
                    soup = BeautifulSoup(r.text, 'html.parser')
                
                dados = {"inscricao": inscricao, "proprietario": "Não encontrado", "debitos": "Não encontrado"}
                
                # Mapeamento de campos no SMARAPD
                # Procurar por spans ou tds que contenham os dados
                for span in soup.find_all(['span', 'td', 'label']):
                    txt = span.text.strip()
                    if 'Proprietário' in txt:
                        # Tentar pegar o próximo elemento
                        nxt = span.find_next(['span', 'td'])
                        if nxt: dados["proprietario"] = nxt.text.strip()
                    elif 'Total de Débitos' in txt:
                        nxt = span.find_next(['span', 'td'])
                        if nxt: dados["debitos"] = nxt.text.strip()
                
                return dados
        except Exception as e:
            print(f"Erro na consulta: {e}")
        return None

if __name__ == "__main__":
    ext = BertiogaFase2Extractor()
    # Teste com uma inscrição real de Bertioga
    res = ext.query_imovel("01.01.001.0001.001")
    print(json.dumps(res, indent=2, ensure_ascii=False))
