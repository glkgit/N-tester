"""
aitestrebort AI 测试用例生成服务 - 真实LLM集成
支持 LangChain + OpenAI 兼容的所有LLM服务商
"""
import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import Request
from tortoise.exceptions import DoesNotExist
from tortoise import transactions

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.models.aitestrebort import (
    aitestrebortProject, aitestrebortTestCase, aitestrebortTestCaseStep, 
    aitestrebortTestCaseModule, aitestrebortProjectMember, aitestrebortLLMConfig
)

logger = logging.getLogger(__name__)


def create_llm_instance(llm_config: 'aitestrebortLLMConfig', temperature: float = 0.7) -> ChatOpenAI:
    """
    根据配置创建LLM实例
    统一使用OpenAI兼容格式，支持所有兼容的服务商
    """
    model_identifier = llm_config.model_name or "gpt-3.5-turbo"
    
    # 清理API密钥，移除可能的Bearer前缀
    api_key = llm_config.api_key
    original_key_length = len(api_key) if api_key else 0
    if api_key and api_key.startswith("Bearer "):
        api_key = api_key[7:].strip()  # 移除"Bearer "前缀
        logger.warning(f"API密钥包含'Bearer '前缀，已自动移除。原长度: {original_key_length}, 新长度: {len(api_key)}")
    
    # 记录API密钥的前后几位（用于调试）
    if api_key:
        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
        logger.info(f"使用API密钥: {masked_key} (长度: {len(api_key)})")
    
    # 清理base_url，移除可能的端点路径和/v1后缀
    base_url = llm_config.base_url
    original_base_url = base_url
    if base_url:
        # 移除常见的端点路径
        endpoints_to_remove = ['/chat/completions', '/completions']
        for endpoint in endpoints_to_remove:
            if base_url.endswith(endpoint):
                base_url = base_url[:-len(endpoint)]
                logger.warning(f"base_url包含端点路径'{endpoint}'，已自动移除。原URL: {original_base_url}, 新URL: {base_url}")
                break

        # 移除末尾的 /v1 后缀，因为 LangChain 会自动添加
        # 用户可以配置不带 /v1 的 base_url（如火山引擎的 /api/v3）
        # 或者带 /v1 的 base_url（如 OpenAI 的 /v1）
        if base_url.endswith('/v1'):
            base_url = base_url[:-3]  # 移除 /v1
            logger.warning(f"base_url末尾包含'/v1'，已自动移除。LangChain会自动添加。原URL: {original_base_url}, 新URL: {base_url}")

        logger.info(f"使用配置的base_url: {base_url}")
    
    llm_kwargs = {
        "model": model_identifier,
        "temperature": temperature,
        "api_key": api_key,
        "base_url": base_url
    }
    
    logger.info(f"创建LLM实例 - 模型: {model_identifier}, base_url: {base_url}, 温度: {temperature}")
    
    llm = ChatOpenAI(**llm_kwargs)
    
    return llm


class RealAITestCaseGenerator:
    """
    真实的AI测试用例生成器
    使用LangChain + OpenAI兼容API
    """
    
    def __init__(self, llm_config: 'aitestrebortLLMConfig'):
        """
        初始化 AI 生成器
        
        Args:
            llm_config: LLM配置对象
        """
        self.llm_config = llm_config
        self.llm = create_llm_instance(llm_config, temperature=0.7)
        logger.info(f"RealAITestCaseGenerator initialized with config: {llm_config.name}")
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一个专业的测试工程师，擅长根据需求描述生成高质量的测试用例。

请根据用户提供的需求描述，生成测试用例。

【输出格式要求】
每个用例输出为JSON格式，包含以下字段：
- name: 用例名称，简洁明确
- precondition: 前置条件，简短描述
- steps: 步骤数组，每项包含 description(操作步骤) 和 expected_result(预期结果)

【质量要求】
- 步骤清晰、可执行
- 预期结果明确、可验证
- 覆盖正常流程、异常流程、边界条件
- 操作步骤和预期结果用分号或句号分隔

【输出示例】
[
  {
    "name": "创建任务-必填字段验证",
    "precondition": "用户已登录系统",
    "steps": [
      {
        "step_number": 1,
        "description": "仅填写任务标题，不填写描述、优先级和截止时间",
        "expected_result": "任务创建成功，标题为填写内容，描述为空，优先级默认为中"
      }
    ]
  }
]"""

    def _build_system_prompt_with_options(self, template_options: Optional[Dict[str, Any]] = None) -> str:
        """
        根据模板选项构建动态系统提示词

        Args:
            template_options: 模板选项，包含：
                - include_precondition: 是否包含前置条件
                - include_level: 是否包含用例等级
                - levels: 允许的等级列表
                - include_compatibility: 是否包含兼容性测试
                - compatibility_types: 兼容性类型
                - include_boundary: 是否包含边界值测试
                - include_error: 是否包含异常处理
        """
        if template_options is None:
            template_options = {}

        include_precondition = template_options.get('include_precondition', True)
        include_level = template_options.get('include_level', True)
        levels = template_options.get('levels', 'P0,P1,P2,P3')
        include_compatibility = template_options.get('include_compatibility', False)
        compatibility_types = template_options.get('compatibility_types', 'Web,iOS,Android')
        include_boundary = template_options.get('include_boundary', True)
        include_error = template_options.get('include_error', True)

        prompt_parts = [
            "你是一个专业的测试工程师，擅长根据需求描述生成高质量的测试用例。",
            "",
            "请根据用户提供的需求描述，生成测试用例。",
            "",
            "【输出格式要求】",
            "每个用例输出为JSON格式，包含以下字段：",
            "- name: 用例名称，简洁明确"
        ]

        if include_precondition:
            prompt_parts.append("- precondition: 前置条件，简短描述")

        if include_level:
            prompt_parts.append(f"- level: 用例等级，取值范围：{levels}（P0=核心功能，P1=重要功能，P2=一般功能，P3=边缘功能）")
            prompt_parts.append("  请根据需求选择合适的等级，确保P0级用例覆盖核心功能")

        prompt_parts.extend([
            "- steps: 步骤数组，每项包含 description(操作步骤) 和 expected_result(预期结果)"
        ])

        if include_compatibility:
            prompt_parts.append("- compatibility: 兼容性测试（如适用）")

        prompt_parts.extend([
            "",
            "【测试场景要求】"
        ])

        scenario_parts = []
        scenario_parts.append("正常流程：验证功能在正常情况下的正确性")
        if include_boundary:
            scenario_parts.append("边界值：验证输入在边界值情况下的行为")
        if include_error:
            scenario_parts.append("异常流程：验证错误处理和异常情况")
        if include_compatibility:
            scenario_parts.append(f"兼容性：验证在不同环境下（{compatibility_types}）的行为")

        prompt_parts.append("；".join(scenario_parts))

        prompt_parts.extend([
            "",
            "【质量要求】",
            "- 步骤清晰、可执行",
            "- 预期结果明确、可验证",
            "- 用例名称简洁明了"
        ])

        prompt_parts.extend([
            "",
            "【输出示例】"
        ])

        # 根据选项生成不同的示例
        if include_level:
            example = f'''[
  {{
    "name": "创建任务-必填字段验证",
    "precondition": "用户已登录系统",
    "level": "P0",
    "steps": [
      {{
        "step_number": 1,
        "description": "仅填写任务标题，不填写描述、优先级和截止时间",
        "expected_result": "任务创建成功，标题为填写内容，描述为空，优先级默认为中"
      }}
    ]
  }}'''
        else:
            example = '''[
  {
    "name": "创建任务-必填字段验证",
    "precondition": "用户已登录系统",
    "steps": [
      {
        "step_number": 1,
        "description": "仅填写任务标题，不填写描述、优先级和截止时间",
        "expected_result": "任务创建成功，标题为填写内容，描述为空，优先级默认为中"
      }
    ]
  }'''

        if include_compatibility:
            example += ''',
  {
    "name": "创建任务-Web端兼容性",
    "precondition": "用户已登录系统，使用Chrome浏览器",
    "level": "P1",
    "steps": [
      {
        "step_number": 1,
        "description": "在Chrome浏览器中创建任务",
        "expected_result": "创建成功，界面显示正常"
      }
    ]
  }'''

        example += "\n]"

        prompt_parts.append(example)

        return "\n".join(prompt_parts)

    async def generate_single_testcase(
        self,
        requirement: str,
        context: Optional[str] = None,
        template_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成单个测试用例

        Args:
            requirement: 需求描述
            context: 上下文信息（可选）
            template_options: 模板选项

        Returns:
            生成的测试用例数据
        """
        try:
            # 根据模板选项构建提示词
            system_prompt = self._build_system_prompt_with_options(template_options)

            # 构建消息
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"需求描述：{requirement}")
            ]
            
            if context:
                messages.append(HumanMessage(content=f"上下文信息：{context}"))
            
            # 调用LLM
            logger.info(f"Calling LLM to generate testcase for requirement: {requirement[:50]}...")
            response = self.llm.invoke(messages)
            
            # 解析响应
            response_content = response.content
            logger.info(f"LLM response received: {response_content[:200]}...")
            
            # 尝试解析JSON
            try:
                testcase_data = json.loads(response_content)
            except json.JSONDecodeError:
                # 如果不是纯JSON，尝试提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if json_match:
                    testcase_data = json.loads(json_match.group())
                else:
                    raise ValueError("LLM response is not valid JSON")
            
            # 验证必需字段
            required_fields = ['name', 'steps']
            for field in required_fields:
                if field not in testcase_data:
                    raise ValueError(f"Missing required field: {field}")
            
            logger.info(f"Successfully generated testcase: {testcase_data['name']}")
            return testcase_data
            
        except Exception as e:
            logger.error(f"Failed to generate testcase: {str(e)}", exc_info=True)
            raise
    
    async def generate_multiple_testcases(
        self,
        requirement: str,
        count: int = 3,
        context: Optional[str] = None,
        template_options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        生成多个测试用例

        Args:
            requirement: 需求描述
            count: 生成数量
            context: 上下文信息（可选）
            template_options: 模板选项

        Returns:
            生成的测试用例列表
        """
        try:
            # 根据模板选项构建提示词
            system_prompt = self._build_system_prompt_with_options(template_options)
            system_prompt += f"\n\n请生成 {count} 个测试用例，覆盖正常流程、异常流程、边界值等不同场景。"
            system_prompt += "\n输出格式为JSON数组：[{testcase1}, {testcase2}, ...]"

            logger.info(f"[generate_multiple] 模板选项: {template_options}")
            logger.info(f"[generate_multiple] 生成提示词长度: {len(system_prompt)}")

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"需求描述：{requirement}")
            ]
            
            if context:
                messages.append(HumanMessage(content=f"上下文信息：{context}"))
            
            # 调用LLM
            logger.info(f"Calling LLM to generate {count} testcases for requirement: {requirement[:50]}...")
            response = self.llm.invoke(messages)
            
            # 解析响应
            response_content = response.content
            logger.info(f"LLM response received: {response_content[:200]}...")
            
            # 尝试解析JSON数组
            try:
                testcases_data = json.loads(response_content)
                if not isinstance(testcases_data, list):
                    # 如果返回的是单个对象，包装成数组
                    testcases_data = [testcases_data]
            except (json.JSONDecodeError, ValueError) as json_err:
                # 如果不是纯JSON，尝试提取JSON数组部分
                import re
                logger.warning(f"JSON解析失败: {str(json_err)}，尝试提取JSON部分")

                # 尝试多种方式提取JSON
                extracted = False

                # 方法1：使用括号计数提取完整的JSON数组（处理截断的JSON）
                testcases_data = self._extract_complete_json_array(response_content)
                if testcases_data is not None:
                    extracted = True
                    logger.info(f"方法1成功提取到 {len(testcases_data)} 个测试用例")

                # 方法2：提取对象格式并包装成数组
                if not extracted:
                    json_match = re.search(r'\{[\s\S]*\}', response_content)
                    if json_match:
                        try:
                            obj = json.loads(json_match.group())
                            testcases_data = [obj]
                            extracted = True
                            logger.info(f"方法2成功提取到 1 个测试用例")
                        except:
                            pass

                # 方法3：尝试修复常见JSON错误并重新解析
                if not extracted:
                    try:
                        # 移除常见的markdown代码块标记
                        cleaned = re.sub(r'```(?:json)?\s*', '', response_content)
                        cleaned = re.sub(r'\s*```', '', cleaned)
                        # 移除行首的行号
                        cleaned = re.sub(r'^\d+\.\s*', '', cleaned, flags=re.MULTILINE)
                        # 移除尾随逗号
                        cleaned = re.sub(r',\s*([\]}])', r'\1', cleaned)

                        testcases_data = json.loads(cleaned)
                        if not isinstance(testcases_data, list):
                            testcases_data = [testcases_data]
                        extracted = True
                        logger.info(f"方法3成功提取到 {len(testcases_data)} 个测试用例")
                    except:
                        pass

                if not extracted:
                    raise ValueError(f"无法解析LLM响应为JSON: {str(json_err)}")
            
            logger.info(f"Successfully generated {len(testcases_data)} testcases")
            return testcases_data[:count]  # 限制返回数量
            
        except Exception as e:
            logger.error(f"Failed to generate multiple testcases: {str(e)}", exc_info=True)
            raise

    def _extract_complete_json_array(self, content: str) -> Optional[List[Dict[str, Any]]]:
        """
        使用括号计数从截断的响应中提取完整的JSON数组

        处理LLM输出被截断的情况，找到所有完整的JSON对象
        """
        import re

        if not content:
            return None

        # 移除markdown代码块标记
        content = re.sub(r'```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```', '', content)

        # 移除行首的行号（如 "1. "）
        content = re.sub(r'^\s*\d+\.\s*', '', content, flags=re.MULTILINE)

        testcases = []
        i = 0
        n = len(content)

        while i < n:
            # 找到数组开始
            while i < n and content[i] not in '[{':
                i += 1

            if i >= n:
                break

            if content[i] == '[':
                # 找到数组开始，尝试用括号计数提取
                bracket_count = 0
                in_string = False
                escape_next = False
                start = i

                j = i
                while j < n:
                    char = content[j]

                    if escape_next:
                        escape_next = False
                        j += 1
                        continue

                    if char == '\\':
                        escape_next = True
                        j += 1
                        continue

                    if char == '"' and not escape_next:
                        in_string = not in_string
                        j += 1
                        continue

                    if in_string:
                        j += 1
                        continue

                    if char == '{':
                        bracket_count += 1
                    elif char == '}':
                        bracket_count -= 1

                    j += 1

                    # 当括号计数回到0，且在字符串外时，我们找到一个完整的数组或对象
                    if bracket_count == 0 and not in_string:
                        # 检查是否找到了完整的数组（以]结尾）
                        while j < n and content[j] in ' \t\n\r':
                            j += 1

                        if j < n and content[j] == ']':
                            j += 1  # 包含]
                            try:
                                arr = json.loads(content[start:j])
                                if isinstance(arr, list):
                                    # 验证每个元素都是有效的测试用例
                                    for item in arr:
                                        if isinstance(item, dict) and 'name' in item and 'steps' in item:
                                            testcases.append(item)
                                    if testcases:
                                        return testcases
                            except:
                                pass
                        break

                i = j
            elif content[i] == '{':
                # 找到单个对象开始
                bracket_count = 0
                in_string = False
                escape_next = False
                start = i

                j = i
                while j < n:
                    char = content[j]

                    if escape_next:
                        escape_next = False
                        j += 1
                        continue

                    if char == '\\':
                        escape_next = True
                        j += 1
                        continue

                    if char == '"' and not escape_next:
                        in_string = not in_string
                        j += 1
                        continue

                    if in_string:
                        j += 1
                        continue

                    if char == '{':
                        bracket_count += 1
                    elif char == '}':
                        bracket_count -= 1

                    j += 1

                    if bracket_count == 0 and not in_string:
                        try:
                            obj = json.loads(content[start:j])
                            if isinstance(obj, dict) and 'name' in obj and 'steps' in obj:
                                testcases.append(obj)
                                # 如果只找到一个对象且是有效的测试用例，返回包装的数组
                                if len(testcases) == 1:
                                    return testcases
                        except:
                            pass
                        break

                i = j
            else:
                i += 1

        if testcases:
            return testcases

        return None

    async def optimize_testcase(
        self,
        testcase_data: Dict[str, Any],
        optimization_request: str
    ) -> Dict[str, Any]:
        """
        优化现有测试用例
        
        Args:
            testcase_data: 现有测试用例数据
            optimization_request: 优化要求
            
        Returns:
            优化后的测试用例
        """
        try:
            # 构建消息
            system_prompt = """你是一个专业的测试工程师，擅长优化和改进测试用例。

请根据用户的优化要求，改进现有的测试用例。

输出格式必须是有效的JSON，保持原有结构。"""
            
            current_testcase_str = json.dumps(testcase_data, ensure_ascii=False, indent=2)
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"当前测试用例：\n{current_testcase_str}"),
                HumanMessage(content=f"优化要求：{optimization_request}")
            ]
            
            # 调用LLM
            logger.info(f"Calling LLM to optimize testcase: {testcase_data.get('name', 'Unknown')}")
            response = self.llm.invoke(messages)
            
            # 解析响应
            response_content = response.content
            logger.info(f"LLM optimization response received: {response_content[:200]}...")
            
            # 尝试解析JSON
            try:
                optimized_data = json.loads(response_content)
            except json.JSONDecodeError:
                # 如果不是纯JSON，尝试提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if json_match:
                    optimized_data = json.loads(json_match.group())
                else:
                    raise ValueError("LLM response is not valid JSON")
            
            logger.info(f"Successfully optimized testcase: {optimized_data.get('name', 'Unknown')}")
            return optimized_data

        except Exception as e:
            logger.error(f"Failed to optimize testcase: {str(e)}", exc_info=True)
            raise

    async def generate_testcase_conversation(
        self,
        requirement: str,
        count: int = 3,
        context: Optional[str] = None
    ) -> str:
        """
        生成测试用例对话内容（真实LLM调用）

        Args:
            requirement: 需求描述
            count: 生成数量
            context: 上下文信息

        Returns:
            格式化的对话内容，包含表格形式的测试用例
        """
        try:
            # 先生成结构化的测试用例
            testcases_data = await self.generate_multiple_testcases(requirement, count, context)

            # 构建对话式的响应内容
            conversation_content = f"""根据您提供的需求描述，我为您生成了以下{len(testcases_data)}个测试用例，请查看：

| 测试模块 | 前置条件 | 操作步骤 | 预期结果 | 等级 | 备注 |
|---------|---------|---------|---------|------|------|"""

            for i, testcase in enumerate(testcases_data, 1):
                # 合并操作步骤
                steps_desc = []
                steps_expected = []
                for step in testcase.get('steps', []):
                    steps_desc.append(f"{step['step_number']}. {step['description']}")
                    steps_expected.append(f"{step['step_number']}. {step['expected_result']}")

                steps_description = "<br>".join(steps_desc)
                steps_expected_result = "<br>".join(steps_expected)

                conversation_content += f"""
| {testcase['name']} | {testcase['precondition']} | {steps_description} | {steps_expected_result} | {testcase['level']} | {testcase.get('notes', '')} |"""

            conversation_content += f"""

以上测试用例涵盖了：
- ✅ 正常流程测试：验证基本功能是否正常工作
- ✅ 异常情况测试：验证系统对异常输入的处理能力
- ✅ 边界条件测试：验证系统在边界值下的表现

每个测试用例都包含了详细的操作步骤和预期结果，可以直接用于测试执行。如果您需要调整某个测试用例或添加更多场景，请告诉我具体需求。"""

            logger.info(f"成功生成测试用例对话内容，包含 {len(testcases_data)} 个测试用例")
            return conversation_content

        except Exception as e:
            logger.error(f"生成测试用例对话失败: {str(e)}", exc_info=True)
            raise


async def test_llm_config(request: Request, config_id: int):
    """
    测试LLM配置是否可用
    
    Args:
        config_id: LLM配置ID
    """
    try:
        # 获取配置
        llm_config = await aitestrebortLLMConfig.get(id=config_id)
        
        logger.info(f"Testing LLM config {config_id}: {llm_config.name}")
        logger.info(f"Provider: {llm_config.provider}, Model: {llm_config.model_name}")
        logger.info(f"Base URL: {llm_config.base_url}")
        
        # 创建LLM实例
        try:
            llm = create_llm_instance(llm_config, temperature=0.7)
            logger.info("LLM instance created successfully")
        except Exception as e:
            logger.error(f"Failed to create LLM instance: {str(e)}")
            return request.app.error(msg=f"创建LLM实例失败: {str(e)}")
        
        # 发送测试消息
        test_message = "请回复'测试成功'来确认连接正常。"
        messages = [HumanMessage(content=test_message)]
        
        try:
            logger.info("Sending test message to LLM...")
            response = llm.invoke(messages)
            
            if hasattr(response, 'content'):
                response_content = response.content
                logger.info(f"LLM test response: {response_content}")
                
                return request.app.get_success(data={
                    "config_id": config_id,
                    "config_name": llm_config.name,
                    "model_name": llm_config.model_name,
                    "provider": llm_config.provider,
                    "test_message": test_message,
                    "response": response_content,
                    "status": "success"
                })
            else:
                logger.error(f"Invalid response format: {response}")
                return request.app.error(msg=f"LLM返回了无效的响应格式: {type(response)}")
                
        except Exception as e:
            logger.error(f"LLM invocation failed: {str(e)}", exc_info=True)
            
            # 提供更详细的错误信息
            error_msg = str(e)
            if "null value for \"choices\"" in error_msg:
                error_msg = "LLM API返回了空的choices字段，可能的原因：\n1. API密钥无效或过期\n2. 模型名称不正确\n3. Base URL配置错误\n4. API服务商暂时不可用"
            elif "401" in error_msg or "Unauthorized" in error_msg:
                error_msg = "API密钥无效或过期，请检查配置"
            elif "404" in error_msg or "Not Found" in error_msg:
                error_msg = "模型不存在或Base URL配置错误"
            elif "timeout" in error_msg.lower():
                error_msg = "请求超时，请检查网络连接或Base URL配置"
            
            return request.app.error(msg=f"LLM配置测试失败: {error_msg}")
        
    except DoesNotExist:
        return request.app.fail(msg="LLM配置不存在")
    except Exception as e:
        logger.error(f"LLM config test failed: {str(e)}", exc_info=True)
        return request.app.error(msg=f"LLM配置测试失败: {str(e)}")


async def generate_testcase_from_requirement_real(
    request: Request,
    project_id: int,
    requirement: str,
    module_id: int,
    count: int = 1,
    context: Optional[str] = None,
    llm_config_id: Optional[int] = None
):
    """
    根据需求生成测试用例（真实LLM调用）
    
    Args:
        project_id: 项目ID
        requirement: 需求描述
        module_id: 模块ID
        count: 生成数量
        context: 上下文信息
        llm_config_id: LLM配置ID
    """
    try:
        project = await aitestrebortProject.get(id=project_id)
        
        # 检查权限
        if not await aitestrebortProjectMember.filter(
            project=project, user_id=request.state.user.id
        ).exists():
            return request.app.forbidden(msg="无权限访问此项目")
        
        # 验证模块是否存在
        module = await aitestrebortTestCaseModule.get(
            id=module_id, project=project
        )
        
        # 获取 LLM 配置
        llm_config = None
        if llm_config_id:
            llm_config = await aitestrebortLLMConfig.get(
                id=llm_config_id,
                project_id=None,  # 全局配置
                creator_id=request.state.user.id,
                is_active=True
            )
        else:
            # 使用默认配置
            llm_config = await aitestrebortLLMConfig.filter(
                project_id=None,
                creator_id=request.state.user.id,
                is_default=True,
                is_active=True
            ).first()
        
        if not llm_config:
            return request.app.fail(msg="未找到可用的 LLM 配置，请先在全局配置中创建并激活LLM配置")
        
        # 初始化真实的 AI 生成器
        generator = RealAITestCaseGenerator(llm_config)
        
        # 生成测试用例
        if count == 1:
            testcase_data = await generator.generate_single_testcase(requirement, context)
            testcases_data = [testcase_data]
        else:
            testcases_data = await generator.generate_multiple_testcases(requirement, count, context)
        
        # 保存到数据库
        created_testcases = []
        
        async with transactions.in_transaction():
            for testcase_data in testcases_data:
                # 创建测试用例
                testcase = await aitestrebortTestCase.create(
                    project=project,
                    module=module,
                    name=testcase_data["name"],
                    precondition=testcase_data["precondition"],
                    level=testcase_data["level"],
                    notes=testcase_data.get("notes", "AI生成"),
                    creator_id=request.state.user.id
                )
                
                # 创建测试步骤
                for step_data in testcase_data["steps"]:
                    await aitestrebortTestCaseStep.create(
                        test_case=testcase,
                        step_number=step_data["step_number"],
                        description=step_data["description"],
                        expected_result=step_data["expected_result"],
                        creator_id=request.state.user.id
                    )
                
                created_testcases.append({
                    "id": testcase.id,
                    "name": testcase.name,
                    "precondition": testcase.precondition,
                    "level": testcase.level,
                    "notes": testcase.notes,
                    "module_id": testcase.module_id,
                    "creator_id": testcase.creator_id,
                    "create_time": testcase.create_time
                })
        
        return request.app.post_success(data={
            "generated_count": len(created_testcases),
            "testcases": created_testcases,
            "llm_config_used": {
                "id": llm_config.id,
                "name": llm_config.name,
                "model_name": llm_config.model_name,
                "provider": llm_config.provider
            }
        })
        
    except DoesNotExist:
        return request.app.fail(msg="项目、模块或 LLM 配置不存在")
    except Exception as e:
        logger.error(f"Generate testcase failed: {str(e)}", exc_info=True)
        return request.app.error(msg=f"生成测试用例失败: {str(e)}")
