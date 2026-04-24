import requests
import json
import time
import os
import re
import io
import shutil
from PyPDF2 import PdfReader

# --- CAMINHOS ABSOLUTOS (baseados na localização deste script) ---
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "data", "output")
_INPUT_DIR  = os.path.join(_SCRIPT_DIR, "..", "data", "input")
_JSON_SAIDA    = os.path.join(_OUTPUT_DIR, "dados_santos_enriquecido.json")
_JSON_ENTRADA  = os.path.join(_INPUT_DIR,  "dados_imoveis_santos.json")
_TXT_CONCLUIDOS = os.path.join(_OUTPUT_DIR, "santos_lotes_concluidos.txt")
_TXT_PERDIDOS   = os.path.join(_OUTPUT_DIR, "santos_unidades_perdidas_revisar.txt")

class SantosEnrichmentBot:
    def __init__(self):
        self.base_url = "https://egov.santos.sp.gov.br"
        self.ano_base = "2026"
        self.renovar_sessao()

    def renovar_sessao(self):
        print("  [*] Iniciando/Renovando Sessão Dinâmica com o Servidor de Santos...")
        self.session = requests.Session()
        # DEIXAR SESSÃO "BURRA/LIMPA" PARA BAIXAR PDF SEM AJAX
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cookie": "tema=pms"
        })
        try:
            self.session.get(f"{self.base_url}/tribusweb/", timeout=15)
            print(f"  [+] Novo Cookie Oficial Resgatado: {self.session.cookies.get_dict()}")
        except Exception as e:
            print(f"  [X] Falha Crítica ao tentar resgatar novo Session Cookie: {e}")

    def registrar_erro_loss(self, inscricao, tipo_falha, excecao):
        """Salva a inscrição com problema num arquivo para o final"""
        with open(_TXT_PERDIDOS, "a", encoding="utf-8") as f:
            f.write(f"{inscricao} | FASE: {tipo_falha} | ERRO: {excecao}\n")

    def extrair_id_lancamento(self, inscricao, session):
        """Descobre se o imóvel existe para este ano e pega o ID da Obrigação (Usa Sessão Efêmera)"""
        url = f"{self.base_url}/tribusweb/Imobiliario/AvisoObrigacao/Principal/{self.ano_base}/{inscricao}"
        
        headers_ajax = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        tentativa = 1
        while tentativa <= 3:
            try:
                r = session.get(url, headers=headers_ajax, timeout=15)
                if "Inscrição Imobiliária não encontrada" in r.text or "Inválid" in r.text:
                    return None
                    
                match = re.search(r'id="OBR_NUOBRIGACAO0"\s+value="(\d+)"', r.text)
                if match:
                    id_lanc = match.group(1)
                    url_listar = f"{self.base_url}/tribusweb/Imobiliario/AvisoObrigacao/ListarParcelaObrigacao/{self.ano_base}/{id_lanc}"
                    session.get(url_listar, headers=headers_ajax, timeout=15)
                    return id_lanc
                else:
                    return None
            except:
                tentativa += 1
                time.sleep(2)
        return None

    def minerar_dados_proprietario_boleto(self, inscricao, id_lanc, session):
        """Busca O Boleto na Memória RAM testando N tributos diferentes (Usa Sessão Efêmera)"""
        tributos = [4, 5, 7, 8, 16, 17] 
        # Data para a URL: A data atual formatada como DD/MM/AAAA (Invariante em 2026 para este script)
        data_santos = time.strftime("%d/%m") + f"/{self.ano_base}"
        
        for tributo in tributos:
            url_aviso = f"{self.base_url}/tribusweb/Geral/BoletoAvisoObrigacao/Principal/1/{self.ano_base}/{id_lanc}/{tributo}/{data_santos}/{inscricao}"
            
            tentativa = 1
            while tentativa <= 3:
                try:
                    # Request do Aviso (Gera o PDF no backend)
                    session.get(url_aviso, timeout=15)
                    
                    # Download Real do PDF (Binary Stream)
                    url_download = f"{self.base_url}/tribusweb/Geral/BoletoDocumento/Principal"
                    r_pdf = session.get(url_download, headers={"Referer": url_aviso}, timeout=15)
                    
                    print(f"      [DEBUG] T-{tributo} Fetch: Status={r_pdf.status_code}, Len={len(r_pdf.content)}")

                    if r_pdf.status_code == 200 and r_pdf.content.startswith(b'%PDF'):
                        # Processamento exclusivamente em RAM (io.BytesIO) para evitar acúmulo de arquivos
                        reader = PdfReader(io.BytesIO(r_pdf.content))
                        text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
                        text = re.sub(r'\n', ' ', text)
                        
                        regex_cpf = re.search(r'CPF/CNPJ[:\s]*([\d\.\-\/]+)', text, re.IGNORECASE)
                        cpf = regex_cpf.group(1).strip() if regex_cpf else None
                        
                        nome = None
                        if "Endereço" in text:
                            bloco_topo = text.split("Endereço")[0]
                            if "Sacado" in bloco_topo:
                                nome = bloco_topo.split("Sacado")[-1].strip()
                            else:
                                nome = bloco_topo.strip()
                        elif "Sacado" in text:
                            nome = text.split("Sacado")[-1].strip()
                        
                        if nome:
                            match_nome = re.search(r'^([A-ZÀ-Ÿ\s\&\.\-]{5,100})', nome, re.IGNORECASE)
                            if match_nome:
                                nome = match_nome.group(1).strip()
                            if re.match(r'^[\s\W]*(ESP[OÓ]LIOS?|ESP\.)', nome, flags=re.IGNORECASE):
                                nome = re.sub(r'^[\s\W]*(ESP[OÓ]LIOS?|ESP\.)\s*(D[EO]\s+)?', '', nome, flags=re.IGNORECASE).strip()
                                nome = f"{nome} (possivel falecido)"
                                
                        if tributo != 4:
                            print(f"      [!] CPF/Nome resgatado com SUCESSO via Boleto Oculto T-{tributo}!")
                            
                        return {"proprietario": nome, "cpf_cnpj": cpf}
                    else:
                        # Se não for PDF, é HTML (Isento/Pago). Tenta o próximo tributo.
                        break 
                except:
                    tentativa += 1
                    time.sleep(1)

        return {"proprietario": None, "cpf_cnpj": None}

    def minerar_dados_certidao(self, inscricao, session):
        """Busca Certidão de Valor Venal (Usa Sessão Efêmera)"""
        url_certidao = f"{self.base_url}/tribusweb/Certidao/CertidaoEmissao/Principal/1/L/{inscricao}/{self.ano_base}"
        
        resultado = {
            "complemento": None,
            "apto_sala": None,
            "valor_venal_total": None,
            "valor_venal_construcao": None,
            "valor_venal_terreno": None
        }
        
        tentativa = 1
        while tentativa <= 3:
            try:
                r_pdf = session.get(url_certidao, timeout=15)
                
                if r_pdf.status_code == 200 and r_pdf.content.startswith(b'%PDF'):
                    reader = PdfReader(io.BytesIO(r_pdf.content))
                    text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
                    text = re.sub(r'\n', ' ', text)
                    
                    # Valores Venais (Cravados em âncoras para evitar matching greedy `.*?` pegando o anterior)
                    v_total = re.search(r'é de R\$\s*([\d\.,]+)', text)
                    v_const = re.search(r'sendo R\$\s*([\d\.,]+)', text)
                    v_terr = re.search(r'construção e R\$\s*([\d\.,]+)', text, re.IGNORECASE)
                    
                    if v_total: resultado["valor_venal_total"] = v_total.group(1)
                    if v_const: resultado["valor_venal_construcao"] = v_const.group(1)
                    # Fallback pro terreno caso a ancôra mude
                    if v_terr: 
                        resultado["valor_venal_terreno"] = v_terr.group(1)
                    else:
                        v_terr_fallback = re.search(r'e R\$\s*([\d\.,]+)\s*\([^\)]+\)\s*de valor venal de terreno', text, re.IGNORECASE)
                        if v_terr_fallback: resultado["valor_venal_terreno"] = v_terr_fallback.group(1)
                    
                    # Complemento e Apto/Sala
                    apto_match = re.search(r'Apto/Sala\s+(\d+)', text, re.IGNORECASE)
                    if apto_match:
                        resultado["apto_sala"] = str(int(apto_match.group(1))) # Transforma "0014" em "14"
                    
                    # Pega tudo que houver entre `nº X` e `Apto/Sala` ou `, sob`
                    compl_match = re.search(r'(?:n[º°]|n\.|n)\s*[\dSN/]+\s+(.*?)(?:Apto/Sala|,?\s*sob a in)', text, re.IGNORECASE)
                    if compl_match:
                        compl = compl_match.group(1).strip()
                        if compl.lower() not in ["", "n"]:
                            resultado["complemento"] = compl
                            
                    if tentativa > 1:
                        print(f"      [✔] Ressurgiu! Certidão de {inscricao} resgatada com sucesso na tentativa {tentativa}!")
                    break # Sucesso, sai do loop Retry
                else:
                    if r_pdf.status_code != 200:
                        r_pdf.raise_for_status() 
                    else:
                        break # Pagina em branco / Sem certidao, segue a vida sem ficar no loop infinito
            except requests.exceptions.RequestException as e:
                print(f"      [!] Timeout no Servidor de CERTIDÃO (Tentativa {tentativa}/3). Aguardando...")
                if tentativa >= 3:
                    print(f"      [↻] Limite de timeouts atingido! A conexão secou. Renovando Sessão e Cookie...")
                    self.renovar_sessao()
                    tentativa = 0
                tentativa += 1
                time.sleep(3)
            except Exception as e:
                print(f"      [!] Falha CRÍTICA no OCR do PDF da Certidão: {e}")
                self.registrar_erro_loss(inscricao, "CERTIDAO", str(e))
                break
                
        return resultado

    def executar(self, dados_lotes, max_parents=100000):
        output_data = []
        
        # Estado de Retomada! Carrega o que já salvamos de Lotes Concluídos
        if os.path.exists(_JSON_SAIDA):
            try:
                with open(_JSON_SAIDA, 'r', encoding='utf-8') as f:
                    output_data = json.load(f)
            except:
                output_data = []
        
        lotes_concluidos = set()
        if os.path.exists(_TXT_CONCLUIDOS):
            with open(_TXT_CONCLUIDOS, 'r') as f:
                lotes_concluidos = set(line.strip() for line in f)

        contador_geral = 0
        print(f"Iniciando Motor Crawler. Lotes já concluídos no histórico: {len(lotes_concluidos)}")
        
        for parent_index, lote_base_dic in enumerate(dados_lotes[:max_parents], 1):
            lote_base_8digitos = str(lote_base_dic.get('lote', '')).strip()
            lote_base_8digitos = ''.join(filter(str.isdigit, lote_base_8digitos))
            
            if len(lote_base_8digitos) != 8: continue
            
            # Pula se o Lote Pai já teve sua árvore varrida completamente no passado
            if lote_base_8digitos in lotes_concluidos:
                continue
            
            print(f"\n[{parent_index}/{max_parents}] ---> Entrando no Lote Pai: {lote_base_8digitos} <---")
            
            # Busca Intra-Save: Se o prédio parar no meio, a gente continua do último Apto salvo!
            lote_existente = next((item for item in output_data if item["lote"] == lote_base_8digitos), None)
            
            pula_para_sublote = 0
            if lote_existente:
                lote_tree = lote_existente
                if lote_tree["economias"]:
                    ultima_insc = lote_tree["economias"][-1]["lote_completo_11"]
                    pula_para_sublote = int(ultima_insc[-3:]) + 1
                    print(f"      [INTRA-SAVE] Retomando a partir do Apto {pula_para_sublote}!")
            else:
                lote_tree = lote_base_dic.copy()
                lote_tree["economias"] = []
                # Já injetamos na cesta final para o "save progressivo" conseguir enxergar ele
                output_data.append(lote_tree)
            
            falhas_consecutivas = 0
            economias_encontradas = 0
            sublote = pula_para_sublote
            
            # Loop de Sublote (Tree Crawling)
            while True:
                str_sublote = str(sublote).zfill(3)
                inscricao = f"{lote_base_8digitos}{str_sublote}"
                
                # --- MOTOR DE SESSÃO EFÊMERA (Contexto de Conexão Totalmente Limpa) ---
                with requests.Session() as s_apt:
                    # Session headers minimalistas que funcionaram no Mock
                    s_apt.headers.update({
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
                        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
                    })
                    
                    try:
                        s_apt.get(f"{self.base_url}/tribusweb/", timeout=15)
                    except:
                        pass

                    id_lanc = self.extrair_id_lancamento(inscricao, s_apt)
                    
                    if not id_lanc:
                        falhas_consecutivas += 1
                        if falhas_consecutivas >= 6:
                            print(f"  [X] 6 Falhas Seguidas atingidas. Encerrando economia do lote {lote_base_8digitos}.")
                            break
                        sublote += 1
                        continue
                    
                    # ---------- SE EXISTIR O IMÓVEL, COMEÇA A EXTRAÇÃO APROFUNDADA ----------
                    falhas_consecutivas = 0 # Reseta Rule of 6!
                    economias_encontradas += 1
                    
                    print(f"  [+] Economia Detectada: {inscricao} !! Baixando Metadados (SESSÃO LIMPA)...")
                    
                    dados_prop = self.minerar_dados_proprietario_boleto(inscricao, id_lanc, s_apt)
                    # Certidão ainda usa a sessão principal (ou a mesma efêmera)
                    dados_cert = self.minerar_dados_certidao(inscricao, s_apt)
                
                # Montagem do Nó Filho (A Economia/Apto)
                economia_filho = {
                    "lote_completo_11": inscricao,
                    "proprietario": dados_prop["proprietario"],
                    "cpf_cnpj": dados_prop["cpf_cnpj"],
                    "complemento": dados_cert["complemento"],
                    "apto_sala": dados_cert["apto_sala"],
                    "valor_venal_total": dados_cert["valor_venal_total"],
                    "valor_venal_construcao": dados_cert["valor_venal_construcao"],
                    "valor_venal_terreno": dados_cert["valor_venal_terreno"]
                }
                
                lote_tree["economias"].append(economia_filho)
                contador_geral += 1
                sublote += 1
                
                # ESCRITA ATÔMICA: salva em .tmp primeiro, só substitui o real quando concluído
                # Isso garante que um Ctrl+C nunca deixa o JSON quebrado pela metade
                _tmp = _JSON_SAIDA + ".tmp"
                with open(_tmp, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=4)
                shutil.copy2(_tmp, _JSON_SAIDA)  # copia conteúdo (Windows-safe)
                os.remove(_tmp)                   # limpa o .tmp
                    
                time.sleep(1) # Intervalo contra banimento
                
            if economias_encontradas == 0 and pula_para_sublote == 0:
                print(f"  [!] Terreno Base {lote_base_8digitos} não respondeu IPTU em NENHUM sublote (000-005).")
            
            # MARCAÇÃO DE SUCESSO DO LOTE PAI INTEIRO NA ÁRVORE
            with open(_TXT_CONCLUIDOS, 'a', encoding='utf-8') as f:
                f.write(lote_base_8digitos + "\n")
            lotes_concluidos.add(lote_base_8digitos)
            
            # (Opcional) Print de conclusão do pai
            print(f"  [✔] Lote Pai Finalizado com sucesso: {lote_base_8digitos}")
            
        print(f"\n========================================================\n"
              f"EXTRAÇÃO COMPLETA: {contador_geral} Unidades Validadas salvas na Árvore JSON!")


if __name__ == "__main__":
    if not os.path.exists(_JSON_ENTRADA):
        print(f"Arquivo de entrada não encontrado em: {_JSON_ENTRADA}")
    else:
        with open(_JSON_ENTRADA, 'r', encoding='utf-8') as f:
            base = json.load(f)
            
        bot = SantosEnrichmentBot()
        bot.executar(base)
