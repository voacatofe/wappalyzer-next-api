from flask import Flask, request, jsonify
import os
import json
import time
import requests
from bs4 import BeautifulSoup
import re
import subprocess
import logging
import tempfile
import shutil

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# URL para o arquivo technologies.json do repositório enthec/webappanalyzer
TECHNOLOGIES_URL = "https://raw.githubusercontent.com/enthec/webappanalyzer/main/src/technologies.json"

# Verificar se o arquivo technologies.json existe, se não, baixá-lo
def download_technologies_json():
    logger.info("Arquivo technologies.json não encontrado. Baixando...")
    try:
        # Criar um arquivo temporário para baixar o technologies.json
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()
        
        # Fazer backup do arquivo antigo se existir
        technologies_path = os.path.join(os.path.dirname(__file__), 'technologies.json')
        if os.path.exists(technologies_path):
            backup_path = technologies_path + '.bak'
            try:
                shutil.copy2(technologies_path, backup_path)
                logger.info(f"Backup do arquivo original criado em {backup_path}")
            except Exception as e:
                logger.warning(f"Não foi possível criar backup: {str(e)}")
        
        # Baixar o novo arquivo diretamente com Python
        logger.info(f"Baixando de {TECHNOLOGIES_URL}...")
        response = requests.get(TECHNOLOGIES_URL, timeout=30)
        response.raise_for_status()
        
        # Verificar se a resposta é um JSON válido
        try:
            json_data = response.json()
            logger.info(f"JSON válido recebido com {len(json_data)} tecnologias")
            
            # Salvar o arquivo se o JSON for válido
            with open(temp_file.name, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
                
            # Mover o arquivo temporário para o destino final
            shutil.move(temp_file.name, technologies_path)
            logger.info("Download do arquivo technologies.json concluído com sucesso.")
            return True
        except json.JSONDecodeError as e:
            logger.error(f"O JSON recebido é inválido: {str(e)}")
            logger.debug(f"Conteúdo recebido: {response.text[:200]}...")
            os.unlink(temp_file.name)
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao baixar technologies.json: {str(e)}")
        
        # Se o arquivo temporário foi criado, removê-lo
        if 'temp_file' in locals() and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
            
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao baixar technologies.json: {str(e)}")
        
        # Se o arquivo temporário foi criado, removê-lo
        if 'temp_file' in locals() and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
            
        return False

# Gerar um arquivo technologies.json vazio (para fallback)
def create_empty_technologies():
    technologies_path = os.path.join(os.path.dirname(__file__), 'technologies.json')
    logger.warning("Criando um arquivo technologies.json vazio")
    
    # Definir algumas tecnologias básicas para o arquivo vazio
    basic_techs = {
        "Google Analytics": {
            "cats": [10],
            "description": "Google Analytics é um serviço de análise da web",
            "icon": "Google Analytics.svg",
            "js": {
                "GoogleAnalyticsObject": ""
            },
            "scriptSrc": [
                "google-analytics\\.com/analytics\\.js",
                "googletagmanager\\.com/gtag/js"
            ],
            "website": "https://marketingplatform.google.com/about/analytics/"
        },
        "WordPress": {
            "cats": [1],
            "description": "WordPress é um sistema de gestão de conteúdo.",
            "html": [
                "<link rel=[\"']stylesheet[\"'] [^>]+wp-(?:content|includes)",
                "<link[^>]+s\\.w\\.org"
            ],
            "icon": "WordPress.svg",
            "implies": "PHP",
            "meta": {
                "generator": "WordPress"
            },
            "scriptSrc": "/wp-includes/",
            "website": "https://wordpress.org"
        }
    }
    
    try:
        with open(technologies_path, 'w', encoding='utf-8') as f:
            json.dump(basic_techs, f, ensure_ascii=False, indent=2)
        logger.info(f"Arquivo technologies.json básico criado com {len(basic_techs)} tecnologias")
        return basic_techs
    except Exception as e:
        logger.error(f"Erro ao criar arquivo technologies.json vazio: {str(e)}")
        return {}

# Carregar o arquivo technologies.json
def load_technologies():
    try:
        technologies_path = os.path.join(os.path.dirname(__file__), 'technologies.json')
        
        if not os.path.exists(technologies_path):
            success = download_technologies_json()
            if not success:
                return create_empty_technologies()
        
        try:
            with open(technologies_path, 'r', encoding='utf-8') as f:
                technologies = json.load(f)
                logger.info(f"Arquivo technologies.json carregado com sucesso. {len(technologies)} tecnologias disponíveis.")
                return technologies
        except json.JSONDecodeError as e:
            logger.warning(f"O arquivo technologies.json existente está corrompido: {str(e)}. Tentando baixar novamente.")
            success = download_technologies_json()
            if success:
                with open(technologies_path, 'r', encoding='utf-8') as f:
                    technologies = json.load(f)
                    return technologies
            else:
                logger.warning("Falha ao recarregar. Usando tecnologias básicas.")
                return create_empty_technologies()
    except Exception as e:
        logger.error(f"Erro ao carregar technologies.json: {str(e)}")
        return create_empty_technologies()

# Carregar tecnologias
TECHNOLOGIES = load_technologies()

@app.route('/')
def index():
    return """
    <html>
    <head>
        <title>Wappalyzer API</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #333; }
            code { background-color: #f4f4f4; padding: 2px 5px; border-radius: 3px; }
            pre { background-color: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }
            .tech-count { font-weight: bold; color: #007bff; }
        </style>
    </head>
    <body>
        <h1>Wappalyzer API</h1>
        <p>Esta API utiliza as fingerprints do <a href="https://github.com/enthec/webappanalyzer" target="_blank">WebAppAnalyzer</a> 
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
    if not pattern:
        return None
        
    try:
        # Limpar padrão removendo tags como \;confidence:50
        clean_pattern = pattern
        if '\\;' in pattern:
            clean_pattern = pattern.split('\\;')[0]
            
        return re.compile(clean_pattern, flags)
    except re.error as e:
        logger.warning(f"Erro ao compilar regex '{pattern}': {str(e)}")
        return None
    except Exception as e:
        logger.warning(f"Erro genérico ao compilar regex '{pattern}': {str(e)}")
        return None

def extract_version(pattern, match, text):
    """Extrai a versão de um padrão com base na tag version"""
    version = ""
    
    if match and "\\;version:" in pattern:
        try:
            version_tag = pattern.split("\\;version:")[1].split("\\;")[0]
            
            # Se o version_tag contém referência ao grupo de captura
            if "\\1" in version_tag:
                if match.groups():
                    # Substituir \\1 pelo primeiro grupo capturado
                    version = version_tag.replace("\\1", match.group(1))
            else:
                # Se é um índice numérico direto
                try:
                    group_index = int(version_tag)
                    if len(match.groups()) >= group_index:
                        version = match.group(group_index)
                except ValueError:
                    # Se não for um número, usa o próprio tag como versão
                    version = version_tag
        except Exception as e:
            logger.warning(f"Erro ao extrair versão: {str(e)}")
            
    return version

def get_confidence(pattern):
    """Extrai o valor de confiança de um padrão"""
    confidence = 100  # Valor padrão
    
    if "\\;confidence:" in pattern:
        try:
            confidence_str = pattern.split("\\;confidence:")[1].split("\\;")[0]
            confidence = int(confidence_str)
        except (ValueError, IndexError):
            pass
            
    return confidence

def compile_patterns():
    """Compila padrões de expressões regulares de todas as tecnologias"""
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
        
        # HTML patterns (deprecated mas ainda suportado)
        if "html" in tech_info:
            patterns[tech_name]["regex"]["html"] = []
            if isinstance(tech_info["html"], list):
                for pattern in tech_info["html"]:
                    compiled = safe_compile_regex(pattern, re.IGNORECASE)
                    if compiled:
                        patterns[tech_name]["regex"]["html"].append({
                            "pattern": pattern,
                            "compiled": compiled,
                            "confidence": get_confidence(pattern)
                        })
                    else:
                        skipped_patterns += 1
            else:
                compiled = safe_compile_regex(tech_info["html"], re.IGNORECASE)
                if compiled:
                    patterns[tech_name]["regex"]["html"].append({
                        "pattern": tech_info["html"],
                        "compiled": compiled,
                        "confidence": get_confidence(tech_info["html"])
                    })
                else:
                    skipped_patterns += 1
        
        # Script source patterns
        if "scriptSrc" in tech_info:
            patterns[tech_name]["regex"]["script"] = []
            if isinstance(tech_info["scriptSrc"], list):
                for pattern in tech_info["scriptSrc"]:
                    compiled = safe_compile_regex(pattern, re.IGNORECASE)
                    if compiled:
                        patterns[tech_name]["regex"]["script"].append({
                            "pattern": pattern,
                            "compiled": compiled,
                            "confidence": get_confidence(pattern)
                        })
                    else:
                        skipped_patterns += 1
            else:
                compiled = safe_compile_regex(tech_info["scriptSrc"], re.IGNORECASE)
                if compiled:
                    patterns[tech_name]["regex"]["script"].append({
                        "pattern": tech_info["scriptSrc"],
                        "compiled": compiled,
                        "confidence": get_confidence(tech_info["scriptSrc"])
                    })
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
                        patterns[tech_name]["regex"]["url"].append({
                            "pattern": pattern,
                            "compiled": compiled,
                            "confidence": get_confidence(pattern)
                        })
                    else:
                        skipped_patterns += 1
            else:
                compiled = safe_compile_regex(tech_info["url"], re.IGNORECASE)
                if compiled:
                    patterns[tech_name]["regex"]["url"].append({
                        "pattern": tech_info["url"],
                        "compiled": compiled,
                        "confidence": get_confidence(tech_info["url"])
                    })
                else:
                    skipped_patterns += 1
        
        # Headers patterns
        if "headers" in tech_info:
            patterns[tech_name]["headers"] = tech_info["headers"]
        
        # JS patterns
        if "js" in tech_info:
            patterns[tech_name]["js"] = tech_info["js"]
        
        # Text patterns
        if "text" in tech_info:
            patterns[tech_name]["regex"]["text"] = []
            if isinstance(tech_info["text"], list):
                for pattern in tech_info["text"]:
                    compiled = safe_compile_regex(pattern, re.IGNORECASE)
                    if compiled:
                        patterns[tech_name]["regex"]["text"].append({
                            "pattern": pattern,
                            "compiled": compiled,
                            "confidence": get_confidence(pattern)
                        })
                    else:
                        skipped_patterns += 1
            else:
                compiled = safe_compile_regex(tech_info["text"], re.IGNORECASE)
                if compiled:
                    patterns[tech_name]["regex"]["text"].append({
                        "pattern": tech_info["text"],
                        "compiled": compiled,
                        "confidence": get_confidence(tech_info["text"])
                    })
                else:
                    skipped_patterns += 1
        
        # CSS patterns
        if "css" in tech_info:
            patterns[tech_name]["regex"]["css"] = []
            if isinstance(tech_info["css"], list):
                for pattern in tech_info["css"]:
                    compiled = safe_compile_regex(pattern, re.IGNORECASE)
                    if compiled:
                        patterns[tech_name]["regex"]["css"].append({
                            "pattern": pattern,
                            "compiled": compiled,
                            "confidence": get_confidence(pattern)
                        })
                    else:
                        skipped_patterns += 1
            else:
                compiled = safe_compile_regex(tech_info["css"], re.IGNORECASE)
                if compiled:
                    patterns[tech_name]["regex"]["css"].append({
                        "pattern": tech_info["css"],
                        "compiled": compiled,
                        "confidence": get_confidence(tech_info["css"])
                    })
                else:
                    skipped_patterns += 1
        
        # Scripts content patterns
        if "scripts" in tech_info:
            patterns[tech_name]["regex"]["scripts"] = []
            if isinstance(tech_info["scripts"], list):
                for pattern in tech_info["scripts"]:
                    compiled = safe_compile_regex(pattern, re.IGNORECASE)
                    if compiled:
                        patterns[tech_name]["regex"]["scripts"].append({
                            "pattern": pattern,
                            "compiled": compiled,
                            "confidence": get_confidence(pattern)
                        })
                    else:
                        skipped_patterns += 1
            else:
                compiled = safe_compile_regex(tech_info["scripts"], re.IGNORECASE)
                if compiled:
                    patterns[tech_name]["regex"]["scripts"].append({
                        "pattern": tech_info["scripts"],
                        "compiled": compiled,
                        "confidence": get_confidence(tech_info["scripts"])
                    })
                else:
                    skipped_patterns += 1
    
    logger.info(f"Total de padrões ignorados devido a erros de expressão regular: {skipped_patterns}")
    return patterns

# Compilar padrões regex uma vez na inicialização
try:
    PATTERNS = compile_patterns()
    logger.info(f"Padrões compilados com sucesso: {len(PATTERNS)} tecnologias carregadas.")
except Exception as e:
    logger.error(f"Erro ao compilar padrões: {str(e)}")
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
        matched_patterns = []
        
        # Verificar padrões HTML
        if "regex" in tech_patterns and "html" in tech_patterns["regex"]:
            for pattern_obj in tech_patterns["regex"]["html"]:
                match = pattern_obj["compiled"].search(html_str)
                if match:
                    pattern_confidence = pattern_obj["confidence"]
                    confidence = max(confidence, pattern_confidence)
                    
                    # Tentar extrair versão
                    extracted_version = extract_version(pattern_obj["pattern"], match, html_str)
                    if extracted_version:
                        version = extracted_version
                        
                    matched_patterns.append(f"html:{pattern_obj['pattern']}")
        
        # Verificar padrões de script
        if "regex" in tech_patterns and "script" in tech_patterns["regex"]:
            script_tags = soup.find_all("script", src=True)
            script_srcs = [script.get("src", "") for script in script_tags]
            script_srcs_str = " ".join(script_srcs)
            
            for pattern_obj in tech_patterns["regex"]["script"]:
                match = pattern_obj["compiled"].search(script_srcs_str)
                if match:
                    pattern_confidence = pattern_obj["confidence"]
                    confidence = max(confidence, pattern_confidence)
                    
                    # Tentar extrair versão
                    extracted_version = extract_version(pattern_obj["pattern"], match, script_srcs_str)
                    if extracted_version:
                        version = extracted_version
                        
                    matched_patterns.append(f"script:{pattern_obj['pattern']}")
        
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
                    
                    if meta_content and isinstance(meta_pattern, str):
                        # Remover a parte de versão para a correspondência
                        match_pattern = meta_pattern.split('\\;')[0] if '\\;' in meta_pattern else meta_pattern
                        match = re.search(match_pattern, meta_content, re.IGNORECASE)
                        
                        if match:
                            # Verificar confiança
                            if "\\;confidence:" in meta_pattern:
                                conf_value = int(meta_pattern.split("\\;confidence:")[1].split("\\;")[0])
                                confidence = max(confidence, conf_value)
                            else:
                                confidence = max(confidence, 100)
                                
                            # Obter versão
                            if "\\;version:" in meta_pattern:
                                try:
                                    version_pattern = meta_pattern.split("\\;version:")[1].split("\\;")[0]
                                    if match.groups() and version_pattern.isdigit():
                                        version = match.group(int(version_pattern))
                                except Exception:
                                    pass
                                    
                            matched_patterns.append(f"meta:{meta_name}={meta_pattern}")
        
        # Verificar padrões de URL
        if "regex" in tech_patterns and "url" in tech_patterns["regex"]:
            for pattern_obj in tech_patterns["regex"]["url"]:
                match = pattern_obj["compiled"].search(url)
                if match:
                    pattern_confidence = pattern_obj["confidence"]
                    confidence = max(confidence, pattern_confidence)
                    
                    # Tentar extrair versão
                    extracted_version = extract_version(pattern_obj["pattern"], match, url)
                    if extracted_version:
                        version = extracted_version
                        
                    matched_patterns.append(f"url:{pattern_obj['pattern']}")
        
        # Verificar padrões de headers
        if "headers" in tech_patterns:
            for header_name, header_pattern in tech_patterns["headers"].items():
                header_value = ""
                
                # Converter cabeçalhos para formato consistente (lowercase)
                for key, value in headers.items():
                    if key.lower() == header_name.lower():
                        header_value = value
                        break
                
                if header_value and isinstance(header_pattern, str):
                    # Remover a parte de versão para a correspondência
                    match_pattern = header_pattern.split('\\;')[0] if '\\;' in header_pattern else header_pattern
                    match = re.search(match_pattern, header_value, re.IGNORECASE)
                    
                    if match:
                        # Verificar confiança
                        if "\\;confidence:" in header_pattern:
                            conf_value = int(header_pattern.split("\\;confidence:")[1].split("\\;")[0])
                            confidence = max(confidence, conf_value)
                        else:
                            confidence = max(confidence, 100)
                            
                        # Obter versão
                        if "\\;version:" in header_pattern:
                            try:
                                version_pattern = header_pattern.split("\\;version:")[1].split("\\;")[0]
                                if match.groups() and version_pattern.isdigit():
                                    version = match.group(int(version_pattern))
                            except Exception:
                                pass
                                
                        matched_patterns.append(f"header:{header_name}={header_pattern}")
        
        # Verificar padrões de texto
        if "regex" in tech_patterns and "text" in tech_patterns["regex"]:
            for pattern_obj in tech_patterns["regex"]["text"]:
                match = pattern_obj["compiled"].search(html_str)
                if match:
                    pattern_confidence = pattern_obj["confidence"]
                    confidence = max(confidence, pattern_confidence)
                    
                    # Tentar extrair versão
                    extracted_version = extract_version(pattern_obj["pattern"], match, html_str)
                    if extracted_version:
                        version = extracted_version
                        
                    matched_patterns.append(f"text:{pattern_obj['pattern']}")
        
        # Verificar padrões de CSS
        if "regex" in tech_patterns and "css" in tech_patterns["regex"]:
            css_str = " ".join([style.string for style in soup.find_all("style") if style.string])
            
            for pattern_obj in tech_patterns["regex"]["css"]:
                match = pattern_obj["compiled"].search(css_str)
                if match:
                    pattern_confidence = pattern_obj["confidence"]
                    confidence = max(confidence, pattern_confidence)
                    
                    # Tentar extrair versão
                    extracted_version = extract_version(pattern_obj["pattern"], match, css_str)
                    if extracted_version:
                        version = extracted_version
                        
                    matched_patterns.append(f"css:{pattern_obj['pattern']}")
        
        # Verificar padrões de scripts
        if "regex" in tech_patterns and "scripts" in tech_patterns["regex"]:
            scripts_str = " ".join([script.string for script in soup.find_all("script") if script.string])
            
            for pattern_obj in tech_patterns["regex"]["scripts"]:
                match = pattern_obj["compiled"].search(scripts_str)
                if match:
                    pattern_confidence = pattern_obj["confidence"]
                    confidence = max(confidence, pattern_confidence)
                    
                    # Tentar extrair versão
                    extracted_version = extract_version(pattern_obj["pattern"], match, scripts_str)
                    if extracted_version:
                        version = extracted_version
                        
                    matched_patterns.append(f"scripts:{pattern_obj['pattern']}")
        
        # Se encontrou alguma evidência, adicionar à lista de tecnologias
        if confidence > 0:
            technologies[tech_name] = {
                "version": version,
                "confidence": confidence,
                "categories": tech_patterns["categories"],
                "icon": tech_patterns.get("icon", ""),
                "website": tech_patterns.get("website", ""),
                "description": tech_patterns.get("description", ""),
                "matched_patterns": matched_patterns
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
                        "description": f"{tech_name} é uma ferramenta de chat e atendimento ao cliente.",
                        "matched_patterns": [f"custom:{pattern}"]
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
