from flask import Flask, render_template_string, request
import feedparser
import requests
from datetime import datetime, timedelta, timezone
import threading
import time
from dateutil import parser

app = Flask(__name__)

# =============================
# CONFIGURAÇÕES
# =============================
VULNERS_API_KEY = "UD6IFI7QQ7AXK8YJB1AX2D0T2HD1H9XXBP1RW2DU01CCTG93U1244HXHCLN1Z0Y9"

RSS_FEEDS = {
    "Exploit Database": "https://www.exploit-db.com/rss.xml",
    "Vulners Alert": "https://vulners.com/rss.xml",
    "Microsoft Security Blog": "https://msrc.microsoft.com/blog/feed",
    "Microsoft Security Alert": "https://www.microsoft.com/en-us/security/blog/feed",
    "Sophos Security Advisories": "https://news.sophos.com/en-us/feed/",
    "Acronis Security Blog": "https://createfeed.fivefilters.org/extract.php?url=https://www.acronis.com/en-us/blog/categories/cybersecurity/&max=10&submit=Create+Feed",
    "Fortinet Security Advisories": "https://www.fortiguard.com/rss/ir.xml",
    "BoletimSec": "https://boletimsec.com.br/feed/"
}

SOURCE_COLORS = {
    "Vulners Alert": "#ff8800",
    "Microsoft Security Alert": "#FF09EA",
    "Exploit Database": "#f75c02",
    "Microsoft Security Blog": "#ff0000",
    "Sophos Security Advisories": "#2F5BD6",
    "Acronis Security Blog": "#541ed3",
    "Fortinet Security Advisories": "#228B22",
    "BoletimSec": "#EEFF00"
}

ULTIMAS_NOTICIAS = []
ULTIMA_ATUALIZACAO = None
UM_MES_ATRAS = datetime.now(timezone.utc) - timedelta(days=30)

# =============================
# FUNÇÕES DE COLETA
# =============================
def buscar_noticias_rss():
    noticias = []
    headers = {"User-Agent": "CVEVulnBot/1.0"}
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url, request_headers=headers)
            for entry in feed.entries[:15]:
                title = getattr(entry, "title", "")
                summary = getattr(entry, "summary", "")
                published_str = getattr(entry, 'published', None) or getattr(entry, 'updated', None)
                if not published_str:
                    continue
                try:
                    published_dt = parser.parse(published_str)
                    if published_dt.tzinfo is None:
                        published_dt = published_dt.replace(tzinfo=timezone.utc)
                    else:
                        published_dt = published_dt.astimezone(timezone.utc)
                except Exception:
                    continue
                if published_dt < UM_MES_ATRAS:
                    continue
                noticias.append({
                    "source": source,
                    "title": title,
                    "link": getattr(entry, "link", "#"),
                    "description": summary,
                    "published": published_dt.strftime("%Y-%m-%d %H:%M"),
                    "color": SOURCE_COLORS.get(source, "#000000")
                })
        except Exception as e:
            print(f"Erro ao ler feed {url}: {e}")
    return noticias

def buscar_noticias_vulners():
    endpoint = "https://vulners.com/api/v3/search/lucene/"
    agora = datetime.now(timezone.utc)
    query = f"published:[{UM_MES_ATRAS.strftime('%Y-%m-%d')} TO {agora.strftime('%Y-%m-%d')}]"

    params = {"query": query, "size": 100, "apiKey": VULNERS_API_KEY}
    noticias = []
    try:
        response = requests.get(endpoint, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data.get("result") == "OK":
            for item in data["data"]["search"]:
                doc = item["_source"]
                cve_list = doc.get("cvelist", [])
                cve_id = cve_list[0] if cve_list else doc.get("id", "Sem ID")
                descricao = doc.get("title", "Sem título")
                data_publicacao = doc.get("published", "")
                try:
                    published_dt = parser.parse(data_publicacao)
                    if published_dt.tzinfo is None:
                        published_dt = published_dt.replace(tzinfo=timezone.utc)
                    else:
                        published_dt = published_dt.astimezone(timezone.utc)
                except Exception:
                    continue
                if published_dt < UM_MES_ATRAS:
                    continue
                noticias.append({
                    "source": "Vulners Alert",
                    "title": f"{cve_id} - {descricao}",
                    "link": f"https://vulners.com/{doc.get('type', 'vuln')}/{doc.get('id')}",
                    "description": doc.get("description", "Sem descrição"),
                    "published": published_dt.strftime("%Y-%m-%d %H:%M"),
                    "color": SOURCE_COLORS.get("Vulners Alert", "#a17e56")
                })
    except Exception as e:
        print("Erro ao acessar API Vulners:", e)
    return noticias

# =============================
# THREAD DE ATUALIZAÇÃO
# =============================
def atualizar_noticias():
    global ULTIMAS_NOTICIAS, ULTIMA_ATUALIZACAO
    while True:
        try:
            vulners = buscar_noticias_vulners()
            rss = buscar_noticias_rss()
            ULTIMAS_NOTICIAS = sorted(vulners + rss, key=lambda x: x["published"], reverse=True)
            ULTIMA_ATUALIZACAO = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            print(f"[INFO] Notícias atualizadas em {ULTIMA_ATUALIZACAO} ({len(ULTIMAS_NOTICIAS)} itens)")
        except Exception as e:
            print("[ERRO] na atualização:", e)
        time.sleep(600)

threading.Thread(target=atualizar_noticias, daemon=True).start()

# =============================
# ROTA FLASK COM FILTRO
# =============================
@app.route('/')
def index():
    filtro = request.args.get("filtro", "Todos")
    if filtro == "Todos":
        noticias_filtradas = ULTIMAS_NOTICIAS
    else:
        noticias_filtradas = [n for n in ULTIMAS_NOTICIAS if n["source"] == filtro]

    html = """
    <html>
    <head>
        <title>Feed Hunt3r</title>
        <meta http-equiv="refresh" content="1800"> <!-- 30 min -->
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: black; margin: 0; padding: 20px;
                   background-image: linear-gradient(to right, #0B1340, transparent, #4A4E7D);}
            h1 { color: white; border-bottom: 3px solid #b22222; padding-bottom: 10px; font-weight: 600; display: flex; align-items: center; justify-content: space-between;}
            .update-time { color: #ccc; font-size: 0.9em; margin-bottom: 20px; }
            ul { list-style-type: none; padding: 0; }
            li { background: white; margin-bottom: 15px; padding: 15px 20px; border-radius: 12px;
                 box-shadow: 0 4px 10px rgba(0,0,0,0.1); transition: box-shadow 0.3s ease; }
            li:hover { box-shadow: 0 8px 20px rgba(0,0,0,0.2); background-color: #F6EBF9; }
            .logo{height: 220px;}
            a { text-decoration: none; font-size: 1.1em; font-weight: 600; color: #b22222; }
            a:hover{color:white; background-color: black;}
            small { display: block; color: #666; margin-top: 8px; font-style: italic; font-size: 0.9em; }
            .source { font-weight: bold; margin-bottom: 5px; display: flex; align-items: center; }
            .dot { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-right: 6px; }
            .published { color: #999; font-size: 0.8em; margin-top: 5px; }
            .filtros { margin-bottom: 20px; }
            .filtros select { margin-right: 10px; padding: 5px 10px; border-radius: 5px; font-size: 0.9em; }

            /* Carrossel */
            .carousel { width: 700px; height: 220px; overflow: hidden; position: relative; }
            .carousel img { width: 100%; height: 100%; position: absolute; left: 0; top: 0; opacity: 0; transition: opacity 1s ease-in-out; border-radius: 10px;}
            .carousel img.active { opacity: 1; }
        </style>
    </head>
    <body>
        <h1>
            <div>
                <img src="https://github.com/Script-Wolf/FILES/blob/main/Browsing.gif?raw=true" class="logo"> Feed Hunt3r
            </div>
            <div class="carousel">
                <!-- Imagens Carrossel -->
                <img src="https://github.com/Script-Wolf/Images_Wallpaper_Design/blob/main/sophos_img.PNG?raw=true" class="active"> <!-- Imagem da Sophos -->
                <img src="https://github.com/Script-Wolf/Images_Wallpaper_Design/blob/main/MS_NEWS-IMG.PNG?raw=true">
                <img src="https://github.com/Script-Wolf/Images_Wallpaper_Design/blob/main/fortinet_logo.PNG?raw=true">
                <img src="https://github.com/Script-Wolf/Images_Wallpaper_Design/blob/main/boletimsec.PNG?raw=true">
                <img src="https://github.com/Script-Wolf/Images_Wallpaper_Design/blob/main/e_database.PNG?raw=true">
                <img src="https://github.com/Script-Wolf/Images_Wallpaper_Design/blob/main/Acronis_logo.PNG?raw=true">
            </div>
        </h1>

        <div class="update-time">Última atualização: {{ ultima_atualizacao }}</div>
        
        <!-- Menu de filtros -->
        <div class="filtros">
            <form method="get">
                <select name="filtro" onchange="this.form.submit()">
                    <option {% if filtro=='Todos' %}selected{% endif %}>Todos</option>
                    {% for fonte in fontes %}
                    <option value="{{ fonte }}" {% if filtro==fonte %}selected{% endif %}>{{ fonte }}</option>
                    {% endfor %}
                </select>
            </form>
        </div>

        <ul>
        {% for noticia in noticias %}
            <li>
                <div class="source">
                    <span class="dot" style="background-color: {{ noticia.color }}"></span>[{{ noticia.source }}]
                </div>
                <a href="{{ noticia.link }}" target="_blank">{{ noticia.title }}</a>
                <small>{{ noticia.description|truncate(150, True, '...') }}</small>
                <div class="published">{{ noticia.published }}</div>
            </li>
        {% endfor %}
        </ul>

        <script>
            const images = document.querySelectorAll('.carousel img');
            let current = 0;
            setInterval(() => {
                images[current].classList.remove('active');
                current = (current + 1) % images.length;
                images[current].classList.add('active');
            }, 5000); // troca a cada 5 segundos
        </script>
    </body>
    </html>
    """
    return render_template_string(html, noticias=noticias_filtradas, ultima_atualizacao=ULTIMA_ATUALIZACAO,
                                  filtro=filtro, fontes=RSS_FEEDS.keys())

# =============================
# MAIN
# =============================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9999, debug=True)
