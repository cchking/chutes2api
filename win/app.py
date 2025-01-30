from flask import Flask, request, Response, stream_with_context, jsonify
import cloudscraper
import json
import uuid
from datetime import datetime, timezone
import time
import os

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

def check_auth():
    """检查认证"""
    auth_token = os.getenv('AUTH_TOKEN')
    if not auth_token:
        return True
    
    request_token = request.headers.get('Authorization', '')
    return request_token == f"Bearer {auth_token}"

def create_scraper():
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'linux',
            'desktop': True,
            'mobile': False,
            'version': '121.0.0.0'
        }
    )
    
    # 设置请求头
    scraper.headers.update({
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Content-Type": "text/plain;charset=UTF-8",
        "Origin": "https://chutes.ai",
        "Pragma": "no-cache",
        "Referer": "https://chutes.ai/",
        "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Linux"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
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
        print(f"Error processing non-stream response: {str(e)}")
        return Response("Failed to process response", status=500)

@app.route('/', methods=['GET'])
def home():
    """健康检查端点"""
    return {"status": "Chutes API Service Running", "version": "1.0"}

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
        chutes_request = create_chutes_request(openai_request)
        scraper = create_scraper()

        headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Content-Type": "text/plain;charset=UTF-8",
            "Origin": "https://chutes.ai",
            "Pragma": "no-cache",
            "Referer": "https://chutes.ai/app/chute/590d919c-8d4c-5b7b-9445-ed2cd71944a8",
            "Sec-Ch-Ua": '"Not A(Brand";v="8", "Chromium";v="132", "Microsoft Edge";v="132"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }

        response = scraper.post(
            "https://chutes.ai/app/api/chat",
            headers=headers,
            json=chutes_request,
            stream=True
        )

        if response.status_code != 200:
            return Response(f"Chutes API error: {response.text}", status=response.status_code)

        # 处理非流式请求
        if not openai_request.get('stream', False):
            result = process_non_stream_response(response, chutes_request["model"])
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
                                        "model": chutes_request["model"],
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
                print(f"Error in generate: {str(e)}")
                return

        return Response(
            stream_with_context(generate()),
            content_type='text/event-stream'
        )

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return Response(f"Internal server error: {str(e)}", status=500)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8805))
    app.run(host='0.0.0.0', port=port, debug=False)
