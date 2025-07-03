// 全局变量
let currentConfig = {};

// DOM 元素
const elements = {
    enabled: document.getElementById('enabled'),
    description: document.getElementById('description'),
    tinyThreshold: document.getElementById('tiny_threshold'),
    smallThreshold: document.getElementById('small_threshold'),
    mediumThreshold: document.getElementById('medium_threshold'),
    largeThreshold: document.getElementById('large_threshold'),
    tinyDisplay: document.getElementById('tiny_display'),
    smallDisplay: document.getElementById('small_display'),
    mediumDisplay: document.getElementById('medium_display'),
    largeDisplay: document.getElementById('large_display'),
    labelTiny: document.getElementById('label_tiny'),
    labelSmall: document.getElementById('label_small'),
    labelMedium: document.getElementById('label_medium'),
    labelLarge: document.getElementById('label_large'),
    labelHuge: document.getElementById('label_huge'),
    labelUnknown: document.getElementById('label_unknown'),
    testFile: document.getElementById('test_file'),
    testBtn: document.getElementById('test-btn'),
    saveBtn: document.getElementById('save-btn'),
    resetBtn: document.getElementById('reset-btn'),
    message: document.getElementById('message'),
    testResult: document.getElementById('test-result'),
    presetDefault: document.getElementById('preset-default'),
    presetMedia: document.getElementById('preset-media'),
    presetDocument: document.getElementById('preset-document')
};

// 预设配置
const presets = {
    default: {
        tiny: 1024,        // 1KB
        small: 1048576,    // 1MB
        medium: 10485760,  // 10MB
        large: 104857600   // 100MB
    },
    media: {
        tiny: 102400,      // 100KB
        small: 5242880,    // 5MB
        medium: 52428800,  // 50MB
        large: 524288000   // 500MB
    },
    document: {
        tiny: 10240,       // 10KB
        small: 1048576,    // 1MB
        medium: 10485760,  // 10MB
        large: 52428800    // 50MB
    }
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
    
    // 预设按钮事件
    elements.presetDefault.addEventListener('click', () => applyPreset('default'));
    elements.presetMedia.addEventListener('click', () => applyPreset('media'));
    elements.presetDocument.addEventListener('click', () => applyPreset('document'));
    
    // 阈值输入事件
    const thresholdInputs = [elements.tinyThreshold, elements.smallThreshold, elements.mediumThreshold, elements.largeThreshold];
    thresholdInputs.forEach(input => {
        input.addEventListener('input', updateSizeDisplays);
        input.addEventListener('change', validateThresholds);
    });
}

// 加载配置
async function loadConfig() {
    try {
        showMessage('正在加载配置...', 'info');
        
        const response = await fetch('/api/plugin/file_size_classifier/get_plugin_config', {
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
        elements.enabled.checked = config.enabled !== false;
        elements.description.value = config.description || '';
        
        // 更新阈值
        const thresholds = config.thresholds || presets.default;
        elements.tinyThreshold.value = thresholds.tiny || 1024;
        elements.smallThreshold.value = thresholds.small || 1048576;
        elements.mediumThreshold.value = thresholds.medium || 10485760;
        elements.largeThreshold.value = thresholds.large || 104857600;
        
        // 更新标签
        const labels = config.labels || {};
        elements.labelTiny.value = labels.tiny || '微型文件';
        elements.labelSmall.value = labels.small || '小文件';
        elements.labelMedium.value = labels.medium || '中等文件';
        elements.labelLarge.value = labels.large || '大文件';
        elements.labelHuge.value = labels.huge || '巨型文件';
        elements.labelUnknown.value = labels.unknown || '未知';
        
        updateSizeDisplays();
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
            description: elements.description.value.trim(),
            thresholds: {
                tiny: parseInt(elements.tinyThreshold.value),
                small: parseInt(elements.smallThreshold.value),
                medium: parseInt(elements.mediumThreshold.value),
                large: parseInt(elements.largeThreshold.value)
            },
            labels: {
                tiny: elements.labelTiny.value.trim(),
                small: elements.labelSmall.value.trim(),
                medium: elements.labelMedium.value.trim(),
                large: elements.labelLarge.value.trim(),
                huge: elements.labelHuge.value.trim(),
                unknown: elements.labelUnknown.value.trim()
            }
        };
        
        // 验证阈值
        if (!validateThresholds()) {
            throw new Error('阈值验证失败，请检查阈值大小关系');
        }
        
        showMessage('正在保存配置...', 'info');
        
        const response = await fetch('/api/plugin/file_size_classifier/update_plugin_config', {
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
        
        const response = await fetch('/api/plugin/file_size_classifier/test_file_size', {
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
            content += `<div class="result-grid">`;
            content += `<div class="result-item"><strong>分类:</strong> ${result.result}</div>`;
            content += `<div class="result-item"><strong>标签:</strong> ${result.label}</div>`;
            content += `<div class="result-item"><strong>文件大小:</strong> ${result.file_size_formatted}</div>`;
            content += `<div class="result-item"><strong>字节数:</strong> ${result.file_size.toLocaleString()}</div>`;
            content += `</div>`;
            
            if (result.threshold_info) {
                content += `<div class="threshold-comparison">`;
                content += `<h5>阈值比较</h5>`;
                for (const [name, info] of Object.entries(result.threshold_info)) {
                    const status = info.under_threshold ? 'under' : 'over';
                    const statusText = info.under_threshold ? '小于' : '大于等于';
                    content += `<div class="comparison-item">`;
                    content += `<span>${name} (${info.threshold_formatted})</span>`;
                    content += `<span class="status ${status}">${statusText}</span>`;
                    content += `</div>`;
                }
                content += `</div>`;
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

// 应用预设
function applyPreset(presetName) {
    const preset = presets[presetName];
    if (!preset) return;
    
    elements.tinyThreshold.value = preset.tiny;
    elements.smallThreshold.value = preset.small;
    elements.mediumThreshold.value = preset.medium;
    elements.largeThreshold.value = preset.large;
    
    updateSizeDisplays();
    validateThresholds();
    
    showMessage(`已应用${presetName}预设`, 'info');
    setTimeout(() => hideMessage(), 1500);
}

// 更新大小显示
function updateSizeDisplays() {
    elements.tinyDisplay.textContent = formatFileSize(parseInt(elements.tinyThreshold.value) || 0);
    elements.smallDisplay.textContent = formatFileSize(parseInt(elements.smallThreshold.value) || 0);
    elements.mediumDisplay.textContent = formatFileSize(parseInt(elements.mediumThreshold.value) || 0);
    elements.largeDisplay.textContent = formatFileSize(parseInt(elements.largeThreshold.value) || 0);
}

// 验证阈值
function validateThresholds() {
    const tiny = parseInt(elements.tinyThreshold.value) || 0;
    const small = parseInt(elements.smallThreshold.value) || 0;
    const medium = parseInt(elements.mediumThreshold.value) || 0;
    const large = parseInt(elements.largeThreshold.value) || 0;
    
    const isValid = tiny < small && small < medium && medium < large;
    
    const inputs = [elements.tinyThreshold, elements.smallThreshold, elements.mediumThreshold, elements.largeThreshold];
    inputs.forEach(input => {
        input.style.borderColor = isValid ? '#28a745' : '#dc3545';
    });
    
    return isValid;
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
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 工具函数：清空表单
function clearForm() {
    elements.enabled.checked = true;
    elements.description.value = '';
    elements.tinyThreshold.value = '1024';
    elements.smallThreshold.value = '1048576';
    elements.mediumThreshold.value = '10485760';
    elements.largeThreshold.value = '104857600';
    elements.labelTiny.value = '微型文件';
    elements.labelSmall.value = '小文件';
    elements.labelMedium.value = '中等文件';
    elements.labelLarge.value = '大文件';
    elements.labelHuge.value = '巨型文件';
    elements.labelUnknown.value = '未知';
    elements.testFile.value = '';
    updateSizeDisplays();
    hideMessage();
    elements.testResult.style.display = 'none';
}
