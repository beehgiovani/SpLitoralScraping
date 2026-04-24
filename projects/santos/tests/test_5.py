import requests
import re

s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
s.get("https://egov.santos.sp.gov.br/tribusweb/")

def get_id(inscricao):
    r = s.get(f"https://egov.santos.sp.gov.br/tribusweb/Imobiliario/AvisoObrigacao/Principal/2026/{inscricao}")
    m = re.search(r'id="OBR_NUOBRIGACAO0"\s+value="(\d+)"', r.text)
    return m.group(1) if m else None

print("002:", get_id("41172004002"))
print("003:", get_id("41172004003"))
