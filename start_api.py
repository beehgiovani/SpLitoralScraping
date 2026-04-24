import os
import subprocess
import glob

def start_api():
    r"""
    [O TRADUTOR DO WINDOWS]: Script em Python para facilitar o boot da API Java.
    Este script resolve automaticamente os erros de 'C:\Program' que o Windows costuma dar
    quando o Java está instalado em pastas com espaços.
    """
    # Descobre onde este script está salvo (raiz do projeto)
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define o caminho para a nova estrutura de pastas por cidade
    api_dir = os.path.join(root_dir, "projects", "santos", "server", "santos-api")
    
    print("--- Ativador de API MetroMarGeo ---")
    
    # 1. BUSCA INTELIGENTE: Tenta encontrar o Java 17 instalado no seu PC
    java_cmd = "java"
    try:
        # Tenta rodar 'java -version' para ver se ele já está configurado no Windows
        subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT)
    except:
        print("  [!] Java não está no PATH. Procurando no computador...")
        # Locais comuns onde o instalador (winget, Microsoft, Oracle) coloca o Java
        common_paths = [
            "C:\\Program Files\\Microsoft\\jdk-17*\\bin\\java.exe",
            "C:\\Program Files\\Java\\jdk-17*\\bin\\java.exe",
            "C:\\Program Files\\Android\\Android Studio\\jbr\\bin\\java.exe"
        ]
        found = False
        for path in common_paths:
            # O 'glob' permite usar o asterisco (*) para achar qualquer sub-versão
            matches = glob.glob(path)
            if matches:
                # Se achou, salva o caminho completo entre aspas para não dar erro de espaço
                java_cmd = f'"{matches[0]}"'
                found = True
                print(f"  [+] Encontrado: {java_cmd}")
                break
        
        if not found:
            print("  [ERR] Java 17 não encontrado. Instale via: winget install Microsoft.OpenJDK.17")
            return

    # 2. VERIFICAÇÃO: Confere se o motor do Java (Maven Wrapper) está na pasta certa
    mvnw_cmd = os.path.join(api_dir, "mvnw.cmd")
    if not os.path.exists(mvnw_cmd):
        print(f"  [ERR] O arquivo mvnw.cmd não foi encontrado em {api_dir}")
        return

    # 3. MÁGICA DE AMBIENTE: Injeta o Java no PATH temporariamente
    # Extraímos a pasta 'bin' do caminho do Java encontrado.
    bin_dir = os.path.dirname(java_cmd.replace('"', ''))
    
    # Configuramos o JAVA_HOME e o PATH apenas para esta janela do terminal.
    # Isso evita que você precise configurar o Windows manualmente toda vez.
    os.environ["JAVA_HOME"] = os.path.dirname(bin_dir)
    os.environ["PATH"] = bin_dir + os.path.pathsep + os.environ.get("PATH", "")
    
    print(f"  [*] Ambiente configurado com JAVA_HOME: {os.environ['JAVA_HOME']}")

    # 4. DECOLAGEM: Inicia o servidor Spring Boot
    print(f"  [*] Iniciando API em {api_dir}...")
    try:
        # Entra na pasta do servidor Java
        os.chdir(api_dir)
        # Executa o Maven: ele baixa o que for preciso e abre o servidor na porta 8080.
        subprocess.run(f"mvnw.cmd spring-boot:run", shell=True, check=True)
    except Exception as e:
        print(f"  [ERR] Erro ao iniciar a API: {e}")

if __name__ == "__main__":
    start_api()
