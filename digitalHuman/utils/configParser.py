# -*- coding: utf-8 -*-
'''
@File    :   configParser.py
@Author  :   一力辉 
'''

import os
import re
from digitalHuman.utils.env import CONFIG_ROOT_PATH, CONFIG_FILE
from yacs.config import CfgNode as CN

__all__ = ['config']

def replaceConfigVariables(config, rootConfig=None):
    """递归替换配置中的变量引用${path.to.value}"""
    if rootConfig is None:
        rootConfig = config
    
    # 处理CfgNode对象
    if isinstance(config, CN):
        for key in list(config.keys()):
            config[key] = replaceConfigVariables(config[key], rootConfig)
    # 处理字典
    elif isinstance(config, dict):
        for key, value in list(config.items()):
            config[key] = replaceConfigVariables(value, rootConfig)
    # 处理列表
    elif isinstance(config, list):
        for i, item in enumerate(config):
            config[i] = replaceConfigVariables(item, rootConfig)
    # 处理字符串
    elif isinstance(config, str):
        # 查找所有${...}格式的变量引用
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, config)
        for match in matches:
            # 解析路径
            keys = match.split('.')
            # 从根配置开始查找值
            value = rootConfig
            try:
                for key in keys:
                    if isinstance(value, CN):
                        value = getattr(value, key, None)
                    elif isinstance(value, dict):
                        value = value.get(key, None)
                    if value is None:
                        break
                
                # 如果找到值，替换引用
                if value is not None:
                    config = config.replace(f'${{{match}}}', str(value))
            except (AttributeError, KeyError, TypeError):
                # 如果路径无效，保持原样
                pass
    return config

def parseConfig(configFile: str, rootConfig=None) -> CN:
    with open(configFile, 'r', encoding='utf-8') as f:
        config = CN.load_cfg(f)
        # 如果提供了根配置，执行变量替换
        if rootConfig is not None:
            # 直接在CfgNode对象上进行替换
            config = replaceConfigVariables(config, rootConfig)
        return config
    
def parseServerConfig(config: CN) -> None:
    # 获取根配置
    root_config = config.get('..', None)
    
    # 加载engines配置文件，传递根配置用于变量替换
    config.ENGINES.ASR.SUPPORT_LIST = [parseConfig(os.path.join(CONFIG_ROOT_PATH, "engines", "asr", configFile), root_config) for configFile in config.ENGINES.ASR.SUPPORT_LIST]
    config.ENGINES.TTS.SUPPORT_LIST = [parseConfig(os.path.join(CONFIG_ROOT_PATH, "engines", "tts", configFile), root_config) for configFile in config.ENGINES.TTS.SUPPORT_LIST]
    config.ENGINES.LLM.SUPPORT_LIST = [parseConfig(os.path.join(CONFIG_ROOT_PATH, "engines", "llm", configFile), root_config) for configFile in config.ENGINES.LLM.SUPPORT_LIST]
    
    # 处理默认引擎配置
    if config.ENGINES.ASR.DEFAULT:
        asr_default_config = parseConfig(os.path.join(CONFIG_ROOT_PATH, "engines", "asr", config.ENGINES.ASR.DEFAULT), root_config)
        config.ENGINES.ASR.DEFAULT = asr_default_config.NAME
    
    if config.ENGINES.TTS.DEFAULT:
        tts_default_config = parseConfig(os.path.join(CONFIG_ROOT_PATH, "engines", "tts", config.ENGINES.TTS.DEFAULT), root_config)
        config.ENGINES.TTS.DEFAULT = tts_default_config.NAME
    
    if config.ENGINES.LLM.DEFAULT:
        llm_default_config = parseConfig(os.path.join(CONFIG_ROOT_PATH, "engines", "llm", config.ENGINES.LLM.DEFAULT), root_config)
        config.ENGINES.LLM.DEFAULT = llm_default_config.NAME
    
    # 加载agents配置文件，传递根配置用于变量替换
    config.AGENTS.SUPPORT_LIST = [parseConfig(os.path.join(CONFIG_ROOT_PATH, "agents", configFile), root_config) for configFile in config.AGENTS.SUPPORT_LIST]
    
    # 获取默认Agent名称
    if config.AGENTS.DEFAULT:
        agent_default_config = parseConfig(os.path.join(CONFIG_ROOT_PATH, "agents", config.AGENTS.DEFAULT), root_config)
        config.AGENTS.DEFAULT = agent_default_config.NAME

def getConfig(configFile: str) -> CN:
    with open(configFile, 'r', encoding='utf-8') as f:
        config = CN.load_cfg(f)
        # 将根配置传递给SERVER配置，以便在加载子配置时使用
        config.SERVER['..'] = config  # 使用特殊键存储根配置引用
        parseServerConfig(config.SERVER)
        # 移除临时引用
        config.SERVER.pop('..', None)
        config.freeze()
        return config

config = getConfig(CONFIG_FILE)
