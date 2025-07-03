# Web UI 文件移动工具

这是一个轻量级的 Web UI 版本，用于替代桌面 GUI。

## 特点

- **极小体积**: 打包后约 10-15MB
- **现代界面**: 响应式设计，支持移动端
- **零依赖前端**: 纯原生 HTML/CSS/JavaScript
- **易于部署**: 单文件启动

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
python app.py
```

服务将自动在浏览器中打开 http://127.0.0.1:5000

## 功能

1. **配置管理**: 设置源目录、目标目录和分配策略
2. **文件扫描**: 扫描指定目录中的文件
3. **智能分配**: 根据策略生成文件分配方案
4. **预览确认**: 在执行前预览分配结果
5. **安全执行**: 确认后执行文件移动

## 打包发布

使用 PyInstaller 可以打包为单文件可执行程序：

```bash
pip install pyinstaller
pyinstaller --onefile --add-data "templates:templates" --add-data "static:static" app.py
```

## 技术栈

- **后端**: Flask (轻量级 Web 框架)
- **前端**: 原生 HTML5 + CSS3 + JavaScript (ES6+)
- **样式**: 现代响应式设计，渐变背景，卡片布局
- **交互**: 原生 Fetch API，无第三方依赖

## 优势

相比桌面 GUI：
- 更现代的用户界面
- 更小的打包体积
- 更好的跨平台兼容性
- 更容易维护和更新
- 支持远程访问（如需要）
