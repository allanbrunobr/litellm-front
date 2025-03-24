from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from flask_cors import CORS
import requests
import json
import os
import logging
import datetime
from datetime import datetime, timedelta
from dotenv import load_dotenv
import uuid
import sqlite3
import json
from pathlib import Path

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_secret_key')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações do LiteLLM
LITELLM_HOST = os.environ.get('LITELLM_HOST', 'https://litellm-server-458225897211.us-central1.run.app')
MASTER_KEY = os.environ.get('LITELLM_MASTER_KEY', '')

# Configuração persistente (pode ser sobrescrita pelos valores no .env)
CONFIG_FILE = 'config.json'

def load_config():
    """Carrega configuração do arquivo config.json se existir"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {str(e)}")
    return {}

def save_config(config):
    """Salva configuração no arquivo config.json"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar configuração: {str(e)}")
        return False

# Carregar configuração
config = load_config()
if 'litellm_host' in config and config['litellm_host']:
    LITELLM_HOST = config['litellm_host']
    logger.info(f"Usando servidor LiteLLM de config.json: {LITELLM_HOST}")
if 'litellm_master_key' in config and config['litellm_master_key']:
    MASTER_KEY = config['litellm_master_key']
    logger.info("Chave mestra carregada de config.json")

# Lista de modelos disponíveis
AVAILABLE_MODELS = [
    "gpt-3.5-turbo", 
    "gpt-4", 
    "gpt-4-turbo",
    "claude-3-opus", 
    "claude-3-sonnet",
    "claude-3-haiku",
    "gemini-pro",
    "gemini-1.5-pro", 
    "grok-1",
    "deepseek-chat",
    "mistral-medium",
    "mistral-large"
]

def get_available_models():
    """Obtém a lista de modelos disponíveis, tentando buscar do servidor se possível"""
    try:
        # Tentar obter do servidor
        url = f"{LITELLM_HOST}/models"
        headers = {"Authorization": f"Bearer {MASTER_KEY}"} if MASTER_KEY else {}
        
        logger.info(f"Tentando obter modelos de {url}")
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # O formato de resposta pode variar dependendo da versão do LiteLLM
            models = []
            
            if isinstance(data, dict) and "data" in data:
                # Formato comum: {"data": [{"id": "model-name"}, ...]}
                model_objs = data.get("data", [])
                for model in model_objs:
                    if isinstance(model, dict) and "id" in model:
                        models.append(model["id"])
            elif isinstance(data, list):
                # Formato alternativo: [{"id": "model-name"}, ...] ou ["model-name", ...]
                for model in data:
                    if isinstance(model, dict) and "id" in model:
                        models.append(model["id"])
                    elif isinstance(model, str):
                        models.append(model)
            
            if models:
                logger.info(f"Obtidos {len(models)} modelos do servidor")
                return models
            else:
                logger.warning(f"Formato de resposta não reconhecido: {data}")
    except Exception as e:
        logger.warning(f"Não foi possível obter modelos do servidor: {str(e)}")
    
    # Retornar a lista padrão se não conseguir obter do servidor
    logger.info(f"Usando lista padrão com {len(AVAILABLE_MODELS)} modelos")
    return AVAILABLE_MODELS

# Funções para interagir com a API do LiteLLM
def create_key(data):
    """Cria uma nova chave via API do LiteLLM"""
    try:
        url = f"{LITELLM_HOST}/key/generate"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MASTER_KEY}"
        }
        
        # Preparar o payload baseado no formato esperado pelo LiteLLM
        payload = {}
        
        # Adicionar campos apenas se tiverem valores
        if 'key_name' in data and data['key_name']:
            payload["key_name"] = data['key_name']
            # Não adicionar key_alias automaticamente, apenas se for explicitamente fornecido
        
        # Adicionar key_alias apenas se for explicitamente fornecido
        if 'key_alias' in data and data['key_alias']:
            payload["key_alias"] = data['key_alias']
        
        if 'models' in data and data['models']:
            payload["models"] = data['models']
        
        if 'max_budget' in data and data['max_budget'] is not None:
            try:
                budget_value = float(data['max_budget'])
                if budget_value > 0:
                    payload["max_budget"] = budget_value
            except (ValueError, TypeError):
                logger.warning(f"Valor inválido para max_budget: {data['max_budget']}")
        
        # Adicionar duration apenas se tiver valor - GARANTIR QUE É STRING
        if 'duration' in data and data['duration']:
            duration_str = data['duration']
            
            # Verificar se já tem um sufixo (d, h, m, s)
            import re
            if re.match(r'^[0-9]+[dhms]$', duration_str):
                # Já está no formato correto como "10d", "24h", etc.
                payload["duration"] = duration_str
            else:
                # Se for apenas um número, assumir que são dias e adicionar "d"
                try:
                    days = int(duration_str)
                    if days > 0:
                        payload["duration"] = f"{days}d"
                except ValueError:
                    logger.warning(f"Formato de duração inválido: {duration_str}")
        
        # Adicionar team_id se foi fornecido
        if 'team_id' in data and data['team_id']:
            payload["team_id"] = data['team_id']
        
        # Adicionar metadados
        payload["metadata"] = data.get('metadata', {})
        if not payload["metadata"]:
            payload["metadata"] = {"created_by": "web_interface"}
        
        logger.info(f"Enviando payload para criar chave: {json.dumps(payload, indent=2)}")
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            logger.info("Chave criada com sucesso")
            return result
        else:
            error_msg = f"Erro ao criar chave: {response.status_code}, Resposta: {response.text}"
            logger.error(error_msg)
            return {"error": error_msg}
    except Exception as e:
        logger.error(f"Exception ao criar chave: {str(e)}")
        return {"error": str(e)}

def get_keys_from_litellm():
    """Obtém lista de IDs de chaves do LiteLLM"""
    try:
        # Usar o endpoint /key/list conforme documentação
        url = f"{LITELLM_HOST}/key/list"
        headers = {"Authorization": f"Bearer {MASTER_KEY}"}
        logger.info(f"Tentando buscar chaves em: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # A resposta tem um formato específico com um campo "keys" que contém um array
            # O array pode conter strings (IDs das chaves) ou objetos (detalhes das chaves)
            
            if isinstance(data, dict) and "keys" in data:
                keys = data["keys"]
                logger.info(f"Chaves encontradas via /key/list: {len(keys)}")
                return keys
            else:
                logger.warning(f"Formato inesperado na resposta /key/list: {data}")
                return []
        else:
            logger.warning(f"Erro ao buscar chaves via /key/list. Status: {response.status_code}, Resposta: {response.text}")
            
            # Tentar endpoint alternativo
            alt_endpoints = [
                f"{LITELLM_HOST}/key/info",
                f"{LITELLM_HOST}/key/all"
            ]
            
            for alt_url in alt_endpoints:
                try:
                    logger.info(f"Tentando endpoint alternativo: {alt_url}")
                    alt_response = requests.get(alt_url, headers=headers, timeout=10)
                    
                    if alt_response.status_code == 200:
                        alt_data = alt_response.json()
                        if isinstance(alt_data, dict) and "keys" in alt_data:
                            alt_keys = alt_data["keys"]
                            logger.info(f"Chaves encontradas via {alt_url}: {len(alt_keys)}")
                            return alt_keys
                        else:
                            logger.warning(f"Formato inesperado na resposta {alt_url}: {alt_data}")
                except Exception as alt_err:
                    logger.error(f"Erro ao tentar endpoint alternativo {alt_url}: {str(alt_err)}")
            
            # Se todas as tentativas falharem, retornar uma lista vazia
            logger.warning("Todas as tentativas de obter chaves falharam. Retornando lista vazia.")
            return []
    except Exception as e:
        logger.error(f"Exception ao buscar chaves: {str(e)}")
        return []

def get_key_info(key_id):
    """Obtém informações detalhadas de uma chave específica"""
    try:
        # Se o key_id começa com sk_, remover esse prefixo para a API
        api_key_id = key_id
        if isinstance(key_id, str) and key_id.startswith("sk_"):
            api_key_id = key_id[3:]  # Remover o prefixo sk_
            
        # Tentar diferentes formatos de endpoints
        endpoints_to_try = [
            # Priorizar o endpoint que sabemos que funciona
            f"{LITELLM_HOST}/key/info?key={api_key_id}",
            f"{LITELLM_HOST}/key/info/{api_key_id}",
            # Tentar também com o prefixo original
            f"{LITELLM_HOST}/key/info?key={key_id}",
            f"{LITELLM_HOST}/key/info/{key_id}"
        ]
        
        headers = {"Authorization": f"Bearer {MASTER_KEY}"}
        
        for url in endpoints_to_try:
            try:
                logger.info(f"Tentando buscar info da chave {key_id} em: {url}")
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Informações da chave {key_id} obtidas com sucesso via {url}")
                    
                    # Verificar o formato da resposta e adaptar conforme necessário
                    if "key" in data:
                        # Formato esperado
                        return data
                    elif "info" in data:
                        # Formato alternativo - adaptar para o formato esperado
                        return {"key": data["info"]}
                    else:
                        # Tentar criar um formato compatível
                        return {"key": data}
            except Exception as e:
                logger.warning(f"Erro ao tentar endpoint {url}: {str(e)}")
                continue
        
        # Se todas as tentativas falharem, gerar dados fictícios para evitar erros de UI
        logger.warning(f"Não foi possível obter informações para a chave {key_id}. Gerando dados simulados.")
        return {
            "key": {
                "id": key_id,
                "key_name": f"Key {key_id[-8:] if len(key_id) > 8 else key_id}",
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
                "models": ["Informação indisponível"],
                "team_id": "N/A",
                "metadata": {"note": "Dados reais indisponíveis"},
                "max_budget": None,
                "spend": 0.0,
                "total_requests": 0,
                "request_history": []
            }
        }
    except Exception as e:
        logger.error(f"Exception ao buscar info da chave {key_id}: {str(e)}")
        # Retornar None para indicar erro
        return None

def delete_key(key_id):
    """Deleta uma chave específica"""
    try:
        # Remover o prefixo sk_ para API calls se existir
        api_key_id = key_id
        if isinstance(key_id, str) and key_id.startswith("sk_"):
            api_key_id = key_id[3:]  # Remover o prefixo sk_
            
        logger.info(f"Tentando revogar chave: {key_id} (API ID: {api_key_id})")
        
        # Usar o formato correto de payload conforme a documentação da API LiteLLM
        # A API espera um payload com "keys" como uma lista de chaves para deletar
        endpoint = f"{LITELLM_HOST}/key/delete"
        headers = {"Authorization": f"Bearer {MASTER_KEY}", "Content-Type": "application/json"}
        
        # Tentar com o formato correto do payload: lista de keys
        payload = {"keys": [api_key_id]}
        logger.info(f"Enviando solicitação DELETE para {endpoint} com payload: {payload}")
        
        response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
        
        # Verificar se a solicitação foi bem-sucedida
        if response.status_code in [200, 201, 202, 204]:
            logger.info(f"Revogação bem-sucedida. Resposta: {response.text}")
            return {"success": True, "message": "Key deleted successfully"}
        else:
            # Se falhar com o ID sem prefixo, tentar com o ID original
            if api_key_id != key_id:
                logger.info(f"Tentando novamente com o ID original: {key_id}")
                payload = {"keys": [key_id]}
                response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
                
                if response.status_code in [200, 201, 202, 204]:
                    logger.info(f"Revogação bem-sucedida com ID original. Resposta: {response.text}")
                    return {"success": True, "message": "Key deleted successfully"}
            
            # Se ambas tentativas falharem, retornar erro
            error_msg = f"Falha ao revogar chave. Status: {response.status_code}, Resposta: {response.text}"
            logger.error(error_msg)
            return {"error": error_msg}
            
    except Exception as e:
        logger.error(f"Exception ao deletar chave {key_id}: {str(e)}")
        return {"error": str(e)}

def parse_key_data(key_info):
    """Parse and format key data for display"""
    if not key_info or not isinstance(key_info, dict):
        logger.warning(f"Dados de chave inválidos: {key_info}")
        return None
    
    try:
        # Determinar o formato dos dados e extrair a parte relevante
        key_data = None
        if "key" in key_info and isinstance(key_info["key"], dict):
            key_data = key_info.get("key", {})
        elif "info" in key_info and isinstance(key_info["info"], dict):
            key_data = key_info.get("info", {})
        else:
            # Se temos um objeto "key" que é uma string e um objeto "info"
            if "key" in key_info and isinstance(key_info["key"], str) and "info" in key_info:
                # Este é provavelmente o formato {key: "ID", info: {detalhes}}
                key_id = key_info.get("key")
                key_data = key_info.get("info", {})
                # Adicionar o ID ao objeto de dados
                key_data["id"] = key_id
            else:
                # Assumir que o próprio objeto é os dados da chave
                key_data = key_info
            
        if not key_data or not isinstance(key_data, dict):
            logger.warning(f"Dados da chave não encontrados ou inválidos: {key_info}")
            return None
        
        # Logging completo para debug
        logger.info(f"Processando dados da chave: {json.dumps(key_data, indent=2)}")
        
        # Obter ID da chave (pode ter diferentes nomes)
        key_id = key_data.get("id", "")
        if not key_id and "key" in key_info and isinstance(key_info["key"], str):
            # Se temos key_info.key como string, este é provavelmente o ID
            key_id = key_info["key"]
        
        if not key_id:
            # Tentar outros campos possíveis
            key_id = key_data.get("token", key_data.get("api_key", key_data.get("key", "")))
        
        # Garantir que o ID da chave tem o prefixo sk_ para exibição
        if isinstance(key_id, str) and not key_id.startswith("sk_") and key_id:
            display_key_id = f"sk_{key_id}"
        else:
            display_key_id = key_id
        
        # CORREÇÃO: Obter o nome de exibição da chave do campo key_alias
        display_name = key_data.get("key_alias", "") 
        if not display_name:
            display_name = key_data.get("name", f"Key-{key_id[-8:] if len(str(key_id)) > 8 else key_id}")
        
        # IMPORTANTE: key_name contém o valor real da chave
        # Na API do LiteLLM, key_name armazena o valor real da chave que o usuário recebe
        actual_key_value = key_data.get("key_name", "")
        
        # Processar dados da chave - o key_name agora contém o valor da chave para exibição
        result = {
            'key_id': key_id,  # ID interno para operações
            'display_key_id': display_key_id,  # ID formatado para exibição
            'key_name': actual_key_value,  # Valor real da chave que o usuário deve ver
            'display_name': display_name,  # Nome de exibição/alias da chave
            'created_at': format_datetime(key_data.get('created_at')),
            'expires_at': None,  # Será configurado abaixo
            'models': key_data.get('models', []),
            'team_id': key_data.get('team_id', ""),
            'metadata': key_data.get('metadata', {}),
            'max_budget': key_data.get('max_budget'),
            'spend': key_data.get('spend', 0.0),
            'is_active': True,  # Por padrão assumimos que está ativa
            'total_requests': key_data.get('total_requests', 0),
            'recent_requests': []  # Inicialmente vazio, será preenchido se disponível
        }
        
        # Processar expiração
        # Primeiro, verificar campos conhecidos
        expires_at = key_data.get('expires_at')
        if not expires_at:
            expires_at = key_data.get('expires', key_data.get('expiry', key_data.get('expiration')))
        
        if expires_at:
            # Formatar a data de expiração
            result['expires_at'] = format_datetime(expires_at)
            
            # Verificar se expirou
            try:
                if isinstance(expires_at, str):
                    # Lidar com diferentes formatos de data
                    if "Z" in expires_at:
                        expires_at = expires_at.replace("Z", "+00:00")
                    if "T" in expires_at and ":" in expires_at:
                        exp_date = datetime.fromisoformat(expires_at)
                    else:
                        # Tentar formato simples como YYYY-MM-DD
                        exp_date = datetime.strptime(expires_at, "%Y-%m-%d")
                    
                    result['is_expired'] = exp_date < datetime.now(exp_date.tzinfo if exp_date.tzinfo else None)
                    result['is_active'] = not result['is_expired']
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(f"Erro ao processar data de expiração '{expires_at}': {str(e)}")
                # Em caso de erro, mantemos o padrão
                result['is_expired'] = False
        
        # Processar requisições recentes se disponíveis
        request_history = key_data.get('request_history', [])
        if request_history and isinstance(request_history, list):
            for req in request_history[-10:]:  # Pegamos apenas as 10 mais recentes
                if isinstance(req, dict):
                    recent_req = {
                        'timestamp': format_datetime(req.get('timestamp')),
                        'model': req.get('model', 'unknown'),
                        'request_type': req.get('call_type', req.get('type', 'chat')),
                        'total_tokens': req.get('total_tokens', 0),
                        'cost': req.get('cost', 0.0)
                    }
                    result['recent_requests'].append(recent_req)
        
        logger.info(f"Dados processados da chave: key_id={result['key_id']}, display_name={result['display_name']}, key_name={result['key_name']}")
        return result
    except Exception as e:
        logger.error(f"Erro ao processar dados da chave: {str(e)}")
        return None

def format_datetime(dt_str):
    """Format datetime string for display"""
    if not dt_str:
        return ""
    
    try:
        # Diferentes formatos de tentativa para analisar a data
        if isinstance(dt_str, str):
            # Formatos ISO com timezone
            if "Z" in dt_str:  # formato UTC com Z
                dt_str = dt_str.replace('Z', '+00:00')
                
            if "T" in dt_str and ":" in dt_str:
                # Formato ISO padrão
                dt = datetime.fromisoformat(dt_str)
            elif "-" in dt_str and len(dt_str.split("-")) == 3:
                # Formato simples de data: YYYY-MM-DD
                dt = datetime.strptime(dt_str, "%Y-%m-%d")
            elif "/" in dt_str and len(dt_str.split("/")) == 3:
                # Formato de data com barras: DD/MM/YYYY ou MM/DD/YYYY
                # Tentamos ambos
                try:
                    dt = datetime.strptime(dt_str, "%d/%m/%Y")
                except ValueError:
                    dt = datetime.strptime(dt_str, "%m/%d/%Y")
            else:
                # Tentar formato timestamp numérico
                dt = datetime.fromtimestamp(float(dt_str))
        elif isinstance(dt_str, (int, float)):
            # Se for número, assumir que é timestamp Unix
            dt = datetime.fromtimestamp(dt_str)
        else:
            # Se não for string nem número, retornar como está
            return str(dt_str)
        
        # Formatar para exibição
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError, AttributeError) as e:
        logger.debug(f"Erro ao formatar data '{dt_str}': {str(e)}")
        # Se falhar, retornar a string original
        return str(dt_str)

def get_statistics():
    """Obtém estatísticas gerais para o dashboard"""
    try:
        # Buscar todas as chaves
        all_keys = []
        keys_list = get_keys_from_litellm()
        
        for key_id in keys_list:
            key_info = get_key_info(key_id)
            if key_info:
                key_data = parse_key_data(key_info)
                if key_data:
                    all_keys.append(key_data)
        
        # Estatísticas gerais
        total_keys = len(all_keys)
        total_spend = sum(k.get('spend', 0) for k in all_keys)
        total_requests = sum(k.get('total_requests', 0) for k in all_keys)
        
        stats = {
            "total_keys": total_keys,
            "total_spend": float(total_spend) if total_spend else 0.0,
            "requests_count": int(total_requests) if total_requests else 0
        }
        
        # Gastos por modelo
        model_spends = {}
        for key in all_keys:
            for req in key.get('recent_requests', []):
                model = str(req.get('model', 'unknown'))
                try:
                    cost = float(req.get('cost', 0))
                except (ValueError, TypeError):
                    cost = 0.0
                
                if model in model_spends:
                    model_spends[model] += cost
                else:
                    model_spends[model] = cost
        
        # Formatando para gráfico e garantindo que valores são serializáveis
        model_spend_data = {"labels": [], "values": []}
        for key, value in model_spends.items():
            # Garantir que a chave é string
            safe_key = str(key)
            # Garantir que o valor é float
            try:
                if callable(value):
                    # Se for uma função ou método, substituir por 0.0
                    logger.warning(f"Valor não serializável encontrado em model_spends: {value}")
                    safe_value = 0.0
                else:
                    try:
                        safe_value = float(value) if value is not None else 0.0
                    except (ValueError, TypeError):
                        logger.warning(f"Valor não conversível para float em model_spends: {value}")
                        safe_value = 0.0
            except Exception as e:
                logger.warning(f"Erro ao processar valor em model_spends: {e}")
                safe_value = 0.0
            
            model_spend_data["labels"].append(safe_key)
            model_spend_data["values"].append(safe_value)
        
        # Gastos diários (últimos 7 dias)
        daily_spend = {}
        today = datetime.now().date()
        
        # Inicializar os últimos 7 dias com zero
        for i in range(7):
            day = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            daily_spend[day] = 0.0
        
        # Preencher com dados reais
        for key in all_keys:
            for req in key.get('recent_requests', []):
                try:
                    req_date = datetime.strptime(str(req.get('timestamp', '')), '%Y-%m-%d %H:%M:%S').date().strftime('%Y-%m-%d')
                    if req_date in daily_spend:
                        try:
                            daily_spend[req_date] += float(req.get('cost', 0))
                        except (ValueError, TypeError):
                            # Ignorar se não conseguir converter para float
                            pass
                except (ValueError, TypeError):
                    continue
        
        # Formatando para gráfico (ordem cronológica)
        sorted_days = sorted(daily_spend.keys())
        daily_spend_data = {"labels": [], "values": []}
        
        # Garantir que todos os valores são serializáveis
        for day in sorted_days:
            safe_day = str(day)
            try:
                value = daily_spend.get(day, 0.0)
                if callable(value):
                    # Se for uma função ou método, substituir por 0.0
                    logger.warning(f"Valor não serializável encontrado em daily_spend: {value}")
                    safe_value = 0.0
                else:
                    try:
                        safe_value = float(value) if value is not None else 0.0
                    except (ValueError, TypeError):
                        logger.warning(f"Erro ao converter valor para float em daily_spend: {value}")
                        safe_value = 0.0
            except Exception as e:
                logger.warning(f"Erro ao processar valor em daily_spend: {e}")
                safe_value = 0.0
            
            daily_spend_data["labels"].append(safe_day)
            daily_spend_data["values"].append(safe_value)
        
        return stats, model_spend_data, daily_spend_data, all_keys
    
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        # Retornar dados vazios em caso de erro
        empty_stats = {"total_keys": 0, "total_spend": 0.0, "requests_count": 0}
        empty_chart_data = {"labels": [], "values": []}
        return empty_stats, empty_chart_data, empty_chart_data, []

def check_litellm_health():
    """Verifica se o servidor LiteLLM está acessível"""
    try:
        url = f"{LITELLM_HOST}/health"
        headers = {"Authorization": f"Bearer {MASTER_KEY}"}
        response = requests.get(url, headers=headers, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Erro ao verificar status do LiteLLM: {str(e)}")
        return False

# Rotas da aplicação web

@app.context_processor
def utility_processor():
    """Define funções e variáveis disponíveis globalmente em todos os templates"""
    return {
        'now': datetime.now(),
        'current_year': lambda: datetime.now().year
    }

@app.route('/')
def index():
    """Página principal (dashboard)"""
    try:
        stats, model_spend_data, daily_spend_data, all_keys = get_statistics()
        
        # Criar dados seguros para o template
        try:
            # Verificar estatísticas básicas
            safe_stats = {
                "total_keys": int(stats.get("total_keys", 0)),
                "total_spend": float(stats.get("total_spend", 0.0)),
                "requests_count": int(stats.get("requests_count", 0))
            }
            
            # Dados para o gráfico de gastos por modelo
            safe_model_data = {"labels": [], "values": []}
            
            # Verificar se model_spend_data tem o formato esperado
            if (isinstance(model_spend_data, dict) and 
                "labels" in model_spend_data and 
                "values" in model_spend_data and
                len(model_spend_data["labels"]) == len(model_spend_data["values"])):
                
                # Processar cada par label/value
                for i in range(len(model_spend_data["labels"])):
                    try:
                        # Garantir que o label é string
                        label = str(model_spend_data["labels"][i])
                        
                        # Garantir que o value é float e não é um callable
                        value = model_spend_data["values"][i]
                        
                        if callable(value):
                            logger.warning(f"Valor não serializável (callable) encontrado em model_spend_data: {value}")
                            value = 0.0
                        else:
                            try:
                                value = float(value) if value is not None else 0.0
                            except (ValueError, TypeError):
                                logger.warning(f"Valor não conversível para float: {value}")
                                value = 0.0
                            
                        # Adicionar valores seguros
                        safe_model_data["labels"].append(label)
                        safe_model_data["values"].append(value)
                    except Exception as e:
                        logger.warning(f"Erro ao processar item {i} de model_spend_data: {str(e)}")
            else:
                logger.warning("model_spend_data não tem o formato esperado")
            
            # Dados para o gráfico de gastos diários
            safe_daily_data = {"labels": [], "values": []}
            
            # Verificar se daily_spend_data tem o formato esperado
            if (isinstance(daily_spend_data, dict) and 
                "labels" in daily_spend_data and 
                "values" in daily_spend_data and
                len(daily_spend_data["labels"]) == len(daily_spend_data["values"])):
                
                # Processar cada par label/value
                for i in range(len(daily_spend_data["labels"])):
                    try:
                        # Garantir que o label é string
                        label = str(daily_spend_data["labels"][i])
                        
                        # Garantir que o value é float e não é um callable
                        value = daily_spend_data["values"][i]
                        
                        if callable(value):
                            logger.warning(f"Valor não serializável (callable) encontrado em daily_spend_data: {value}")
                            value = 0.0
                        else:
                            try:
                                value = float(value) if value is not None else 0.0
                            except (ValueError, TypeError):
                                logger.warning(f"Valor não conversível para float: {value}")
                                value = 0.0
                            
                        # Adicionar valores seguros
                        safe_daily_data["labels"].append(label)
                        safe_daily_data["values"].append(value)
                    except Exception as e:
                        logger.warning(f"Erro ao processar item {i} de daily_spend_data: {str(e)}")
            else:
                logger.warning("daily_spend_data não tem o formato esperado")
            
            # Processar chaves recentes
            safe_recent_keys = []
            
            if all_keys and isinstance(all_keys, list):
                # Ordenar por data de criação (mais recentes primeiro)
                try:
                    recent_keys = sorted(all_keys, key=lambda k: k.get('created_at', ''), reverse=True)[:5]
                except Exception as e:
                    logger.warning(f"Erro ao ordenar chaves: {str(e)}")
                    recent_keys = all_keys[:5]  # Usar as primeiras 5 sem ordenar
                
                # Processar cada chave
                for key in recent_keys:
                    try:
                        if not isinstance(key, dict):
                            logger.warning(f"Chave não é um dicionário: {key}")
                            continue
                            
                        # Criar uma cópia segura com valores primitivos
                        safe_key = {
                            "key_id": str(key.get("key_id", "")),
                            "key_name": str(key.get("key_name", "")),
                            "display_name": str(key.get("display_name", "")),
                            "display_key_id": str(key.get("display_key_id", "")),
                            "created_at": str(key.get("created_at", "")),
                            "expires_at": str(key.get("expires_at", "")),
                            "models": [],
                            "team_id": str(key.get("team_id", "")),
                            "max_budget": None,
                            "spend": 0.0,
                            "is_active": bool(key.get("is_active", True)),
                            "total_requests": int(key.get("total_requests", 0))
                        }
                        
                        # Processar max_budget
                        if key.get("max_budget") is not None:
                            try:
                                safe_key["max_budget"] = float(key.get("max_budget"))
                            except (ValueError, TypeError):
                                safe_key["max_budget"] = None
                        
                        # Processar spend
                        try:
                            safe_key["spend"] = float(key.get("spend", 0.0))
                        except (ValueError, TypeError):
                            safe_key["spend"] = 0.0
                        
                        # Processar models
                        models = key.get("models", [])
                        if isinstance(models, list):
                            safe_key["models"] = [str(model) for model in models]
                        else:
                            # Se models não for uma lista, criar uma lista vazia
                            safe_key["models"] = []
                        
                        safe_recent_keys.append(safe_key)
                    except Exception as e:
                        logger.warning(f"Erro ao processar chave para exibição: {str(e)}")
            
            # Renderizar o template com dados seguros
            return render_template('index.html', 
                                  stats=safe_stats, 
                                  model_spend_data=safe_model_data,
                                  daily_spend_data=safe_daily_data,
                                  recent_keys=safe_recent_keys)
                                  
        except Exception as internal_e:
            # Logar o erro em detalhes
            logger.error(f"Erro ao processar dados para o dashboard: {str(internal_e)}", exc_info=True)
            flash(f"Erro ao processar dados do dashboard: {str(internal_e)}", "danger")
            
            # Fornecer dados vazios para evitar erros de renderização
            empty_stats = {"total_keys": 0, "total_spend": 0.0, "requests_count": 0}
            empty_chart_data = {"labels": [], "values": []}
            return render_template('index.html', 
                                  stats=empty_stats,
                                  model_spend_data=empty_chart_data,
                                  daily_spend_data=empty_chart_data,
                                  recent_keys=[],
                                  error_message="Erro ao processar dados do dashboard. Verifique o log para mais detalhes.")
    
    except Exception as e:
        # Logar o erro em detalhes
        logger.error(f"Erro ao renderizar dashboard: {str(e)}", exc_info=True)
        flash(f"Erro ao carregar dados do dashboard: {str(e)}", "danger")
        
        # Fornecer dados vazios para evitar erros de renderização
        empty_stats = {"total_keys": 0, "total_spend": 0.0, "requests_count": 0}
        empty_chart_data = {"labels": [], "values": []}
        return render_template('index.html', 
                              stats=empty_stats,
                              model_spend_data=empty_chart_data,
                              daily_spend_data=empty_chart_data,
                              recent_keys=[],
                              error_message="Não foi possível carregar os dados do dashboard. Verifique o log para mais detalhes.")

@app.route('/keys')
def keys():
    """Página de gerenciamento de chaves"""
    try:
        # Buscar todas as chaves
        keys_list = get_keys_from_litellm()
        processed_keys = []
        
        for key_id in keys_list:
            key_info = get_key_info(key_id)
            if key_info:
                key_data = parse_key_data(key_info)
                if key_data:
                    processed_keys.append(key_data)
        
        # Ordenar chaves por data de criação (mais recentes primeiro)
        processed_keys = sorted(processed_keys, key=lambda k: k.get('created_at', ''), reverse=True)
        
        # Obter a lista dinâmica de modelos disponíveis
        available_models = get_available_models()
        
        logger.info(f"Renderizando página de chaves com {len(processed_keys)} chaves encontradas e {len(available_models)} modelos disponíveis")
        
        return render_template('keys.html', 
                            keys=processed_keys,
                            available_models=available_models)
    except Exception as e:
        logger.error(f"Erro ao renderizar página de chaves: {str(e)}")
        flash(f"Erro ao carregar lista de chaves: {str(e)}", "danger")
        return render_template('keys.html', 
                            keys=[],
                            available_models=AVAILABLE_MODELS,
                            error_message="Não foi possível carregar a lista de chaves. Verifique o log para mais detalhes.")

@app.route('/keys/<key_id>')
def key_detail(key_id):
    """Página de detalhes de uma chave específica"""
    key_info = get_key_info(key_id)
    
    if key_info:
        key_data = parse_key_data(key_info)
        return render_template('key_detail.html', key=key_data)
    else:
        flash('Chave não encontrada', 'danger')
        return redirect(url_for('keys'))

@app.route('/settings')
def settings():
    """Página de configurações"""
    # Verificar conexão com o servidor LiteLLM
    litellm_status = check_litellm_health()
    
    # Buscar configuração atual
    config = {
        'litellm_host': LITELLM_HOST,
        'master_key': MASTER_KEY,
        'environment': os.environ.get('FLASK_ENV', 'development'),
    }
    
    return render_template('settings.html', 
                           config=config,
                           litellm_status=litellm_status)

# API Routes

@app.route('/api/health', methods=['GET'])
def api_health():
    """Endpoint para verificar a saúde da aplicação e conexão com LiteLLM"""
    litellm_status = check_litellm_health()
    return jsonify({
        "status": "ok",
        "litellm_server": litellm_status,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/keys', methods=['GET'])
def api_get_keys():
    """Endpoint para listar todas as chaves (API)"""
    try:
        keys_list = get_keys_from_litellm()
        processed_keys = []
        
        for key_id in keys_list:
            key_info = get_key_info(key_id)
            if key_info:
                key_data = parse_key_data(key_info)
                if key_data:
                    processed_keys.append(key_data)
        
        return jsonify({"keys": processed_keys})
    except Exception as e:
        logger.error(f"API error retrieving keys: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/keys/<key_id>', methods=['GET'])
def api_get_key(key_id):
    """Endpoint para obter detalhes de uma chave específica (API)"""
    try:
        key_info = get_key_info(key_id)
        if key_info:
            key_data = parse_key_data(key_info)
            if key_data:
                return jsonify(key_data)
        
        return jsonify({"error": "Key not found"}), 404
    except Exception as e:
        logger.error(f"API error retrieving key {key_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/keys/<key_id>', methods=['DELETE'])
def api_delete_key(key_id):
    """Endpoint para deletar uma chave (API)"""
    try:
        logger.info(f"Recebida solicitação para deletar chave: {key_id}")
        result = delete_key(key_id)
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"API error deleting key {key_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/keys', methods=['POST'])
def api_create_key():
    """Endpoint para criar uma nova chave"""
    try:
        data = request.json
        logger.info(f"Solicitação para criar chave recebida: {data}")
        
        # Validação básica
        if not data:
            return jsonify({"error": "Dados inválidos ou ausentes"}), 400
            
        # Validar que temos pelo menos key_alias (nome descritivo da chave)
        if not data.get('key_alias'):
            return jsonify({"error": "Nome da chave (key_alias) é obrigatório"}), 400
        
        # Garantir que key_name não está sendo definido pelo cliente
        # O servidor LiteLLM é que deve gerar esse valor
        if 'key_name' in data:
            logger.warning("Cliente está tentando definir key_name, que será ignorado")
            data.pop('key_name')
        
        # Validar duração se fornecida
        if 'duration' in data and data['duration']:
            import re
            if not re.match(r'^[0-9]+[dhms]?$', data['duration']):
                return jsonify({"error": "Formato de duração inválido. Use números seguidos por d (dias), h (horas), m (minutos) ou s (segundos)."}), 400
        
        # Validar orçamento se fornecido
        if 'max_budget' in data and data['max_budget']:
            try:
                budget = float(data['max_budget'])
                if budget <= 0:
                    return jsonify({"error": "Orçamento máximo deve ser maior que zero"}), 400
            except (ValueError, TypeError):
                return jsonify({"error": "Valor de orçamento inválido"}), 400
        
        # Validar modelos (se não for fornecido, todos os modelos são permitidos)
        if 'models' in data and not isinstance(data['models'], list):
            return jsonify({"error": "Modelos deve ser uma lista"}), 400
        
        # Criar chave
        result = create_key(data)
        
        if 'error' in result:
            return jsonify(result), 400
        
        # Registrar sucesso no log e retornar resultado
        logger.info(f"Chave criada com sucesso com alias: {data.get('key_alias', '')}")
        return jsonify(result)
    except Exception as e:
        error_msg = f"Erro ao processar solicitação de criação de chave: {str(e)}"
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 500

@app.route('/api/test_connection', methods=['POST'])
def api_test_connection():
    """Endpoint para testar a conexão com o servidor LiteLLM"""
    try:
        data = request.json
        
        # Extrair parâmetros
        server_url = data.get('server_url', LITELLM_HOST)
        master_key = data.get('master_key', MASTER_KEY)
        
        if not server_url:
            return jsonify({"error": "URL do servidor é obrigatória"}), 400
        
        # Tentar conectar ao endpoint de saúde
        test_url = f"{server_url}/health"
        headers = {"Authorization": f"Bearer {master_key}"} if master_key else {}
        
        logger.info(f"Testando conexão com {test_url}")
        response = requests.get(test_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            logger.info("Teste de conexão bem-sucedido")
            return jsonify({
                "success": True,
                "message": "Conexão com o servidor bem-sucedida",
                "status_code": response.status_code,
                "response": response.json() if response.text else {}
            })
        else:
            error_msg = f"Erro ao conectar. Status: {response.status_code}"
            logger.warning(error_msg)
            return jsonify({
                "success": False,
                "error": error_msg,
                "status_code": response.status_code,
                "response": response.text
            }), 400
    except requests.exceptions.RequestException as e:
        error_msg = f"Erro ao conectar ao servidor: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 400
    except Exception as e:
        error_msg = f"Erro interno ao testar conexão: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    """Endpoint para salvar configurações do servidor"""
    try:
        data = request.json
        
        # Validar dados
        if not data:
            return jsonify({"error": "Dados inválidos"}), 400
            
        # Atualizar as configurações globais
        global LITELLM_HOST, MASTER_KEY
        
        # Verificar e atualizar cada configuração
        if 'server_url' in data and data['server_url']:
            LITELLM_HOST = data['server_url']
        
        if 'master_key' in data:
            MASTER_KEY = data['master_key']
        
        # Salvar no arquivo de configuração
        config = {
            'litellm_host': LITELLM_HOST,
            'litellm_master_key': MASTER_KEY
        }
        
        if save_config(config):
            return jsonify({
                "success": True,
                "message": "Configurações salvas com sucesso",
                "config": {
                    "litellm_host": LITELLM_HOST,
                    "master_key_set": bool(MASTER_KEY)  # Não enviar a chave de volta, apenas indicar se está definida
                }
            })
        else:
            return jsonify({
                "error": "Não foi possível salvar a configuração no arquivo"
            }), 500
    except Exception as e:
        error_msg = f"Erro ao salvar configurações: {str(e)}"
        logger.error(error_msg)

# Inicialização da aplicação

def init_app():
    """Inicializa a aplicação, configurando templates"""
    # Criar diretórios necessários
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    # Garantir que arquivos principais existem
    if not os.path.exists('static/css/style.css'):
        logger.warning("Arquivo CSS não encontrado, será criado")
        with open('static/css/style.css', 'w') as f:
            f.write('/* Arquivo CSS base */\n')
    
    if not os.path.exists('static/js/scripts.js'):
        logger.warning("Arquivo JavaScript não encontrado, será criado")
        with open('static/js/scripts.js', 'w') as f:
            f.write('/* Arquivo JavaScript base */\n')
    
    logger.info(f"Aplicação inicializada.")
    logger.info(f"Servidor LiteLLM: {LITELLM_HOST}")

# Inicializar a aplicação no startup
init_app()

# Executar servidor web quando este script é executado diretamente
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV", "production") != "production"
    
    logger.info(f"Iniciando servidor na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=debug) 