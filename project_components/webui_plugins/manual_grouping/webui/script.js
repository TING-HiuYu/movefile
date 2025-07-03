// 手动分组插件 Web UI 脚本
class ManualGroupingUI {
    constructor() {
        this.groups = [];
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadConfig();
    }

    bindEvents() {
        // 主要操作按钮
        document.getElementById('add-group-btn').addEventListener('click', () => this.addGroup());
        document.getElementById('test-config-btn').addEventListener('click', () => this.toggleTestSection());
        document.getElementById('clear-all-btn').addEventListener('click', () => this.clearAllGroups());
        
        // 测试相关
        document.getElementById('run-test-btn').addEventListener('click', () => this.runTest());
        
        // 底部按钮
        document.getElementById('save-btn').addEventListener('click', () => this.saveConfig());
        document.getElementById('cancel-btn').addEventListener('click', () => this.cancel());
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/plugin/manual_grouping/config');
            const data = await response.json();
            
            if (data.success && data.config && data.config.groups) {
                this.groups = data.config.groups;
                this.renderGroups();
            } else {
                // 没有配置或配置为空，显示默认空状态
                this.groups = [];
                this.renderGroups();
            }
        } catch (error) {
            console.error('加载配置失败:', error);
            this.showMessage('加载配置失败: ' + error.message, 'error');
        }
    }

    addGroup() {
        const newGroup = {
            name: '新分组',
            strategies: []
        };
        this.groups.push(newGroup);
        this.renderGroups();
    }

    deleteGroup(index) {
        if (confirm(`确定要删除分组 "${this.groups[index].name}" 吗？`)) {
            this.groups.splice(index, 1);
            this.renderGroups();
        }
    }

    addStrategy(groupIndex) {
        const newStrategy = {
            type: 'contains',
            pattern: '',
            range_filter: ''
        };
        this.groups[groupIndex].strategies.push(newStrategy);
        this.renderGroups();
    }

    deleteStrategy(groupIndex, strategyIndex) {
        if (confirm('确定要删除此策略吗？')) {
            this.groups[groupIndex].strategies.splice(strategyIndex, 1);
            this.renderGroups();
        }
    }

    renderGroups() {
        const container = document.getElementById('groups-container');
        container.innerHTML = '';

        if (this.groups.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="text-align: center; padding: 40px; color: var(--text-muted);">
                    <p>暂无分组配置</p>
                    <p style="font-size: 0.9rem; margin-top: 8px;">点击"新建分组"开始配置</p>
                </div>
            `;
            return;
        }

        this.groups.forEach((group, groupIndex) => {
            const groupElement = this.createGroupElement(group, groupIndex);
            container.appendChild(groupElement);
        });
    }

    createGroupElement(group, groupIndex) {
        const groupDiv = document.createElement('div');
        groupDiv.className = 'strategy-group';
        
        groupDiv.innerHTML = `
            <div class="group-header">
                <div class="group-title">分组 ${groupIndex + 1}</div>
                <input type="text" class="group-name-input" value="${group.name}" 
                       placeholder="输入分组名称" data-group="${groupIndex}">
                <div class="group-actions">
                    <button class="btn small success" onclick="manualGroupingUI.addStrategy(${groupIndex})">
                        添加策略
                    </button>
                    <button class="btn small danger" onclick="manualGroupingUI.deleteGroup(${groupIndex})">
                        删除分组
                    </button>
                </div>
            </div>
            <div class="strategies-list" id="strategies-${groupIndex}">
                ${this.renderStrategies(group.strategies, groupIndex)}
            </div>
        `;

        // 绑定分组名称输入事件
        const nameInput = groupDiv.querySelector('.group-name-input');
        nameInput.addEventListener('input', (e) => {
            this.groups[groupIndex].name = e.target.value;
        });

        return groupDiv;
    }

    renderStrategies(strategies, groupIndex) {
        if (strategies.length === 0) {
            return `
                <button class="add-strategy-btn" onclick="manualGroupingUI.addStrategy(${groupIndex})">
                    点击添加第一个策略
                </button>
            `;
        }

        let html = '';
        strategies.forEach((strategy, strategyIndex) => {
            html += this.createStrategyHTML(strategy, groupIndex, strategyIndex);
        });

        html += `
            <button class="add-strategy-btn" onclick="manualGroupingUI.addStrategy(${groupIndex})">
                添加更多策略
            </button>
        `;

        return html;
    }

    createStrategyHTML(strategy, groupIndex, strategyIndex) {
        const rangeFilterVisible = strategy.type === 'wildcard' ? 'visible' : '';
        
        return `
            <div class="strategy-item">
                <button class="strategy-delete" onclick="manualGroupingUI.deleteStrategy(${groupIndex}, ${strategyIndex})">
                    ×
                </button>
                <div class="strategy-header">
                    <label>策略 ${strategyIndex + 1}:</label>
                    <select class="strategy-type-select" data-group="${groupIndex}" data-strategy="${strategyIndex}">
                        <option value="contains" ${strategy.type === 'contains' ? 'selected' : ''}>包含字符串</option>
                        <option value="wildcard" ${strategy.type === 'wildcard' ? 'selected' : ''}>通配符</option>
                        <option value="regex" ${strategy.type === 'regex' ? 'selected' : ''}>正则表达式</option>
                    </select>
                </div>
                <div class="strategy-inputs">
                    <div class="input-group">
                        <label>匹配内容:</label>
                        <input type="text" placeholder="${this.getPlaceholder(strategy.type)}" 
                               value="${strategy.pattern}" 
                               data-group="${groupIndex}" data-strategy="${strategyIndex}" data-field="pattern">
                    </div>
                    <div class="input-group range-filter-group ${rangeFilterVisible}" data-group="${groupIndex}" data-strategy="${strategyIndex}">
                        <label>数值范围:</label>
                        <input type="text" placeholder="如: {100-111},{jpg,png}" 
                               value="${strategy.range_filter || ''}"
                               data-group="${groupIndex}" data-strategy="${strategyIndex}" data-field="range_filter">
                    </div>
                </div>
            </div>
        `;
    }

    getPlaceholder(type) {
        switch (type) {
            case 'contains':
                return '输入要包含的字符串，如: IMG_';
            case 'wildcard':
                return '使用通配符，如: *.jpg, *_1920*';
            case 'regex':
                return '输入正则表达式，如: ^IMG_\\d+\\.jpg$';
            default:
                return '';
        }
    }

    // 为了方便事件绑定，将事件处理放在 renderGroups 后统一绑定
    bindGroupEvents() {
        // 策略类型选择变更
        document.querySelectorAll('.strategy-type-select').forEach(select => {
            select.addEventListener('change', (e) => {
                const groupIndex = parseInt(e.target.dataset.group);
                const strategyIndex = parseInt(e.target.dataset.strategy);
                const newType = e.target.value;
                
                this.groups[groupIndex].strategies[strategyIndex].type = newType;
                
                // 更新对应的输入框占位符和范围过滤器显示
                const strategyItem = e.target.closest('.strategy-item');
                const patternInput = strategyItem.querySelector('[data-field="pattern"]');
                const rangeFilterGroup = strategyItem.querySelector('.range-filter-group');
                
                patternInput.placeholder = this.getPlaceholder(newType);
                
                if (newType === 'wildcard') {
                    rangeFilterGroup.classList.add('visible');
                } else {
                    rangeFilterGroup.classList.remove('visible');
                    this.groups[groupIndex].strategies[strategyIndex].range_filter = '';
                }
            });
        });

        // 策略输入框变更
        document.querySelectorAll('.strategy-inputs input').forEach(input => {
            input.addEventListener('input', (e) => {
                const groupIndex = parseInt(e.target.dataset.group);
                const strategyIndex = parseInt(e.target.dataset.strategy);
                const field = e.target.dataset.field;
                
                this.groups[groupIndex].strategies[strategyIndex][field] = e.target.value;
            });
        });
    }

    // 重新渲染后重新绑定事件
    renderGroups() {
        const container = document.getElementById('groups-container');
        container.innerHTML = '';

        if (this.groups.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="text-align: center; padding: 40px; color: var(--text-muted);">
                    <p>暂无分组配置</p>
                    <p style="font-size: 0.9rem; margin-top: 8px;">点击"新建分组"开始配置</p>
                </div>
            `;
            return;
        }

        this.groups.forEach((group, groupIndex) => {
            const groupElement = this.createGroupElement(group, groupIndex);
            container.appendChild(groupElement);
        });

        // 重新绑定事件
        this.bindGroupEvents();
    }

    clearAllGroups() {
        if (this.groups.length === 0) {
            this.showMessage('当前没有分组可清空', 'info');
            return;
        }

        if (confirm(`确定要清空所有 ${this.groups.length} 个分组吗？\n此操作不可撤销！`)) {
            this.groups = [];
            this.renderGroups();
            this.showMessage('所有分组已清空', 'success');
        }
    }

    toggleTestSection() {
        const testSection = document.getElementById('test-section');
        const isVisible = testSection.style.display !== 'none';
        
        if (isVisible) {
            testSection.style.display = 'none';
            document.getElementById('test-config-btn').textContent = '测试配置';
        } else {
            testSection.style.display = 'block';
            document.getElementById('test-config-btn').textContent = '隐藏测试';
        }
    }

    async runTest() {
        const testFiles = document.getElementById('test-files').value.trim();
        if (!testFiles) {
            this.showMessage('请输入测试文件名', 'warning');
            return;
        }

        const fileList = testFiles.split('\n').map(line => line.trim()).filter(line => line);
        
        if (fileList.length === 0) {
            this.showMessage('请输入有效的测试文件名', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/plugin/manual_grouping/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    config: { groups: this.groups },
                    test_files: fileList
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.displayTestResults(data.results);
            } else {
                this.showMessage('测试失败: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('测试失败:', error);
            this.showMessage('测试请求失败: ' + error.message, 'error');
        }
    }

    displayTestResults(results) {
        const resultsContainer = document.getElementById('test-results');
        let html = '<h4>测试结果：</h4><pre>';
        
        let matchedCount = 0;
        const totalCount = Object.keys(results).length;
        
        for (const [filename, groups] of Object.entries(results)) {
            if (groups.length > 0) {
                html += `<div class="test-result-success">✓ ${filename} → ${groups.join(', ')}</div>`;
                matchedCount++;
            } else {
                html += `<div class="test-result-fail">✗ ${filename} → (未匹配)</div>`;
            }
        }
        
        html += '</pre>';
        html += `<p><strong>匹配率: ${matchedCount}/${totalCount} (${(matchedCount/totalCount*100).toFixed(1)}%)</strong></p>`;
        
        resultsContainer.innerHTML = html;
    }

    async saveConfig() {
        // 验证配置
        const validGroups = this.groups.filter(group => {
            return group.name.trim() && group.strategies.some(strategy => strategy.pattern.trim());
        });

        if (validGroups.length === 0) {
            this.showMessage('请至少配置一个有效的分组', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/plugin/manual_grouping/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    config: { groups: validGroups }
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showMessage(`配置保存成功！已保存 ${validGroups.length} 个分组`, 'success');
                // 通知父窗口配置已保存
                if (window.parent && window.parent.closePluginModal) {
                    setTimeout(() => {
                        window.parent.closePluginModal();
                    }, 1500);
                }
            } else {
                this.showMessage('保存失败: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('保存失败:', error);
            this.showMessage('保存请求失败: ' + error.message, 'error');
        }
    }

    cancel() {
        if (window.parent && window.parent.closePluginModal) {
            window.parent.closePluginModal();
        }
    }

    showMessage(message, type = 'info') {
        // 创建临时消息提示
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        
        switch (type) {
            case 'success':
                messageDiv.style.background = 'var(--secondary-color)';
                break;
            case 'error':
                messageDiv.style.background = 'var(--danger-color)';
                break;
            case 'warning':
                messageDiv.style.background = 'var(--warning-color)';
                break;
            default:
                messageDiv.style.background = 'var(--info-color)';
        }
        
        messageDiv.textContent = message;
        document.body.appendChild(messageDiv);
        
        // 3秒后自动移除
        setTimeout(() => {
            messageDiv.remove();
        }, 3000);
    }
}

// 全局实例
let manualGroupingUI;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    manualGroupingUI = new ManualGroupingUI();
});

// 添加滑入动画
const style = document.createElement('style');
style.textContent = `
@keyframes slideIn {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}
`;
document.head.appendChild(style);
