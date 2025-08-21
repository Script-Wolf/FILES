from flask import Flask, render_template_string
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

# Feeds RSS públicos
RSS_FEEDS = {
    "NVD CVE Feed": "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml",
    "Exploit Database": "https://www.exploit-db.com/rss.xml",
    "Qualys Security Advisories": "https://blog.qualys.com/rss",
    "SOCRADAR Threat Intel": "https://www.socradar.com/rss",
    "Vulners RSS": "https://vulners.com/rss.xml",
    "CISA Cybersecurity Advisories": "https://www.cisa.gov/news.xml",
    "Microsoft Security Blog": "https://msrc.microsoft.com/blog/feed",
    "Sophos Security News": "https://news.sophos.com/feed/",
    "Sophos Security Advisories": "https://www.sophos.com/pt-br/security-advisories/feed",
    "Acronis Security Blog": "https://www.acronis.com/en-us/blog/feed/",
    "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
    "SecurityWeek": "https://www.securityweek.com/rss"
}

# Cores para bolinha de cada fonte
SOURCE_COLORS = {
    "Vulners": "#ff8800",
    "NVD CVE Feed": "#0056b3",
    "Exploit Database": "#b22222",
    "Cisco Security Advisories": "#228B22",
    "Qualys Security Advisories": "#008b8b",
    "CISA Cybersecurity Advisories": "#ff4500",
    "Microsoft Security Blog": "#0078d7",
    "Sophos Security News": "#9400d3",
    "Acronis Security Blog": "#ff1493",
    "The Hacker News": "#ff4500",
    "SecurityWeek": "#8b0000"
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

                # Filtrar apenas CVE ou Exploit para Hacker News e SecurityWeek
                if source in ["The Hacker News", "SecurityWeek"]:
                    if "CVE" not in title.upper() and "EXPLOIT" not in title.upper() and \
                       "CVE" not in summary.upper() and "EXPLOIT" not in summary.upper():
                        continue

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
                    "source": "Vulners",
                    "title": f"{cve_id} - {descricao}",
                    "link": f"https://vulners.com/{doc.get('type', 'vuln')}/{doc.get('id')}",
                    "description": doc.get("description", "Sem descrição"),
                    "published": published_dt.strftime("%Y-%m-%d %H:%M"),
                    "color": SOURCE_COLORS.get("Vulners", "#a17e56")
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
        time.sleep(10)

threading.Thread(target=atualizar_noticias, daemon=True).start()

# =============================
# ROTA FLASK
# =============================
@app.route('/')
def index():
    html = """
    <html>
    <head>
        <title>Feed Hunt3r</title>
        <meta http-equiv="refresh" content="1800"> <!-- 30 Min -->
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: black; margin: 0; padding: 20px;
                   background-image: linear-gradient(to right, #0B1340, transparent, #4A4E7D);}
            h1 { color: white; border-bottom: 3px solid #b22222; padding-bottom: 10px; font-weight: 600; }
            .update-time { color: #444; font-size: 0.9em; margin-bottom: 20px; }
            ul { list-style-type: none; padding: 0; }
            li { background: white; margin-bottom: 15px; padding: 15px 20px; border-radius: 12px;
                 box-shadow: 0 4px 10px rgba(0,0,0,0.1); transition: box-shadow 0.3s ease; }
            li:hover { box-shadow: 0 8px 20px rgba(0,0,0,0.2); background-color: #F6EBF9; }
            .logo{height: 220px;}
            a { text-decoration: none; font-size: 1.1em; font-weight: 600; color: #b22222; }
            a:hover{color:white; background-color: black;}
            .loading{ }
            small { display: block; color: #666; margin-top: 8px; font-style: italic; font-size: 0.9em; }
            .source { font-weight: bold; margin-bottom: 5px; display: flex; align-items: center; }
            .dot { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-right: 6px; }
            .published { color: #999; font-size: 0.8em; margin-top: 5px; }
            .image2{height: 280px; width: 290px; margin-left: 500px;}

            /* LOADING SCREEN */
            #loading {
                position: fixed;
                width: 100%;
                height: 100%;
                background: black;
                top: 0;
                left: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            }
            #loading img {
                width: 200px;
            }
            #conteudo { display: none; }
        </style>
        
        
        <script>
            window.onload = function() {
                setTimeout(function(){
                    document.getElementById("loading").style.display = "none";
                    document.getElementById("conteudo").style.display = "block";
                }, 4000); // 4 segundos
            }
        </script>
    </head>
    <body>
        <!-- LOADING -->
        <div id="loading">
            <!-- >>> Image Loading <<< -->
            <img src="https://github.com/Script-Wolf/FILES/blob/main/Cybersecurity.gif?raw=true"" alt="Carregando..." class="loading">
        </div>

        <!-- CONTEÚDO -->
        <div id="conteudo">
            <h1><img src="https://github.com/Script-Wolf/FILES/blob/main/Browsing.gif?raw=true" class="logo">Feed Hunt3r</h1>

            <div class="update-time">Última atualização: {{ ultima_atualizacao }}</div>
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
            <footer>
                <img src="https://github.com/Script-Wolf/FILES/blob/main/Buy%20me%20a%20coffee%20badge.gif?raw=true" class="image2">
            </footer>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, noticias=ULTIMAS_NOTICIAS, ultima_atualizacao=ULTIMA_ATUALIZACAO)

# =============================
# MAIN
# =============================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9999, debug=True)
