import requests
import re
import ddddocr
import random
import time

class TestBot:
    def __init__(self):
        self.base_url = "https://egov.santos.sp.gov.br"
        self.ano_base = "2026"
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9"
        })

    def test_flow(self, inscricao):
        print(f"[*] Iniciando teste DUAL para Inscr: {inscricao}")
        
        # 0. Sync inicial
        self.session.get(f"{self.base_url}/tribusweb/", timeout=30)
        
        url_captcha    = f"{self.base_url}/tribusweb/Geral/Captcha/Principal/null/{random.random()}"
        url_solve      = f"{self.base_url}/tribusweb/Geral/Captcha/SolveCaptcha/"
        url_lancamento = f"{self.base_url}/tribusweb/Imobiliario/Lancamento"
        url_aviso      = f"{self.base_url}/tribusweb/Imobiliario/AvisoObrigacao/Principal/{self.ano_base}/{inscricao}"

        def solve_stage(name, referer):
            print(f"[*] Resolvendo para {name}...")
            for i in range(5):
                r_img = self.session.get(url_captcha, timeout=30)
                codigo = self.ocr.classification(r_img.content)
                r_solve = self.session.get(f"{url_solve}{codigo}", 
                                           headers={"X-Requested-With": "XMLHttpRequest", "Referer": referer}, 
                                           timeout=30)
                if r_solve.text.strip() == '2':
                    print(f"[+] {name} VALIDADO: {codigo}")
                    return codigo
            return None

        # STAGE 1
        cod_1 = solve_stage("LANCAMENTO", url_lancamento)
        if not cod_1: return
        payload_1 = {"args[cboaaexercicio]": self.ano_base, "args[txtnulancamento]": inscricao, "codigo": cod_1}
        self.session.post(url_lancamento, data=payload_1, headers={"Referer": url_lancamento}, timeout=30)

        # STAGE 2
        cod_2 = solve_stage("AVISO", url_aviso)
        if not cod_2: return
        payload_2 = {"args[cboaaexercicio]": self.ano_base, "args[txtnulancamento]": inscricao, "codigo": cod_2}
        r = self.session.post(url_aviso, data=payload_2, headers={"Referer": url_aviso}, timeout=30)
        
        print(f"[*] POST Final Status: {r.status_code}")
        
        match = re.search(r'id="OBR_NUOBRIGACAO0"\s+value="(\d+)"', r.text)
        if match:
            print(f"[SUCCESS] ID Lancamento: {match.group(1)}")
        else:
            print("[FAIL] ID nao encontrado no HTML.")
            with open("debug_fail_dual.html", "w", encoding="utf-8") as f:
                f.write(r.text)

if __name__ == "__main__":
    t = TestBot()
    t.test_flow("77018016001")
