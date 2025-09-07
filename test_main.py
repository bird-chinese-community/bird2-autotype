#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BIRD 配置文件类型补全工具的单元测试
"""

import pytest
import tempfile
from pathlib import Path
from main import BirdTypeInferencer, BirdConfigProcessor, process_path


@pytest.fixture
def inferencer():
    """BirdTypeInferencer 实例 fixture"""
    return BirdTypeInferencer()


@pytest.fixture 
def processor():
    """BirdConfigProcessor 实例 fixture"""
    return BirdConfigProcessor()


class TestBirdTypeInferencer:
    """测试 BirdTypeInferencer 类"""
    
    @pytest.mark.parametrize("value,expected", [
        ("1", True),
        ("123", True),
        ("-5", True),
        ("  42  ", True),
        ("1.5", False),
        ("abc", False),
        ("true", False),
    ])
    def test_int_detection(self, inferencer, value, expected):
        """测试整数类型检测"""
        assert inferencer._is_int(value) == expected
    
    @pytest.mark.parametrize("value,expected", [
        ("(1, 2)", True),
        ("(1234, 5678)", True),
        ("(1+2, a+b)", True),
        ("  (10, 10)  ", True),
        ("(AS, NODE_ID)", True),
        ("(1)", False),
        ("1, 2", False),
        ("{1, 2}", False),
        ("(1, 2, 3)", False),
    ])
    def test_pair_detection(self, inferencer, value, expected):
        """测试 pair 类型检测"""
        assert inferencer._is_pair(value) == expected
    
    @pytest.mark.parametrize("value,expected", [
        ("1.2.3.4", True),
        ("192.168.1.1", True),
        ("fec0:3:4::1", True),
        ("fe80::1", True),
        ("1.2.3.4.mask(8)", True),
        ("fe80::ffff.mask(64)", True),
        ("1.2.3.4/24", False),  # 这是前缀，不是 IP
        ("invalid", False),
        ("256.1.1.1", False),
    ])
    def test_ip_detection(self, inferencer, value, expected):
        """测试 IP 地址类型检测"""
        assert inferencer._is_ip(value) == expected
    
    @pytest.mark.parametrize("value,expected", [
        ("1.2.3.4/32", True),
        ("192.168.0.0/16", True),
        ("fe80::1/64", True),
        ("2001:db8::/32", True),
        ("net.mask(16)", True),
        ("net.mask(24)", True),
        ("1.2.3.4", False),
        ("invalid/24", False),
        ("1.2.3.4.mask(8)", False),  # 这是 IP，不是前缀
    ])
    def test_prefix_detection(self, inferencer, value, expected):
        """测试前缀类型检测"""
        assert inferencer._is_prefix(value) == expected
    
    @pytest.mark.parametrize("value,expected", [
        ('"hello world"', True),
        ("'single quotes'", True),
        ('"path, first: ", P.first, ", last: ", P.last', True),
        ('"path length: ", P.len', True),
        ('hello world', False),  # 没有引号
        ('123', False),
        ('true', False),
    ])
    def test_string_detection(self, inferencer, value, expected):
        """测试字符串类型检测"""
        assert inferencer._is_string(value) == expected
    
    @pytest.mark.parametrize("value,expected", [
        ("{1, 2, 3, 4}", True),
        ("{1}", True),
        ("{  }", True),
        ("  {1, 2}  ", True),
        ("1, 2, 3", False),
        ("(1, 2)", False),
        ("[1, 2]", False),
    ])
    def test_set_detection(self, inferencer, value, expected):
        """测试集合类型检测"""
        assert inferencer._is_set(value) == expected
    
    @pytest.mark.parametrize("value,expected", [
        ("true", True),
        ("false", True),
        ("net ~ BOGON_PREFIXES_v4", True),
        ("a > b", True),
        ("x && y", True),
        ("!condition", True),
        ("value != null", True),
        ("1", False),
        ('"string"', False),
    ])
    def test_bool_detection(self, inferencer, value, expected):
        """测试布尔类型检测"""
        assert inferencer._is_bool(value) == expected
    
    @pytest.mark.parametrize("return_values,expected", [
        # void 函数
        ([], None),
        
        # 各种单一类型
        (["1"], "int"),
        (["(1, 2)"], "pair (int, int)"),
        (["1.2.3.4"], "ip"),
        (["1.2.3.4/32"], "prefix"),
        (['"hello"'], "string"),
        (["{1, 2, 3}"], "set"),
        (["true"], "bool"),
        (["net ~ BOGON_PREFIXES"], "bool"),
        
        # 多个返回值，类型一致
        (["1", "42", "-5"], "int"),
        (["true", "false", "x > y"], "bool"),
        
        # 混合类型应该返回能匹配所有值的类型
        (["1", "true"], "bool"),  # 'true' 不是 int，但都是 bool
    ])
    def test_infer_return_type(self, inferencer, return_values, expected):
        """测试返回类型推断"""
        result = inferencer.infer_return_type(return_values)
        assert result == expected


class TestBirdConfigProcessor:
    """测试 BirdConfigProcessor 类"""
    
    @pytest.mark.parametrize("function_body,expected", [
        # 单个返回值
        ("{\n  return 1;\n}", ["1"]),
        
        # 多个返回值
        ("""{\n  if (condition) return true;\n  return false;\n}""", 
         ["true", "false"]),
        
        # 复杂返回值
        ("""{\n  return "path, first: ", P.first, ", last: ", P.last;\n}""",
         ['"path, first: ", P.first, ", last: ", P.last']),
        
        # 无返回值
        ("{\n  dest = RTD_BLACKHOLE;\n}", []),
    ])
    def test_extract_return_values(self, processor, function_body, expected):
        """测试返回值提取"""
        result = processor.extract_return_values(function_body)
        assert result == expected
    
    def test_process_single_function_void(self, processor):
        """测试处理 void 函数"""
        function_content = """function test_void()
{
  if (65535,0,666) ~ bgp_large_community then dest = RTD_BLACKHOLE;
}"""
        
        result = processor.process_single_function(function_content)
        # void 函数不应该添加返回类型
        assert result == function_content
        assert '->' not in result
    
    def test_process_single_function_with_return_type(self, processor):
        """测试处理有返回值的函数"""
        function_content = """function test_int()
{
    return 1;
}"""
        
        expected = """function test_int() -> int
{
    return 1;
}"""
        
        result = processor.process_single_function(function_content)
        assert result.strip() == expected.strip()
    
    def test_process_single_function_already_typed(self, processor):
        """测试已有类型声明的函数不被修改"""
        function_content = """function test_typed() -> int
{
    return 1;
}"""
        
        result = processor.process_single_function(function_content)
        assert result == function_content
    
    def test_process_single_function_inline_brace(self, processor):
        """测试单行函数定义"""
        function_content = """function test_inline() {
    return 1;
}"""
        
        result = processor.process_single_function(function_content)
        assert '-> int' in result
        assert '{' in result


@pytest.fixture
def temp_test_env():
    """临时测试环境 fixture"""
    test_dir = Path(tempfile.mkdtemp())
    test_file = test_dir / "test.conf"
    
    yield test_dir, test_file
    
    # 清理
    if test_file.exists():
        test_file.unlink()
    for file in test_dir.glob("*.conf"):
        file.unlink()
    test_dir.rmdir()


class TestIntegration:
    """集成测试"""
    
    def test_process_file_with_various_functions(self, temp_test_env):
        """测试处理包含各种函数的文件"""
        test_dir, test_file = temp_test_env
        
        content = """# Test configuration

function test_void()
{
  dest = RTD_BLACKHOLE;
}

function test_int()
{
    return 1;
}

function test_string()
{
    return "hello world";
}

function test_pair()
{
    return (1, 2);
}

function test_already_typed() -> bool
{
    return true;
}"""
        
        # 写入测试文件
        test_file.write_text(content, encoding='utf-8')
        
        # 处理文件
        result = process_path(str(test_file), in_place=False)
        
        # 验证结果
        assert "test_void()" in result  # void 函数不变
        assert "test_void() ->" not in result
        
        assert "test_int() -> int" in result
        assert "test_string() -> string" in result  
        assert "test_pair() -> pair (int, int)" in result
        
        # 已有类型的函数不变
        assert "test_already_typed() -> bool" in result
    
    def test_process_directory(self, temp_test_env):
        """测试处理目录"""
        test_dir, test_file = temp_test_env
        
        # 创建多个配置文件
        file1 = test_dir / "config1.conf"
        file2 = test_dir / "config2.conf"
        
        file1.write_text("function test1() { return 1; }", encoding='utf-8')
        file2.write_text("function test2() { return true; }", encoding='utf-8')
        
        # 处理目录
        result = process_path(test_dir, in_place=False)
        
        # 验证结果包含两个文件的处理结果
        assert "config1.conf" in result
        assert "config2.conf" in result
        assert "-> int" in result
        assert "-> bool" in result
    
    def test_in_place_modification(self, temp_test_env):
        """测试原地修改功能"""
        _, test_file = temp_test_env
        
        original_content = """function test()
{
    return 1;
}"""
        
        test_file.write_text(original_content, encoding='utf-8')
        
        # 执行原地修改
        result = process_path(str(test_file), in_place=True)
        
        # 验证文件被修改
        modified_content = test_file.read_text(encoding='utf-8')
        assert "-> int" in modified_content
        assert "已处理文件" in result


class TestRealWorldCases:
    """真实世界用例测试"""
    
    @pytest.mark.parametrize("function_content,expected_type", [
        # void 函数
        ("""function test_empty_void1()
{
  if (65535,0,666) ~ bgp_large_community then dest = RTD_BLACKHOLE;
}""", None),  # 应该保持不变
        
        # pair 函数  
        ("""function test_bgp_large_community(int AS, int REGION, int NODE_ID)
{
  if (65535, 10, 10) ~ bgp_large_community then return (10, 10);
  if (65535, 3, NODE_ID) ~ bgp_large_community then return (3, NODE_ID);
  return (1, 1);
}""", "pair (int, int)"),
        
        # prefix 函数
        ("""function test_prefix_return_base1()
{
    if 1.0.0.0/24 ~ RTS_STATIC then return 1.0.0.0/24;
    return 2.0.0.0/24;
}""", "prefix"),
        
        # set 函数
        ("""function test_set_return()
{
    return {1, 2, 3, 4};
}""", "set"),
        
        # int 函数
        ("""function test_int_return()
{
    return 1;
}""", "int"),
    ])
    def test_sample_functions(self, processor, function_content, expected_type):
        """测试样例文件中的函数"""
        if expected_type is None:
            # void 函数不应该被修改
            result = processor.process_single_function(function_content)
            assert result == function_content
        else:
            result = processor.process_single_function(function_content)
            assert f"-> {expected_type}" in result


if __name__ == '__main__':
    pytest.main(["-v", __file__])