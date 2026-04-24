import requests
import json
import time
import os
import re
import io
import shutil
import random
import ddddocr # type: ignore 
from PyPDF2 import PdfReader 

# --- CAMINHOS ABSOLUTOS (baseados na localização deste script) ---
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "data", "output")
_INPUT_DIR  = os.path.join(_SCRIPT_DIR, "..", "data", "input")

_PID = os.getpid()
_JSON_SAIDA    = os.path.join(_OUTPUT_DIR, f"dados_santos_enriquecido_{_PID}.json")
_JSON_ENTRADA  = os.path.join(_INPUT_DIR,  "dados_imoveis_santos.json")
_TXT_CONCLUIDOS = os.path.join(_OUTPUT_DIR, "santos_lotes_concluidos.txt")
_TXT_PERDIDOS   = os.path.join(_OUTPUT_DIR, "santos_unidades_perdidas_revisar.txt")
_JSON_CONSOLIDADO = os.path.join(_OUTPUT_DIR, "dados_santos_enriquecido.json")

_RESERVAS_DIR = os.path.join(_OUTPUT_DIR, "reservas")
os.makedirs(_RESERVAS_DIR, exist_ok=True)
    

class SantosEnrichmentBot:
    def __init__(self):
        self.base_url = "https://egov.santos.sp.gov.br"
        self.ano_base = "2026"
        # Inicializa o OCR apenas UMA vez para economizar memória (5 instâncias consumirão ~800MB)
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        self.renovar_sessao()

    def renovar_sessao(self):
        print("  [*] Iniciando/Renovando Sessao Dinamica com o Servidor de Santos...")
        tentativa = 1
        while tentativa <= 5:
            self.session = requests.Session()
            # DEIXAR SESSÃO "BURRA/LIMPA" PARA BAIXAR PDF SEM AJAX
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cookie": "tema=pms"
            })
            try:
                # Aumentado timeout para 30s para evitar quedas em carga alta
                self.session.get(f"{self.base_url}/tribusweb/", timeout=30)
                print(f"  [+] Novo Cookie Oficial Resgatado: {self.session.cookies.get_dict()}")
                return True
            except Exception as e:
                print(f"  [!] Tentativa {tentativa}/5 - Falha ao resgatar Session Cookie: {e}")
                time.sleep(tentativa * 5) # Backoff exponencial simples (5s, 10s, 15s...)
                tentativa += 1
        
        print("  [X] Falha Critica: Nao foi possivel estabelecer sessao apos 5 tentativas.")
        return False

    def registrar_erro_loss(self, inscricao, tipo_falha, excecao):
        """Salva a inscrição com problema num arquivo para o final"""
        with open(_TXT_PERDIDOS, "a", encoding="utf-8") as f:
            f.write(f"{inscricao} | FASE: {tipo_falha} | ERRO: {excecao}\n")


    def _resolver_captcha_etapa(self, session, referer):
        """Helper para baixar e validar captcha em qualquer etapa do processo."""
        url_captcha = f"{self.base_url}/tribusweb/Geral/Captcha/Principal/null/{random.random()}"
        url_solve   = f"{self.base_url}/tribusweb/Geral/Captcha/SolveCaptcha/"
        
        tentativa_ocr = 1
        for tentativa_ocr in range(1, 20):
            try:
                r_img = session.get(url_captcha, timeout=30)
                if r_img.status_code != 200: continue
                
                codigo = self.ocr.classification(r_img.content)
                # Santos usa 6 caracteres. Ignorar resoluções curtas.
                if not codigo or len(codigo) < 6:
                    continue
                
                # Validação AJAX (Santos espera '2')
                r_val = session.get(f"{url_solve}{codigo}", 
                                    headers={"X-Requested-With": "XMLHttpRequest", "Referer": referer}, 
                                    timeout=30)
                status_ajax = r_val.text.strip()
                if status_ajax == '2':
                    return codigo
                else:
                    print(f"      [!] Captcha {codigo} invalidado (status {status_ajax}). Tentando ocr {tentativa_ocr}/20...")
            except Exception:
                pass
            time.sleep(random.uniform(0.5, 1.5))
        return None

    def extrair_id_lancamento(self, inscricao, session):
        """
        Extração Completa com Bypass de Captcha em duas etapas (se necessário).
        """
        url_base_lanc = f"{self.base_url}/tribusweb/Imobiliario/Lancamento"
        url_post_aviso = f"{self.base_url}/tribusweb/Imobiliario/AvisoObrigacao"

        try:
            # 1. AUTORIZAÇÃO INICIAL (ETAPA LANÇAMENTO)
            session.get(url_base_lanc, timeout=30) # Pega PHPSESSID inicial
            
            print(f"    [*] Resolvendo Captcha Etapa 1 (Lancamento) para {inscricao}...")
            codigo_1 = self._resolver_captcha_etapa(session, url_base_lanc)
            if not codigo_1:
                return None
            
            payload_1 = {
                "args[cboaaexercicio]": self.ano_base,
                "args[txtnulancamento]": inscricao,
                "args[txtnulancamento_mask]": "",
                "codigo": codigo_1
            }
            
            # Submissão que leva ao AvisoObrigacao
            r = session.post(url_post_aviso, data=payload_1, headers={"Referer": url_base_lanc}, timeout=30)
            
            # ETAPA 2: Caso o servidor exija captcha NOVAMENTE na tela de resultados (AvisoObrigacao)
            if "Geral/Captcha" in r.text or "código de controle" in r.text:
                print(f"    [*] Resolvendo Captcha Etapa 2 (AvisoObrigacao) para {inscricao}...")
                codigo_2 = self._resolver_captcha_etapa(session, url_post_aviso)
                if codigo_2:
                    payload_1["codigo"] = codigo_2
                    r = session.post(url_post_aviso, data=payload_1, headers={"Referer": url_base_lanc}, timeout=30)
            
            if "Inscrição Imobiliária não encontrada" in r.text or "Não foram encontradas obrigações" in r.text:
                return None
                
            # Procura o ID da Obrigação no HTML resultante
            match = re.search(r'id="OBR_NUOBRIGACAO0"\s+value="(\d+)"', r.text)
            if match:
                id_lanc = match.group(1)
                
                # Se ainda houver um campo de captcha na página (mesmo com ID), resolvemos via AJAX 
                # para "limpar" o acesso aos boletos na próxima fase.
                if "SolveCaptcha" in r.text:
                    print("    [*] Limpando barreira de Captcha residual para acesso aos boletos...")
                    self._resolver_captcha_etapa(session, url_post_aviso)

                print(f"    [+] Extração OK! ID Obrigação: {id_lanc}")
                return id_lanc
            
        except Exception as e:
            print(f"    [!] Erro fatal no bypass de captcha: {e}")
            
        return None

    def minerar_dados_proprietario_boleto(self, inscricao, id_lanc, session):
        """Busca O Boleto na Memória RAM testando N tributos diferentes (Usa Sessão Efêmera)"""
        
        tributos = [1, 30]
        # Data para a URL: A data atual formatada como DD/MM/AAAA (Invariante em 2026 para este script)
        data_santos = time.strftime("%d/%m") + f"/{self.ano_base}"
        
        for tributo in tributos:
            url_aviso = f"{self.base_url}/tribusweb/Geral/BoletoAvisoObrigacao/Principal/1/{self.ano_base}/{id_lanc}/{tributo}/{data_santos}/{inscricao}"
            
            for tentativa in range(1, 4):
                try:
                    # Request do Aviso (Gera o PDF no backend)
                    session.get(url_aviso, timeout=30)
                    
                    # Download Real do PDF (Binary Stream)
                    url_download = f"{self.base_url}/tribusweb/Geral/BoletoDocumento/Principal"
                    r_pdf = session.get(url_download, headers={"Referer": url_aviso}, timeout=30)
                    
                    # Verificação de Bloqueio por Captcha na Segunda Etapa (Acesso ao Documento)
                    if r_pdf.status_code != 200 or not r_pdf.content.startswith(b'%PDF'):
                        # Se Len for ~7KB ou contiver Captcha, é um bloqueio de WAF
                        if "Geral/Captcha" in r_pdf.text or (len(r_pdf.content) > 7000 and len(r_pdf.content) < 8500):
                            # TENTA ATÉ 10 VEZES O BYPASS PARA ESTE TRIBUTO ESPECÍFICO (Mais que isso queima a sessão)
                            for bypass_attempt in range(1, 11):
                                print(f"      [!] Retenção WAF detectada ({len(r_pdf.content)}B). Tentando bypass {bypass_attempt}/10...")
                                
                                # Delay humano aleatório para não parecer martelamento
                                time.sleep(random.uniform(1.2, 3.0))

                                if self._resolver_captcha_etapa(session, url_aviso):
                                    # Tenta disparar a geração NOVAMENTE
                                    session.get(url_aviso, timeout=30)
                                    r_pdf = session.get(url_download, headers={"Referer": url_aviso}, timeout=30)
                                    
                                    if r_pdf.content.startswith(b'%PDF'):
                                        break # Bypass teve sucesso!
                                    
                                    if len(r_pdf.content) == 0:
                                        print(f"      [!] Bloqueio Crítico (0B) detectado. Renovando Sessão...")
                                        self.renovar_sessao()
                                        session = self.session # Atualiza a referência local
                                        break # Sai do loop de bypass para tentar o tributo de novo com sessão limpa

                    # Se Len ainda for baixo ou não for PDF, pula para o próximo tributo
                    if r_pdf.status_code != 200 or not r_pdf.content.startswith(b'%PDF'):
                        if len(r_pdf.content) > 0:
                            print(f"      [-] Falha ao obter PDF (ContentType: {r_pdf.headers.get('Content-Type')}, Size: {len(r_pdf.content)}B)")
                        break

                    print(f"      [DEBUG] T-{tributo} Fetch PDF OK! Len={len(r_pdf.content)}")

                    with io.BytesIO(r_pdf.content) as f:
                        reader = PdfReader(f)
                        text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
                        text = re.sub(r'\n', ' ', text)
                        
                        # CPF/CNPJ: Procura por padrões numéricos após a etiqueta
                        regex_cpf = re.search(r'CPF/CNPJ[:\s]*([\d\.\-\/]+)', text, re.IGNORECASE)
                        cpf = regex_cpf.group(1).strip() if regex_cpf else None
                        
                        # NOME: Lógica Multinível ultra-agressiva
                        nome = None
                        # 1. Filtro Padrão (Entre Sacado e o próximo rótulo)
                        match_universal = re.search(r'Sacado[:\s]+(.*?)\s+(?:Endere[^\s]*o|CPF/CNPJ|AVENIDA|RUA|PRACA|PCA|AV\.|LOGRADOURO)', text, re.IGNORECASE)
                        if match_universal:
                            nome = match_universal.group(1).strip()
                        
                        if not nome or len(nome) < 3:
                            # 2. Filtro de Bloco (Pega o que parece nome logo após Sacado)
                            match_sacado = re.search(r'Sacado[:\s]+([A-ZÀ-Ÿ0-9\s\.&/-]{3,120})', text, re.IGNORECASE)
                            if match_sacado:
                                nome = match_sacado.group(1).strip()

                        if not nome:
                            # 3. Filtro Reverso (Pega o que vem antes do CPF no contexto do Sacado)
                            match_rev = re.search(r'Sacado[:\s]+(.*?)(?:\s+CPF/CNPJ)', text, re.IGNORECASE)
                            if match_rev:
                                nome = match_rev.group(1).strip()
                        
                        if nome:
                            # Limpeza profissional (Esponlio, Prefixos, etc)
                            is_espolio = re.search(r'^[\s\W]*(ESP[OÓ]LIOS?|ESP\.)', nome, flags=re.IGNORECASE)
                            nome = re.sub(r'^[\s\W]*(ESP[OÓ]LIOS?|ESP\.)\s*(D[EO]\s+)?', '', nome, flags=re.IGNORECASE).strip()
                            
                            # Filtro de caracteres válidos (A-Z)
                            match_nome = re.search(r'^([A-ZÀ-Ÿ\s\&\.\-]{3,100})', nome, re.IGNORECASE)
                            if match_nome:
                                nome = match_nome.group(1).strip()
                            
                            if is_espolio:
                                nome = f"{nome} (possivel falecido)"
                                
                        if nome:
                            return {"proprietario": nome, "cpf_cnpj": cpf}
                    
                    # Se chegou aqui é porque percorreu o PDF e não achou os dados. Tentar próximo tributo.
                    break 

                except Exception as e:
                    print(f"      [!] Erro no tributo T-{tributo} (tentativa {tentativa}/3): {e}")
                    time.sleep(1)

        return {"proprietario": None, "cpf_cnpj": None}

    def minerar_dados_certidao(self, inscricao, session):
        """Busca Certidão de Valor Venal (Usa Sessão Efêmera)"""
        url_certidao = f"{self.base_url}/tribusweb/Certidao/CertidaoEmissao/Principal/1/L/{inscricao}/{self.ano_base}"
        
        resultado = {
            "proprietario": None,
            "complemento": None,
            "apto_sala": None,
            "valor_venal_total": None,
            "valor_venal_construcao": None,
            "valor_venal_terreno": None
        }
        
        tentativa = 1
        while tentativa <= 3:
            try:
                r_pdf = session.get(url_certidao, timeout=30)
                
                # Segunda Etapa na Certidão (Bypass de WAF)
                if r_pdf.status_code != 200 or not r_pdf.content.startswith(b'%PDF'):
                    if "Geral/Captcha" in r_pdf.text or (len(r_pdf.content) > 7000 and len(r_pdf.content) < 8500):
                        print(f"      [!] Certidão retida pelo WAF ({len(r_pdf.content)}B). Resolvendo bypass...")
                        if self._resolver_captcha_etapa(session, url_certidao):
                            r_pdf = session.get(url_certidao, timeout=30)

                if r_pdf.status_code == 200 and r_pdf.content.startswith(b'%PDF'):
                    reader = PdfReader(io.BytesIO(r_pdf.content))
                    text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
                    text = re.sub(r'\n', ' ', text)
                    
                    # NOME NA CERTIDÃO: Captura agressiva entre Contribuinte e o próximo campo fixo
                    match_prop = re.search(r'Contribuinte[:\s]+(.*?)\s+(?:Logradouro|Endere[^\s]*o|Cadastro|Inscri|Docum|Nacionalidade)', text, re.IGNORECASE)
                    if match_prop:
                        resultado["proprietario"] = match_prop.group(1).strip()
                    else:
                        # Fallback ainda mais agressivo para blocos de letras após rótulo
                        match_fallback = re.search(r'Contribuinte[:\s]+([A-ZÀ-Ÿ0-9\s\.&/-]{3,120})', text, re.IGNORECASE)
                        if match_fallback:
                            resultado["proprietario"] = match_fallback.group(1).strip()
                    
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
                print(f"      [!] Timeout no Servidor de CERTIDÃO ({e}) (Tentativa {tentativa}/3). Aguardando...")
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

    def executar(self, dados_lotes, retry_mode=False):
        max_parents = len(dados_lotes)
        output_data = []
        
        # 1. Carregar progresso anterior do arquivo de saída se ele ja existir (Resume)
        if os.path.exists(_JSON_SAIDA):
            try:
                with open(_JSON_SAIDA, 'r', encoding='utf-8') as f:
                    output_data = json.load(f)
            except:
                output_data = []
        
        lotes_concluidos = set()
        if not retry_mode:
            if os.path.exists(_TXT_CONCLUIDOS):
                with open(_TXT_CONCLUIDOS, 'r') as f:
                    for line in f:
                        clean_lote = line.strip()
                        if clean_lote: lotes_concluidos.add(clean_lote)

            # Carrega também do arquivo consolidado global para evitar retrabalho
            if os.path.exists(_JSON_CONSOLIDADO):
                try:
                    with open(_JSON_CONSOLIDADO, 'r', encoding='utf-8') as f:
                        dados_finais = json.load(f)
                        for item in dados_finais:
                            lote_id = str(item.get("lote", "")).strip()
                            if lote_id:
                                lotes_concluidos.add(lote_id)
                    print(f"  [*] Base consolidada carregada. Total de lotes ignorados agora: {len(lotes_concluidos)}")
                except Exception as e:
                    print(f"  [!] Alerta: Erro ao ler base consolidada para pular lotes: {e}")

        contador_geral = 0
        if not retry_mode:
            print(f"Iniciando Motor Crawler. Lotes já concluídos no histórico: {len(lotes_concluidos)}")
        else:
            print(f"Iniciando Motor Crawler em MODO REPESCAGEM (Ignorando histórico).")
        
        for parent_index, lote_base_dic in enumerate(dados_lotes[:max_parents], 1):
            lote_base_8digitos = str(lote_base_dic.get('lote', '')).strip()
            lote_base_8digitos = ''.join(filter(str.isdigit, lote_base_8digitos))
            
            if len(lote_base_8digitos) != 8: continue
            
            # Pula se o Lote Pai já teve sua árvore varrida completamente no passado (A menos que seja Retry)
            if not retry_mode and lote_base_8digitos in lotes_concluidos:
                continue
            
            # ------- SISTEMA DE RESERVA ATÔMICA -------
            time.sleep(random.uniform(0.1, 1.5)) # Jitter leve para minizar colisões simultâneas exatas
            
            lock_file = os.path.join(_RESERVAS_DIR, f"{lote_base_8digitos}.lock")
            try:
                # O modo 'x' é atômico no OS. Se o arquivo já existir, ele lança FileExistsError.
                with open(lock_file, 'x') as f:
                    f.write(str(_PID))
            except FileExistsError:
                # Já reservado por outro bot ativo ou pendente de limpeza.
                print(f"\n[{parent_index}/{max_parents}] Lote {lote_base_8digitos} já reservado por outro processo. Pulando...")
                continue
            except Exception as e:
                print(f"Erro ao tentar reservar lote {lote_base_8digitos}: {e}")
                continue
            # ------------------------------------------
            
            print(f"\n[{parent_index}/{max_parents}] ---> Entrando no Lote Pai: {lote_base_8digitos} (PID: {_PID}) <---")
            
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
                
                # --- MOTOR DE SESSÃO EFÊMERA (Contexto de Conexão Totalmente Limpa - Igual Lambda) ---
                with requests.Session() as s_apt:
                    s_apt.headers.update({
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept-Language": "pt-BR,pt;q=0.9"
                    })
                    
                    try:
                        s_apt.get(f"{self.base_url}/tribusweb/", timeout=30)
                    except:
                        pass

                    id_lanc = self.extrair_id_lancamento(inscricao, s_apt)
                    
                    if not id_lanc:
                        falhas_consecutivas += 1
                        if falhas_consecutivas >= 10:
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
                
                # Decisão Inteligente de Proprietário: Boleto é prioritário (tem CPF), Certidão é fallback
                nome_final = dados_prop.get("proprietario") or dados_cert.get("proprietario")
                cpf_final = dados_prop.get("cpf_cnpj")

                # Montagem do Nó Filho (A Economia/Apto)
                economia_filho = {
                    "lote_completo_11": inscricao,
                    "proprietario": nome_final,
                    "cpf_cnpj": cpf_final,
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
