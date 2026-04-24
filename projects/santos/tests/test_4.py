import requests
import re
import os

s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
s.get("https://egov.santos.sp.gov.br/tribusweb/")

inscricao = "41172004003"

r1 = s.get(f"https://egov.santos.sp.gov.br/tribusweb/Imobiliario/AvisoObrigacao/Principal/2026/{inscricao}")
m = re.search(r'id="OBR_NUOBRIGACAO0"\s+value="(\d+)"', r1.text)
if m:
    id_lanc = m.group(1)
    s.get(f"https://egov.santos.sp.gov.br/tribusweb/Imobiliario/AvisoObrigacao/ListarParcelaObrigacao/2026/{id_lanc}")
    
    # Testa IPTU (4)
    url_aviso_4 = f"https://egov.santos.sp.gov.br/tribusweb/Geral/BoletoAvisoObrigacao/Principal/1/2026/{id_lanc}/4/06/04/2026/{inscricao}"
    s.get(url_aviso_4)
    r_pdf_4 = s.get("https://egov.santos.sp.gov.br/tribusweb/Geral/BoletoDocumento/Principal", headers={"Referer": url_aviso_4})
    
    print(f"T-4 (IPTU): Status={r_pdf_4.status_code}, Tamanho={len(r_pdf_4.content)}, Inicia_por={r_pdf_4.content[:10]}")
    if r_pdf_4.content.startswith(b'%PDF'):
        with open("boleto_003_T4.pdf", "wb") as f:
            f.write(r_pdf_4.content)
            
    # Testa Bem Estar Animal (16)
    url_aviso_16 = f"https://egov.santos.sp.gov.br/tribusweb/Geral/BoletoAvisoObrigacao/Principal/1/2026/{id_lanc}/16/06/04/2026/{inscricao}"
    s.get(url_aviso_16)
    r_pdf_16 = s.get("https://egov.santos.sp.gov.br/tribusweb/Geral/BoletoDocumento/Principal", headers={"Referer": url_aviso_16})
    
    print(f"T-16 (Animal): Status={r_pdf_16.status_code}, Tamanho={len(r_pdf_16.content)}, Inicia_por={r_pdf_16.content[:10]}")
    if r_pdf_16.content.startswith(b'%PDF'):
        with open("boleto_003_T16.pdf", "wb") as f:
            f.write(r_pdf_16.content)
            
else:
    print("No ID found")
