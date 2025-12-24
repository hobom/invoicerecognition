// 获取 DOM 元素
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const folderInput = document.getElementById('folderInput');
const fileName = document.getElementById('fileName');
const fileList = document.getElementById('fileList');
const form = document.getElementById('uploadForm');
const loading = document.getElementById('loading');
const progress = document.getElementById('progress');
const progressText = document.getElementById('progressText');
const progressFill = document.getElementById('progressFill');
const result = document.getElementById('result');
const error = document.getElementById('error');
const submitBtn = document.getElementById('submitBtn');

let selectedFiles = [];

// 更新文件列表显示
function updateFileList() {
    if (selectedFiles.length === 0) {
        fileName.textContent = '';
        fileList.innerHTML = '';
        return;
    }
    
    if (selectedFiles.length === 1) {
        fileName.textContent = `已选择: ${selectedFiles[0].name}`;
        fileList.innerHTML = '';
    } else {
        fileName.textContent = `已选择 ${selectedFiles.length} 个文件`;
        fileList.innerHTML = selectedFiles.slice(0, 10).map(f => 
            `<div class="file-item">${f.name}</div>`
        ).join('');
        if (selectedFiles.length > 10) {
            fileList.innerHTML += `<div class="file-item">... 还有 ${selectedFiles.length - 10} 个文件</div>`;
        }
    }
}

// 拖拽上传事件处理
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files).filter(f => 
        f.type.startsWith('image/')
    );
    if (files.length > 0) {
        selectedFiles = files;
        updateFileList();
    }
});

// 文件选择事件处理
fileInput.addEventListener('change', (e) => {
    selectedFiles = Array.from(e.target.files);
    updateFileList();
});

folderInput.addEventListener('change', (e) => {
    selectedFiles = Array.from(e.target.files).filter(f => 
        f.type.startsWith('image/')
    );
    updateFileList();
});

// 表单提交事件处理
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (selectedFiles.length === 0) {
        showError('请选择要上传的文件');
        return;
    }
    
    const formData = new FormData();
    
    // 多文件上传 - 使用流式接口获取进度
    if (selectedFiles.length > 1) {
        selectedFiles.forEach(file => {
            formData.append('files[]', file);
        });
        
        formData.append('save_json', form.save_json.checked);
        formData.append('save_db', form.save_db.checked);
        
        // 显示加载状态
        loading.classList.add('show');
        progress.classList.add('show');
        result.classList.remove('show');
        error.classList.remove('show');
        submitBtn.disabled = true;
        
        // 更新进度
        updateProgress(0);
        
        // 使用流式接口
        try {
            const response = await fetch('/api/predict/stream', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('请求失败');
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let finalData = null;
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // 保留最后一个不完整的行
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.type === 'start') {
                                updateProgress(0);
                            } else if (data.type === 'progress') {
                                updateProgress(data.percent);
                                // 可选：显示当前处理的文件
                                if (data.file) {
                                    progressText.textContent = `${data.percent}% - 正在处理: ${data.file}`;
                                }
                            } else if (data.type === 'complete') {
                                updateProgress(100);
                                finalData = data;
                                showBatchResult({
                                    success: true,
                                    total: data.total,
                                    success_count: data.success_count,
                                    failed_count: data.failed_count,
                                    data: data.data
                                });
                            } else if (data.type === 'error') {
                                showError(data.message || '处理失败');
                                break;
                            }
                        } catch (e) {
                            console.error('解析进度数据失败:', e);
                        }
                    }
                }
            }
            
            if (!finalData) {
                showError('处理未完成');
            }
        } catch (err) {
            showError('网络错误: ' + err.message);
        } finally {
            loading.classList.remove('show');
            progress.classList.remove('show');
            submitBtn.disabled = false;
            progressText.textContent = '0%';
        }
    } else {
        // 单文件上传 - 使用普通接口
        formData.append('file', selectedFiles[0]);
        formData.append('save_json', form.save_json.checked);
        formData.append('save_db', form.save_db.checked);
        
        // 显示加载状态
        loading.classList.add('show');
        progress.classList.add('show');
        result.classList.remove('show');
        error.classList.remove('show');
        submitBtn.disabled = true;
        
        // 更新进度
        updateProgress(0);
        
        try {
            const response = await fetch('/api/predict', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                updateProgress(100);
                showResult(data.data);
            } else {
                showError(data.error || '识别失败');
            }
        } catch (err) {
            showError('网络错误: ' + err.message);
        } finally {
            loading.classList.remove('show');
            progress.classList.remove('show');
            submitBtn.disabled = false;
        }
    }
});

// 更新进度条
function updateProgress(percent) {
    const percentValue = Math.min(100, Math.max(0, percent));
    progressFill.style.width = `${percentValue}%`;
    progressFill.textContent = `${percentValue}%`;
    // 如果progressText没有显示文件名，则更新百分比
    if (!progressText.textContent.includes('正在处理:')) {
        progressText.textContent = `${percentValue}%`;
    }
}

// 显示单个结果
function showResult(data) {
    const content = document.getElementById('resultContent');
    let html = `<p><strong>图片名称:</strong> ${data.image_name}</p>`;
    html += `<p><strong>检测项数:</strong> ${data.检测项数}</p>`;
    html += '<h3 style="margin-top: 20px;">检测详情:</h3>';
    
    data.detections.forEach(det => {
        html += `<div class="result-item">`;
        html += `<strong>${det.class_name}</strong> (置信度: ${(det.confidence * 100).toFixed(2)}%)<br>`;
        if (det.extracted_text) {
            const text = Array.isArray(det.extracted_text) 
                ? det.extracted_text.join(', ') 
                : det.extracted_text;
            html += `识别内容: ${text}`;
        } else {
            html += `识别内容: 无`;
        }
        html += `</div>`;
    });
    
    content.innerHTML = html;
    result.classList.add('show');
}

// 显示批量结果
function showBatchResult(data) {
    const content = document.getElementById('resultContent');
    let html = `<div class="batch-summary">`;
    html += `<p><strong>总计:</strong> ${data.total} 个文件</p>`;
    html += `<p><strong>成功:</strong> <span style="color: #28a745;">${data.success_count}</span> 个</p>`;
    html += `<p><strong>失败:</strong> <span style="color: #dc3545;">${data.failed_count}</span> 个</p>`;
    html += `</div>`;
    
    html += '<h3 style="margin-top: 20px;">处理详情:</h3>';
    
    data.data.forEach((item, index) => {
        if (item.success) {
            html += `<div class="result-item success">`;
            html += `<p><strong>${index + 1}. ${item.file}</strong> ✅</p>`;
            html += `<p>检测项数: ${item.result.检测项数}</p>`;
            html += `</div>`;
        } else {
            html += `<div class="result-item failed">`;
            html += `<p><strong>${index + 1}. ${item.file}</strong> ❌</p>`;
            html += `<p>错误: ${item.error}</p>`;
            html += `</div>`;
        }
    });
    
    content.innerHTML = html;
    result.classList.add('show');
}

// 显示错误信息
function showError(message) {
    error.textContent = message;
    error.classList.add('show');
}

