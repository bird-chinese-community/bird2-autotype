# bird2-autotype

一个用于 **BIRD Internet Routing Daemon (v2.17+)** 的小工具，可自动为 BIRD 配置文件中的函数补全显式返回类型声明。

[English Version](README.en.md) | 中文版本

## 背景

自 BIRD 2.17 起，如果函数未显式声明返回类型，就会产生警告，例如：

```bash

bird <WARN>: Inferring function foo return type from its return value: bool

```

这个工具可以批量扫描并修改配置文件中的函数定义，根据推断结果自动补全 `-> <类型>`，方便一次性迁移

> [!NOTE]
>
> 注意: 在生产环境请谨慎使用此工具，并确保已备份原始配置文件。

## 支持推断的类型

排序按照优先级从高到低

| 类型            | example                                                                                                 | 是否支持? |
| --------------- | ------------------------------------------------------------------------------------------------------- | --------- |
| int             | `return 1;`                                                                                             | ✅        |
| pair            | `return (1234,5678);` <br> `return (1+2, a+b);`                                                         | ✅        |
| ip              | `return 1.2.3.4;`, `return fec0:3:4::1;` <br> `return 1.2.3.4.mask(8);`, `return fe80::ffff:.mask(64);` | ✅        |
| prefix          | `return 1.2.3.4/32;`, `return fe80::1/64;`                                                              | ✅        |
| string          | `return "hello world";`                                                                                 | ✅        |
| set             | `return {1, 2, 3, 4};`                                                                                  | ✅        |
| bool (默认类型) | `return true;` <br> 带有运算符\*                                                                        | ✅        |
| bytestring      | /                                                                                                       | ❌        |
| rd              | /                                                                                                       | ❌        |
| enum            | /                                                                                                       | ❌        |
| bgppath         | /                                                                                                       | ❌        |
| bgp_mask        | /                                                                                                       | ❌        |
| clist           | /                                                                                                       | ❌        |
| eclist          | /                                                                                                       | ❌        |
| lcist           | /                                                                                                       | ❌        |

## \* 运算符

- 比较运算符: `=`, `!=`, `<`, `>`, `<=`, `>=`
- 逻辑运算符: `&&`, `||`, `!`
- 数学运算符: `+`, `-`, `*`, `/`, `%`
- 判断运算符: `~`, `!~`

## 已经过测试的环境

- BIRD 2.17+
- Python 3.13.7
- Linux/MacOS

## 使用方法

```bash
wget https://raw.githubusercontent.com/bird-chinese-community/bird2-autotype/refs/heads/main/main.py -O main.py

python3 main.py --help
```

```bash
usage: main.py [-i] [-h] path

BIRD2 Auto Type Completion

positional arguments:
  path            BIRD 配置文件或目录路径

options:
  -i, --in-place  直接修改文件
  -h, --help      显示帮助


详细示例:

  # 处理单个文件
  main.py /path/to/bird.conf

  # 直接修改文件
  main.py -i /etc/bird/filter.conf

  # 批量处理目录
  main.py /path/to/configs/

支持类型:
  • int:     return 1;
  • pair:    return (1, 2);  →  -> pair (int, int)
  • ip:      return 1.2.3.4;
  • prefix:  return 1.2.3.4/32; return net;
  • string:  return "hello";
  • set:     return {1, 2, 3};
  • bool:    return true; (默认类型)

注: 无返回值函数将保持不变
```

## 示例

修改前：

```bash
function is_bogon_prefixes_v4() {
  return net ~ BOGON_PREFIXES_v4;
}
```

修改后：

```bash
function is_bogon_prefixes_v4() -> bool {
  return net ~ BOGON_PREFIXES_v4;
}
```

## TODO

- [ ] 支持从 BIRD 日志解析警告并自动修复
- [ ] 支持 bytestring/rd/enum/bgppath/bgp_mask/clist/eclist/lcist 等较为冷门的数据类型
- [ ] 支持智能鉴别 quad/ip 数据类型，目前永远认为 quad 是 ip
- [ ] 支持使用 `birdc eval expr` 模拟 return 运算结果，并根据结果推断类型

## 参考资料

- [5.2 Data types | BIRD Official Documentation](https://bird.network.cz/?get_doc&v=20&f=bird-5.html#ss5.2)
- [第五章·第二节 数据类型 (Data types) | BIRD 中文文档](https://bird.xmsl.dev/docs/user-guide/5-2-data-types.html)
- [BIRD 与 BGP 的新手开场](https://soha.moe/post/bird-bgp-kickstart.html)

---

## License

MIT
