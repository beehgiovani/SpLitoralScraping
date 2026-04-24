import requests
import re

# Headers do BOT que podem estar atrapalhando
bot_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "X-Requested-With": "XMLHttpRequest",
    "Cookie": "tema=pms"
}

s = requests.Session()
s.headers.update(bot_headers)

# 1. Inicia sessão
s.get("https://egov.santos.sp.gov.br/tribusweb/")

inscricao = "41172004002"

# 2. Pega ID (com headers de AJAX)
r1 = s.get(f"https://egov.santos.sp.gov.br/tribusweb/Imobiliario/AvisoObrigacao/Principal/2026/{inscricao}")
m = re.search(r'id="OBR_NUOBRIGACAO0"\s+value="(\d+)"', r1.text)
if m:
    id_lanc = m.group(1)
    print(f"ID Encontrado: {id_lanc}")
    
    # 3. Listar Parcela (Ativa backend)
    s.get(f"https://egov.santos.sp.gov.br/tribusweb/Imobiliario/AvisoObrigacao/ListarParcelaObrigacao/2026/{id_lanc}")
    
    # 4. Tenta Tributo 16 (Bem Estar Animal)
    url_aviso = f"https://egov.santos.sp.gov.br/tribusweb/Geral/BoletoAvisoObrigacao/Principal/1/2026/{id_lanc}/16/06/04/2026/{inscricao}"
    r_aviso = s.get(url_aviso)
    print(f"Aviso T-16 Status: {r_aviso.status_code}")
    
    # 5. Download do PDF
    url_download = "https://egov.santos.sp.gov.br/tribusweb/Geral/BoletoDocumento/Principal"
    r_pdf = s.get(url_download, headers={"Referer": url_aviso})
    
    print(f"PDF T-16: Status={r_pdf.status_code}, Tamanho={len(r_pdf.content)}")
    if r_pdf.content.startswith(b'%PDF'):
        print("SUCESSO: Iniciando por %PDF")
    else:
        print(f"FALHA: Começa com {r_pdf.content[:20]}")
else:
    print("ERRO: ID não encontrado")
