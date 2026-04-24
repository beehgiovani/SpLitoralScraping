# --- EXTRAÇÃO GEOSAMPA - SÃO PAULO CAPITAL (METROMARGEO) ---
# Este script se conecta ao WFS (Web Feature Service) do GeoSampa para baixar
# informações sobre os Lotes Fiscais da maior cidade do país.

import requests
import pandas as pd
import json
import os
from concurrent.futures import ThreadPoolExecutor


class SaoPauloExtractor:
    """
    Motor de coleta para a Prefeitura de São Paulo.
    """

    def __init__(self):
        # Endpoint oficial do GeoSampa para requisições geográficas
        self.base_url = (
            "http://wfs.geosampa.prefeitura.sp.gov.br/geoserver/geoportal/wfs"
        )
        self.session = requests.Session()

    def fetch_features(self, type_name, cql_filter=None, limit=10000):
        """Busca as feições (features) no servidor geográfico com retentativas."""
        params = {
            "service": "WFS",
            "version": "1.0.0",
            "request": "GetFeature",
            "typeName": type_name,
            "maxFeatures": limit,
            "outputFormat": "application/json",
        }
        if cql_filter:
            params["cql_filter"] = cql_filter

        for attempt in range(3):
            try:
                r = self.session.get(self.base_url, params=params, timeout=60)
                if r.status_code == 200:
                    return r.json().get("features", [])
            except:
                continue
        return []

    def format_inscricao_sao_paulo(self, setor, quadra, lote):
        """Formata o SQL (Setor-Quadra-Lote) e calcula o Dígito Verificador (DV)."""
        s, q, l = str(setor).zfill(3), str(quadra).zfill(3), str(lote).zfill(4)
        sql_basico = f"{s}{q}{l}"

        # Algoritmo de DV oficial de SP (Módulo 11 reverso)
        soma, mult = 0, 2
        for char in reversed(sql_basico):
            soma += int(char) * mult
            mult = 1 if mult == 10 else mult + 1
        resto = soma % 11
        digito = 0 if resto == 0 else (1 if resto == 1 else 11 - resto)

        return f"{s}.{q}.{l}-{digito}"

    def process_all_setores(self, max_workers=2):
        """Gerencia a extração paralela usando Threads para ganhar velocidade."""
        # --- DEFINIÇÃO DE CAMINHOS ---
        base_path = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(base_path, "..", "data", "extracao_sao_paulo")

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 1. Resgata a lista de todos os setores fiscais (bairros/regiões)
        setores = sorted(
            list(
                set(
                    [
                        f["properties"]["cd_setor_fiscal"]
                        for f in self.fetch_features("geoportal:setor_fiscal")
                    ]
                )
            )
        )

        print(f"Iniciando extração paralela de {len(setores)} setores...")
        all_data = []

        # O ThreadPoolExecutor permite baixar vários setores ao mesmo tempo
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Em cada thread, o Java extrai os lotes de um setor específico
            for setor_data in executor.map(self.extract_lotes_by_setor, setores):
                if setor_data:
                    all_data.extend(setor_data)

        if all_data:
            df = pd.DataFrame(all_data)
            filename = os.path.join(output_dir, "DADOS_SAO_PAULO_COMPLETO.json")
            df.to_json(filename, orient="records", force_ascii=False, indent=4)
            print(f"Sucesso: {len(df)} registros salvos em {filename}")

    def extract_lotes_by_setor(self, setor_fiscal):
        """Extrai lotes individuais de um setor específico."""
        cql = f"cd_setor_fiscal='{setor_fiscal}'"
        lotes = self.fetch_features("geoportal:lote_cidadao", cql_filter=cql)

        data = []
        for f in lotes:
            p = f["properties"]
            data.append(
                {
                    "inscricao_formatada": self.format_inscricao_sao_paulo(
                        p.get("cd_setor_fiscal"),
                        p.get("cd_quadra_fiscal"),
                        p.get("cd_lote"),
                    ),
                    "logradouro": p.get("nm_logradouro_completo", ""),
                    "numero": p.get("cd_numero_porta", ""),
                    "bairro": p.get("bairro", ""),
                    "area_m2": p.get("qt_area_terreno", ""),
                }
            )
        return data


if __name__ == "__main__":
    SaoPauloExtractor().process_all_setores()
