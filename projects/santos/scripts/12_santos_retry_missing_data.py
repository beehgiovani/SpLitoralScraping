import os
import json
import sys
# Adiciona o diretório de scripts ao path para importar o bot
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(_SCRIPT_DIR)

 
# Caminhos
_OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "data", "output")
_CONSOLIDATED_FILE = os.path.join(_OUTPUT_DIR, "dados_santos_enriquecido.json")
_RETRY_OUTPUT = os.path.join(_OUTPUT_DIR, f"dados_santos_enriquecido_retry_{os.getpid()}.json")

def main():
    print("=== MONITOR DE QUALIDADE: REPESCAGEM DE DADOS FALTANTES (SANTOS) ===")
    
    # 1. Carregar toda a base disponível (Consolidada + Parciais dos bots ativos)
    database = []
    import glob
    
    # Pega o arquivo mestre se existir
    if os.path.exists(_CONSOLIDATED_FILE):
        with open(_CONSOLIDATED_FILE, 'r', encoding='utf-8') as f:
            try:
                database.extend(json.load(f))
                print(f"[*] Base consolidada carregada.")
            except:
                pass
    
    # Pega todos os arquivos parciais de bots que estão rodando em paralelo
    parciais = glob.glob(os.path.join(_OUTPUT_DIR, "dados_santos_enriquecido_*.json"))
    for arq in parciais:
        if "retry" in arq: continue # Pula arquivos de repescagens anteriores
        if os.path.abspath(arq) == os.path.abspath(_CONSOLIDATED_FILE): continue
        
        try:
            with open(arq, 'r', encoding='utf-8') as f:
                database.extend(json.load(f))
                print(f"  -> Escaneando arquivo parcial: {os.path.basename(arq)}")
        except:
            continue

    # 2. Identificar lotes "problemáticos" (que tenham pelo menos uma economia sem proprietário ou CPF)
    lotes_para_retry = []
    lotes_originais_map = {} # Guardamos os metadados originais
    
    for item in database:
        lote_id = item.get("lote")
        economias = item.get("economias", [])
        
        precisa_retry = False
        for econ in economias:
            if not econ.get("proprietario") or not econ.get("cpf_cnpj"):
                precisa_retry = True
                break
        
        if precisa_retry:
            lotes_para_retry.append(item)
            lotes_originais_map[lote_id] = item

    total_retry = len(lotes_para_retry)
    print(f"[*] Total de Lotes com dados faltantes encontrados: {total_retry}")
    
    if total_retry == 0:
        print("[✔] Parabéns! Todos os registros da base possuem Proprietário e CPF.")
        return

    # 3. Preparar o Bot
    # Importamos dinamicamente do 09_santos_enrichment_bot
    import importlib.util
    bot_path = os.path.join(_SCRIPT_DIR, "09_santos_enrichment_bot.py")
    spec = importlib.util.spec_from_file_location("bot09", bot_path)
    bot09 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bot09)
    
    SantosEnrichmentBot = bot09.SantosEnrichmentBot

    print(f"[*] Iniciando extração focada em {total_retry} lotes...")
    
    bot = SantosEnrichmentBot()
    # Forçamos o bot a usar um arquivo de saída específico para o retry
    bot09._JSON_SAIDA = _RETRY_OUTPUT
    bot09._TXT_CONCLUIDOS = os.path.join(_OUTPUT_DIR, "lotes_concluidos_retry.txt")
    
    # IMPORTANTE: No modo Retry, não queremos pular os lotes que já estão no concluídos_retry.txt 
    # se acabamos de começar, mas queremos persistência.
    if os.path.exists(bot09._JSON_SAIDA):
        os.remove(bot09._JSON_SAIDA)

    bot.executar(lotes_para_retry)

    print(f"\n[✔] Repescagem concluída! Resultados salvos em: {os.path.basename(_RETRY_OUTPUT)}")
    print("[TIP] Agora rode o script '10_merge_results_santos.py' para unificar os novos dados na base principal.")

if __name__ == "__main__":
    main()
