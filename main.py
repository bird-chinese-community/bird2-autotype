#!/usr/bin/env python3
"""BIRD Internet Routing Daemon (v2.17+) Auto Type Completion Tool.

Automatically adds explicit return type declarations to functions in BIRD
config files to eliminate type inference warnings in BIRD 2.17+.
"""

import argparse
import ipaddress
import locale
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union


@dataclass
class LanguageConfig:
    lang: str
    usage_title: str
    usage_method: str
    basic_examples: str
    options: str
    detailed_help: str
    detailed_examples: str
    supported_types: str
    note: str
    error_missing_args: str
    error_path_not_exists: str
    error_processing: str
    success_processed: str
    no_conf_files: str


class LanguageManager:
    def __init__(self):
        self._current_lang = self._detect_language()
        self._configs = {
            "zh": LanguageConfig(
                lang="zh",
                usage_title="BIRD2 Auto Type Completion",
                usage_method="用法",
                basic_examples="示例",
                options="选项",
                detailed_help="详细帮助: python3 main.py --help",
                detailed_examples="详细示例",
                supported_types="支持类型",
                note="注: 无返回值函数将保持不变",
                error_missing_args="错误: 缺少参数",
                error_path_not_exists="错误: 路径 '{}' 不存在",
                error_processing="处理错误: {}",
                success_processed="完成: {}",
                no_conf_files="目录 {} 中无 .conf 文件",
            ),
            "en": LanguageConfig(
                lang="en",
                usage_title="BIRD2 Auto Type Completion",
                usage_method="Usage",
                basic_examples="Examples",
                options="Options",
                detailed_help="For help: python3 main.py --help",
                detailed_examples="Detailed examples",
                supported_types="Supported types",
                note="Note: Void functions remain unchanged",
                error_missing_args="Error: Missing arguments",
                error_path_not_exists="Error: Path '{}' not found",
                error_processing="Error: {}",
                success_processed="Done: {}",
                no_conf_files="No .conf files in {}",
            ),
        }

    def _detect_language(self) -> str:
        for var in ["LANG", "LC_ALL", "LC_MESSAGES"]:
            value = os.environ.get(var, "").lower()
            if "zh" in value or "cn" in value:
                return "zh"

        try:
            default_locale = locale.getlocale()[0]
            if default_locale and (
                "zh" in default_locale.lower() or "cn" in default_locale.lower()
            ):
                return "zh"
        except:
            pass

        return "en"

    @property
    def config(self) -> LanguageConfig:
        return self._configs[self._current_lang]


class BirdTypeInferencer:
    TYPE_PATTERNS = [
        ("int", lambda v: re.match(r"^\s*-?\d+\s*$", v.strip())),
        ("pair", lambda v: re.match(r"^\s*\([^,)]+,\s*[^,)]+\)\s*$", v.strip())),
        ("ip", lambda v: BirdTypeInferencer._is_ip_address(v.strip())),
        ("prefix", lambda v: BirdTypeInferencer._is_prefix_type(v.strip())),
        ("string", lambda v: BirdTypeInferencer._is_string_type(v.strip())),
        ("set", lambda v: re.match(r"^\s*\{[^}]*\}\s*$", v.strip())),
        ("bool", lambda v: BirdTypeInferencer._is_bool_type(v.strip())),
    ]

    @staticmethod
    def _is_ip_address(value: str) -> bool:
        if "/" in value:
            return False

        # 处理 .mask() 函数的情况，例如 1.2.3.4.mask(8)
        if ".mask(" in value:
            # 提取 .mask() 之前的部分
            base_ip = value.split(".mask(")[0]
            try:
                ipaddress.ip_address(base_ip)
                return True
            except ValueError:
                return False

        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_prefix_type(value: str) -> bool:
        if "/" in value:
            try:
                ipaddress.ip_network(value, strict=False)
                return True
            except ValueError:
                pass

        # 处理 .mask() 的情况
        if ".mask(" in value:
            # 如果 .mask() 之前的部分是有效的IP地址，则这是IP类型，不是前缀
            base_part = value.split(".mask(")[0]
            try:
                ipaddress.ip_address(base_part)
                return False  # 这是IP地址的掩码操作，不是前缀
            except ValueError:
                # 如果不是有效IP，检查是否是 net.mask() 这种前缀操作
                return base_part == "net" or base_part.startswith("net.")

        return bool(re.match(r"^(net(\.mask\(\d+\))?|.*\.mask\(\d+\))$", value))

    @staticmethod
    def _is_string_type(value: str) -> bool:
        if re.search(r'["\'][^"\'\n]*["\']', value):
            return True
        return "," in value and not value.startswith(("(", "{"))

    @staticmethod
    def _is_bool_type(value: str) -> bool:
        if value in ["true", "false"]:
            return True
        operators = ["=", "!=", "<", ">", "<=", ">=", "&&", "||", "!", "~", "!~"]
        return any(op in value for op in operators)

    def infer_return_type(self, return_values: List[str]) -> Optional[str]:
        if not return_values:
            return None

        for type_name, checker in self.TYPE_PATTERNS:
            if all(checker(val) for val in return_values):
                return f"{type_name} (int, int)" if type_name == "pair" else type_name

        return "bool"

    # Compatibility methods for existing tests
    def _is_int(self, value: str) -> bool:
        return self.TYPE_PATTERNS[0][1](value) is not None

    def _is_pair(self, value: str) -> bool:
        return self.TYPE_PATTERNS[1][1](value) is not None

    def _is_ip(self, value: str) -> bool:
        return BirdTypeInferencer._is_ip_address(value)

    def _is_prefix(self, value: str) -> bool:
        return BirdTypeInferencer._is_prefix_type(value)

    def _is_string(self, value: str) -> bool:
        return BirdTypeInferencer._is_string_type(value)

    def _is_set(self, value: str) -> bool:
        return self.TYPE_PATTERNS[5][1](value) is not None

    def _is_bool(self, value: str) -> bool:
        return BirdTypeInferencer._is_bool_type(value)


class BirdConfigProcessor:
    FUNCTION_START = re.compile(r"^\s*function\s+\w+")
    RETURN_PATTERN = re.compile(r"return\s+([^;]+);", re.MULTILINE)

    def __init__(self):
        self.inferencer = BirdTypeInferencer()

    def extract_return_values(self, function_body: str) -> List[str]:
        matches = self.RETURN_PATTERN.findall(function_body)
        return [" ".join(match.strip().split()) for match in matches]

    def _add_return_type(self, lines: List[str], inferred_type: str) -> List[str]:
        result = []
        func_header = lines[0]
        remaining = lines[1:] if len(lines) > 1 else []

        if "{" in func_header:
            parts = func_header.split("{", 1)
            result.append(f"{parts[0].rstrip()} -> {inferred_type} {{{parts[1]}")
            result.extend(remaining)
        else:
            # Add type directly to function header
            result.append(f"{func_header.rstrip()} -> {inferred_type}")
            result.extend(remaining)

        return result

    def process_content(self, content: str) -> str:
        lines = content.split("\n")
        processed_lines = []
        function_lines = []
        in_function = False
        brace_count = 0

        for line in lines:
            if self.FUNCTION_START.match(line) and not in_function:
                in_function = True
                function_lines = [line]
                brace_count = line.count("{") - line.count("}")

                if brace_count == 0 and "{" in line and "}" in line:
                    processed_function = self._process_function_lines(function_lines)
                    processed_lines.extend(processed_function)
                    in_function = False
                    function_lines = []

            elif in_function:
                function_lines.append(line)
                brace_count += line.count("{") - line.count("}")

                if brace_count == 0:
                    processed_function = self._process_function_lines(function_lines)
                    processed_lines.extend(processed_function)
                    in_function = False
                    function_lines = []
            else:
                processed_lines.append(line)

        return "\n".join(processed_lines)

    def _process_function_lines(self, lines: List[str]) -> List[str]:
        if not lines:
            return lines

        function_content = "\n".join(lines)
        return_values = self.extract_return_values(function_content)
        inferred_type = self.inferencer.infer_return_type(return_values)

        if inferred_type is None or " -> " in function_content:
            return lines

        return self._add_return_type(lines, inferred_type)

    def process_single_function(self, function_content: str) -> str:
        """Compatibility method for existing tests."""
        lines = function_content.split("\n")
        processed_lines = self._process_function_lines(lines)
        return "\n".join(processed_lines)


def process_file(
    file_path: Path, in_place: bool = False, lang_config: LanguageConfig = None
) -> str:
    processor = BirdConfigProcessor()

    encodings = ["utf-8", "latin-1"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Cannot decode file {file_path}")

    processed_content = processor.process_content(content)

    if in_place:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(processed_content)
        return f"已处理文件: {file_path}"

    return processed_content


def process_path(
    path: Union[str, Path], in_place: bool = False, lang_config: LanguageConfig = None
) -> str:
    path_obj = Path(path)

    if path_obj.is_file():
        return process_file(path_obj, in_place, lang_config)
    elif path_obj.is_dir():
        conf_files = list(path_obj.glob("*.conf")) + list(path_obj.glob("**/*.conf"))

        if not conf_files:
            return (
                lang_config.no_conf_files.format(path)
                if lang_config
                else f"No .conf files found in directory {path}"
            )

        results = []
        for conf_file in conf_files:
            if in_place:
                results.append(
                    process_file(conf_file, in_place=True, lang_config=lang_config)
                )
            else:
                content = process_file(
                    conf_file, in_place=False, lang_config=lang_config
                )
                results.append(f"# === File: {conf_file} ===\n{content}\n")

        return "\n".join(results)
    else:
        return f"Error: Path {path} does not exist"


class ColorFormatter:
    COLORS = (
        {
            "cyan": "\033[1;36m",
            "yellow": "\033[1;33m",
            "green": "\033[1;32m",
            "red": "\033[1;31m",
            "reset": "\033[0m",
        }
        if sys.stdout.isatty()
        else {key: "" for key in ["cyan", "yellow", "green", "red", "reset"]}
    )

    @classmethod
    def format(cls, text: str, color: str) -> str:
        return f"{cls.COLORS.get(color, '')}{text}{cls.COLORS['reset']}"


def show_usage(lang_config: LanguageConfig):
    examples = {
        "zh": [
            "python3 main.py config.conf            # 处理单个文件",
            "python3 main.py -i config.conf         # 直接修改文件",
            "python3 main.py /path/to/configs/      # 批量处理目录",
        ],
        "en": [
            "python3 main.py config.conf            # Process single file",
            "python3 main.py -i config.conf         # Modify file in-place",
            "python3 main.py /path/to/configs/      # Batch process directory",
        ],
    }

    options = {
        "zh": ["-i, --in-place    直接修改文件", "-h, --help        显示帮助"],
        "en": [
            "-i, --in-place    Modify files in-place",
            "-h, --help        Show help",
        ],
    }

    lang = lang_config.lang

    print(
        f"""
{ColorFormatter.format(lang_config.usage_title, 'cyan')}

{ColorFormatter.format(lang_config.usage_method, 'yellow')}
  python3 main.py <config_file_or_directory> [options]

{ColorFormatter.format(lang_config.basic_examples, 'yellow')}
{chr(10).join('  ' + ex for ex in examples[lang])}

{ColorFormatter.format(lang_config.options, 'yellow')}
{chr(10).join('  ' + opt for opt in options[lang])}

{ColorFormatter.format(lang_config.detailed_help, 'green')}
"""
    )


def create_argument_parser(lang_config: LanguageConfig) -> argparse.ArgumentParser:
    detailed_examples = {
        "zh": """
详细示例:

  # 处理单个文件
  %(prog)s /path/to/bird.conf

  # 直接修改文件
  %(prog)s -i /etc/bird/filter.conf

  # 批量处理目录
  %(prog)s /path/to/configs/

支持类型:
  • int:     return 1;
  • pair:    return (1, 2);  →  -> pair (int, int)
  • ip:      return 1.2.3.4;
  • prefix:  return 1.2.3.4/32; return net;
  • string:  return "hello";
  • set:     return {1, 2, 3};
  • bool:    return true; (默认类型)

注: 无返回值函数将保持不变
        """,
        "en": """
Detailed examples:

  # Process single file
  %(prog)s /path/to/bird.conf

  # Modify file in-place
  %(prog)s -i /etc/bird/filter.conf

  # Batch process directory
  %(prog)s /path/to/configs/

Supported types:
  • int:     return 1;
  • pair:    return (1, 2);  →  -> pair (int, int)
  • ip:      return 1.2.3.4;
  • prefix:  return 1.2.3.4/32; return net;
  • string:  return "hello";
  • set:     return {1, 2, 3};
  • bool:    return true; (default type)

Note: Void functions remain unchanged
        """,
    }

    lang = lang_config.lang

    parser = argparse.ArgumentParser(
        description=lang_config.usage_title,
        epilog=ColorFormatter.format(detailed_examples[lang], "yellow"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )

    path_help = (
        "BIRD 配置文件或目录路径"
        if lang == "zh"
        else "BIRD config file or directory path"
    )
    inplace_help = "直接修改文件" if lang == "zh" else "Modify files in-place"
    help_help = "显示帮助" if lang == "zh" else "Show help"

    parser.add_argument("path", help=path_help)
    parser.add_argument("-i", "--in-place", action="store_true", help=inplace_help)
    parser.add_argument("-h", "--help", action="help", help=help_help)

    return parser


def main():
    lang_manager = LanguageManager()
    lang_config = lang_manager.config

    if len(sys.argv) == 1:
        show_usage(lang_config)
        sys.exit(0)

    parser = create_argument_parser(lang_config)

    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code == 2:
            print(f"\n{ColorFormatter.format(lang_config.error_missing_args, 'red')}")
            show_usage(lang_config)
        sys.exit(e.code)

    if not os.path.exists(args.path):
        print(
            ColorFormatter.format(
                lang_config.error_path_not_exists.format(args.path), "red"
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        result = process_path(args.path, args.in_place, lang_config)

        if args.in_place:
            print(
                ColorFormatter.format(
                    lang_config.success_processed.format(result), "green"
                ),
                file=sys.stderr,
            )
        else:
            print(result)
    except Exception as e:
        print(
            ColorFormatter.format(lang_config.error_processing.format(e), "red"),
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
