# MetroMarGeo - Inteligência Geográfica Metrópole & Mar
import requests
import pandas as pd
import ddddocr
import urllib3
from bs4 import BeautifulSoup
import json
import os
import time
import re
from html import unescape

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PeruibeFase2Extractor:
    def __init__(self):
        self.base_url = "https://servicosonline.gcaspp.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def query_ficha_cadastral(self, inscricao):
        url = f"{self.base_url}/wpfichacadastralR.aspx"
        try:
            r1 = self.session.get(url, verify=False, timeout=20)
            match = re.search(r'name="GXState" value=\'(.*?)\'', r1.text)
            if not match:
                match = re.search(r'id="GXState" value=\'(.*?)\'', r1.text)
            
            if match:
                gxstate = unescape(match.group(1))
                data = {
                    "GXState": gxstate,
                    "vCDSISTEMA": "0",
                    "vINSCRICAOMUNICIPAL": inscricao,
                    "_EventName": "E'ENTER'.",
                    "_EventGridId": "",
                    "_EventRowId": ""
                }
                
                r2 = self.session.post(url, data=data, verify=False, timeout=30)
                if r2.status_code == 200:
                    if "Cadastro não encontrado" in r2.text:
                        return {"inscricao": inscricao, "status": "nao_encontrado"}
                    
                    # Extrair dados do HTML de sucesso
                    soup = BeautifulSoup(r2.text, 'html.parser')
                    dados = {"inscricao": inscricao, "status": "sucesso"}
                    
                    # No GeneXus, os dados costumam vir em spans com IDs específicos
                    # Vamos buscar por labels e seus valores próximos
                    campos = {
                        "vNMPROPRIETARIO": "proprietario",
                        "vDSLOGRADOURO": "logradouro",
                        "vNRIMOVEL": "numero",
                        "vDSBAIRRO": "bairro",
                        "vNRCEP": "cep",
                        "vQTDT_AREA_TERRENO": "area_terreno",
                        "vQTDT_AREA_CONSTRUIDA": "area_construida"
                    }
                    
                    for gx_id, label in campos.items():
                        # O GeneXus costuma colocar o ID no span que contém o valor
                        span = soup.find('span', {'id': re.compile(gx_id, re.I)})
                        if span:
                            dados[label] = span.text.strip()
                        else:
                            # Tentar encontrar por label se o ID falhar
                            label_tag = soup.find('label', string=re.compile(label, re.I))
                            if label_tag:
                                val = label_tag.find_next('span')
                                if val: dados[label] = val.text.strip()
                    
                    return dados
            return None
        except Exception as e:
            print(f"Erro na consulta: {e}")
        return None

if __name__ == "__main__":
    ext = PeruibeFase2Extractor()
    res = ext.query_ficha_cadastral("1.7.133.0000")
    if res:
        print(f"Dados extraídos: {json.dumps(res, indent=2, ensure_ascii=False)}")
    else:
        print("Falha na consulta.")
