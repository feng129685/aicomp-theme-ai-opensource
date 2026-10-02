# 智校园 AI 文档解析工具链

这是面向高校学习与校园事务资料的可复现解析工具链。它把文本或 OCR 输出转换为统一的 `ParseResult v1`，并把同一事项的两份通知转换为 `ChangeProposal v1`，供上层应用展示、追溯和在用户确认后应用。

## 当前能力

- 读取 UTF-8 文本并保留字段证据：原文、位置、页码和置信度。
- 通过统一的 `ParserAdapter` 接入人工 OCR 夹具或记录式 OCR JSON。
- 解析课程考核权重；信息不完整或结构冲突时返回不可计算或待确认状态，不擅自补全。
- 比较通知前后版本，生成截止时间、地点等字段的变更建议。
- 对冲突日期设置确认门槛，不自动选择候选值。
- 通过合同守卫校验 `ParseResult` 和 `ChangeProposal` 的结构与枚举。

本仓库只负责解析、证据和变更建议，不写数据库、不创建任务、不修改提醒，也不自动接受变更。上层应用应在用户确认后再应用建议。

## 快速开始

需要 Python 3.10 或更高版本。项目运行时只使用 Python 标准库。

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

## 目录

```text
src/          解析器、输入适配器、通知差异和合同守卫
schemas/      ParseResult v1 与 ChangeProposal v1
samples/      脱敏输入、请求、输出和 OCR 接入格式示例
tests/        单元与集成回归测试
validation/   可复现验收脚本
docs/         接口、OCR 测试口径和第三方依赖说明
```

## OCR 说明

仓库中的课程、通知、OCR 图片、文字和 JSON 均为合成或脱敏测试数据，不对应任何真实学校、课程、教师或通知。当前没有捆绑或运行真实 OCR 引擎，也没有测量字符准确率、字段准确率或模型准确率。真实引擎接入时，应按照 [docs/ocr-evaluation.md](docs/ocr-evaluation.md) 保存版本、参数、原始输出和统计口径。

Schema 中的 `example.invalid` 只是离线标识符，不需要联网加载。

## 许可证

本项目采用 MIT License，详见 [LICENSE](LICENSE)。
