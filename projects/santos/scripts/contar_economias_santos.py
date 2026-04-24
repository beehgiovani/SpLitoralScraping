import json
import os
import glob

def contar_economias():
    output_dir = 'c:/Users/bruno/AndroidStudioProjects/Metromargeo/projects/santos/data/output'
    # O padrão '*' já captura tanto o arquivo mestre quanto os parciais (ex: arquivo.json e arquivo_123.json)
    arquivos = glob.glob(os.path.join(output_dir, 'dados_santos_enriquecido*.json'))
    
    if not arquivos:
        print(f"Nenhum arquivo de dados gerado em {output_dir} ainda.")
        return

    print(f"Localizados {len(arquivos)} arquivos para analise:")
    for arq in arquivos:
        print(f"   - {os.path.basename(arq)}")

    lotes_base = 0
    total_economias = 0
    sem_proprietario = 0
    sem_cpf = 0
    arquivos_lidos = 0

    for arquivo in arquivos:
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            lotes_base += len(data)
            for lote in data:
                economias = lote.get('economias', [])
                total_economias += len(economias)
                for eco in economias:
                    if not eco.get('proprietario'):
                        sem_proprietario += 1
                    if not eco.get('cpf_cnpj'):
                        sem_cpf += 1
            
            arquivos_lidos += 1
            
        except json.JSONDecodeError:
            print(f"\n[!] O Robo esta gravando em {os.path.basename(arquivo)} neste exato milissegundo. Pulando este temporariamente...\n")
        except Exception as e:
            print(f"Erro inesperado no arquivo {os.path.basename(arquivo)}: {e}")

    print(f"\n==============================================")
    print(f"ESTATISTICA EM TEMPO REAL DOS BOTS:")
    print(f"==============================================")
    print(f"Arquivos JSON Lidos........: {arquivos_lidos}")
    print(f"Terrenos/Lotes Extraidos...: {lotes_base}")
    print(f"Economias/Salas Extraidas..: {total_economias}")
    print(f"Sem Nome Proprietario......: {sem_proprietario}")
    print(f"Sem CPF/CNPJ...............: {sem_cpf}")
    print(f"==============================================\n")

if __name__ == "__main__":
    contar_economias()
