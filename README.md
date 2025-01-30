# Chutes2api
### 对你有用的话麻烦给个stars谢谢

## 支持模型
- nvidia/Llama-3.1-405B-Instruct-FP8
- deepseek-ai/DeepSeek-R1  
- Qwen/Qwen2.5-72B-Instruct
- Qwen/Qwen2.5-Coder-32B-Instruc
- bytedance-research/UI-TARS-72B-DPO
- OpenGVLab/InternVL2_5-78B
- hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4
- NousResearch/Hermes-3-Llama-3.1-8B
- Qwen/QVQ-72B-Preview
- deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
- jondurbin/bagel-8b-v1.0
- unsloth/QwQ-32B-Preview
- Qwen/QwQ-32B-Preview
- jondurbin/airoboros-34b-3.3
- NovaSky-AI/Sky-T1-32B-Preview
- driaforall/Dria-Agent-a-3B
- NousResearch/Nous-Hermes-Llama2-13b
- unsloth/Llama-3.2-1B-Instruct


## 请求路由
 - /v1/models
 - /v1/chat/completions
 - 如果有配置AUTH_TOKEN请求都要带key


## 请求格式
和 OpenAI 的请求格式相同，支持非流式和流式响应

## Docker部署

### Linux版本
```bash
# 拉取
docker pull mtxyt/chutes2api-linux:1.2

# 运行(不带认证)
docker run -d -p 8805:8805 mtxyt/chutes2api-linux:1.2

# 运行(带认证)
docker run -d -e AUTH_TOKEN=your_token -p 8805:8805 mtxyt/chutes2api-linux:1.2
```

### Windows版本
```bash
# 拉取
docker pull mtxyt/chutes2api:1.5

# 运行(不带认证)
docker run -d -p 8805:8805 mtxyt/chutes2api:1.5

# 运行(带认证)
docker run -d -e AUTH_TOKEN=your_token -p 8805:8805 mtxyt/chutes2api:1.5
```

## Token获取方式
### 准备步骤
1. 访问 [chutes.ai](https://chutes.ai)
2. 随便找一个LLM模型切换到chat聊天界面里
4. 打开开发者工具(F12)，切换到网络面板
5. 随便发起一个对话
6. 在请求中找到 cf_clearance cookie(如果没有多对话几次回复空值就是触发盾了刷新网页过人机验证再请求就有了)
![image](https://github.com/user-attachments/assets/9e5423aa-9b4c-4c97-a737-281d3f195884)

如果你配置了 AUTH_TOKEN，完整的认证格式为：`AUTH_TOKEN|||cf_clearance`

例如:
- AUTH_TOKEN=123456
- cf_clearance=abcdef
- 最终认证格式: `123456|||abcdef`

## 注意事项
1. cf_clearance 有时效性，过期后会自动获取新的
2. 支持配置和不配置 AUTH_TOKEN 两种方式
3. 服务启动后可以访问根路径查看服务状态

## 更多
目前提供 Linux 和 Windows 两个版本的镜像，win版本在win系统系统运行时稳定性更好。

## 声明
本项目仅供学习研究使用，请勿用于商业用途。
