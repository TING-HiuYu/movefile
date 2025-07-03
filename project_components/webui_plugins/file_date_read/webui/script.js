// 全局变量
let currentConfig = {};

// DOM 元素
const elements = {
    enabled: document.getElementById('enabled'),
    fallbackToMtime: document.getElementById('fallback_to_mtime'),
    dateFormat: document.getElementById('date_format'),
    description: document.getElementById('description'),
    testFile: document.getElementById('test_file'),
    testBtn: document.getElementById('test-btn'),
    saveBtn: document.getElementById('save-btn'),
    resetBtn: document.getElementById('reset-btn'),
    message: document.getElementById('message'),
    testResult: document.getElementById('test-result')
};

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    loadConfig();
    bindEvents();
});

// 绑定事件
function bindEvents() {
    elements.saveBtn.addEventListener('click', saveConfig);
    elements.resetBtn.addEventListener('click', loadConfig);
    elements.testBtn.addEventListener('click', testFile);
    
    // 输入验证
    elements.dateFormat.addEventListener('input', validateDateFormat);
}

// 加载配置
async function loadConfig() {
    try {
        showMessage('正在加载配置...', 'info');
        
        const response = await fetch('/api/plugin/file_date_read/get_plugin_config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const config = await response.json();
        currentConfig = config;
        
        // 更新界面
        elements.enabled.checked = config.enabled || false;
        elements.fallbackToMtime.checked = config.fallback_to_mtime !== false;
        elements.dateFormat.value = config.date_format || '%Y-%m-%d';
        elements.description.value = config.description || '';
        
        showMessage('配置加载成功', 'success');
        setTimeout(() => hideMessage(), 2000);
        
    } catch (error) {
        console.error('加载配置失败:', error);
        showMessage(`加载配置失败: ${error.message}`, 'error');
    }
}

// 保存配置
async function saveConfig() {
    try {
        const newConfig = {
            enabled: elements.enabled.checked,
            fallback_to_mtime: elements.fallbackToMtime.checked,
            date_format: elements.dateFormat.value.trim(),
            description: elements.description.value.trim()
        };
        
        // 验证日期格式
        if (!newConfig.date_format) {
            throw new Error('日期格式不能为空');
        }
        
        showMessage('正在保存配置...', 'info');
        
        const response = await fetch('/api/plugin/file_date_read/update_plugin_config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(newConfig)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            currentConfig = newConfig;
            showMessage('配置保存成功', 'success');
        } else {
            throw new Error(result.message || '保存失败');
        }
        
    } catch (error) {
        console.error('保存配置失败:', error);
        showMessage(`保存配置失败: ${error.message}`, 'error');
    }
}

// 测试文件
async function testFile() {
    const filepath = elements.testFile.value.trim();
    if (!filepath) {
        showTestResult('请输入文件路径', 'error');
        return;
    }
    
    try {
        elements.testBtn.disabled = true;
        elements.testBtn.textContent = '测试中...';
        
        const response = await fetch('/api/plugin/file_date_read/test_file_date', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filepath: filepath })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            let content = `<h4>测试结果</h4>`;
            content += `<p><strong>提取的日期:</strong> ${result.result}</p>`;
            if (result.file_info) {
                content += `<p><strong>文件大小:</strong> ${formatFileSize(result.file_info.size)}</p>`;
                content += `<p><strong>修改时间:</strong> ${result.file_info.mtime}</p>`;
            }
            if (result.exif_date) {
                content += `<p><strong>EXIF日期:</strong> ${result.exif_date}</p>`;
            } else {
                content += `<p><strong>EXIF信息:</strong> 无</p>`;
            }
            
            showTestResult(content, 'success');
        } else {
            showTestResult(result.message || '测试失败', 'error');
        }
        
    } catch (error) {
        console.error('测试失败:', error);
        showTestResult(`测试失败: ${error.message}`, 'error');
    } finally {
        elements.testBtn.disabled = false;
        elements.testBtn.textContent = '测试';
    }
}

// 验证日期格式
function validateDateFormat() {
    const format = elements.dateFormat.value.trim();
    if (!format) {
        elements.dateFormat.style.borderColor = '#dc3545';
        return false;
    }
    
    // 简单验证是否包含合法的格式字符
    if (format.includes('%Y') || format.includes('%m') || format.includes('%d')) {
        elements.dateFormat.style.borderColor = '#28a745';
        return true;
    } else {
        elements.dateFormat.style.borderColor = '#ffc107';
        return true; // 允许但提示
    }
}

// 显示消息
function showMessage(text, type) {
    elements.message.textContent = text;
    elements.message.className = `message ${type}`;
    elements.message.style.display = 'block';
}

// 隐藏消息
function hideMessage() {
    elements.message.style.display = 'none';
}

// 显示测试结果
function showTestResult(content, type) {
    elements.testResult.innerHTML = content;
    elements.testResult.className = `test-result ${type}`;
    elements.testResult.style.display = 'block';
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 工具函数：清空表单
function clearForm() {
    elements.enabled.checked = true;
    elements.fallbackToMtime.checked = true;
    elements.dateFormat.value = '%Y-%m-%d';
    elements.description.value = '';
    elements.testFile.value = '';
    hideMessage();
    elements.testResult.style.display = 'none';
}
