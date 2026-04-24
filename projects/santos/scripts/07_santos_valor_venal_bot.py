import requests
import json
import time
import os
import pytesseract
from PIL import Image
from io import BytesIO
import random
from bs4 import BeautifulSoup

# Configuração do Caminho do Tesseract (se no Windows e não estiver no PATH)
# descomente e edite a linha abaixo caso dê erro de 'tesseract is not installed'
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class SantosValorVenalBot:
    def __init__(self, ano_base=2026):
        self.base_url = "https://egov.santos.sp.gov.br"
        self.ano_base = ano_base
        self.session = requests.Session()
        # Headers para similar um navegador padrão e evitar bloqueios fáceis
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        })

    def solve_captcha(self):
        """Baixa e tenta resolver o captcha do TribusWeb usando Tesseract"""
        captcha_url = f"{self.base_url}/tribusweb/Geral/Captcha/Principal/null/{random.random()}"
        
        try:
            r = self.session.get(captcha_url, timeout=10)
            if r.status_code == 200:
                img = Image.open(BytesIO(r.content))
                # Pré-processamento básico para tentar ajudar o Tesseract
                img = img.convert('L') # Escala de cinza
                
                # Tesseract OCR: configurado para modo single block e caracteres alfanuméricos
                custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                texto = pytesseract.image_to_string(img, config=custom_config).strip()
                texto = texto.replace(" ", "")
                return texto
        except Exception as e:
            print(f"  [!] Erro no OCR do Captcha: {e}")
        return ""

    def validate_captcha(self, text):
        """Envia o texto para avaliação do servidor. O servidor retorna '2' se sucesso."""
        val_url = f"{self.base_url}/tribusweb/Geral/Captcha/SolveCaptcha/{text}"
        try:
            r = self.session.get(val_url, timeout=10)
            if r.text.strip() == '2':
                return True
        except:
            pass
        return False

    def emitir_certidao(self, inscricao):
        """Faz o fluxo completo de Captcha -> Certidao para uma única inscrição de 11 dígitos"""
        max_captcha_tries = 8 # Margem do Tesseract (que não é perfeito)
        
        for tentativa in range(1, max_captcha_tries + 1):
            solucao = self.solve_captcha()
            if not solucao or len(solucao) < 3:
                continue
                
            if self.validate_captcha(solucao):
                print(f"  [+] Captcha quebrado! ('{solucao}') - Requisitando Certidão para {inscricao}...")
                cert_url = f"{self.base_url}/tribusweb/Certidao/CertidaoEmissao/Principal/1/L/{inscricao}/{self.ano_base}"
                
                try:
                    r = self.session.get(cert_url, timeout=20)
                    if r.status_code == 200:
                        return self.parse_valor_venal(r.text)
                except Exception as e:
                    print(f"  [!] Erro de conexão na Certidão: {e}")
                return "Erro Conexão"
        
        print(f"  [-] Falha ao quebrar Captcha após {max_captcha_tries} tentativas.")
        return "Erro Captcha"

    def parse_valor_venal(self, html):
        """Busca o Valor Venal dentro do HTML da página de resposta da Certidão"""
        if "Inscrição Inválida" in html or "não encontrada" in html.lower() or "não encontrado" in html.lower():
            return "Inválido"
            
        soup = BeautifulSoup(html, 'html.parser')
        
        tds = soup.find_all('td')
        for i, td in enumerate(tds):
            text = td.get_text(strip=True).upper()
            if "VALOR VENAL" in text and "TOTAL" in text:
                try:
                    return tds[i+1].get_text(strip=True)
                except: pass
            elif "VALOR VENAL" in text:
                try:
                     val = tds[i+1].get_text(strip=True)
                     if "R$" in val or "," in val:
                         return val
                except: pass
        
        # Fallback brancal
        for b in soup.find_all(['b', 'strong', 'span']):
            if "R$" in b.get_text():
                return b.get_text(strip=True)
                
        return "Certidão Emitida, Valor Não Encontrado no Layout"

    def processar_base(self, caminho_json, max_lotes=100, max_sublotes_por_lote=3):
        if not os.path.exists(caminho_json):
            print(f"ERRO: Arquivo base {caminho_json} não encontrado!")
            return

        with open(caminho_json, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            
        print(f"Iniciando Bot TribusWeb para {min(max_lotes, len(dados))} Lotes Base do arquivo {caminho_json}")
        
        resultados = []
        
        for index, item in enumerate(dados[:max_lotes]):
            lote_base = str(item.get('lote', '')).strip()
            lote_base = ''.join(filter(str.isdigit, lote_base))
            
            if len(lote_base) != 8:
                print(f"\n[{index+1}] Pulando lote {lote_base} (tamanho != 8)")
                continue
                
            print(f"\n[{index+1}/{max_lotes}] Processando Lote Base: {lote_base}")
            
            for sublote_num in range(max_sublotes_por_lote):
                sublote_str = str(sublote_num).zfill(3) 
                inscricao_completa = f"{lote_base}{sublote_str}"
                
                print(f"  -> Testando Economia: {inscricao_completa}")
                valor_venal = self.emitir_certidao(inscricao_completa)
                
                print(f"  -> Resultado: {valor_venal}")
                
                item_copia = item.copy()
                item_copia['inscricao_testada'] = inscricao_completa
                item_copia['valor_venal'] = valor_venal
                resultados.append(item_copia)
                
                if valor_venal == "Inválido":
                    print(f"  -> Inscrição inválida. Economia {sublote_str} não existe. Indo pro próximo Lote.")
                    break
                    
                time.sleep(1)
                
        output_file = "dados_santos_com_valor_venal.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, ensure_ascii=False, indent=4)
        print(f"\nProcesso concluído! Salvo em: {output_file}")


if __name__ == "__main__":
    bot = SantosValorVenalBot(ano_base=2026)
    caminho = "dados_imoveis_santos.json"
    bot.processar_base(caminho, max_lotes=5, max_sublotes_por_lote=3)
