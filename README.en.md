# bird2-autotype

A utility tool for **BIRD Internet Routing Daemon (v2.17+)** that automatically adds explicit return type declarations to functions in BIRD configuration files.

[中文版本](README.md) | English Version

## Background

Since BIRD 2.17, functions without explicit return type declarations will trigger warnings, for example:

```bash
bird <WARN>: Inferring function foo return type from its return value: bool
```

This tool can scan and modify function definitions in configuration files in batch, automatically adding `-> <type>` based on inference results, facilitating one-time migration.

> [!NOTE]
>
> Note: Use this tool with caution in production environments and ensure you have backups of original configuration files.

## Supported Types

Sorted by priority from high to low

| Type           | Example                                                                                                 | Supported? |
| -------------- | ------------------------------------------------------------------------------------------------------- | ---------- |
| int            | `return 1;`                                                                                             | ✅         |
| pair           | `return (1234,5678);` <br> `return (1+2, a+b);`                                                         | ✅         |
| ip             | `return 1.2.3.4;`, `return fec0:3:4::1;` <br> `return 1.2.3.4.mask(8);`, `return fe80::ffff:.mask(64);` | ✅         |
| prefix         | `return 1.2.3.4/32;`, `return fe80::1/64;`                                                              | ✅         |
| string         | `return "hello world";`                                                                                 | ✅         |
| set            | `return {1, 2, 3, 4};`                                                                                  | ✅         |
| bool (default) | `return true;` <br> With operators\*                                                                    | ✅         |
| bytestring     | /                                                                                                       | ❌         |
| rd             | /                                                                                                       | ❌         |
| enum           | /                                                                                                       | ❌         |
| bgppath        | /                                                                                                       | ❌         |
| bgp_mask       | /                                                                                                       | ❌         |
| clist          | /                                                                                                       | ❌         |
| eclist         | /                                                                                                       | ❌         |
| lcist          | /                                                                                                       | ❌         |

## \* Operators

- Comparison: `=`, `!=`, `<`, `>`, `<=`, `>=`
- Logical: `&&`, `||`, `!`
- Arithmetic: `+`, `-`, `*`, `/`, `%`
- Matching: `~`, `!~`

## Tested Environments

- BIRD 2.17+
- Python 3.13.7
- Linux/MacOS

## Usage

```bash
wget https://raw.githubusercontent.com/bird-chinese-community/bird2-autotype/refs/heads/main/main.py -O main.py

python3 main.py --help
```

```bash
usage: main.py [-i] [-h] path

BIRD2 Auto Type Completion

positional arguments:
  path            BIRD config file or directory path

options:
  -i, --in-place  Modify files in-place
  -h, --help      Show help


Detailed examples:

  # Process single file
  main.py /path/to/bird.conf

  # Modify file in-place
  main.py -i /etc/bird/filter.conf

  # Batch process directory
  main.py /path/to/configs/

Supported types:
  • int:     return 1;
  • pair:    return (1, 2);  →  -> pair (int, int)
  • ip:      return 1.2.3.4;
  • prefix:  return 1.2.3.4/32; return net;
  • string:  return "hello";
  • set:     return {1, 2, 3};
  • bool:    return true; (default type)

Note: Void functions remain unchanged
```

## Example

Before:

```bash
function is_bogon_prefixes_v4() {
  return net ~ BOGON_PREFIXES_v4;
}
```

After:

```bash
function is_bogon_prefixes_v4() -> bool {
  return net ~ BOGON_PREFIXES_v4;
}
```

## TODO

- [ ] Parse warnings from BIRD logs and auto-fix
- [ ] Support less common types: bytestring/rd/enum/bgppath/bgp_mask/clist/eclist/lcist
- [ ] Improve type discrimination between quad/ip (currently always assumes quad is ip)
- [ ] Use `birdc eval expr` to simulate return expressions and infer types

## References

- [5.2 Data types | BIRD Official Documentation](https://bird.network.cz/?get_doc&v=20&f=bird-5.html#ss5.2)
- [Chapter 5.2 Data types | BIRD Chinese Documentation](https://bird.xmsl.dev/docs/user-guide/5-2-data-types.html)
- [Getting Started with BIRD and BGP](https://soha.moe/post/bird-bgp-kickstart.html)

---

## License

MIT
