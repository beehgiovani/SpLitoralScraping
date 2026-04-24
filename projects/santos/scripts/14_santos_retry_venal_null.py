import os
import json
import sys

# Força UTF-8 no stdout do Windows para evitar UnicodeEncodeError com cp1252
sys.stdout.reconfigure(encoding="utf-8")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_OUTPUT_DIR = os.path.join(_SCRIPT_DIR, "..", "data", "output")
_CONSOLIDATED_FILE = os.path.join(_OUTPUT_DIR, "dados_santos_enriquecido.json")

# Saidas
_TXT_RETRY_LIST = os.path.join(_OUTPUT_DIR, "santos_lotes_retry_venal.txt")
_JSON_RETRY_LOTES = os.path.join(_OUTPUT_DIR, "dados_santos_retry_venal.json")


def main():
    print("=" * 70)
    print("  AUDITOR DE QUALIDADE: VALOR VENAL NULO (SANTOS)")
    print("=" * 70)

    if not os.path.exists(_CONSOLIDATED_FILE):
        print(f"[X] Arquivo consolidado nao encontrado: {_CONSOLIDATED_FILE}")
        return

    with open(_CONSOLIDATED_FILE, "r", encoding="utf-8") as f:
        database = json.load(f)

    total_lotes = len(database)
    total_economias = 0
    economias_venal_null = 0
    lotes_afetados = []  # Lista de dicts dos lotes pais que precisam re-scan
    lotes_ids_afetados = set()

    for lote in database:
        lote_id = lote.get("lote", "???")
        economias = lote.get("economias", [])
        lote_tem_problema = False

        for econ in economias:
            total_economias += 1

            vt = econ.get("valor_venal_total")
            vc = econ.get("valor_venal_construcao")
            vr = econ.get("valor_venal_terreno")

            # Todos os 3 campos nulos = certidao falhou completamente
            if vt is None and vc is None and vr is None:
                economias_venal_null += 1
                lote_tem_problema = True

        if lote_tem_problema:
            lotes_afetados.append(lote)
            lotes_ids_afetados.add(str(lote_id))

    # --- Relatorio ---
    print(f"\n[*] Base analisada: {_CONSOLIDATED_FILE}")
    print(f"    Total de Lotes:                 {total_lotes:,}")
    print(f"    Total de Economias:             {total_economias:,}")
    print(f"    Economias com Venal 100% NULL:  {economias_venal_null:,}")
    print(f"    Lotes Pais Afetados (unicos):   {len(lotes_afetados):,}")

    if economias_venal_null == 0:
        print(
            "\n[OK] Parabens! Todas as economias possuem ao menos um valor venal preenchido."
        )
        return

    pct = (economias_venal_null / total_economias * 100) if total_economias > 0 else 0
    print(f"    Percentual de falha:            {pct:.2f}%")

    # --- Salvar TXT com lotes pais para retry ---
    with open(_TXT_RETRY_LIST, "w", encoding="utf-8") as f:
        for lid in sorted(lotes_ids_afetados):
            f.write(lid + "\n")
    print(
        f"\n[+] Lista de lotes para re-scan salva em: {os.path.basename(_TXT_RETRY_LIST)}"
    )

    # --- Salvar JSON filtrado (apenas lotes afetados, estrutura identica a original) ---
    # Isso permite que o bot 09 consuma diretamente sem adaptacoes
    with open(_JSON_RETRY_LOTES, "w", encoding="utf-8") as f:
        json.dump(lotes_afetados, f, ensure_ascii=False, indent=4)
    print(
        f"[+] JSON com {len(lotes_afetados)} lotes afetados salvo em: {os.path.basename(_JSON_RETRY_LOTES)}"
    )

    # --- Remover esses lotes do arquivo de concluidos para permitir re-scan ---
    _TXT_CONCLUIDOS = os.path.join(_OUTPUT_DIR, "santos_lotes_concluidos.txt")
    if os.path.exists(_TXT_CONCLUIDOS):
        with open(_TXT_CONCLUIDOS, "r", encoding="utf-8") as f:
            concluidos = set(line.strip() for line in f if line.strip())

        removidos = concluidos & lotes_ids_afetados
        if removidos:
            novos_concluidos = concluidos - lotes_ids_afetados
            with open(_TXT_CONCLUIDOS, "w", encoding="utf-8") as f:
                for lid in sorted(novos_concluidos):
                    f.write(lid + "\n")
            print(
                f"[+] {len(removidos)} lotes removidos de '{os.path.basename(_TXT_CONCLUIDOS)}' para permitir re-varredura."
            )
        else:
            print(
                f"[*] Nenhum lote afetado encontrado em '{os.path.basename(_TXT_CONCLUIDOS)}'."
            )

    # --- Zerar as economias problematicas no JSON consolidado para forcar re-extracao limpa ---
    print(
        f"\n[?] Deseja LIMPAR as economias defeituosas da base consolidada para forcar re-extracao?"
    )
    print(
        f"    Isso vai REMOVER as {economias_venal_null} economias sem valor venal do arquivo principal."
    )
    resp = input("    (s/n): ").strip().lower()

    if resp == "s":
        economias_removidas = 0
        for lote in database:
            lote_id = str(lote.get("lote", ""))
            if lote_id in lotes_ids_afetados:
                economias_originais = lote.get("economias", [])
                # Remove apenas as economias que tem os 3 campos nulos
                economias_limpas = [
                    e
                    for e in economias_originais
                    if not (
                        e.get("valor_venal_total") is None
                        and e.get("valor_venal_construcao") is None
                        and e.get("valor_venal_terreno") is None
                    )
                ]
                removidas_neste = len(economias_originais) - len(economias_limpas)
                economias_removidas += removidas_neste
                lote["economias"] = economias_limpas

        with open(_CONSOLIDATED_FILE, "w", encoding="utf-8") as f:
            json.dump(database, f, ensure_ascii=False, indent=4)
        print(
            f"[OK] {economias_removidas} economias defeituosas removidas da base consolidada."
        )
        print(
            f"    Agora rode o bot '09_santos_enrichment_bot.py' normalmente - ele vai re-extrair os lotes faltantes."
        )
    else:
        print("[*] Base consolidada mantida intacta.")

    print(f"\n{'=' * 70}")
    print(f"  PROXIMOS PASSOS:")
    print(f"  1. Rode o orquestrador (11) ou o bot (09) normalmente")
    print(f"     -> Os lotes afetados ja foram desbloqueados do 'concluidos.txt'")
    print(f"  2. Apos a re-extracao, rode o merge (10) para unificar")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
