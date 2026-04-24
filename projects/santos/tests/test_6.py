import requests, re, io, time
from PyPDF2 import PdfReader

s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
s.get("https://egov.santos.sp.gov.br/tribusweb/")

def process(inscricao):
    r1 = s.get(f"https://egov.santos.sp.gov.br/tribusweb/Imobiliario/AvisoObrigacao/Principal/2026/{inscricao}")
    m = re.search(r'id="OBR_NUOBRIGACAO0"\s+value="(\d+)"', r1.text)
    if not m:
        return "ID FAIL"
    id_lanc = m.group(1)
    s.get(f"https://egov.santos.sp.gov.br/tribusweb/Imobiliario/AvisoObrigacao/ListarParcelaObrigacao/2026/{id_lanc}")
    
    tributos = [4, 16, 17]
    for tributo in tributos:
        url_aviso = f"https://egov.santos.sp.gov.br/tribusweb/Geral/BoletoAvisoObrigacao/Principal/1/2026/{id_lanc}/{tributo}/06/04/2026/{inscricao}"
        s.get(url_aviso)
        r_pdf = s.get("https://egov.santos.sp.gov.br/tribusweb/Geral/BoletoDocumento/Principal", headers={"Referer": url_aviso})
        if r_pdf.status_code == 200 and r_pdf.content.startswith(b'%PDF'):
            with open(f"test_bot_{inscricao}_T{tributo}.pdf", "wb") as f:
                f.write(r_pdf.content)
            return f"SUCCESS T-{tributo}"
    return "FAIL ALL"

print("002:", process("41172004002"))
print("003:", process("41172004003"))
