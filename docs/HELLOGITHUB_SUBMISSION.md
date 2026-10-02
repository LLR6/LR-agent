# HelloGitHub 项目自荐稿

状态：2026-10-02 已通过 GitHub 网页提交，等待审核。

公开投稿：https://github.com/521xueweihan/HelloGitHub/issues/3826

投稿标题：[开源推荐] LR-Agent：给 AI 编程补丁做连续维护压力测试

---

### 项目地址

https://github.com/LLR6/LR-agent

### 类别

人工智能

### 项目标题

给 AI 编程补丁做连续维护压力测试

### 项目描述

LR-Agent 是一个 Python 编程 Agent 实验项目，关注“当前测试通过的补丁，遇到后续维护变化会怎样”。它在隔离工作区生成候选补丁并执行验证，再让仓库连续经历依赖、接口或功能变化，每一代重放原始检查，输出补丁生存和维护成本报告。适合对编程 Agent、软件测试和维护实验感兴趣的开发者；完整运行需要配置兼容模型接口。

### 亮点

- 候选补丁在独立工作区中修改与验证，比较依据包含实际命令退出码。
- 连续维护实验中，后一代继承前一代的代码，便于观察累积变化造成的回归。
- 原有测试和长期约束会被重新执行，保留可检查的实验工作区和报告。
- 提供 CLI、Web 界面、最小示例以及研究边界说明，欢迎提交最小反例。

目前是研究型工程原型。合成场景和维护成本指标属于启发式实验，不能证明现实未来正确性，也没有据此声称领先其他 Agent。完整实验会调用模型，时间与费用随配置而变化。

### 示例代码

配置模型并完成安装后，可在示例工作区运行：

```bash
lr-agent doctor
lr-agent chrono "Keep current client configuration behavior stable while allowing future configuration evolution" --generations 3 --trajectories 3
```

安装、环境配置和示例工作区设置：
https://github.com/LLR6/LR-agent/blob/main/docs/DEMO_CHRONOFORGE.md

### 截图或演示视频

![LR-Agent 流程展示](https://raw.githubusercontent.com/LLR6/LR-agent/main/docs/media/chronoforge-showcase.gif)

上面的 GIF 是确定性流程展示，用于解释交互与实验结构，不是实际模型运行的 benchmark 成绩。

### 推荐者说明

项目自荐。希望收集安装体验、维护场景设计和报告解释方面的反馈，尤其欢迎能揭示误导性结果的最小案例。