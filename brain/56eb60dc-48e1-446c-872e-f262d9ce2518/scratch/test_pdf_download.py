import requests
import re
import time
import random
import os
import io
from ddddocr import DdddOcr

def test_download_final():
    base_url = "https://egov.santos.sp.gov.br"
    # Inscrição que funcionou no log anterior
    inscricao = "79035015000"
    ano_base = "2026"
    ocr = DdddOcr(show_ad=False)
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    def solve_captcha(referer):
        url_captcha = f"{base_url}/tribusweb/Geral/Captcha/Principal/null/{random.random()}"
        url_solve   = f"{base_url}/tribusweb/Geral/Captcha/SolveCaptcha/"
        for i in range(1, 16):
            r_img = session.get(url_captcha)
            code = ocr.classification(r_img.content)
            if len(code) < 6: continue
            r_val = session.get(f"{url_solve}{code}", headers={"X-Requested-With": "XMLHttpRequest", "Referer": referer})
            if r_val.text.strip() == '2':
                print(f"      [+] Captcha Resolvido: {code}")
                return code
        return None

    print(f"[*] Iniciando Teste de Download para {inscricao}...")
    
    # 1. Lancamento
    url_lanc = f"{base_url}/tribusweb/Imobiliario/Lancamento"
    session.get(url_lanc)
    code1 = solve_captcha(url_lanc)
    
    # 2. POST Aviso
    url_aviso_post = f"{base_url}/tribusweb/Imobiliario/AvisoObrigacao"
    payload = {
        "args[cboaaexercicio]": ano_base,
        "args[txtnulancamento]": inscricao,
        "args[txtnulancamento_mask]": "",
        "codigo": code1
    }
    r_aviso = session.post(url_aviso_post, data=payload, headers={"Referer": url_lanc})
    
    # Pegar ID
    match = re.search(r'id="OBR_NUOBRIGACAO0"\s+value="(\d+)"', r_aviso.text)
    if not match:
        print("[!] ID nao encontrado. Lote pode estar sem divida.")
        return
    id_lanc = match.group(1)
    print(f"[+] ID Encontrado: {id_lanc}")

    # 3. Tentar baixar PDF (Tributo 4 - IPTU)
    data_santos = time.strftime("%d/%m/%Y")
    tributo = 4
    url_gen = f"{base_url}/tribusweb/Geral/BoletoAvisoObrigacao/Principal/1/{ano_base}/{id_lanc}/{tributo}/{data_santos}/{inscricao}"
    
    print(f"[*] Solicitando geracao do PDF (T-{tributo})...")
    session.get(url_gen)
    
    url_download = f"{base_url}/tribusweb/Geral/BoletoDocumento/Principal"
    r_pdf = session.get(url_download, headers={"Referer": url_gen})
    
    # Checar 7KB WAF
    if "Geral/Captcha" in r_pdf.text or (len(r_pdf.content) > 7000 and len(r_pdf.content) < 8000):
        print("[!] Bloqueio de 7KB detectado! Tentando Bypass Final...")
        solve_captcha(url_gen)
        session.get(url_gen)
        r_pdf = session.get(url_download, headers={"Referer": url_gen})

    if r_pdf.content.startswith(b'%PDF'):
        filename = "santos_test_boleto.pdf"
        with open(filename, "wb") as f:
            f.write(r_pdf.content)
        print(f"[SUCCESS] Boleto baixado com sucesso: {filename} ({len(r_pdf.content)} bytes)")
    else:
        print(f"[FAIL] Nao foi possivel obter o PDF. Recebido: {len(r_pdf.content)} bytes")
        with open("fail_debug.html", "w", encoding="utf-8") as f:
            f.write(r_pdf.text)

if __name__ == "__main__":
    test_download_final()
