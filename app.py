from flask import Flask, request, jsonify
import os
import json
import time
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

# Definições de tecnologias e seus padrões de detecção
TECH_PATTERNS = {
    # Frameworks de Frontend
    "React": {
        "patterns": [
            r"react\.js",
            r"react-dom",
            r"__REACT_ROOT__",
            r"_reactListening"
        ],
        "categories": ["JavaScript frameworks"]
    },
    "Vue.js": {
        "patterns": [
            r"vue\.js",
            r"__vue__",
            r"Vue\.version"
        ],
        "categories": ["JavaScript frameworks"]
    },
    "Angular": {
        "patterns": [
            r"angular\.js",
            r"ng-app",
            r"ng-controller",
            r"angular\.version"
        ],
        "categories": ["JavaScript frameworks"]
    },
    "jQuery": {
        "patterns": [
            r"jquery\.js",
            r"jquery\.min\.js",
            r"jquery-\d+\.\d+\.\d+"
        ],
        "categories": ["JavaScript libraries"]
    },
    
    # Ferramentas de Chat/Atendimento
    "Zendesk Chat": {
        "patterns": [
            r"zopim",
            r"zendesk",
            r"zdassets",
            r"zd-chat"
        ],
        "categories": ["Live chat", "Customer service"]
    },
    "Intercom": {
        "patterns": [
            r"intercom",
            r"intercomcdn",
            r"intercomassets"
        ],
        "categories": ["Live chat", "Customer service"]
    },
    "Drift": {
        "patterns": [
            r"drift",
            r"driftt\.com",
            r"js\.driftt\.com"
        ],
        "categories": ["Live chat", "Customer service"]
    },
    "Crisp": {
        "patterns": [
            r"crisp",
            r"crisp\.chat",
            r"client\.crisp\.chat"
        ],
        "categories": ["Live chat", "Customer service"]
    },
    "Tawk.to": {
        "patterns": [
            r"tawk\.to",
            r"embed\.tawk\.to"
        ],
        "categories": ["Live chat", "Customer service"]
    },
    "LiveChat": {
        "patterns": [
            r"livechat",
            r"livechatinc",
            r"cdn\.livechatinc\.com"
        ],
        "categories": ["Live chat", "Customer service"]
    },
    "Olark": {
        "patterns": [
            r"olark",
            r"static\.olark\.com"
        ],
        "categories": ["Live chat", "Customer service"]
    },
    "HubSpot Chat": {
        "patterns": [
            r"hubspot",
            r"js\.hs-scripts\.com",
            r"js\.usemessages\.com"
        ],
        "categories": ["Live chat", "Customer service"]
    },
    "Freshchat": {
        "patterns": [
            r"freshchat",
            r"wchat\.freshchat\.com"
        ],
        "categories": ["Live chat", "Customer service"]
    },
    "LivePerson": {
        "patterns": [
            r"liveperson",
            r"lpcdn\.lpsnmedia\.net"
        ],
        "categories": ["Live chat", "Customer service"]
    },
    "Chatwoot": {
        "patterns": [
            r"chatwoot",
            r"app\.chatwoot\.com"
        ],
        "categories": ["Live chat", "Customer service"]
    },
    
    # CMS
    "WordPress": {
        "patterns": [
            r"wp-content",
            r"wp-includes",
            r"wordpress"
        ],
        "categories": ["CMS"]
    },
    "Drupal": {
        "patterns": [
            r"drupal",
            r"drupal\.js",
            r"drupal\.settings"
        ],
        "categories": ["CMS"]
    },
    "Joomla": {
        "patterns": [
            r"joomla",
            r"\/media\/jui\/"
        ],
        "categories": ["CMS"]
    },
    
    # Analytics
    "Google Analytics": {
        "patterns": [
            r"google-analytics\.com",
            r"ga\.js",
            r"analytics\.js",
            r"gtag"
        ],
        "categories": ["Analytics"]
    },
    "Google Tag Manager": {
        "patterns": [
            r"googletagmanager\.com",
            r"gtm\.js",
            r"gtm-"
        ],
        "categories": ["Tag managers"]
    },
    "Facebook Pixel": {
        "patterns": [
            r"connect\.facebook\.net",
            r"fbevents\.js",
            r"fbq\("
        ],
        "categories": ["Analytics"]
    },
    
    # Outros
    "Bootstrap": {
        "patterns": [
            r"bootstrap",
            r"bootstrap\.css",
            r"bootstrap\.js",
            r"bootstrap\.min\.css"
        ],
        "categories": ["UI frameworks"]
    },
    "Tailwind CSS": {
        "patterns": [
            r"tailwind",
            r"tailwindcss"
        ],
        "categories": ["UI frameworks"]
    },
    "Font Awesome": {
        "patterns": [
            r"font-awesome",
            r"fontawesome"
        ],
        "categories": ["Font scripts"]
    }
}

@app.route('/')
def index():
    return """
    <html>
    <head>
        <title>Wappalyzer-Next API</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #333; }
            code { background-color: #f4f4f4; padding: 2px 5px; border-radius: 3px; }
            pre { background-color: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>Wappalyzer-Next API</h1>
        <p>Esta API permite detectar tecnologias em websites, com foco especial em tecnologias de frontend e ferramentas de chat/atendimento ao cliente.</p>
        
        <h2>Como usar:</h2>
        <p>Faça uma requisição GET para o endpoint <code>/detect</code> com o parâmetro <code>url</code>:</p>
        <pre>GET /detect?url=https://exemplo.com</pre>
        
        <h2>Parâmetros opcionais:</h2>
        <ul>
            <li><code>timeout</code>: Tempo limite em segundos para a requisição (padrão: 10)</li>
            <li><code>cookie</code>: String de cookie para sites que requerem autenticação</li>
        </ul>
        
        <h2>Exemplo:</h2>
        <p><a href="/detect?url=https://google.com">Detectar tecnologias em google.com</a></p>
        
        <h2>Integração com N8N:</h2>
        <p>Use um nó HTTP Request com a URL:</p>
        <pre>https://n8n-wappalyzer-next.hvlihi.easypanel.host/detect?url={{$json.website}}</pre>
    </body>
    </html>
    """

@app.route('/status')
def status():
    return jsonify({
        "status": "online",
        "version": "1.0.0",
        "timestamp": time.time()
    })

def detect_technologies(html_content, url, headers):
    """Detecta tecnologias com base no conteúdo HTML e headers"""
    technologies = {}
    
    # Converter HTML para minúsculas para facilitar a busca
    html_lower = html_content.lower()
    
    # Verificar cada tecnologia
    for tech_name, tech_info in TECH_PATTERNS.items():
        for pattern in tech_info["patterns"]:
            if re.search(pattern.lower(), html_lower) or re.search(pattern.lower(), str(headers).lower()):
                technologies[tech_name] = {
                    "version": "",  # Versão não detectada nesta implementação simplificada
                    "confidence": 100,
                    "categories": tech_info["categories"],
                    "groups": []
                }
                break
    
    # Detecções específicas baseadas em meta tags, scripts, etc.
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Detectar WordPress
    if soup.find('meta', {'name': 'generator', 'content': re.compile('WordPress', re.I)}):
        version = ""
        generator = soup.find('meta', {'name': 'generator'})
        if generator and 'content' in generator.attrs:
            version_match = re.search(r'WordPress\s+(\d+\.\d+(\.\d+)?)', generator['content'])
            if version_match:
                version = version_match.group(1)
        
        technologies["WordPress"] = {
            "version": version,
            "confidence": 100,
            "categories": ["CMS"],
            "groups": []
        }
    
    # Detectar React com base em atributos específicos
    if soup.find(attrs={"data-reactroot": True}) or soup.find(attrs={"data-reactid": True}):
        technologies["React"] = {
            "version": "",
            "confidence": 100,
            "categories": ["JavaScript frameworks"],
            "groups": []
        }
    
    # Detectar Vue.js com base em atributos específicos
    if soup.find(attrs={"data-v-": re.compile(r'')}):
        technologies["Vue.js"] = {
            "version": "",
            "confidence": 100,
            "categories": ["JavaScript frameworks"],
            "groups": []
        }
    
    # Detectar Angular com base em atributos específicos
    if soup.find(attrs={"ng-": re.compile(r'')}):
        technologies["Angular"] = {
            "version": "",
            "confidence": 100,
            "categories": ["JavaScript frameworks"],
            "groups": []
        }
    
    return technologies

@app.route('/detect')
def detect():
    url = request.args.get('url')
    timeout = int(request.args.get('timeout', 10))
    cookie = request.args.get('cookie', '')
    
    if not url:
        return jsonify({"error": "URL parameter is required"}), 400
    
    try:
        # Configurar headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        # Adicionar cookies se fornecidos
        if cookie:
            headers['Cookie'] = cookie
            
        # Fazer a requisição
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Detectar tecnologias
        technologies = detect_technologies(response.text, url, response.headers)
        
        # Montar resultado
        result = {
            "url": url,
            "technologies": technologies
        }
        
        return jsonify(result)
    
    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": f"Request error: {str(e)}",
            "url": url
        }), 500
    except Exception as e:
        return jsonify({
            "error": str(e),
            "url": url
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
