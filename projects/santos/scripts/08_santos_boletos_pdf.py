import requests
import json
import time
import os
import re

class SantosBoletoDownloader:
    def __init__(self):
        self.base_url = "https://egov.santos.sp.gov.br"
        self.ano_base = "2026"
        self.session = requests.Session()
        
        # Injetando exatemente os headers que você sniffou no navegador
        # Atenção: O PHPSESSID expira, então caso rode no futuro, basta atualizar o cookie aqui.
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "Cookie": "tema=pms; PHPSESSID=ef389257d2c4822843e2abecbc080742; _ga=GA1.1.401611654.1775461192; _ga_RVC6QH1G64=GS2.1.s1775461192$o1$g0$t1775461194$j58$l0$h0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://egov.santos.sp.gov.br/tribusweb/Imobiliario/AvisoObrigacao/Principal/2026/77018016009",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        })
        
        self.output_dir = "boletos_santos"
        os.makedirs(self.output_dir, exist_ok=True)

    def extrair_id_lancamento(self, inscricao):
        """Acessa a tela principal da inscrição e caça o NUOBRIGACAO gerado"""
        url_principal = f"{self.base_url}/tribusweb/Imobiliario/AvisoObrigacao/Principal/{self.ano_base}/{inscricao}"
        try:
            r = self.session.get(url_principal, timeout=15)
            if r.status_code != 200:
                print(f"  [-] Erro HTTP {r.status_code} na página principal.")
                return None
            
            # Novo padrão direto da tabela HTML reportada pelo usuário!
            match = re.search(r'id="OBR_NUOBRIGACAO0"\s+value="(\d+)"', r.text)
            
            if match:
                id_lanc = match.group(1)
                
                # O Clique Mágico no Radio Button que o usuário detectou:
                # O servidor possivelmente usa isso para ativar a sessão do boleto.
                url_listar = f"{self.base_url}/tribusweb/Imobiliario/AvisoObrigacao/ListarParcelaObrigacao/{self.ano_base}/{id_lanc}"
                self.session.get(url_listar, timeout=10) # Bate na rota igual o AJAX faria
                
                return id_lanc
                
            print("  [-] ID Lançamento (NUOBRIGACAO) não encontrado no HTML. Lote deve estar sem IPTU ativo.")
        except Exception as e:
            print(f"  [!] Erro de conexão na extração do ID: {e}")
            
        return None

    def baixar_boleto(self, inscricao, id_lanc, parcela="4"):
        """Realiza o processo de Geração e Baixa do Boleto (2 Saltos) para parcelas isoladas"""
        
        # Salto 1: O Preparo. Requisita a URL que gera a tela HTML com o botão.
        # Isso informa ao Session da prefeitura qual o PDF ele deve engatilhar no buffer.
        url_preparo = f"{self.base_url}/tribusweb/Geral/BoletoAvisoObrigacao/Principal/1/{self.ano_base}/{id_lanc}/{parcela}/06/04/2026/{inscricao}"
        
        try:
            print(f"  -> [Passo 1] Preparando Parcela {parcela} no servidor...")
            self.session.get(url_preparo, timeout=120)
            
            # Salto 2: O Download Seguro. Com a sessão preparada, o servidor vomita o PDF nesta URL estática.
            url_download_final = f"{self.base_url}/tribusweb/Geral/BoletoDocumento/Principal"
            
            # Replicamos o Referer igual ao seu log original
            self.session.headers.update({
                "Referer": url_preparo
            })
            
            print(f"  -> [Passo 2] Capturando fluxo binário do PDF do servidor...")
            r_pdf = self.session.get(url_download_final, timeout=60)
            
            if r_pdf.status_code == 200 and r_pdf.headers.get("content-type", "").startswith("application/pdf"):
                file_path = os.path.join(self.output_dir, f"Boleto_{inscricao}_P{parcela}.pdf")
                with open(file_path, "wb") as f:
                    f.write(r_pdf.content)
                print(f"  [+] SUCESSO ABSOLUTO! Boleto isolado salvo em: {file_path}")
                return True
            else:
                print(f"  [-] Falha: O conteúdo não era um PDF válido. Tipo recebido: {r_pdf.headers.get('content-type')}")
                
        except Exception as e:
            print(f"  [!] Erro de conexão ao baixar o Boleto: {e}")
        return False

    def executar_teste(self):
        # A Inscrição que você confirmou ter boleto pendente!
        inscricoes = [
            "77018016009"
        ]
        
        print(f"Iniciando Bot Python para download de {len(inscricoes)} boletos...\n")
        
        for i, insc in enumerate(inscricoes, 1):
            print(f"[{i}/{len(inscricoes)}] Processando Inscrição: {insc} ...")
            
            id_lanc = self.extrair_id_lancamento(insc)
            
            if id_lanc:
                print(f"  -> NUOBRIGACAO detectado: {id_lanc}. Baixando PDF...")
                self.baixar_boleto(insc, id_lanc)
            else:
                print(f"  -> Ignorando. (Inscrição sem IPTU ou não vinculada a este exercício)")
            
            time.sleep(2) # Sleep para evitar IP Ban


if __name__ == "__main__":
    bot = SantosBoletoDownloader()
    bot.executar_teste()
