import json
import os
import glob
import folium
from folium.plugins import MarkerCluster, Search
from pyproj import Transformer

# Configurações de caminhos
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data", "output")
INPUT_PATTERN = os.path.join(DATA_DIR, "dados_santos_enriquecido*.json")
BAIRROS_GEOJSON = os.path.join(DATA_DIR, "santos_bairros.json")
OUTPUT_MAP = os.path.join(DATA_DIR, "santos_map.html")

# Projeção: UTM Zone 23S -> WGS84
transformer = Transformer.from_crs("epsg:31983", "epsg:4326", always_xy=True)

def convert_coords(x, y):
    try:
        lon, lat = transformer.transform(x, y)
        return lat, lon
    except:
        return None, None

def sanitize_js(text):
    if not isinstance(text, str):
        return str(text)
    return text.replace("`", "\\`").replace("'", "\\'").replace('"', '\\"').replace("\n", " ").replace("\r", "")

def format_currency_python(value):
    try:
        if isinstance(value, str):
            value = float(value.replace(".", "").replace(",", "."))
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def load_and_merge_data():
    files = glob.glob(INPUT_PATTERN)
    all_data = {}
    print(f"Lendo {len(files)} arquivos...")
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                batch = json.load(f)
                for item in batch:
                    lote_id = item.get("lote")
                    if not lote_id: continue
                    if lote_id not in all_data:
                        all_data[lote_id] = item
                    else:
                        existing_econs = {e.get("lote_completo_11") for e in all_data[lote_id].get("economias", [])}
                        for econ in item.get("economias", []):
                            if econ.get("lote_completo_11") not in existing_econs:
                                all_data[lote_id].setdefault("economias", []).append(econ)
        except Exception as e:
            print(f"Erro ao ler {file_path}: {e}")
    return list(all_data.values())

def generate_demand_map():
    data = load_and_merge_data()
    if not data: return

    # Organizar dados POR BAIRRO para o JIT Loading
    bairros_db = {}
    for lote in data:
        lat, lon = convert_coords(lote.get("coord_x"), lote.get("coord_y"))
        if not lat or not lon: continue
        
        b = lote.get("bairro", "N/A").strip().upper()
        if b not in bairros_db: bairros_db[b] = []
        
        economias = lote.get("economias", [])
        v_venal = sum([float(e.get("valor_venal_total", "0").replace(".", "").replace(",", ".")) for e in economias if isinstance(e.get("valor_venal_total"), str)])
        props = sorted(list(set([e.get("proprietario") for e in economias if e.get("proprietario")])))
        missing = sum([1 for e in economias if not e.get("proprietario")])
        
        bairros_db[b].append({
            "id": lote.get("lote"),
            "addr": f"{lote.get('logradouro', '')}, {lote.get('numero', '')}",
            "units": len(economias),
            "v": format_currency_python(v_venal),
            "m": missing,
            "o": props,
            "lt": lat, "ln": lon
        })

    # Carregar Polígonos dos Bairros
    with open(BAIRROS_GEOJSON, 'r', encoding='utf-8') as f:
        geojson_bairros = json.load(f)

    # Inicializar o mapa
    m = folium.Map(location=[-23.96, -46.33], zoom_start=14, tiles=None)
    # Camadas Base
    folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Satélite').add_to(m)
    folium.TileLayer('cartodb dark_matter', name='Dark Mode').add_to(m)
    
    # Forçar o Folium a incluir as dependências (MarkerCluster, AwesomeMarkers, FontAwesome)
    # Criando objetos "dummy" que registram esses plugins no cabeçalho na ordem correta
    _ = MarkerCluster().add_to(m)
    _ = folium.Marker([0,0], icon=folium.Icon(color='blue', icon='home', prefix='fa'), opacity=0).add_to(m)

    # CSS para Sidebar e Estilo
    custom_css = """
    <style>
        #sidebar { position: fixed; top: 10px; left: 10px; width: 250px; height: 95vh; background: rgba(34,34,34,0.95); 
                    z-index: 1000; overflow-y: auto; color: white; padding: 15px; border-radius: 10px; font-family: sans-serif;
                    box-shadow: 0 0 20px rgba(0,0,0,0.5); border: 1px solid #444; }
        .b-item { padding: 8px; cursor: pointer; border-bottom: 1px solid #333; transition: 0.2s; }
        .b-item:hover { background: #444; color: #00d2ff; }
        .active-b { background: #00d2ff !important; color: black !important; font-weight: bold; }
        #search-b { width: 100%; padding: 8px; margin-bottom: 10px; border-radius: 5px; border: none; background: #444; color: white; }
    </style>
    """
    m.get_root().header.add_child(folium.Element(custom_css))

    # Sidebar HTML
    b_names = sorted(bairros_db.keys())
    sidebar_html = f"""
    <div id="sidebar">
        <h3 style="color: #00d2ff; margin-top: 0;">Seleção de Bairro</h3>
        <input type="text" id="search-b" placeholder="Filtrar bairro..." onkeyup="filterBairros()">
        <div id="b-list">
            {" ".join([f'<div class="b-item" onclick="loadBairro(\'{name}\', this)">{name} ({len(bairros_db[name])})</div>' for name in b_names])}
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(sidebar_html))

    # JS Logic
    bairros_json_str = json.dumps(bairros_db)
    # Folium gera um ID único para o mapa (map_xxxx), precisamos usá-lo no JS
    map_id = m.get_name()
    
    jit_js = f"""
    <script>
        var BAIRROS_DATA = {bairros_json_str};
        var currentCluster = null;
        
        function filterBairros() {{
            let q = document.getElementById('search-b').value.toUpperCase();
            document.querySelectorAll('.b-item').forEach(el => {{
                el.style.display = el.innerText.includes(q) ? 'block' : 'none';
            }});
        }}

        function loadBairro(name, el) {{
            // UI Update
            document.querySelectorAll('.b-item').forEach(x => x.classList.remove('active-b'));
            if(el) el.classList.add('active-b');
            
            var map_obj = {map_id}; // Referência ao mapa do Folium
            
            // Clear Map
            if(currentCluster) map_obj.removeLayer(currentCluster);
            
            currentCluster = L.markerClusterGroup({{ chunkedLoading: true }});
            
            let data = BAIRROS_DATA[name];
            if(!data) return;
            
            let bounds = L.latLngBounds();
            
            data.forEach(p => {{
                let color = "blue";
                if (p.m > 0) color = "orange";
                if (p.m === p.units) color = "red";
                
                let marker = L.marker([p.lt, p.ln], {{
                    icon: L.AwesomeMarkers.icon({{icon: 'home', markerColor: color, prefix: 'fa'}})
                }});
                
                marker.on('click', function(e) {{
                    marker.bindPopup(buildPopup(p)).openPopup();
                }});
                
                currentCluster.addLayer(marker);
                bounds.extend([p.lt, p.ln]);
            }});
            
            map_obj.addLayer(currentCluster);
            map_obj.fitBounds(bounds);
        }}

        function buildPopup(p) {{
            let p_html = p.o.length > 0 
                ? '<ul>' + p.o.slice(0, 10).map(o => `<li>${{o}}</li>`).join('') + (p.o.length > 10 ? `<li>... e mais ${{p.o.length-10}}</li>` : '') + '</ul>'
                : '<i style="color: #888;">Não localizado</i>';

            return `
            <div style="font-family: 'Segoe UI', Arial; color: #eee; background-color: #222; padding: 12px; border-radius: 8px; min-width: 250px;">
                <h4 style="margin: 0 0 8px 0; color: #00d2ff; border-bottom: 1px solid #444;">Lote: ${{p.id}}</h4>
                <div style="font-size: 0.9em;">
                    <p style="margin: 3px 0;">📍 <b>Endereço:</b> ${{p.addr}}</p>
                    <p style="margin: 3px 0;">🔢 <b>Unidades:</b> ${{p.units}}</p>
                    <p style="margin: 3px 0;">💰 <b>Valor Venal:</b> <span style="color: #4cd137;">${{p.v}}</span></p>
                    <p style="margin: 3px 0;">⚠️ <b>Faltam Proprietários:</b> ${{p.m}}</p>
                    <div style="margin-top: 8px; border-top: 1px solid #444; padding-top: 5px;">
                        <b>👥 Proprietários:</b>
                        <div style="max-height: 80px; overflow-y: auto; background: #333; padding: 4px; border-radius: 4px; margin-top: 3px;">
                            ${{p_html}}
                        </div>
                    </div>
                </div>
                <a href="https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${{p.lt}},${{p.ln}}" target="_blank" 
                   style="display: block; text-align: center; background-color: #00d2ff; color: #000; padding: 8px; border-radius: 4px; text-decoration: none; font-weight: bold; margin-top: 10px;">
                   ABRIR STREET VIEW
                </a>
            </div>`;
        }}
    </script>
    """
    m.get_root().html.add_child(folium.Element(jit_js))

    # Camada de Bairros (Polígonos Interativos)
    def style_bairros(feature):
        return {
            'fillColor': '#00d2ff',
            'color': 'white',
            'weight': 1,
            'fillOpacity': 0.1
        }

    def highlight_bairros(feature):
        return {
            'fillOpacity': 0.4,
            'weight': 2
        }

    gj_bairros = folium.GeoJson(
        geojson_bairros,
        name="Divisão por Bairros",
        style_function=style_bairros,
        highlight_function=highlight_bairros,
        tooltip=folium.GeoJsonTooltip(fields=['nome'], aliases=['Bairro:'])
    ).add_to(m)

    # Injetar Clique no Polígono para carregar
    gj_bairros.add_child(folium.Element("""
        <script>
            {
                let layer = %s;
                layer.on('click', function(e) {
                    let name = e.layer.feature.properties.nome.toUpperCase();
                    loadBairro(name);
                });
            }
        </script>
    """ % gj_bairros.get_name()))

    # Adicionar mais opções de camadas base
    folium.TileLayer('openstreetmap', name='OpenStreetMap', overlay=False).add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satélite (Esri)',
        overlay=False
    ).add_to(m)

    # Controle de Camadas (Sempre no final)
    folium.LayerControl(collapsed=False).add_to(m)

    print(f"Salvando mapa JIT em: {OUTPUT_MAP}")
    m.save(OUTPUT_MAP)
    print("Sucesso!")

if __name__ == "__main__":
    generate_demand_map()
