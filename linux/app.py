from flask import Flask, request, Response, stream_with_context, jsonify
import cloudscraper
import json
import uuid
from datetime import datetime, timezone
import time
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)

# 模型映射字典
MODEL_MAPPING = {
   "nvidia/Llama-3.1-405B-Instruct-FP8": "chutes-nvidia-llama-3-1-405b-instruct-fp8",
   "deepseek-ai/DeepSeek-R1": "chutes-deepseek-ai-deepseek-r1",
   "Qwen/Qwen2.5-72B-Instruct": "chutes-qwen-qwen2-5-72b-instruct", 
   "Qwen/Qwen2.5-Coder-32B-Instruc": "chutes-qwen-qwen2-5-coder-32b-instruct",
   "bytedance-research/UI-TARS-72B-DPO": "chutes-bytedance-research-ui-tars-72b-dpo",
   "OpenGVLab/InternVL2_5-78B": "chutes-opengvlab-internvl2-5-78b",
   "hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4": "chutes-hugging-quants-meta-llama-3-1-70b-instruct-awq-int4",
   "NousResearch/Hermes-3-Llama-3.1-8B": "cxmplexbb-nousresearch-hermes-3-llama-3-1-8b",
   "Qwen/QVQ-72B-Preview": "chutes-qwen-qvq-72b-preview",
   "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B": "chutes-deepseek-ai-deepseek-r1-distill-qwen-32b",
   "jondurbin/bagel-8b-v1.0": "chutes-jondurbin-bagel-8b-v1-0",
   "unsloth/QwQ-32B-Preview": "cxmplexbb-unsloth-qwq-32b-preview",
   "Qwen/QwQ-32B-Preview": "chutes-qwq-32b-preview",
   "jondurbin/airoboros-34b-3.3": "chutes-jondurbin-airoboros-34b-3-3",
   "NovaSky-AI/Sky-T1-32B-Preview": "chutes-novasky-ai-sky-t1-32b-preview",
   "driaforall/Dria-Agent-a-3B": "chutes-driaforall-dria-agent-a-3b",
   "NousResearch/Nous-Hermes-Llama2-13b": "cxmplexbb-nousresearch-nous-hermes-llama2-13b",
   "unsloth/Llama-3.2-1B-Instruct": "chutes-unsloth-llama-3-2-1b-instruct"
}

# 存储当前的 cf_clearance 和 key
current_cf_clearance = None
auth_token = os.getenv('AUTH_TOKEN', '')  # 从环境变量获取 AUTH_TOKEN

def check_auth():
    """检查认证"""
    request_token = request.headers.get('Authorization', '')
    if not auth_token:
        return True
    return request_token == f"Bearer {auth_token}"

def get_new_cf_clearance():
    """动态获取新的 cf_clearance"""
    try:
        temp_scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'firefox',
                'platform': 'windows',
                'mobile': False
            },
            delay=10,
            allow_brotli=False,
            doubleDown=True
        )
        
        if current_cf_clearance:
            if auth_token:
                temp_scraper.headers.update({
                    "Authorization": f"Bearer {auth_token}|||{current_cf_clearance}"
                })
            else:
                temp_scraper.headers.update({
                    "Authorization": f"Bearer {current_cf_clearance}"
                })
        elif auth_token:
            temp_scraper.headers.update({
                "Authorization": f"Bearer {auth_token}"
            })
            
        logging.info("尝试获取新的 cf_clearance")
        response = temp_scraper.get('https://chutes.ai')
        
        if 'cf_clearance' in temp_scraper.cookies:
            new_cf = temp_scraper.cookies['cf_clearance']
            logging.info(f"成功获取新的 cf_clearance: {new_cf[:10]}...")
            return new_cf
        logging.warning("未能获取 cf_clearance")
        return None
    except Exception as e:
        logging.error(f"获取新的 cf_clearance 失败: {str(e)}")
        return None

def create_scraper(cf_clearance=None):
    """创建配置好的 scraper"""
    global current_cf_clearance
    
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'firefox',
            'platform': 'windows',
            'mobile': False
        },
        delay=10,
        allow_brotli=False,
        doubleDown=True
    )
    
    # 基础请求头配置
    scraper.headers.update({
        "Accept": "text/event-stream",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "Origin": "https://chutes.ai",
        "Pragma": "no-cache",
        "Referer": "https://chutes.ai/",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Microsoft Edge";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
        "X-Requested-With": "XMLHttpRequest"
    })
    
    # 使用提供的或当前的 cf_clearance
    cf_value = cf_clearance or current_cf_clearance
    if cf_value:
        scraper.cookies.update({
            "cf_clearance": cf_value
        })
        # 构造 Authorization 头
        if auth_token:
            scraper.headers.update({
                "Authorization": f"Bearer {auth_token}|||{cf_value}"
            })
        else:
            # 如果没有 auth_token，只使用 cf_clearance
            scraper.headers.update({
                "Authorization": f"Bearer {cf_value}"
            })
    
    return scraper

def create_chutes_request(openai_request):
    """将OpenAI格式请求转换为Chutes格式"""
    messages = openai_request['messages']
    message_id = str(uuid.uuid4())
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    model = openai_request.get('model', 'deepseek-ai/DeepSeek-R1')
    chute_name = MODEL_MAPPING.get(model, 'chutes-deepseek-ai-deepseek-r1')
    
    return {
        "messages": [{
            "role": messages[-1]['role'],
            "content": messages[-1]['content'],
            "id": message_id,
            "createdOn": current_time
        }],
        "model": model,
        "chuteName": chute_name
    }

def process_chunk(chunk):
    """处理响应数据块"""
    try:
        if "choices" in chunk and chunk["choices"][0]["delta"].get("content"):
            return chunk["choices"][0]["delta"]["content"]
        return None
    except:
        return None

def process_non_stream_response(response, model):
    """处理非流式响应"""
    try:
        full_content = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = process_chunk(chunk)
                        if content:
                            full_content += content
                    except json.JSONDecodeError:
                        continue

        if not full_content:
            return Response("Empty response from server", status=500)

        return {
            "id": str(uuid.uuid4()),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": full_content
                },
                "finish_reason": "stop",
                "index": 0
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
    except Exception as e:
        logging.error(f"处理非流式响应时出错: {str(e)}")
        return Response("Failed to process response", status=500)

def make_request_with_retry(openai_request, max_retries=3):
    """带重试机制的请求函数"""
    global current_cf_clearance
    
    chutes_request = create_chutes_request(openai_request)
    last_error = None
    
    for attempt in range(max_retries):
        try:
            scraper = create_scraper()
            logging.info(f"尝试第 {attempt + 1} 次请求")
            
            response = scraper.post(
                "https://chutes.ai/app/api/chat",
                json=chutes_request,
                stream=True
            )
            
            logging.info(f"请求状态码: {response.status_code}")
            
            # 如果响应成功,返回响应对象
            if response.status_code == 200:
                return response
                
            # 如果是 403 错误,尝试获取新的 cf_clearance
            if response.status_code == 403:
                logging.warning(f"尝试 {attempt + 1}: 获取新的 cf_clearance")
                new_cf_clearance = get_new_cf_clearance()
                if new_cf_clearance:
                    current_cf_clearance = new_cf_clearance
                    continue
                    
            last_error = f"Status code: {response.status_code}, Response: {response.text}"
            logging.error(f"请求失败: {last_error}")
            
        except Exception as e:
            last_error = str(e)
            logging.error(f"尝试 {attempt + 1} 失败: {last_error}", exc_info=True)
        
        # 在重试之前等待一段时间
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # 指数退避
            
    # 所有重试都失败后返回错误
    return Response(f"请求失败,所有重试均未成功。最后的错误: {last_error}", status=500)

@app.route('/', methods=['GET'])
def home():
    """健康检查端点"""
    config_info = {
        "status": "Chutes API Service Running",
        "version": "1.0",
        "has_auth_token": bool(auth_token),
        "has_cf_clearance": bool(current_cf_clearance)
    }
    return config_info

@app.route('/v1/models', methods=['GET'])
def get_models():
    """获取可用模型列表"""
    if not check_auth():
        return Response("Unauthorized", status=401)
        
    models = []
    for model_id in MODEL_MAPPING.keys():
        models.append({
            "id": model_id,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "chutes"
        })
    
    return jsonify({
        "object": "list",
        "data": models
    })

@app.route('/v1/chat/completions', methods=['POST'])
def chat():
    """聊天完成接口"""
    try:
        if not check_auth():
            return Response("Unauthorized", status=401)

        openai_request = request.json
        logging.info("收到新的聊天请求")
        response = make_request_with_retry(openai_request)
        
        # 如果返回的是错误响应,直接返回
        if isinstance(response, Response):
            return response
            
        # 处理非流式请求
        if not openai_request.get('stream', False):
            result = process_non_stream_response(response, openai_request.get('model'))
            return Response(
                json.dumps(result, ensure_ascii=False),
                status=200,
                content_type='application/json'
            ) if isinstance(result, dict) else result

        # 处理流式请求
        def generate():
            try:
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                yield "data: [DONE]\n\n"
                                break
                            
                            try:
                                chunk = json.loads(data)
                                content = process_chunk(chunk)
                                if content:
                                    response_chunk = {
                                        "id": str(uuid.uuid4()),
                                        "object": "chat.completion.chunk",
                                        "created": int(time.time()),
                                        "model": openai_request.get('model'),
                                        "choices": [{
                                            "delta": {
                                                "content": content
                                            },
                                            "index": 0,
                                            "finish_reason": None
                                        }]
                                    }
                                    yield f"data: {json.dumps(response_chunk, ensure_ascii=False)}\n\n"
                            except json.JSONDecodeError:
                                continue
                            
            except Exception as e:
                logging.error(f"生成响应时出错: {str(e)}", exc_info=True)
                return

        return Response(
            stream_with_context(generate()),
            content_type='text/event-stream'
        )

    except Exception as e:
        logging.error(f"聊天接口出错: {str(e)}", exc_info=True)
        return Response(f"服务器内部错误: {str(e)}", status=500)

if __name__ == '__main__':
   port = int(os.getenv('PORT', 8805))
   app.run(host='0.0.0.0', port=port, debug=False)
