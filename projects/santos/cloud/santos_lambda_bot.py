# --- Módulo AWS Lambda para Extração em Escala ---

import requests
import io
import re
import time
import json
from PyPDF2 import PdfReader

class SantosLambdaBot:
    """
    Esta classe encapsula a lógica de extração para UM único imóvel.
    Ela foi desenhada para ser 'stateless' (sem estado), ideal para rodar na nuvem.
    """
    def __init__(self):
        self.base_url = "https://egov.santos.sp.gov.br"
        self.ano_base = "2026"

    def extrair_id_lancamento(self, inscricao, session):
        """
        O portal de Santos exige um ID interno (id_lanc) para gerar boletos.
        Este método faz uma chamada AJAX 'limpa' para resgatar esse ID.
        """
        url = f"{self.base_url}/tribusweb/Imobiliario/AvisoObrigacao/Principal/{self.ano_base}/{inscricao}"
        headers_ajax = {"X-Requested-With": "XMLHttpRequest"}
        try:
            r = session.get(url, headers=headers_ajax, timeout=10)
            m = re.search(r'id="OBR_NUOBRIGACAO0"\s+value="(\d+)"', r.text)
            return m.group(1) if m else None
        except:
            return None

    def minerar_dados_proprietario(self, inscricao, id_lanc, session):
        """
        Tenta extrair o nome do proprietário navegando por diferentes tributos.
        Usa o processamento em RAM (io.BytesIO) para evitar escrita em disco.
        """
        # Testamos múltiplos tributos para garantir que algum boleto traga o nome
        tributos = [4, 5, 7, 8, 16, 17] 
        data_santos = time.strftime("%d/%m") + f"/{self.ano_base}"
        
        for tributo in tributos:
            url_aviso = f"{self.base_url}/tribusweb/Geral/BoletoAvisoObrigacao/Principal/1/{self.ano_base}/{id_lanc}/{tributo}/{data_santos}/{inscricao}"
            try:
                # 1. Ativa a geração do boleto no servidor deles
                session.get(url_aviso, timeout=10)
                
                # 2. Baixa o PDF direto para a memória RAM
                url_download = f"{self.base_url}/tribusweb/Geral/BoletoDocumento/Principal"
                r_pdf = session.get(url_download, headers={"Referer": url_aviso}, timeout=10)
                
                if r_pdf.status_code == 200 and r_pdf.content.startswith(b'%PDF'):
                    # Analisamos o PDF sem criar arquivos temporários
                    reader = PdfReader(io.BytesIO(r_pdf.content))
                    text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
                    text = re.sub(r'\n', ' ', text)
                    
                    # Capturamos o CPF/CNPJ via Expressão Regular (Mais flexível)
                    regex_cpf = re.search(r'CPF/CNPJ[:\s]*([\d\.\-\/]+)', text, re.IGNORECASE)
                    cpf = regex_cpf.group(1).strip() if regex_cpf else None
                    
                    # Lógica de Nome Universal (Blindada contra caracteres corrompidos)
                    nome = None
                    # Tenta capturar entre 'Sacado' e o próximo campo lógico (Endereço, CPF ou Logradouro)
                    match_uni = re.search(r'Sacado\s+(.*?)\s+(?:Endere[^\s]*o|CPF/CNPJ|AVENIDA|RUA|PCA|AV\.)', text, re.IGNORECASE)
                    if match_uni:
                        nome = match_uni.group(1).strip()
                    
                    if not nome or len(nome) < 3:
                        # Fallback: Bloco antes do endereço (String manual)
                        if "Endereço" in text:
                            bloco = text.split("Endereço")[0]
                            nome = bloco.split("Sacado")[-1].strip() if "Sacado" in bloco else bloco.strip()
                        else:
                            # Fallback 2: Regex de letras maiúsculas logo após Sacado
                            match_sacado = re.search(r'Sacado\s+([A-ZÀ-Ÿ\s\.&/-]{3,100})', text, re.IGNORECASE)
                            if match_sacado:
                                nome = match_sacado.group(1).strip()
                    
                    if nome:
                        # Limpeza profissional (Esponlio, Prefixos, etc)
                        nome = re.sub(r'^[\s\W]*(ESP[OÓ]LIOS?|ESP\.)\s*(D[EO]\s+)?', '', nome, flags=re.IGNORECASE).strip()
                        match_nome = re.search(r'^([A-ZÀ-Ÿ\s\&\.\-]{3,100})', nome, re.IGNORECASE)
                        if match_nome:
                            nome = match_nome.group(1).strip()
                    
                    if nome:
                        return {"proprietario": nome, "cpf_cnpj": cpf, "tributo_origem": tributo}
            except:
                continue
        return None

def lambda_handler(event, context):
    """
    Função de entrada da AWS Lambda.
    'event' é o dicionário com os dados que você envia (ex: Inscrição Imobiliária).
    """
    inscricao = event.get('inscricao')
    if not inscricao:
        return {"statusCode": 400, "body": json.dumps({"error": "Falta parametro 'inscricao'"})}

    bot = SantosLambdaBot()
    
    # Criamos uma sessão HTTP isolada para cada execução (Anti-Bot)
    with requests.Session() as s:
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9"
        })
        
        # Sincroniza a sessão inicial
        s.get(f"{bot.base_url}/tribusweb/", timeout=5)
        
        id_lanc = bot.extrair_id_lancamento(inscricao, s)
        if not id_lanc:
            return {"statusCode": 404, "body": json.dumps({"error": "ID de lancamento nao encontrado"})}
            
        resultado = bot.minerar_dados_proprietario(inscricao, id_lanc, s)
        
        if resultado:
            # Integração futura com S3: s3.put_object(Bucket='...', Key='...', Body=json.dumps(resultado))
            return {
                "statusCode": 200,
                "body": resultado
            }
        else:
            return {
                "statusCode": 404,
                "body": {"message": "Boleto nao encontrado para nenhum tributo"}
            }

# --- TESTE LOCAL ---
if __name__ == "__main__":
    test_event = {"inscricao": "41172004002"}
    print(f"Executando Mock Lambda para: {test_event['inscricao']}")
    print(lambda_handler(test_event, None))
