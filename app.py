from flask import Flask, request, jsonify
import os
import json
import time
import requests
from bs4 import BeautifulSoup
import re
import subprocess

app = Flask(__name__)

# Verificar se o arquivo technologies.json existe, se não, baixá-lo
def download_technologies_json():
    print("Arquivo technologies.json não encontrado. Baixando...")
    try:
        # Fazer backup do arquivo antigo se existir
        technologies_path = os.path.join(os.path.dirname(__file__), 'technologies.json')
        if os.path.exists(technologies_path):
            backup_path = technologies_path + '.bak'
            os.rename(technologies_path, backup_path)
            print(f"Backup do arquivo original criado em {backup_path}")
        
        # Baixar o novo arquivo
        url = "https://raw.githubusercontent.com/AliasIO/wappalyzer/master/src/technologies.json"
        response = requests.get(url)
        response.raise_for_status()
        
        # Verificar se é um JSON válido antes de salvar
        json_data = response.json()  # Isso vai lançar uma exceção se o JSON for inválido
        
        # Salvar o arquivo se o JSON for válido
        with open(technologies_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
            
        print("Download do arquivo technologies.json concluído com sucesso.")
        return True
    except Exception as e:
        print(f"Erro ao baixar technologies.json: {str(e)}")
        
        # Tentar restaurar o backup se existir
        backup_path = technologies_path + '.bak'
        if os.path.exists(backup_path):
            os.rename(backup_path, technologies_path)
            print("Arquivo de backup restaurado.")
        return False

# Tentar carregar o arquivo technologies.json
try:
    technologies_path = os.path.join(os.path.dirname(__file__), 'technologies.json')
    
    if not os.path.exists(technologies_path):
        success = download_technologies_json()
        if not success:
            print("Não foi possível baixar o arquivo. Criando um arquivo vazio.")
            TECHNOLOGIES = {}
            # Criar um arquivo JSON vazio válido
            with open(technologies_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        else:
            with open(technologies_path, 'r', encoding='utf-8') as f:
                TECHNOLOGIES = json.load(f)
    else:
        try:
            with open(technologies_path, 'r', encoding='utf-8') as f:
                TECHNOLOGIES = json.load(f)
        except json.JSONDecodeError:
            print("O arquivo technologies.json existente está corrompido. Tentando baixar novamente.")
            success = download_technologies_json()
            if success:
                with open(technologies_path, 'r', encoding='utf-8') as f:
                    TECHNOLOGIES = json.load(f)
            else:
                TECHNOLOGIES = {}
                # Criar um arquivo JSON vazio válido
                with open(technologies_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
except Exception as e:
    print(f"Erro ao carregar technologies.json: {str(e)}")
    TECHNOLOGIES = {}

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
            .tech-count { font-weight: bold; color: #007bff; }
        </style>
    </head>
    <body>
        <h1>Wappalyzer-Next API</h1>
        <p>Esta API utiliza as fingerprints do <a href="https://github.com/AliasIO/wappalyzer" target="_blank">Wappalyzer</a> 
        para detectar tecnologias em websites, com foco especial em tecnologias de frontend e ferramentas de chat/atendimento ao cliente.</p>
        
        <p>Base de dados: <span class="tech-count">{}</span> tecnologias disponíveis para detecção.</p>
        
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
    """.format(len(TECHNOLOGIES))

@app.route('/status')
def status():
    return jsonify({
        "status": "online",
        "version": "1.0.0",
        "technologies_count": len(TECHNOLOGIES),
        "timestamp": time.time()
    })

def safe_compile_regex(pattern, flags=0):
    """Compila um padrão regex com tratamento de erros"""
    try:
        return re.compile(pattern, flags)
    except re.error as e:
        print(f"Erro ao compilar regex '{pattern}': {str(e)}")
        return None
    except Exception as e:
        print(f"Erro genérico ao compilar regex '{pattern}': {str(e)}")
        return None

def get_regex_patterns():
    """Extrai padrões regex de todas as tecnologias"""
    patterns = {}
    skipped_patterns = 0
    
    for tech_name, tech_info in TECHNOLOGIES.items():
        patterns[tech_name] = {
            "regex": {},
            "categories": tech_info.get("cats", []),
            "icon": tech_info.get("icon", ""),
            "website": tech_info.get("website", ""),
            "description": tech_info.get("description", "")
        }
        
        # HTML patterns
        if "html" in tech_info:
            patterns[tech_name]["regex"]["html"] = []
            if isinstance(tech_info["html"], list):
                for pattern in tech_info["html"]:
                    compiled = safe_compile_regex(pattern, re.IGNORECASE)
                    if compiled:
                        patterns[tech_name]["regex"]["html"].append(compiled)
                    else:
                        skipped_patterns += 1
            else:
                compiled = safe_compile_regex(tech_info["html"], re.IGNORECASE)
                if compiled:
                    patterns[tech_name]["regex"]["html"].append(compiled)
                else:
                    skipped_patterns += 1
        
        # Script patterns
        if "scriptSrc" in tech_info:
            patterns[tech_name]["regex"]["script"] = []
            if isinstance(tech_info["scriptSrc"], list):
                for pattern in tech_info["scriptSrc"]:
                    compiled = safe_compile_regex(pattern, re.IGNORECASE)
                    if compiled:
                        patterns[tech_name]["regex"]["script"].append(compiled)
                    else:
                        skipped_patterns += 1
            else:
                compiled = safe_compile_regex(tech_info["scriptSrc"], re.IGNORECASE)
                if compiled:
                    patterns[tech_name]["regex"]["script"].append(compiled)
                else:
                    skipped_patterns += 1
        
        # Meta patterns
        if "meta" in tech_info:
            patterns[tech_name]["meta"] = tech_info["meta"]
        
        # URL patterns
        if "url" in tech_info:
            patterns[tech_name]["regex"]["url"] = []
            if isinstance(tech_info["url"], list):
                for pattern in tech_info["url"]:
                    compiled = safe_compile_regex(pattern, re.IGNORECASE)
                    if compiled:
                        patterns[tech_name]["regex"]["url"].append(compiled)
                    else:
                        skipped_patterns += 1
            else:
                compiled = safe_compile_regex(tech_info["url"], re.IGNORECASE)
                if compiled:
                    patterns[tech_name]["regex"]["url"].append(compiled)
                else:
                    skipped_patterns += 1
        
        # Headers patterns
        if "headers" in tech_info:
            patterns[tech_name]["headers"] = tech_info["headers"]
        
        # JS patterns
        if "js" in tech_info:
            patterns[tech_name]["js"] = tech_info["js"]
        
        # DOM patterns
        if "dom" in tech_info:
            patterns[tech_name]["regex"]["dom"] = []
            if isinstance(tech_info["dom"], list):
                for pattern in tech_info["dom"]:
                    compiled = safe_compile_regex(pattern, re.IGNORECASE)
                    if compiled:
                        patterns[tech_name]["regex"]["dom"].append(compiled)
                    else:
                        skipped_patterns += 1
            else:
                compiled = safe_compile_regex(tech_info["dom"], re.IGNORECASE)
                if compiled:
                    patterns[tech_name]["regex"]["dom"].append(compiled)
                else:
                    skipped_patterns += 1
    
    print(f"Total de padrões ignorados devido a erros de expressão regular: {skipped_patterns}")
    return patterns

# Compilar padrões regex uma vez na inicialização
try:
    PATTERNS = get_regex_patterns()
    print(f"Padrões compilados com sucesso: {len(PATTERNS)} tecnologias carregadas.")
except Exception as e:
    print(f"Erro ao compilar padrões: {str(e)}")
    PATTERNS = {}

def detect_technologies(html_content, url, headers, soup=None):
    """Detecta tecnologias com base no conteúdo HTML, URL e headers"""
    if soup is None:
        soup = BeautifulSoup(html_content, 'html.parser')
    
    technologies = {}
    
    # Converter HTML para string para facilitar a busca
    html_str = str(html_content).lower()
    
    for tech_name, tech_patterns in PATTERNS.items():
        confidence = 0
        version = ""
        
        # Verificar padrões HTML
        if "regex" in tech_patterns and "html" in tech_patterns["regex"]:
            for pattern in tech_patterns["regex"]["html"]:
                if pattern and pattern.search(html_str):
                    confidence = max(confidence, 100)
                    # Tentar extrair versão se o padrão contiver grupo de captura
                    match = pattern.search(html_str)
                    if match and "\\;version:" in pattern.pattern:
                        version_pattern = pattern.pattern.split("\\;version:")[1].split("\\;")[0]
                        try:
                            if match.groups():
                                version = match.group(int(version_pattern))
                        except:
                            pass
        
        # Verificar padrões de script
        if "regex" in tech_patterns and "script" in tech_patterns["regex"]:
            script_tags = soup.find_all("script", src=True)
            script_srcs = [script.get("src", "") for script in script_tags]
            script_srcs_str = " ".join(script_srcs)
            
            for pattern in tech_patterns["regex"]["script"]:
                if pattern and pattern.search(script_srcs_str):
                    confidence = max(confidence, 100)
                    # Tentar extrair versão
                    match = pattern.search(script_srcs_str)
                    if match and "\\;version:" in pattern.pattern:
                        version_pattern = pattern.pattern.split("\\;version:")[1].split("\\;")[0]
                        try:
                            if match.groups():
                                version = match.group(int(version_pattern))
                        except:
                            pass
        
        # Verificar padrões de meta tags
        if "meta" in tech_patterns:
            meta_tags = soup.find_all("meta")
            for meta_tag in meta_tags:
                for meta_name, meta_pattern in tech_patterns["meta"].items():
                    meta_content = None
                    
                    # Verificar diferentes atributos de meta tags
                    if meta_tag.get("name", "").lower() == meta_name.lower():
                        meta_content = meta_tag.get("content", "")
                    elif meta_tag.get("property", "").lower() == meta_name.lower():
                        meta_content = meta_tag.get("content", "")
                    elif meta_tag.get("http-equiv", "").lower() == meta_name.lower():
                        meta_content = meta_tag.get("content", "")
                    
                    if meta_content:
                        if isinstance(meta_pattern, str):
                            if re.search(meta_pattern, meta_content, re.IGNORECASE):
                                confidence = max(confidence, 100)
                                # Tentar extrair versão
                                if "\\;version:" in meta_pattern:
                                    version_pattern = meta_pattern.split("\\;version:")[1].split("\\;")[0]
                                    match = re.search(meta_pattern.split("\\;")[0], meta_content, re.IGNORECASE)
                                    try:
                                        if match and match.groups():
                                            version = match.group(int(version_pattern))
                                    except:
                                        pass
                                elif "\\;confidence:" in meta_pattern:
                                    conf_pattern = meta_pattern.split("\\;confidence:")[1].split("\\;")[0]
                                    try:
                                        confidence = max(confidence, int(conf_pattern))
                                    except:
                                        pass
        
        # Verificar padrões de URL
        if "regex" in tech_patterns and "url" in tech_patterns["regex"]:
            for pattern in tech_patterns["regex"]["url"]:
                if pattern and pattern.search(url):
                    confidence = max(confidence, 100)
                    # Tentar extrair versão
                    match = pattern.search(url)
                    if match and "\\;version:" in pattern.pattern:
                        version_pattern = pattern.pattern.split("\\;version:")[1].split("\\;")[0]
                        try:
                            if match.groups():
                                version = match.group(int(version_pattern))
                        except:
                            pass
                    elif match and "\\;confidence:" in pattern.pattern:
                        conf_pattern = pattern.pattern.split("\\;confidence:")[1].split("\\;")[0]
                        try:
                            confidence = max(confidence, int(conf_pattern))
                        except:
                            pass
        
        # Verificar padrões de headers
        if "headers" in tech_patterns:
            for header_name, header_pattern in tech_patterns["headers"].items():
                if header_name.lower() in headers:
                    header_value = headers[header_name.lower()]
                    if isinstance(header_pattern, str):
                        if re.search(header_pattern, header_value, re.IGNORECASE):
                            confidence = max(confidence, 100)
                            # Tentar extrair versão
                            if "\\;version:" in header_pattern:
                                version_pattern = header_pattern.split("\\;version:")[1].split("\\;")[0]
                                match = re.search(header_pattern.split("\\;")[0], header_value, re.IGNORECASE)
                                try:
                                    if match and match.groups():
                                        version = match.group(int(version_pattern))
                                except:
                                    pass
        
        # Verificar padrões DOM
        if "regex" in tech_patterns and "dom" in tech_patterns["regex"]:
            dom_str = str(soup)
            for pattern in tech_patterns["regex"]["dom"]:
                if pattern and pattern.search(dom_str):
                    confidence = max(confidence, 100)
        
        # Se encontrou alguma evidência, adicionar à lista de tecnologias
        if confidence > 0:
            technologies[tech_name] = {
                "version": version,
                "confidence": confidence,
                "categories": tech_patterns["categories"],
                "icon": tech_patterns.get("icon", ""),
                "website": tech_patterns.get("website", ""),
                "description": tech_patterns.get("description", "")
            }
    
    # Detecções específicas para tecnologias de chat e atendimento ao cliente
    chat_patterns = {
        "Zendesk Chat": [r"zopim", r"zendesk", r"zdassets", r"zd-chat"],
        "Intercom": [r"intercom", r"intercomcdn", r"intercomassets"],
        "Drift": [r"drift", r"driftt\.com", r"js\.driftt\.com"],
        "Crisp": [r"crisp", r"crisp\.chat", r"client\.crisp\.chat"],
        "Tawk.to": [r"tawk\.to", r"embed\.tawk\.to"],
        "LiveChat": [r"livechat", r"livechatinc", r"cdn\.livechatinc\.com"],
        "Olark": [r"olark", r"static\.olark\.com"],
        "HubSpot Chat": [r"hubspot", r"js\.hs-scripts\.com", r"js\.usemessages\.com"],
        "Freshchat": [r"freshchat", r"wchat\.freshchat\.com"],
        "LivePerson": [r"liveperson", r"lpcdn\.lpsnmedia\.net"],
        "Chatwoot": [r"chatwoot", r"app\.chatwoot\.com"]
    }
    
    for tech_name, patterns in chat_patterns.items():
        if tech_name not in technologies:  # Evitar duplicatas
            for pattern in patterns:
                if re.search(pattern, html_str, re.IGNORECASE) or re.search(pattern, url, re.IGNORECASE) or re.search(pattern, str(headers), re.IGNORECASE):
                    technologies[tech_name] = {
                        "version": "",
                        "confidence": 100,
                        "categories": [52],  # Categoria "Live chat"
                        "icon": "",
                        "website": "",
                        "description": f"{tech_name} é uma ferramenta de chat e atendimento ao cliente."
                    }
                    break
    
    return technologies

@app.route('/detect', methods=['GET'])
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
        
        # Preparar BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Detectar tecnologias
        technologies = detect_technologies(response.text, url, response.headers, soup)
        
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
