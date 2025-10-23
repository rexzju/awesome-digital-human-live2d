# -*- coding: utf-8 -*-
'''
@File    :   difyAgnet.py
@Author  :   一力辉 
'''

from ..builder import AGENTS
from ..agentBase import BaseAgent
import re
import json
import asyncio
from digitalHuman.protocol import *
from digitalHuman.utils import httpxAsyncClient, logger, resonableStreamingParser

__all__ = ["DifyApiAgent"]


@AGENTS.register("Dify")
class DifyApiAgent(BaseAgent):
    def _normalize_api_server(self, api_server):
        """规范化 API 服务器 URL，确保包含协议前缀"""
        if not api_server:
            raise ValueError("Dify API Server URL is required")
        # 确保 URL 包含协议前缀
        if not api_server.startswith(('http://', 'https://')):
            api_server = f'http://{api_server}'
        # 确保 URL 末尾没有斜杠
        if api_server.endswith('/'):
            api_server = api_server[:-1]
        return api_server
    
    async def createConversation(self, **kwargs) -> str:
        # 参数校验
        paramters = self.checkParameter(**kwargs)
        api_server = self._normalize_api_server(paramters["api_server"])
        api_key = paramters["api_key"]
        username = paramters["username"]

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        payload = {
            "inputs": {},
            "query": "hello",
            "response_mode": "blocking",
            "user": username,
            "conversation_id": "",
            "files":[]
        }

        # 添加显式重试机制，最多重试3次
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 使用全局的 httpxAsyncClient 并确保正确的错误处理
                logger.debug(f"[DIFY] 正在创建对话，尝试连接服务器 {api_server}，尝试次数: {retry_count + 1}/{max_retries}")
                response = await httpxAsyncClient.post(api_server + "/chat-messages", headers=headers, json=payload)
                logger.debug(f"[DIFY] 创建对话请求成功，状态码: {response.status_code}")
                
                if response.status_code != 200:
                    raise RuntimeError(f"DifyAPI agent api error: {response.status_code}, message: {response.text}")

                data = json.loads(response.text)
                if 'conversation_id' not in data:
                    logger.error(f"[AGENT] Engine create conversation failed: {data}")
                    return ""
                logger.debug(f"[DIFY] 成功创建对话，conversation_id: {data['conversation_id']}")
                return data['conversation_id']
            except Exception as e:
                retry_count += 1
                error_type = str(type(e).__name__)
                
                # 只对连接错误和超时错误进行重试
                if "ConnectError" in error_type or "TimeoutException" in error_type:
                    if retry_count < max_retries:
                        logger.warning(f"[DIFY] 创建对话连接失败，将在{retry_count * 2}秒后重试 ({retry_count}/{max_retries}): {str(e)}")
                        import asyncio
                        await asyncio.sleep(retry_count * 2)  # 指数退避策略
                        continue  # 继续重试
                    else:
                        # 重试次数用尽，抛出错误
                        if "ConnectError" in error_type:
                            error_msg = f"无法连接到 Dify 服务器: {api_server}。请检查服务器地址是否正确以及网络连接。"
                            logger.error(f"[DIFY] 创建对话连接错误 (已重试{max_retries}次): {str(e)}", exc_info=True)
                            raise RuntimeError(error_msg) from e
                        elif "TimeoutException" in error_type:
                            error_msg = f"连接 Dify 服务器超时: {api_server}。请检查服务器是否正常运行。"
                            logger.error(f"[DIFY] 创建对话超时错误 (已重试{max_retries}次): {str(e)}", exc_info=True)
                            raise RuntimeError(error_msg) from e
                # 非连接错误，直接抛出
                logger.error(f"[DifyApiAgent] 创建对话异常: {e}", exc_info=True)
                raise


    async def run(
        self, 
        input: TextMessage, 
        streaming: bool,
        **kwargs
    ):
        # 参数校验
        try:
            if not streaming:
                raise KeyError("Dify Agent only supports streaming mode")
            # 参数校验
            paramters = self.checkParameter(**kwargs)
            api_server = self._normalize_api_server(paramters["api_server"])
            api_key = paramters["api_key"]
            username = paramters["username"]
        
            conversation_id = paramters["conversation_id"] if "conversation_id" in paramters else ""
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }

            responseMode = "streaming" if streaming else "blocking"
            payload = {
                "inputs": {},
                "query": input.data,
                "response_mode": responseMode,
                "user": username,
                "conversation_id": conversation_id,
                "files":[]
            }

            pattern = re.compile(r'data:\s*({.*})')
            
            # 添加显式重试机制，最多重试3次
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    # 使用全局的 httpxAsyncClient 进行流式请求
                    logger.debug(f"[DIFY] 正在尝试连接到服务器 {api_server}，尝试次数: {retry_count + 1}/{max_retries}")
                    # 添加超时参数，防止连接建立后一直等待
                    async with httpxAsyncClient.stream('POST', api_server + "/chat-messages", headers=headers, json=payload, timeout=30.0) as response:
                        logger.debug(f"[DIFY] 成功连接到服务器并收到响应，状态码: {response.status_code}")
                        coversaiotnIdRequire = False if conversation_id else True
                        async def generator(coversaiotnIdRequire):
                            message_id = ""
                            # 设置最大等待时间（秒）
                            max_wait_time = 60
                            last_data_time = asyncio.get_event_loop().time()
                            
                            async for chunk in response.aiter_lines():
                                # 更新最后收到数据的时间
                                last_data_time = asyncio.get_event_loop().time()
                                
                                chunkStr = chunk.strip()
                                if not chunkStr: continue
                                chunkData = pattern.search(chunkStr)
                                # 返回不完整，该模板匹配会失效
                                if not chunkStr.endswith('}') or not chunkData: 
                                    logger.warning(f"[AGENT] Engine return truncated data: {chunkStr}")
                                    continue
                                chunkData = chunkData.group(1)

                                # 处理流式返回字符串
                                data = json.loads(chunkData)
                                # 首次返回conversation_id
                                if coversaiotnIdRequire and 'conversation_id' in data:
                                    yield (EVENT_TYPE.CONVERSATION_ID, data['conversation_id'])
                                    coversaiotnIdRequire = False
                                if not message_id and 'message_id' in data:
                                    message_id = data['message_id']
                                if "message" in data["event"] and 'answer' in data:
                                    logger.debug(f"[AGENT] Engine response: {data}")
                                    yield (EVENT_TYPE.TEXT, data['answer'])
                            
                            # 检查是否超时
                            current_time = asyncio.get_event_loop().time()
                            if current_time - last_data_time > max_wait_time:
                                logger.error(f"[DIFY] 流式响应超时，超过{max_wait_time}秒未收到新数据")
                                yield (EVENT_TYPE.ERROR, f"Dify API响应超时，超过{max_wait_time}秒未收到数据")
                            else:
                                yield (EVENT_TYPE.MESSAGE_ID, message_id)
                        async for parseResult in resonableStreamingParser(generator(coversaiotnIdRequire)):
                            yield parseResult
                    yield eventStreamDone()
                    break  # 成功完成，退出重试循环
                except Exception as e:
                    retry_count += 1
                    error_type = str(type(e).__name__)
                    
                    # 只对连接错误和超时错误进行重试
                    if "ConnectError" in error_type or "TimeoutException" in error_type:
                        if retry_count < max_retries:
                            logger.warning(f"[DIFY] 连接失败，将在{retry_count * 2}秒后重试 ({retry_count}/{max_retries}): {str(e)}")
                            await asyncio.sleep(retry_count * 2)  # 指数退避策略
                            continue  # 继续重试
                        else:
                            # 重试次数用尽，返回错误
                            if "ConnectError" in error_type:
                                error_msg = f"无法连接到 Dify 服务器: {api_server}。请检查服务器地址是否正确、网络连接是否正常。"
                                logger.error(f"[DIFY] 连接错误 (已重试{max_retries}次): {str(e)}", exc_info=True)
                                yield eventStreamError(error_msg)
                            elif "TimeoutException" in error_type:
                                error_msg = f"连接 Dify 服务器超时: {api_server}。请检查服务器是否正常运行，或尝试增加超时时间。"
                                logger.error(f"[DIFY] 超时错误 (已重试{max_retries}次): {str(e)}", exc_info=True)
                                yield eventStreamError(error_msg)
                    else:
                        # 非连接错误，直接返回错误
                        logger.error(f"[DifyApiAgent] 请求处理异常: {e}", exc_info=True)
                        yield eventStreamError(str(e))
                    break  # 处理完错误后退出循环
        except Exception as e:
            # 处理参数校验等前置错误
            logger.error(f"[DifyApiAgent] 初始化错误: {e}", exc_info=True)
            yield eventStreamError(f"Dify代理初始化错误: {str(e)}")