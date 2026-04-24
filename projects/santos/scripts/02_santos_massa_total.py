# --- EXTRAÇÃO DE MASSA TOTAL - SANTOS (METROMARGEO) ---
# Este script se conecta ao servidor de mapas (GeoServer) da prefeitura de Santos
# para baixar todos os lotes cadastrados no município por bairro.

import requests
import pandas as pd
import time
import os
import re

class SantosMassExtractor:
    """
    Motor encargado de coletar o mapeamento base (lotes e áreas) de Santos.
    """
    def __init__(self):
        # URL oficial do serviço Geográfico de Santos (WFS)
        self.geoserver_url = "https://egov.santos.sp.gov.br/geoserver/santos/ows"
        self.session = requests.Session()

    def fetch_layer(self, layer, bairro=None, limit=10000):
        """Faz a requisição de uma camada específica (ex: lotes, bairros)."""
        params = {
            "service": "WFS", "version": "1.0.0", "request": "GetFeature",
            "typeName": layer, "maxFeatures": limit, "outputFormat": "application/json"
        }
        if bairro:
            # Filtro Geográfico CQL: Filtra os dados por nome do bairro
            params["cql_filter"] = f"bairro='{bairro}'"
        try:
            r = self.session.get(self.geoserver_url, params=params, timeout=60)
            if r.status_code == 200:
                return r.json().get('features', [])
        except: pass
        return []

    def format_inscricao_santos(self, lote_str):
        """Converte o ID do mapa para o padrão oficial de 11 dígitos da prefeitura."""
        numeric_lote = re.sub(r'[^0-9]', '', str(lote_str))
        if len(numeric_lote) == 8:
            # Muitos lotes no mapa são de 8 dígitos, adicionamos 000 para a unidade base
            numeric_lote = f"{numeric_lote}000"
        return f"{numeric_lote[0:2]}.{numeric_lote[2:5]}.{numeric_lote[5:8]}.{numeric_lote[8:11]}"

    def process_bairro(self, bairro, limit=10000):
        """Cruza dados de camadas diferentes: Lotes + Área + Zoneamento (LUOS)."""
        print(f"--- Extraindo Bairro: {bairro} ---")
        
        lotes_feat = self.fetch_layer("santos:lotes", bairro, limit)
        areas_feat = self.fetch_layer("santos:lotesarea", bairro, limit)
        luos_feat = self.fetch_layer("santos:lotesluos", bairro, limit)

        # Mapeamos as áreas e zonas por ID do lote para busca rápida
        areas_map = {f['properties']['lote']: f['properties'].get('area', '') for f in areas_feat}
        luos_map = {f['properties']['lote']: f['properties'].get('zona', '') for f in luos_feat}

        data = []
        for f in lotes_feat:
            p = f['properties']
            lote_raw = str(p['lote'])
            data.append({
                "inscricao_original": lote_raw,
                "inscricao_formatada": self.format_inscricao_santos(lote_raw),
                "logradouro": p.get('logradouro', ''),
                "numero": p.get('numero', ''),
                "bairro": p.get('bairro', ''),
                "area_m2": areas_map.get(lote_raw, ''),
                "zona_luos": luos_map.get(lote_raw, '')
            })
        return pd.DataFrame(data)

if __name__ == "__main__":
    ext = SantosMassExtractor()
    # Pega a lista de bairros oficiais do sistema
    bairros = sorted(list(set([f['properties']['nome'] for f in ext.fetch_layer("santos:bairros")])))
    
    # --- CAMINHO DE SAÍDA ATUALIZADO ---
    base_path = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_path, "..", "data", "output", "extracao_santos_total")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for bairro in bairros:
        try:
            df = ext.process_bairro(bairro, limit=50) # Amostra para demonstração
            if df is not None:
                filename = os.path.join(output_dir, f"DADOS_SANTOS_{bairro.replace(' ', '_').upper()}.json")
                df.to_json(filename, orient='records', force_ascii=False, indent=4)
                print(f"Sucesso: registros salvos em {filename}")
        except Exception as e:
            print(f"Erro no bairro {bairro}: {e}")
