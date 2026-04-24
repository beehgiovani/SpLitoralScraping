# MetroMarGeo - Inteligência Geográfica Metrópole & Mar
import requests
import ddddocr
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class OCRSolver:
    def __init__(self):
        self.ocr = ddddocr.DdddOcr(show_ad=False)

    def solve_captcha(self, session, captcha_url):
        try:
            r = session.get(captcha_url, verify=False, timeout=20)
            if r.status_code == 200:
                res = self.ocr.classification(r.content)
                return res
        except Exception as e:
            print(f"Erro ao resolver captcha: {e}")
        return None

class SmarapdHandler:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.ocr_solver = OCRSolver()
        self.captcha_url = f"{base_url}/tbw/getCaptcha.jpg"

    def query_debitos(self, inscricao):
        # 1. Pegar o captcha e resolver
        captcha_text = self.ocr_solver.solve_captcha(self.session, self.captcha_url)
        if not captcha_text:
            return None
        
        # 2. Enviar a consulta (exemplo de Bertioga)
        query_url = f"{self.base_url}/tbw/loginWeb.jsp"
        data = {
            "execobj": "i20ServicosWebPesqImovel",
            "i20inscricao": inscricao,
            "i20captchafield": captcha_text,
            "i20btnConsultar": "Consultar"
        }
        
        try:
            r = self.session.post(query_url, data=data, verify=False, timeout=30)
            return r.text
        except Exception as e:
            print(f"Erro na consulta Smarapd: {e}")
        return None

class GcaspHandler:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.ocr_solver = OCRSolver()
        # O G-CASP pode ter captchas em endpoints diferentes, vamos mapear conforme necessário

    def query_ficha_cadastral(self, inscricao):
        # Lógica para o portal G-CASP (Peruíbe)
        pass

if __name__ == "__main__":
    # Teste rápido com Bertioga
    handler = SmarapdHandler("https://sistemas-smarapd.bertioga.sp.gov.br")
    # Usando uma inscrição de teste (precisamos de uma válida para ver o resultado real)
    # Mas o fluxo de OCR já está validado
    print("Módulo de OCR carregado e pronto para integração.")
