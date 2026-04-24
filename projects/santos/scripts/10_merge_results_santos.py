import os
import json
import glob
import shutil

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "data", "output")
_FINAL_OUTPUT = os.path.join(_OUTPUT_DIR, "dados_santos_enriquecido.json")
_RESERVAS_DIR = os.path.join(_OUTPUT_DIR, "reservas")

def main():
    print("Iniciando mesclagem dos resultados dos bots paralelos...")
    
    # 1. Carregar o arquivo final existente, se houver
    dados_finais = []
    lotes_existentes = set()
    
    if os.path.exists(_FINAL_OUTPUT):
        with open(_FINAL_OUTPUT, 'r', encoding='utf-8') as f:
            try:
                dados_finais = json.load(f)
                for item in dados_finais:
                    lotes_existentes.add(item.get("lote"))
                print(f"[*] Base existente carregada com {len(dados_finais)} lotes.")
            except:
                print("[!] Arquivo final existente está corrompido ou vazio. Iniciando do zero.")
                dados_finais = []
                
    # 2. Procurar arquivos parciais gerados pelos bots
    arquivos_parciais = glob.glob(os.path.join(_OUTPUT_DIR, "dados_santos_enriquecido_*.json"))
    
    if not arquivos_parciais:
        print("[!] Nenhum arquivo parcial encontrado para mesclar.")
        return
        
    lotes_adicionados = 0
    
    for arq in arquivos_parciais:
        print(f"  -> Processando: {os.path.basename(arq)}")
        try:
            with open(arq, 'r', encoding='utf-8') as f:
                dados_parciais = json.load(f)
                
            for lote_d in dados_parciais:
                lote_id = lote_d.get("lote")
                if lote_id not in lotes_existentes:
                    dados_finais.append(lote_d)
                    lotes_existentes.add(lote_id)
                    lotes_adicionados += 1
                else:
                    # Lógica de "Upgrade": Se o lote já existe, verifica se o novo tem mais dados
                    idx = next((i for i, x in enumerate(dados_finais) if x.get("lote") == lote_id), None)
                    if idx is not None:
                        old_lote = dados_finais[idx]
                        upgraded = False
                        # Comparamos as economias uma a uma
                        for i, new_econ in enumerate(lote_d.get("economias", [])):
                            if i < len(old_lote.get("economias", [])):
                                old_econ = old_lote["economias"][i]
                                # Se o antigo não tinha proprietário/CPF e o novo tem, atualiza
                                if not old_econ.get("proprietario") and new_econ.get("proprietario"):
                                    old_econ["proprietario"] = new_econ["proprietario"]
                                    upgraded = True
                                if not old_econ.get("cpf_cnpj") and new_econ.get("cpf_cnpj"):
                                    old_econ["cpf_cnpj"] = new_econ["cpf_cnpj"]
                                    upgraded = True
                        
                        if upgraded:
                            print(f"      [+] Lote {lote_id} ATUALIZADO com novos dados de proprietário/CPF.")
                            lotes_adicionados += 1
        except Exception as e:
            print(f"      [X] Erro ao ler {arq}: {e}")
            
    # 3. Salvar o arquivo final
    if lotes_adicionados > 0:
        with open(_FINAL_OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(dados_finais, f, ensure_ascii=False, indent=4)
        print(f"\n[+] Sucesso! {lotes_adicionados} NOVOS lotes foram mesclados no arquivo final.")
    else:
        print("\n[*] Nenhum lote novo encontrado para mesclar.")
        
    print(f"Total de lotes na base unificada: {len(dados_finais)}")
    
    # 4. Limpeza opcional (Locks e arquivos parciais)
    resp = input("\nDeseja apagar os arquivos parciais e limpar a pasta de reservas? (s/n): ")
    if resp.lower() == 's':
        for arq in arquivos_parciais:
            os.remove(arq)
            print(f"  [-] Removido: {os.path.basename(arq)}")
            
        if os.path.exists(_RESERVAS_DIR):
            lock_files = glob.glob(os.path.join(_RESERVAS_DIR, "*.lock"))
            for lock in lock_files:
                try:
                    os.remove(lock)
                except:
                    pass
            print(f"  [-] {len(lock_files)} travas (locks) removidas.")
            
        print("[✔] Limpeza concluída!")

if __name__ == "__main__":
    main()
