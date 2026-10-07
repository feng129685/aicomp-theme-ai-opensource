# 智校园文档解析工具链

这是面向高校学习与校园事务资料的可复现解析工具链。它把文本或 OCR 输出转换为统一的 `ParseResult v1`，并把同一事项的两份通知转换为 `ChangeProposal v1`，供上层应用展示、追溯和在用户确认后应用。

## 当前能力

- 读取 UTF-8 文本并保留字段证据：原文、位置、页码和置信度。
- 通过统一的 `ParserAdapter` 接入人工 OCR 夹具或记录式 OCR JSON。
- 解析课程考核权重；信息不完整或结构冲突时返回不可计算或待确认状态，不擅自补全。
- 比较通知前后版本，生成截止时间、地点等字段的变更建议。
- 对冲突日期设置确认门槛，不自动选择候选值。
- 通过合同守卫校验 `ParseResult` 和 `ChangeProposal` 的结构与枚举。
- 可选接入 EasyOCR 1.7.2：图片直接识别，PDF 逐页渲染后进入同一解析链路。
- 用稳定的 `course_id`、`document_id`、`asset_id` 和 `task_id` 表达课程、资料与任务关系。

本仓库只负责解析、证据和变更建议，不写数据库、不创建任务、不修改提醒，也不自动接受变更。上层应用应在用户确认后再应用建议。

## 快速开始

需要 Python 3.10 或更高版本。基础文本解析只使用 Python 标准库；EasyOCR 输入需要额外安装可选依赖。

```powershell
python -m unittest discover -s tests -v
python cli.py self-check
python validation/validate.py
```

Windows 用户也可以运行完整验证脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\validation\validate.ps1
```

复现一个文本解析和通知比较示例：

```powershell
python cli.py parse-text `
  --request samples/requests/COURSE-001-SIMPLE.request.json `
  --input samples/input/COURSE-001-SIMPLE.md `
  --output samples/outputs/COURSE-001-SIMPLE.parse-result.json

python cli.py compare `
  --old samples/outputs/NOTICE-003-V1.parse-result.json `
  --new samples/outputs/NOTICE-003-V2.parse-result.json `
  --task-map samples/task-map-example.json `
  --output samples/outputs/NOTICE-003.change-proposal.json
```

复现通知截止时间的非冲突变化：

```powershell
python validation/generate_stage7_samples.py
python -m unittest tests.test_stage7_deliverables -v
```

复现同步语义夹具：

```powershell
python -m unittest tests.test_sync_fixtures -v
python validation/validate_sync_fixtures.py
```

## 目录

```text
src/          解析器、输入适配器、通知差异和合同守卫
schemas/      ParseResult v1 与 ChangeProposal v1
samples/      脱敏输入、请求、输出和 OCR 接入格式示例
tests/        单元与集成回归测试
validation/   可复现验收脚本
docs/         接口、OCR 测试口径和第三方依赖说明
```

## 同步语义夹具

`samples/sync-baseline-v1.json` 和 `samples/sync-cases-v1.json` 提供稳定编号、原文证据、任务关系以及在线、离线、失败、冲突四类合成场景。它们用于约束未来同步实现的行为，不包含账号系统、服务器或网络客户端，也不扩展 `ParseResult v1` 和 `ChangeProposal v1` 的公共字段。样例中的 `account_id` 和 `device_id` 只是合成标识，用于关系测试，不提供认证或账号能力。

离线和失败场景必须保留本机副本，冲突场景必须保留两边候选值并等待用户选择。字段不变量见 [docs/sync-field-invariants.md](docs/sync-field-invariants.md)，场景矩阵见 [docs/sync-scenario-matrix.md](docs/sync-scenario-matrix.md)。

## OCR 说明

仓库中的课程、通知、OCR 图片、文字和 JSON 均为合成或脱敏测试数据，不对应任何真实学校、课程、教师或通知。当前没有捆绑或运行真实 OCR 引擎，也没有测量字符准确率、字段准确率或模型准确率。真实引擎接入时，应按照 [docs/ocr-evaluation.md](docs/ocr-evaluation.md) 保存版本、参数、原始输出和统计口径。

NOTICE-004 样例演示截止时间变化和稳定任务映射：变化建议仍是“待确认”，只有用户确认后上层应用才应更新任务。`course-relationship-stage7.json` 演示周视图所需字段与稳定编号关系，关系夹具不扩展公共 Schema。

Schema 中的 `example.invalid` 只是离线标识符，不需要联网加载。

## 许可证

本项目采用 MIT License，详见 [LICENSE](LICENSE)。
