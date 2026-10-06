# 第三方依赖说明

基础解析链只依赖 Python 标准库。EasyOCR 接入是可选能力，当前代码按 EasyOCR 1.7.2 适配，并依赖 PyTorch、torchvision、Pillow 与 PyMuPDF；仓库不捆绑模型文件。

安装可选依赖的示例：

```powershell
python -m pip install easyocr==1.7.2 PyMuPDF
```

EasyOCR 首次运行可能下载模型；模型缓存应保留在本机，不提交到仓库。默认单元测试使用 FakeReader，只验证格式转换和错误边界，不等同于真实 OCR 准确率。

`JsonOcrProvider` 接收外部 OCR 引擎已经生成的 JSON。接入具体引擎前，需要单独核对引擎版本、模型文件来源、许可证、移动端体积、隐私处理和服务条款；本仓库不会默认上传任何模型文件或 API 密钥。

PyMuPDF 采用 AGPL 或商业双许可，部署到闭源或商业产品前必须按实际分发方式完成许可评估。

如使用云端 OCR，还应在产品侧明确数据传输、日志留存、费用和数据出境规则。
