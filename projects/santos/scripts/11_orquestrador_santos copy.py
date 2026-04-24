import subprocess
import time
import os
import sys

# --- CONFIGURAÇÃO ---
NUM_INSTANCIAS = 5
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_BOT = os.path.join(SCRIPT_DIR, "09_santos_enrichment_bot.py")

def main():
    print("==========================================================")
    print(f"ORQUESTRADOR SANTOS: INICIANDO {NUM_INSTANCIAS} INSTANCIAS")
    print("==========================================================")
    print(f"PID do Orquestrador: {os.getpid()}")
    print(f"Script alvo: {os.path.basename(SCRIPT_BOT)}")
    print("----------------------------------------------------------")
    
    processos = []
    
    try:
        for i in range(NUM_INSTANCIAS):
            print(f"[*] Lançando Instância #{i+1} na fila...")
            # Inicia o processo do bot
            p = subprocess.Popen([sys.executable, SCRIPT_BOT])
            processos.append(p)
            # Pequeno delay maior (10s) para evitar sobrecarga no servidor e erros de timeout inicial
            time.sleep(10) 
            
        print("\n[OK] Todas as instancias estao em execucao.")
        print("[!] Pressione Ctrl+C para encerrar o orquestrador e todos os bots.\n")
        
        while True:
            vivos = 0
            for i, p in enumerate(processos):
                status = p.poll()
                if status is None:
                    vivos += 1
                elif status != 0:
                    # Opcional: reiniciar o processo se ele falhar catastróficamente
                    # print(f"  [!] Instância #{i+1} encerrou com erro (code {status}).")
                    pass
            
            if vivos == 0:
                print("\n[DONE] Todos os bots finalizaram suas tarefas.")
                break
            
            # Atualização de status a cada 30 segundos no console
            # print(f"  [Status] {vivos}/{NUM_INSTANCIAS} instâncias ativas...")
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n[STOP] Interrupcao detectada! Finalizando todos os processos filhos...")
        for p in processos:
            try:
                p.terminate()
            except:
                pass
        print("[OK] Bots encerrados com sucesso.")
        
    except Exception as e:
        print(f"\n[X] Erro crítico no orquestrador: {e}")
        for p in processos:
            p.terminate()

if __name__ == "__main__":
    main()
