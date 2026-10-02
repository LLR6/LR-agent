# 测试今天都通过，为什么改一个配置项就回归？一次 ChronoForge 离线实跑

作者：LLR6

LR-Agent 的 ChronoForge 会把维护变更放进独立工作区，再重放原始测试。这次用一个很小的超时配置例子，实际运行这条链路，保留通过和失败的输出。

**实验边界：维护动作由脚本执行，没有调用大模型。测试由真实 pytest 进程执行。这个案例验证工作区隔离、测试重放和回归记录，不代表模型能力、真实生产项目成功率或预测准确率。**

## 一个容易忽略的兼容约定

初始实现支持旧配置键 `timeout_s`，默认值为 15：

```python
def timeout(config):
    return config.get('timeout_s', 15)
```

两条原始测试检查默认值和旧配置 `{'timeout_s': 7}`。基线实际运行得到 `2 passed`，退出码为 0。

第一轮维护加入新配置键，保留旧键回退：

```python
def timeout(config):
    return config.get('request_timeout', config.get('timeout_s', 15))
```

第二轮维护删除旧键回退：

```python
def timeout(config):
    return config.get('request_timeout', 15)
```

第二轮仍然返回合法数字，默认值测试也仍然通过。但原来指定 7 秒的配置变成 15 秒，原始兼容约定被破坏了。

## 实跑结果

| 阶段 | 原始测试结果 | 退出码 | 存活状态 |
| --- | --- | --- | --- |
| 基线 | 2 passed | 0 | 初始状态 |
| 第一轮：新增键并保留回退 | 2 passed | 0 | True |
| 第二轮：删除旧键回退 | 1 failed, 1 passed | 1 | False |

第二轮实际失败信息：

```text
def test_legacy_config():
    assert timeout({'timeout_s': 7}) == 7
E   assert 15 == 7
```

单条轨迹的存活曲线为：第 0 代 1.0，第 1 代 1.0，第 2 代 0.0。这里只运行了一条预设轨迹，这些数字不是统计估计。

脚本还检查每轮原始测试的文本完全相同，避免通过修改测试掩盖回归。保存的证据包含每轮实现、测试文本、真实验证输出和原始测试 SHA-256。

## 自己复现

在仓库根目录使用 Python 3.12 和独立虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/demo_chronoforge_offline.py
```

Windows 可用 `.venv\Scripts\activate` 激活。请确保虚拟环境的 `pytest` 命令在 PATH 中：ChronoForge 会调用这个命令。脚本只在临时工作区修改示例文件，无需模型接口密钥。

运行结束后查看 `artifacts/chronoforge-offline/evidence.json`。原始报告里的临时工作区路径会在退出后失效，所以案例另存了实现、测试和输出。

- [可执行脚本](../scripts/demo_chronoforge_offline.py)
- [这次运行的证据 JSON](cases/chronoforge-offline/evidence.json)
- [完整终端输出](cases/chronoforge-offline/run.log)

## 它说明了什么

一轮改动通过测试，并不保证下一轮维护仍然保留原始约定。这个最小例子展示了 ChronoForge 怎样把连续维护后的回归显式记录出来，便于定位是哪一轮开始破坏旧行为。

接下来可把维护执行器换成真实模型，加入多种项目、多个随机种子和更多轨迹，再讨论模型表现。离线案例本身不回答哪个模型更好，也不能证明这套测试能覆盖所有兼容问题。
