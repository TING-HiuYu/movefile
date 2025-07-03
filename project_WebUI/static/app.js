// 文件分类器 Web UI JavaScript

class FileClassifierApp {
    constructor() {
        this.variables = [];
        this.usedVariables = new Set();
        this.templateComponents = [];
        this.selectedFiles = [];
        this.allocatedFiles = [];
        this.currentOutputDirectory = '';
        this.clientId = 'client_' + Math.random().toString(36).substr(2, 9);
        this.heartbeatInterval = null;
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.checkInitialConfig();
        await this.loadVariables();
        this.setupDragAndDrop();
        await this.loadOutputDirectory();
        await this.loadCurrentHashAlgorithm();
        this.setupHashAlgorithmSelector();
        await this.populateHashSelector();
        
        // 启动心跳包
        this.startHeartbeat();
        
        // 页面关闭时停止心跳包
        window.addEventListener('beforeunload', () => {
            this.stopHeartbeat();
        });
    }

    startHeartbeat() {
        // 立即发送一次心跳包
        this.sendHeartbeat();
        
        // 每1.5秒发送一次心跳包
        this.heartbeatInterval = setInterval(() => {
            this.sendHeartbeat();
        }, 1500);
    }

    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    async sendHeartbeat() {
        try {
            await fetch('/api/heartbeat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    client_id: this.clientId,
                    timestamp: Date.now()
                })
            });
        } catch (error) {
            // 忽略心跳包错误，避免控制台噪音
            console.debug('心跳包发送失败:', error);
        }
    }

    setupEventListeners() {
        // 初始配置相关
        document.getElementById('save-config').addEventListener('click', () => this.saveConfig());
        document.getElementById('browse-plugins').addEventListener('click', () => this.browseDirectory('plugins-dir'));
        document.getElementById('browse-output').addEventListener('click', () => this.browseDirectory('output-dir'));

        // 模板编辑相关
        document.getElementById('refresh-variables').addEventListener('click', () => this.loadVariables());
        document.getElementById('clear-template').addEventListener('click', () => this.clearTemplate());
        document.getElementById('save-template').addEventListener('click', () => this.saveTemplate());
        document.getElementById('browse-output-dir').addEventListener('click', () => this.browseOutputDirectory());

        // 文件处理相关
        document.getElementById('select-files').addEventListener('click', () => this.showFileDialog());
        document.getElementById('browse-system-files').addEventListener('click', () => this.browseSystemFiles());
        document.getElementById('process-files').addEventListener('click', () => this.processFiles());

        // 文件选择对话框
        document.getElementById('browse-scan-dir').addEventListener('click', () => this.browseDirectory('scan-directory'));
        document.getElementById('cancel-file-select').addEventListener('click', () => this.hideFileDialog());
        document.getElementById('confirm-file-select').addEventListener('click', () => this.scanFiles());
    }

    async checkInitialConfig() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();
            
            if (!data.success || !data.config.target_folder || data.config.target_folder === '/tmp/output') {
                this.showInitConfigDialog();
            } else {
                this.showMainInterface();
            }
        } catch (error) {
            console.error('检查配置失败:', error);
            this.showInitConfigDialog();
        }
    }

    showInitConfigDialog() {
        document.getElementById('init-config-dialog').style.display = 'flex';
        document.getElementById('main-interface').style.display = 'none';
    }

    showMainInterface() {
        document.getElementById('init-config-dialog').style.display = 'none';
        document.getElementById('main-interface').style.display = 'flex';
    }

    async saveConfig() {
        const pluginsDir = document.getElementById('plugins-dir').value;
        const outputDir = document.getElementById('output-dir').value;
        const hashAlgorithm = document.getElementById('hash-algorithm').value;

        if (!pluginsDir || !outputDir) {
            alert('请选择插件目录和输出目录');
            return;
        }

        try {
            this.showLoading(true);
            
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    external_plugins_dir: pluginsDir,
                    target_folder: outputDir,
                    hash_check_enable: hashAlgorithm,
                    is_initial_setup: true  // 标记为首次配置
                })
            });

            const data = await response.json();
            
            if (data.success) {
                if (data.requires_restart) {
                    // 显示重启提示
                    this.showRestartMessage();
                    
                    // 延迟调用重启API
                    setTimeout(async () => {
                        try {
                            await fetch('/api/restart-server', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ delay: 1 })
                            });
                        } catch (error) {
                            console.log('重启请求已发送');
                        }
                        
                        // 等待服务器重启并轮询配置状态
                        this.waitForConfiguration();
                    }, 1000);
                } else {
                    this.showMainInterface();
                    await this.loadVariables();
                    await this.loadOutputDirectory();
                }
            } else {
                alert('保存配置失败: ' + data.error);
            }
        } catch (error) {
            console.error('保存配置失败:', error);
            alert('保存配置失败');
        } finally {
            this.showLoading(false);
        }
    }

    showRestartMessage() {
        // 创建重启提示覆盖层
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10000;
            color: white;
            font-size: 18px;
            text-align: center;
        `;
        
        overlay.innerHTML = `
            <div style="background: #2c2c2c; padding: 30px; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
                <div style="margin-bottom: 20px;">配置保存成功！</div>
                <div style="margin-bottom: 10px;">应用正在重启以加载新配置...</div>
                <div style="font-size: 14px; color: #999;">请稍候，页面将自动刷新</div>
                <div style="margin-top: 20px;">
                    <div class="loading-spinner" style="border: 3px solid #333; border-top: 3px solid #409eff; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto;"></div>
                </div>
            </div>
        `;
        
        // 添加旋转动画
        const style = document.createElement('style');
        style.textContent = `
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(overlay);
    }

    async waitForServerRestart() {
        const maxAttempts = 30; // 最多等待30秒
        let attempts = 0;
        
        // 停止心跳包，避免干扰重启
        this.stopHeartbeat();
        
        const checkServer = async () => {
            try {
                const response = await fetch('/api/config', { 
                    method: 'GET',
                    cache: 'no-cache'
                });
                
                if (response.ok) {
                    // 服务器恢复，重新启动心跳包并刷新页面内容
                    this.startHeartbeat();
                    window.location.reload();
                    return;
                }
            } catch (error) {
                // 服务器还未恢复，继续等待
            }
            
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(checkServer, 1000); // 每秒检查一次
            } else {
                // 超时，手动刷新页面
                alert('服务器重启可能需要更长时间，请手动刷新页面');
                window.location.reload();
            }
        };
        
        // 等待3秒后开始检查（给服务器重启时间）
        setTimeout(checkServer, 3000);
    }

    async loadOutputDirectory() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();
            
            if (data.success && data.config.target_folder) {
                this.currentOutputDirectory = data.config.target_folder;
                const outputElement = document.getElementById('output-path');
                outputElement.innerHTML = `<span class="path-text">${this.currentOutputDirectory}</span>`;
                outputElement.classList.add('selected');
            }
        } catch (error) {
            console.error('加载输出目录失败:', error);
        }
    }

    async browseOutputDirectory() {
        try {
            const response = await fetch('/api/browse-system', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'directory'
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.currentOutputDirectory = data.path;
                this.updateOutputDirectory();
            } else {
                // 回退到自定义浏览器
                this.currentBrowseCallback = (selectedPath) => {
                    this.currentOutputDirectory = selectedPath;
                    this.updateOutputDirectory();
                };
                this.showDirectoryDialog();
            }
        } catch (error) {
            console.error('系统文件浏览器失败:', error);
            // 回退到自定义浏览器
            this.currentBrowseCallback = (selectedPath) => {
                this.currentOutputDirectory = selectedPath;
                this.updateOutputDirectory();
            };
            this.showDirectoryDialog();
        }
    }

    async updateOutputDirectory() {
        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    target_folder: this.currentOutputDirectory
                })
            });

            const data = await response.json();
            
            if (data.success) {
                const outputElement = document.getElementById('output-path');
                outputElement.innerHTML = `<span class="path-text">${this.currentOutputDirectory}</span>`;
                outputElement.classList.add('selected');
            } else {
                alert('更新输出目录失败: ' + data.error);
            }
        } catch (error) {
            console.error('更新输出目录失败:', error);
        }
    }

    async loadVariables() {
        try {
            const response = await fetch('/api/variables');
            const data = await response.json();
            
            if (data.success) {
                this.variables = data.variables;
                this.renderVariables();
            } else {
                console.error('加载变量失败:', data.error);
            }
        } catch (error) {
            console.error('加载变量失败:', error);
        }
    }

    renderVariables() {
        const panel = document.getElementById('variables-panel');
        panel.innerHTML = '';

        this.variables.forEach(plugin => {
            if (!plugin.variables || plugin.variables.length === 0) return;

            const group = document.createElement('div');
            group.className = 'variable-group';

            const title = document.createElement('div');
            title.className = 'variable-group-title';
            
            // 只显示描述的第一行作为标题
            const fullDescription = plugin.description || plugin.plugin_name;
            const shortDescription = fullDescription.split('\n')[0].split('。')[0].split(',')[0];
            title.textContent = shortDescription;
            
            // 如果描述很长，添加展开功能
            if (fullDescription.length > shortDescription.length + 10) {
                title.style.cursor = 'pointer';
                title.title = '点击查看完整描述';
                
                const expandIcon = document.createElement('span');
                expandIcon.textContent = ' ▼';
                expandIcon.style.fontSize = '0.8em';
                expandIcon.style.color = 'var(--text-muted)';
                title.appendChild(expandIcon);
                
                let expanded = false;
                title.addEventListener('click', () => {
                    if (expanded) {
                        title.textContent = shortDescription;
                        title.appendChild(expandIcon);
                        expandIcon.textContent = ' ▼';
                    } else {
                        title.textContent = fullDescription;
                        title.appendChild(expandIcon);
                        expandIcon.textContent = ' ▲';
                    }
                    expanded = !expanded;
                });
            }

            // 添加插件设置按钮（如果支持 webui）
            if (plugin.webui && plugin.webui.enabled) {
                const settingsBtn = document.createElement('button');
                settingsBtn.className = 'plugin-settings-btn';
                settingsBtn.textContent = '设置';
                settingsBtn.onclick = () => this.openPluginSettings(plugin.plugin_name, plugin.webui);
                title.appendChild(settingsBtn);
            }

            group.appendChild(title);

            plugin.variables.forEach(variable => {
                const item = document.createElement('div');
                item.className = 'variable-item';
                item.draggable = true;
                item.dataset.variableName = variable.name;
                item.dataset.description = variable.description;
                
                const nameDiv = document.createElement('div');
                nameDiv.textContent = variable.name;
                item.appendChild(nameDiv);

                const descDiv = document.createElement('div');
                descDiv.className = 'variable-description';
                descDiv.textContent = variable.description;
                item.appendChild(descDiv);

                // 检查是否已使用
                if (this.usedVariables.has(variable.name)) {
                    item.classList.add('used');
                    item.draggable = false;
                }

                group.appendChild(item);
            });

            panel.appendChild(group);
        });
    }

    setupDragAndDrop() {
        // 设置变量拖拽
        document.addEventListener('dragstart', (e) => {
            if (e.target.classList.contains('variable-item') && !e.target.classList.contains('used')) {
                e.dataTransfer.setData('text/plain', e.target.dataset.variableName);
                e.target.classList.add('dragging');
                // 不创建拖拽预览，使用原生拖拽效果
            }
        });

        document.addEventListener('dragend', (e) => {
            if (e.target.classList.contains('variable-item')) {
                e.target.classList.remove('dragging');
            }
            this.removeDragPreview();
            this.removeDropPlaceholders();
        });

        // 设置模板编辑器拖拽接收
        const templateEditor = document.getElementById('template-editor');
        
        templateEditor.addEventListener('dragover', (e) => {
            e.preventDefault();
            templateEditor.classList.add('drag-over');
            this.showDropPlaceholders(e);
        });

        templateEditor.addEventListener('dragleave', (e) => {
            if (!templateEditor.contains(e.relatedTarget)) {
                templateEditor.classList.remove('drag-over');
                this.removeDropPlaceholders();
            }
        });

        templateEditor.addEventListener('drop', (e) => {
            e.preventDefault();
            templateEditor.classList.remove('drag-over');
            
            const variableName = e.dataTransfer.getData('text/plain');
            if (variableName && !this.usedVariables.has(variableName)) {
                const dropPosition = this.getDropPosition(e);
                this.addVariableToTemplate(variableName, dropPosition);
            }
            this.removeDropPlaceholders();
        });
    }

    createDragPreview(text, x, y) {
        const preview = document.createElement('div');
        preview.className = 'drag-preview';
        preview.textContent = text;
        preview.style.left = x + 'px';
        preview.style.top = y + 'px';
        preview.id = 'drag-preview';
        document.body.appendChild(preview);

        // 更新预览位置
        document.addEventListener('dragover', (e) => {
            const preview = document.getElementById('drag-preview');
            if (preview) {
                preview.style.left = e.clientX + 10 + 'px';
                preview.style.top = e.clientY + 10 + 'px';
            }
        });
    }

    removeDragPreview() {
        const preview = document.getElementById('drag-preview');
        if (preview) {
            preview.remove();
        }
    }

    addVariableToTemplate(variableName, position = null) {
        // 标记变量为已使用
        this.usedVariables.add(variableName);
        
        // 添加到模板组件
        const newComponent = {
            type: 'variable',
            name: variableName
        };

        if (position !== null && position < this.templateComponents.length) {
            this.templateComponents.splice(position, 0, newComponent);
        } else {
            this.templateComponents.push(newComponent);
        }

        // 重新渲染模板和变量面板
        this.renderTemplate();
        this.renderVariables();
        this.updatePathPreview();
    }

    renderTemplate() {
        const editor = document.getElementById('template-editor');
        
        if (this.templateComponents.length === 0) {
            editor.innerHTML = '<div class="template-hint">拖拽左侧变量到此处构建路径模板</div>';
            return;
        }

        const container = document.createElement('div');
        container.className = 'template-components';

        this.templateComponents.forEach((component, index) => {
            const wrapper = document.createElement('div');
            wrapper.className = 'template-component';

            if (component.type === 'variable') {
                const element = document.createElement('div');
                element.className = 'template-variable';
                element.textContent = component.name; // 不显示 {}
                wrapper.appendChild(element);

                // 添加删除按钮（右上角）
                const removeBtn = document.createElement('button');
                removeBtn.className = 'component-remove';
                removeBtn.innerHTML = '×';
                removeBtn.onclick = () => this.removeComponent(index);
                wrapper.appendChild(removeBtn);
                
            } else if (component.type === 'separator') {
                const element = document.createElement('div');
                element.className = 'template-separator';
                element.textContent = '/';
                wrapper.appendChild(element);

                // 添加删除按钮（右上角）
                const removeBtn = document.createElement('button');
                removeBtn.className = 'component-remove';
                removeBtn.innerHTML = '×';
                removeBtn.onclick = () => this.removeComponent(index);
                wrapper.appendChild(removeBtn);
                
            } else if (component.type === 'text') {
                const element = document.createElement('input');
                element.className = 'template-text-input';
                element.type = 'text';
                element.value = component.value || '';
                element.placeholder = '输入文本';
                element.onchange = () => {
                    this.templateComponents[index].value = element.value;
                    this.updatePathPreview();
                };
                wrapper.appendChild(element);

                // 添加删除按钮（右上角）
                const removeBtn = document.createElement('button');
                removeBtn.className = 'component-remove';
                removeBtn.innerHTML = '×';
                removeBtn.onclick = () => this.removeComponent(index);
                wrapper.appendChild(removeBtn);
            }

            container.appendChild(wrapper);

            // 在每个组件后添加添加按钮（除了最后一个）
            if (index < this.templateComponents.length - 1) {
                const addBtn = this.createAddButton(index + 1);
                container.appendChild(addBtn);
            }
        });

        // 在最后添加添加按钮
        const finalAddBtn = this.createAddButton(this.templateComponents.length);
        container.appendChild(finalAddBtn);

        editor.innerHTML = '';
        editor.appendChild(container);
    }

    createAddButton(position) {
        const addBtn = document.createElement('div');
        addBtn.className = 'add-component-btn';
        addBtn.innerHTML = '+';
        addBtn.onclick = () => this.showAddMenu(addBtn, position);
        return addBtn;
    }

    showAddMenu(button, position) {
        // 创建简单的添加菜单
        const menu = document.createElement('div');
        menu.style.cssText = `
            position: absolute;
            background: var(--panel-color);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            padding: var(--spacing-sm);
            z-index: 100;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        `;

        const separatorBtn = document.createElement('button');
        separatorBtn.textContent = '添加分隔符 /';
        separatorBtn.className = 'btn secondary';
        separatorBtn.style.cssText = `
            display: block;
            width: 100%;
            margin-bottom: var(--spacing-xs);
        `;
        separatorBtn.onclick = () => {
            this.insertComponent(position, { type: 'separator' });
            menu.remove();
        };

        const textBtn = document.createElement('button');
        textBtn.textContent = '添加文本';
        textBtn.className = 'btn secondary';
        textBtn.style.cssText = `
            display: block;
            width: 100%;
        `;
        textBtn.onclick = () => {
            this.insertComponent(position, { type: 'text', value: '' });
            menu.remove();
        };

        menu.appendChild(separatorBtn);
        menu.appendChild(textBtn);

        // 定位菜单
        const rect = button.getBoundingClientRect();
        menu.style.left = rect.left + 'px';
        menu.style.top = rect.bottom + 5 + 'px';

        document.body.appendChild(menu);

        // 点击其他地方关闭菜单
        setTimeout(() => {
            document.addEventListener('click', function closeMenu(e) {
                if (!menu.contains(e.target)) {
                    menu.remove();
                    document.removeEventListener('click', closeMenu);
                }
            });
        }, 100);
    }

    insertComponent(position, component) {
        this.templateComponents.splice(position, 0, component);
        this.renderTemplate();
        this.updatePathPreview();
    }

    removeComponent(index) {
        const component = this.templateComponents[index];
        if (component.type === 'variable') {
            this.usedVariables.delete(component.name);
        }
        this.templateComponents.splice(index, 1);
        this.renderTemplate();
        this.renderVariables();
        this.updatePathPreview();
    }

    clearTemplate() {
        this.templateComponents = [];
        this.usedVariables.clear();
        this.renderTemplate();
        this.renderVariables();
        this.updatePathPreview();
    }

    async saveTemplate() {
        try {
            let templateString = this.buildTemplateString();
            
            // 自动在末尾添加 /{filename} 如果模板不以文件名相关变量结尾
            const fileVariables = ['filename', 'basename'];
            const endsWithFileVariable = fileVariables.some(varName => 
                templateString.endsWith(`{${varName}}`)
            );
            
            if (!endsWithFileVariable && templateString.trim() !== '') {
                // 如果模板不为空且不以文件变量结尾，自动添加 /{filename}
                if (!templateString.endsWith('/')) {
                    templateString += '/';
                }
                templateString += '{filename}';
            }
            
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    path_template: templateString
                })
            });

            const data = await response.json();
            
            if (data.success) {
                alert('模板保存成功' + (templateString !== this.buildTemplateString() ? '（已自动添加 /{filename}）' : ''));
                // 重新加载配置以获取最新的模板
                await this.loadConfig();
            } else {
                alert('保存模板失败: ' + data.error);
            }
        } catch (error) {
            console.error('保存模板失败:', error);
            alert('保存模板失败');
        }
    }

    buildTemplateString() {
        return this.templateComponents.map(component => {
            switch (component.type) {
                case 'variable':
                    return `{${component.name}}`;
                case 'separator':
                    return '/';
                case 'text':
                    return component.value || '';
                default:
                    return '';
            }
        }).join('');
    }

    async updatePathPreview() {
        const previewElement = document.getElementById('path-preview');
        
        if (this.templateComponents.length === 0) {
            previewElement.innerHTML = '<div class="preview-hint">模板构建完成后这里将显示路径预览</div>';
            return;
        }

        try {
            const templateString = this.buildTemplateString();
            const response = await fetch('/api/template-preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    template: templateString
                })
            });

            const data = await response.json();
            
            if (data.success) {
                // 处理路径预览，分隔符后换行，显示为目录树结构
                const previewPath = data.preview || '';
                const pathParts = previewPath.split('/').filter(part => part.length > 0);
                
                let previewHTML = '';
                if (pathParts.length > 0) {
                    previewHTML = pathParts.map((part, index) => {
                        const indent = '　'.repeat(index); // 使用全角空格缩进
                        const icon = index === pathParts.length - 1 ? '  ' : '> ';
                        return `${indent}${icon} ${part}`;
                    }).join('\n');
                } else {
                    previewHTML = '根目录';
                }
                
                previewElement.textContent = previewHTML;
            } else {
                previewElement.innerHTML = '<div class="preview-hint">预览生成失败: ' + (data.error || '未知错误') + '</div>';
            }
        } catch (error) {
            console.error('更新路径预览失败:', error);
            previewElement.innerHTML = '<div class="preview-hint">预览生成失败</div>';
        }
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();
            
            if (data.success) {
                // 更新输出目录
                if (data.config.target_folder) {
                    this.currentOutputDirectory = data.config.target_folder;
                    const outputElement = document.getElementById('output-path');
                    outputElement.innerHTML = `<span class="path-text">${this.currentOutputDirectory}</span>`;
                    outputElement.classList.add('selected');
                }
                
                // 更新模板（如果有的话）
                if (data.config.path_template) {
                    // 这里可以解析模板并更新UI，但目前我们暂时不自动更新模板编辑器
                    // 因为这可能会覆盖用户正在编辑的内容
                }
            }
        } catch (error) {
            console.error('加载配置失败:', error);
        }
    }

    async browseDirectory(inputId) {
        try {
            const response = await fetch('/api/browse-system', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'directory'
                })
            });

            const data = await response.json();
            
            if (data.success && data.path) {
                document.getElementById(inputId).value = data.path;
            } else {
                alert('目录选择失败: ' + (data.error || '未知错误'));
            }
        } catch (error) {
            console.error('系统文件浏览器失败:', error);
            alert('无法打开系统文件浏览器，请手动输入路径');
        }
    }

    async browseOutputDirectory() {
        try {
            const response = await fetch('/api/browse-system', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'directory'
                })
            });

            const data = await response.json();
            
            if (data.success && data.path) {
                this.currentOutputDirectory = data.path;
                document.getElementById('output-path').innerHTML = 
                    `<span class="path-text">${data.path}</span>`;
                await this.saveOutputDirectory();
            } else {
                alert('目录选择失败: ' + (data.error || '未知错误'));
            }
        } catch (error) {
            console.error('输出目录选择失败:', error);
            alert('无法打开系统文件浏览器，请检查系统支持');
        }
    }

    showFileDialog() {
        document.getElementById('file-dialog').style.display = 'flex';
    }

    hideFileDialog() {
        document.getElementById('file-dialog').style.display = 'none';
    }

    async scanFiles() {
        const directory = document.getElementById('scan-directory').value;
        const recursive = document.getElementById('recursive-scan').checked;

        if (!directory) {
            alert('请选择要扫描的目录');
            return;
        }

        try {
            this.showLoading(true);
            this.hideFileDialog();

            const response = await fetch('/api/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    directory: directory,
                    recursive: recursive
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.selectedFiles = data.files;
                this.renderFileList();
                this.updateFileStats();
                document.getElementById('process-files').disabled = false;
            } else {
                alert('扫描文件失败: ' + data.error);
            }
        } catch (error) {
            console.error('扫描文件失败:', error);
            alert('扫描文件失败');
        } finally {
            this.showLoading(false);
        }
    }

    renderFileList() {
        const list = document.getElementById('file-list');
        list.innerHTML = '';

        if (this.selectedFiles.length === 0) {
            list.innerHTML = '<div class="file-hint">未找到文件</div>';
            return;
        }

        this.selectedFiles.slice(0, 10).forEach(file => {
            const item = document.createElement('div');
            item.className = 'file-item';

            const icon = document.createElement('div');
            icon.className = 'file-icon';
            icon.textContent = 'FILE';
            item.appendChild(icon);

            const name = document.createElement('div');
            name.className = 'file-name';
            name.textContent = file.name;
            item.appendChild(name);

            const size = document.createElement('div');
            size.className = 'file-size';
            size.textContent = this.formatFileSize(file.size);
            item.appendChild(size);

            list.appendChild(item);
        });

        if (this.selectedFiles.length > 10) {
            const more = document.createElement('div');
            more.className = 'file-hint';
            more.textContent = `还有 ${this.selectedFiles.length - 10} 个文件...`;
            list.appendChild(more);
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    updateFileStats() {
        document.getElementById('total-files').textContent = this.selectedFiles.length;
        document.getElementById('processed-files').textContent = '0';
    }

    async processFiles() {
        if (this.selectedFiles.length === 0) {
            alert('请先扫描文件');
            return;
        }

        if (this.templateComponents.length === 0) {
            alert('请先构建路径模板');
            return;
        }

        try {
            this.showLoading(true);
            this.updateProgressBar(0, '开始处理...');

            // 使用后端处理文件
            const response = await fetch('/api/process-files', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    files: this.selectedFiles,
                    enable_hash: document.getElementById('enable-hash').checked
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showProcessResults(data);
                this.updateProgressBar(100, '处理完成!');
                document.getElementById('processed-files').textContent = data.completed_files;
                alert(`文件处理完成！共处理 ${data.total_files} 个文件，成功 ${data.completed_files} 个，失败 ${data.failed_files} 个`);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('处理文件失败:', error);
            alert('处理文件失败: ' + error.message);
            this.updateProgressBar(0, '处理失败');
        } finally {
            this.showLoading(false);
        }
    }

    showProcessResults(data) {
        const list = document.getElementById('file-list');
        list.innerHTML = '';

        if (data.results.length === 0) {
            list.innerHTML = '<div class="file-hint">没有处理结果</div>';
            return;
        }

        data.results.forEach(result => {
            const item = document.createElement('div');
            item.className = 'file-item ' + (result.success ? 'success' : 'failed');

            const icon = document.createElement('div');
            icon.className = 'file-icon';
            icon.textContent = result.success ? '成功' : '失败';
            item.appendChild(icon);

            const info = document.createElement('div');
            info.className = 'file-info';
            
            const name = document.createElement('div');
            name.className = 'file-name';
            name.textContent = result.source.split('/').pop();
            info.appendChild(name);

            if (!result.success) {
                const error = document.createElement('div');
                error.className = 'file-error';
                error.textContent = result.error;
                info.appendChild(error);
            }

            item.appendChild(info);

            const progress = document.createElement('div');
            progress.className = 'file-progress';
            progress.textContent = result.success ? '完成' : '失败';
            item.appendChild(progress);

            list.appendChild(item);
        });
    }

    updateProgressBar(percent, text) {
        const progressFill = document.querySelector('.progress-fill');
        const progressText = document.querySelector('.progress-text');
        
        progressFill.style.width = percent + '%';
        progressText.textContent = text;
    }

    showLoading(show) {
        document.getElementById('loading').style.display = show ? 'flex' : 'none';
    }

    showDropPlaceholders(e) {
        const templateComponents = document.querySelector('.template-components');
        if (!templateComponents) return;

        // 移除现有占位符
        this.removeDropPlaceholders();

        const rect = templateComponents.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // 找到最接近的插入位置
        const components = Array.from(templateComponents.children);
        let insertIndex = 0;
        let showPlaceholder = false;

        // 增加检测范围和阈值，减少抽搐
        const dropZoneThreshold = 20; // 20px的检测范围

        for (let i = 0; i < components.length; i++) {
            const component = components[i];
            if (component.classList.contains('add-component-btn')) continue;

            const componentRect = component.getBoundingClientRect();
            const componentX = componentRect.left - rect.left;
            const componentRight = componentX + componentRect.width;
            
            // 检查是否在组件之间的间隙附近
            if (i === 0 && x < componentX + dropZoneThreshold) {
                insertIndex = 0;
                showPlaceholder = true;
                break;
            } else if (x > componentRight - dropZoneThreshold && x < componentRight + dropZoneThreshold) {
                insertIndex = i + 1;
                showPlaceholder = true;
                break;
            }
        }

        // 如果在最后一个组件后面
        if (!showPlaceholder && components.length > 0) {
            const lastComponent = components[components.length - 1];
            if (!lastComponent.classList.contains('add-component-btn')) {
                const lastRect = lastComponent.getBoundingClientRect();
                const lastRight = lastRect.left - rect.left + lastRect.width;
                if (x > lastRight - dropZoneThreshold) {
                    insertIndex = components.length;
                    showPlaceholder = true;
                }
            }
        }

        // 如果没有组件或者鼠标在空白区域
        if (components.length === 0 || (x > dropZoneThreshold && !showPlaceholder)) {
            insertIndex = components.length;
            showPlaceholder = true;
        }

        // 只有在合适的位置才显示占位符
        if (showPlaceholder) {
            const placeholder = document.createElement('div');
            placeholder.className = 'drop-placeholder';
            placeholder.style.cssText = `
                width: 80px;
                height: 30px;
                border: 2px dashed var(--primary-color);
                border-radius: var(--border-radius);
                margin: 0 var(--spacing-xs);
                display: flex;
                align-items: center;
                justify-content: center;
                color: var(--primary-color);
                font-size: 0.8rem;
                background: rgba(64, 158, 255, 0.1);
            `;
            placeholder.textContent = '拖放到此';

            // 插入占位符
            const targetComponent = components[insertIndex];
            if (targetComponent) {
                templateComponents.insertBefore(placeholder, targetComponent);
            } else {
                templateComponents.appendChild(placeholder);
            }
        }
    }

    removeDropPlaceholders() {
        document.querySelectorAll('.drop-placeholder').forEach(el => el.remove());
    }

    getDropPosition(e) {
        const templateComponents = document.querySelector('.template-components');
        if (!templateComponents) return this.templateComponents.length;

        const placeholder = document.querySelector('.drop-placeholder');
        if (!placeholder) return this.templateComponents.length;

        // 计算占位符在组件中的位置
        const components = Array.from(templateComponents.children);
        return components.indexOf(placeholder);
    }

    async browseSystemFiles() {
        try {
            this.showLoading(true);
            
            const response = await fetch('/api/browse-system', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: 'files' })
            });

            const data = await response.json();
            
            if (data.success && data.paths && data.paths.length > 0) {
                // 将选择的文件路径转换为文件信息格式
                this.selectedFiles = data.paths.map(path => ({
                    path: path,
                    name: path.split('/').pop(),
                    size: 0  // 文件大小后续可以通过其他API获取
                }));
                
                this.renderFileList();
                this.updateFileStats();
                document.getElementById('process-files').disabled = false;
                this.hideFileDialog();
            } else {
                if (data.error === "User cancelled") {
                    // 用户取消，不显示错误
                } else {
                    alert('选择文件失败: ' + (data.error || '未知错误'));
                }
            }
        } catch (error) {
            console.error('选择文件失败:', error);
            alert('选择文件失败');
        } finally {
            this.showLoading(false);
        }
    }

    openPluginSettings(pluginName, webuiConfig) {
        this.showPluginModal(pluginName, webuiConfig);
    }

    showPluginModal(pluginName, webuiConfig) {
        // 创建模态背景
        const modalOverlay = document.createElement('div');
        modalOverlay.className = 'plugin-modal-overlay';
        modalOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        // 创建模态窗口
        const modal = document.createElement('div');
        modal.className = 'plugin-modal';
        modal.style.cssText = `
            background: var(--panel-color);
            border-radius: 12px;
            width: ${webuiConfig.width || 800}px;
            height: ${webuiConfig.height || 600}px;
            max-width: 90vw;
            max-height: 90vh;
            position: relative;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        `;

        // 创建标题栏
        const header = document.createElement('div');
        header.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            border-bottom: 1px solid var(--border-color);
            background: var(--bg-color);
            border-radius: 12px 12px 0 0;
        `;

        const title = document.createElement('h3');
        title.textContent = webuiConfig.title || `${pluginName} 设置`;
        title.style.cssText = `
            margin: 0;
            color: var(--primary-color);
            font-size: 16px;
        `;

        const closeBtn = document.createElement('button');
        closeBtn.textContent = '×';
        closeBtn.style.cssText = `
            background: none;
            border: none;
            color: var(--text-color);
            font-size: 24px;
            cursor: pointer;
            padding: 0;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
        `;
        closeBtn.onmouseover = () => closeBtn.style.background = 'rgba(255, 255, 255, 0.1)';
        closeBtn.onmouseout = () => closeBtn.style.background = 'none';
        closeBtn.onclick = () => this.closePluginModal();

        header.appendChild(title);
        header.appendChild(closeBtn);

        // 创建 iframe 容器
        const iframe = document.createElement('iframe');
        iframe.src = `/plugin/${pluginName}/${webuiConfig.path}/index.html`;
        iframe.style.cssText = `
            width: 100%;
            height: 100%;
            border: none;
            border-radius: 0 0 12px 12px;
        `;

        modal.appendChild(header);
        modal.appendChild(iframe);
        modalOverlay.appendChild(modal);

        // 添加到页面
        document.body.appendChild(modalOverlay);
        this.currentPluginModal = modalOverlay;

        // 点击背景关闭
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                this.closePluginModal();
            }
        });

        // ESC 键关闭
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                this.closePluginModal();
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);

        // 存储事件处理器以便清理
        modalOverlay._escapeHandler = handleEscape;
    }

    closePluginModal() {
        if (this.currentPluginModal) {
            // 清理事件监听器
            if (this.currentPluginModal._escapeHandler) {
                document.removeEventListener('keydown', this.currentPluginModal._escapeHandler);
            }
            
            // 移除模态窗口
            this.currentPluginModal.remove();
            this.currentPluginModal = null;
            
            // 重新加载变量（可能配置有变化）
            this.loadVariables();
        }
   }

    // 哈希算法状态管理方法
    async loadCurrentHashAlgorithm() {
        try {
            const response = await fetch('/api/hash-algorithms/current');
            const data = await response.json();
            
            if (data.success) {
                this.updateHashStatus(data.current_algorithm, data.enabled);
            } else {
                this.updateHashStatus('', false);
            }
        } catch (error) {
            console.error('加载当前哈希算法失败:', error);
            this.updateHashStatus('', false);
        }
    }

    updateHashStatus(algorithm, enabled) {
        const statusElement = document.getElementById('hash-status');
        const textElement = document.getElementById('hash-status-text');
        
        if (enabled && algorithm) {
            statusElement.className = 'hash-status enabled';
            textElement.textContent = algorithm.toUpperCase();
        } else {
            statusElement.className = 'hash-status disabled';
            textElement.textContent = '未启用';
        }
    }

    setupHashAlgorithmSelector() {
        const statusElement = document.getElementById('hash-status');
        const selectorElement = document.getElementById('hash-algorithm-selector');
        
        // 点击状态文字显示下拉框
        statusElement.addEventListener('click', () => {
            statusElement.style.display = 'none';
            selectorElement.style.display = 'block';
            selectorElement.focus();
        });
        
        // 选择算法后更新配置
        selectorElement.addEventListener('change', async () => {
            const selectedAlgorithm = selectorElement.value;
            await this.updateHashAlgorithm(selectedAlgorithm);
            this.hideHashSelector();
        });
        
        // 失去焦点时隐藏下拉框
        selectorElement.addEventListener('blur', () => {
            setTimeout(() => this.hideHashSelector(), 150);
        });
    }

    hideHashSelector() {
        const statusElement = document.getElementById('hash-status');
        const selectorElement = document.getElementById('hash-algorithm-selector');
        
        statusElement.style.display = 'block';
        selectorElement.style.display = 'none';
    }

    async updateHashAlgorithm(algorithm) {
        try {
            const response = await fetch('/api/hash-algorithms/current', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ algorithm: algorithm })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateHashStatus(data.current_algorithm, data.enabled);
            } else {
                alert('更新完整性校验算法失败: ' + data.error);
            }
        } catch (error) {
            console.error('更新哈希算法失败:', error);
            alert('更新完整性校验算法失败');
        }
    }

    async populateHashSelector() {
        try {
            const response = await fetch('/api/hash-algorithms');
            const data = await response.json();
            
            if (data.success) {
                const selectorElement = document.getElementById('hash-algorithm-selector');
                selectorElement.innerHTML = '';
                
                data.algorithms.forEach(algo => {
                    const option = document.createElement('option');
                    option.value = algo.value;
                    option.textContent = algo.name;
                    option.title = algo.description;
                    selectorElement.appendChild(option);
                });
            }
        } catch (error) {
            console.error('加载哈希算法列表失败:', error);
        }
    }

    async waitForConfiguration() {
        const maxAttempts = 60; // 最多等待60秒
        let attempts = 0;
        
        // 停止心跳包，避免干扰重启
        this.stopHeartbeat();
        
        const checkConfiguration = async () => {
            try {
                const response = await fetch('/api/configured', { 
                    method: 'GET',
                    cache: 'no-cache'
                });
                
                if (response.ok) {
                    // 配置完成，跳转到主界面
                    console.log('配置检查完成，准备重定向');
                    this.startHeartbeat();
                    this.redirectToMainInterface();
                    await this.loadVariables();
                    await this.loadOutputDirectory();
                    await this.loadCurrentHashAlgorithm();
                    await this.populateHashSelector();
                    return;
                }
            } catch (error) {
                // 服务器还未恢复或配置未完成，继续等待
            }
            
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(checkConfiguration, 1000); // 每秒检查一次
            } else {
                // 超时，重新刷新页面
                alert('配置检查超时，将重新刷新页面');
                window.location.reload();
            }
        };
        
        // 等待3秒后开始检查（给服务器重启时间）
        setTimeout(checkConfiguration, 3000);
    }

    redirectToMainInterface() {
        console.log('重定向到主界面');
        // 方法1：直接跳转到主界面
        // this.showMainInterface();
        
        // 方法2：如果需要完全刷新页面，可以使用：
        window.location.reload();
        
        // 方法3：如果需要跳转到特定URL，可以使用：
        // window.location.href = '/';
    }

    // ...existing code...
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new FileClassifierApp();
});
