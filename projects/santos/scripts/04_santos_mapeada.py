# MetroMarGeo - Inteligência Geográfica Metrópole & Mar
import requests
import json
import pandas as pd
import sys
import argparse

def extrair_dados_santos(bairro=None, logradouro=None, max_features=1000):
    """
    Extrai dados de lotes/imóveis do GeoServer da Prefeitura de Santos.
    """
    url = "https://egov.santos.sp.gov.br/geoserver/santos/ows"
    
    # Construir filtro CQL
    filters = []
    if bairro:
        filters.append(f"bairro='{bairro}'")
    if logradouro:
        filters.append(f"logradouro='{logradouro}'")
    
    cql_filter = " AND ".join(filters) if filters else "1=1"
    
    params = {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": "santos:lotes",
        "maxFeatures": max_features,
        "outputFormat": "application/json",
        "cql_filter": cql_filter
    }
    
    print(f"Buscando dados com filtro: {cql_filter}...")
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        features = data.get("features", [])
        if not features:
            return None
            
        registros = []
        for f in features:
            item = f["properties"]
            # Adicionar ID único do lote como referência
            item["id_unico"] = f["id"]
            # Adicionar coordenadas simplificadas (centroide ou ponto inicial)
            geom = f["geometry"]
            if geom["type"] == "MultiPolygon":
                # Ponto de referência (primeiro ponto do primeiro polígono)
                coords = geom["coordinates"][0][0][0]
                item["coord_x"] = coords[0]
                item["coord_y"] = coords[1]
            registros.append(item)
            
        return pd.DataFrame(registros)
        
    except Exception as e:
        print(f"Erro na extração: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extrator de Dados Imobiliários - Santos Mapeada')
    parser.add_argument('--bairro', type=str, help='Nome do bairro (ex: "Aparecida")')
    parser.add_argument('--rua', type=str, help='Nome completo do logradouro (ex: "Rua Dona Anália Franco")')
    parser.add_argument('--limite', type=int, default=1000, help='Limite de registros')
    parser.add_argument('--output', type=str, default='dados_imoveis_santos.json', help='Arquivo de saída')
    
    args = parser.parse_args()
    
    df = extrair_dados_santos(bairro=args.bairro, logradouro=args.rua, max_features=args.limite)
    
    if df is not None:
        df.to_json(args.output, orient='records', force_ascii=False, indent=4)
        print(f"\nSucesso! {len(df)} registros salvos em: {args.output}")
        print("\nColunas extraídas:")
        print(", ".join(df.columns))
    else:
        print("\nNenhum dado encontrado para os critérios informados.")
