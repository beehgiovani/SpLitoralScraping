import requests
import re

s = requests.Session()
s.get("https://egov.santos.sp.gov.br/tribusweb/")

inscricao = "41172004002"

r1 = s.get(f"https://egov.santos.sp.gov.br/tribusweb/Imobiliario/AvisoObrigacao/Principal/2026/{inscricao}")
m = re.search(r'id="OBR_NUOBRIGACAO0"\s+value="(\d+)"', r1.text)
if m:
    id_lanc = m.group(1)
    r2 = s.get(f"https://egov.santos.sp.gov.br/tribusweb/Imobiliario/AvisoObrigacao/ListarParcelaObrigacao/2026/{id_lanc}")
    
    print('PROPRIET' in r2.text.upper())
    print(r2.text[:200])
else:
    print("No ID")
