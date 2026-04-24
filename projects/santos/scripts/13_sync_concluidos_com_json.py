import json
import os

# Caminhos absolutos
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "data", "output")

_JSON_CONSOLIDADO = os.path.join(_OUTPUT_DIR, "dados_santos_enriquecido.json")
_TXT_CONCLUIDOS = os.path.join(_OUTPUT_DIR, "santos_lotes_concluidos.txt")

def sincronizar():
    print("=== SINCRONIZADOR DE PROGRESSO (SANTOS) ===")
    
    if not os.path.exists(_JSON_CONSOLIDADO):
        print(f"[!] Erro: Arquivo JSON não encontrado em {_JSON_CONSOLIDADO}")
        return
    
    # 1. Carregar lotes presentes no JSON
    print(f"[*] Lendo base consolidada: {os.path.basename(_JSON_CONSOLIDADO)}...")
    try:
        with open(_JSON_CONSOLIDADO, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except Exception as e:
        print(f"[!] Erro ao ler JSON: {e}")
        return
    
    lotes_no_json = set()
    for item in dados:
        # Pega o ID do lote pai
        lote = str(item.get("lote", "")).strip()
        # Garante que o lote tem economias/dados extraídos (não é um nó vazio)
        if lote and item.get("economias"):
            lotes_no_json.add(lote)
    
    print(f"    [+] {len(lotes_no_json)} lotes válidos (com dados) encontrados no JSON.")

    # 2. Ler o arquivo de concluídos (.txt)
    if not os.path.exists(_TXT_CONCLUIDOS):
        print("[!] Arquivo de lotes concluídos não existe. Nada a sincronizar.")
        return

    with open(_TXT_CONCLUIDOS, 'r', encoding='utf-8') as f:
        # Usamos set para remover duplicatas que possam ter ocorrido no merge
        lotes_no_txt = list(set(line.strip() for line in f if line.strip()))
    
    print(f"[*] Lendo histórico: {len(lotes_no_txt)} entradas únicas no TXT.")

    # 3. Filtrar: Manter no TXT apenas o que realmente está no JSON
    lotes_finais = [l for l in lotes_no_txt if l in lotes_no_json]
    removidos = len(lotes_no_txt) - len(lotes_finais)

    # 4. Salvar de volta
    if removidos > 0:
        print(f"[!] Identificados {removidos} lotes 'fantasmas' (marcados como concluídos mas sem dados no JSON).")
        # Criar um backup por segurança
        backup_path = _TXT_CONCLUIDOS + ".bak"
        import shutil
        shutil.copy2(_TXT_CONCLUIDOS, backup_path)
        
        with open(_TXT_CONCLUIDOS, 'w', encoding='utf-8') as f:
            for lote in sorted(lotes_finais):
                f.write(lote + "\n")
        
        print(f"[✔] Sincronização concluída!")
        print(f"    - Mantidos: {len(lotes_finais)}")
        print(f"    - Removidos: {removidos}")
        print(f"    - Backup criado em: {os.path.basename(backup_path)}")
        print("\n[TIP] Na próxima vez que rodar o orquestrador, o robô irá re-processar os lotes removidos.")
    else:
        print("[✔] Tudo certo! O histórico TXT está 100% sincronizado com a base JSON.")

if __name__ == "__main__":
    sincronizar()
