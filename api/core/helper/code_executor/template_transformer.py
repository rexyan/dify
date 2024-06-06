import json
import re
from abc import ABC, abstractmethod
from base64 import b64encode
from typing import Optional

from pydantic import BaseModel

from core.helper.code_executor.entities import CodeDependency


class TemplateTransformer(ABC, BaseModel):
    _code_placeholder: str = '{{code}}'
    _inputs_placeholder: str = '{{inputs}}'
    _result_tag: str = '<<RESULT>>'

    @classmethod
    def get_standard_packages(cls) -> set[str]:
        return set()

    @classmethod
    def transform_caller(cls, code: str, inputs: dict,
                         dependencies: Optional[list[CodeDependency]] = None) -> tuple[str, str, list[CodeDependency]]:
        """
        Transform code to python runner
        :param code: code
        :param inputs: inputs
        :return: runner, preload
        """
        runner_script = cls.assemble_runner_script(code, inputs)
        preload_script = cls.get_preload_script()

        packages = dependencies or []
        standard_packages = cls.get_standard_packages()
        for package in standard_packages:
            if package not in packages:
                packages.append(CodeDependency(name=package, version=''))
        packages = list({dep.name: dep for dep in packages if dep.name}.values())

        return runner_script, preload_script, packages

    @classmethod
    def extract_result_str_from_response(cls, response: str) -> str:
        result = re.search(rf'{cls._result_tag}(.*){cls._result_tag}', response, re.DOTALL)
        if not result:
            raise ValueError('Failed to parse result')
        result = result.group(1)
        return result

    @classmethod
    def transform_response(cls, response: str) -> dict:
        """
        Transform response to dict
        :param response: response
        :return:
        """
        return json.loads(cls.extract_result_str_from_response(response))

    @classmethod
    @abstractmethod
    def get_runner_script(cls) -> str:
        """
        Get runner script
        """
        pass

    @classmethod
    def serialize_inputs(cls, inputs: dict) -> str:
        inputs_json_str = json.dumps(inputs, ensure_ascii=False).encode()
        input_base64_encoded = b64encode(inputs_json_str).decode('utf-8')
        return input_base64_encoded

    @classmethod
    def assemble_runner_script(cls, code: str, inputs: dict) -> str:
        # assemble runner script
        script = cls.get_runner_script()
        script = script.replace(cls._code_placeholder, code)
        inputs_str = cls.serialize_inputs(inputs)
        script = script.replace(cls._inputs_placeholder, inputs_str)
        return script

    @classmethod
    def get_preload_script(cls) -> str:
        """
        Get preload script
        """
        return ''
