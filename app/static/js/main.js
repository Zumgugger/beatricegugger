// Main JavaScript for public site

// Hamburger menu toggle
document.addEventListener('DOMContentLoaded', function() {
    const hamburger = document.getElementById('hamburger');
    const navMenu = document.getElementById('navMenu');
    
    if (hamburger && navMenu) {
        hamburger.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            if (!hamburger.contains(event.target) && !navMenu.contains(event.target)) {
                navMenu.classList.remove('active');
            }
        });
    }
    
    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.transition = 'opacity 0.5s';
            message.style.opacity = '0';
            setTimeout(function() {
                message.remove();
            }, 500);
        }, 5000);
    });

    // Inline editing for admins
    const isAdmin = document.body.dataset.isAdmin === '1';
    if (isAdmin) {
        enableInlineEditing();
    }
});


function enableInlineEditing() {
    const notice = createNotice();

    // Text editing
    document.querySelectorAll('.editable-text').forEach((el) => {
        el.setAttribute('contenteditable', 'true');
        el.addEventListener('blur', async () => {
            const entity = el.dataset.entity;
            const id = el.dataset.entityId;
            const field = el.dataset.field || 'content';
            // Use textContent for title/subtitle (plain text), innerHTML for content (rich text)
            const isPlainText = field === 'title' || field === 'subtitle';
            const content = isPlainText ? el.textContent.trim() : el.innerHTML.trim();
            const url = buildTextEndpoint(entity, id);
            if (!url) return;
            
            let payload = {};
            payload[field] = content;
            
            try {
                await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                showNotice(notice, 'Gespeichert');
            } catch (err) {
                console.error(err);
                showNotice(notice, 'Speichern fehlgeschlagen', true);
            }
        });
    });

    // Image editing
    document.querySelectorAll('.editable-image').forEach((wrapper) => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.style.display = 'none';
        document.body.appendChild(input);

        input.addEventListener('change', async () => {
            console.log('File selected:', input.files);
            if (!input.files.length) return;
            let file = input.files[0];
            const entity = wrapper.dataset.entity;
            const id = wrapper.dataset.entityId;
            console.log('Uploading for entity:', entity, 'id:', id);
            const url = buildImageEndpoint(entity, id);
            console.log('Upload URL:', url);
            if (!url) return;

            // Check image size before upload
            const checkResult = await checkImageSize(file, entity);
            
            const doUpload = async (uploadFile) => {
                const formData = new FormData();
                formData.append('image', uploadFile);
                try {
                    console.log('Sending fetch...');
                    const resp = await fetch(url, { method: 'POST', body: formData });
                    const data = await resp.json();
                    console.log('Response:', data);
                    if (data.success && data.image_path) {
                        let img = wrapper.querySelector('img');
                        if (!img) {
                            img = document.createElement('img');
                            wrapper.innerHTML = '';
                            wrapper.appendChild(img);
                        }
                        img.src = `/uploads/${data.image_path}?t=${Date.now()}`;
                        img.alt = data.title || 'Uploaded image';
                        showNotice(notice, 'Bild aktualisiert');
                    } else {
                        showNotice(notice, data.message || 'Fehler beim Hochladen', true);
                    }
                } catch (err) {
                    console.error('Upload error:', err);
                    showNotice(notice, 'Bild konnte nicht gespeichert werden', true);
                } finally {
                    input.value = '';
                }
            };
            
            // Show warning if image doesn't meet standards
            if (checkResult.warnings.length > 0) {
                showImageWarning(
                    checkResult,
                    // Continue with original
                    () => doUpload(file),
                    // Cancel
                    () => { input.value = ''; },
                    // Optimize and upload
                    async () => {
                        const result = await optimizeImage(file, checkResult.standard);
                        showOptimizationSuccess(result, notice);
                        await doUpload(result.file);
                    }
                );
            } else {
                doUpload(file);
            }
        });

        wrapper.addEventListener('click', (e) => {
            console.log('Image clicked:', wrapper.dataset);
            e.preventDefault();
            e.stopPropagation();
            input.click();
        });
    });
}


function buildTextEndpoint(entity, id) {
    if (!entity || !id) return null;
    if (entity === 'page') {
        return `/admin/api/page/${id}/content`;
    }
    if (entity === 'course') {
        return `/admin/api/course/${id}/content`;
    }
    if (entity === 'art-category') {
        return `/admin/api/art-category/${id}/content`;
    }
    if (entity === 'workshop-category') {
        return `/admin/api/workshop-category/${id}/content`;
    }
    return null;
}

function buildImageEndpoint(entity, id) {
    if (!entity || !id) return null;
    if (entity === 'page') {
        return `/admin/api/page/${id}/image`;
    }
    if (entity === 'course') {
        return `/admin/api/course/${id}/image`;
    }
    if (entity === 'art-category') {
        return `/admin/api/art-category/${id}/image`;
    }
    if (entity === 'workshop-category') {
        return `/admin/api/workshop-category/${id}/image`;
    }
    return null;
}


function createNotice() {
    const el = document.createElement('div');
    el.className = 'inline-notice';
    el.style.position = 'fixed';
    el.style.top = '16px';
    el.style.right = '16px';
    el.style.padding = '10px 14px';
    el.style.background = '#4a7c59';
    el.style.color = '#fff';
    el.style.borderRadius = '6px';
    el.style.boxShadow = '0 4px 10px rgba(0,0,0,0.15)';
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.2s';
    document.body.appendChild(el);
    return el;
}


function showNotice(el, text, isError = false, isWarning = false) {
    if (!el) return;
    el.textContent = text;
    if (isError) {
        el.style.background = '#b33636';
    } else if (isWarning) {
        el.style.background = '#d4a012';
    } else {
        el.style.background = '#4a7c59';
    }
    el.style.opacity = '1';
    setTimeout(() => {
        el.style.opacity = '0';
    }, isWarning ? 5000 : 2000);  // Show warnings longer
}


// Image size standards for optimization warnings
const IMAGE_STANDARDS = {
    navigation: { maxWidth: 400, maxHeight: 400, maxSizeKB: 200, label: 'Navigation' },
    art: { maxWidth: 1200, maxHeight: 1200, maxSizeKB: 500, label: 'Kunst' },
    category: { maxWidth: 800, maxHeight: 800, maxSizeKB: 300, label: 'Kategorie' },
    general: { maxWidth: 1200, maxHeight: 1200, maxSizeKB: 500, label: 'Allgemein' }
};

// Determine image type based on entity
function getImageStandard(entity) {
    if (entity === 'navigation' || entity === 'nav-item') {
        return IMAGE_STANDARDS.navigation;
    }
    if (entity === 'art-image' || entity === 'art-category') {
        return IMAGE_STANDARDS.art;
    }
    if (entity === 'workshop-category' || entity === 'course') {
        return IMAGE_STANDARDS.category;
    }
    return IMAGE_STANDARDS.general;
}

// Check image dimensions and file size
async function checkImageSize(file, entity) {
    const standard = getImageStandard(entity);
    const warnings = [];
    
    // Check file size
    const fileSizeKB = file.size / 1024;
    if (fileSizeKB > standard.maxSizeKB) {
        warnings.push(`Dateigrösse (${Math.round(fileSizeKB)} KB) überschreitet empfohlene ${standard.maxSizeKB} KB`);
    }
    
    // Check dimensions using Image object
    return new Promise((resolve) => {
        const img = new Image();
        img.onload = function() {
            if (this.width > standard.maxWidth || this.height > standard.maxHeight) {
                warnings.push(`Bildgrösse (${this.width}x${this.height}) überschreitet empfohlene ${standard.maxWidth}x${standard.maxHeight} px`);
            }
            resolve({
                warnings,
                standard,
                actual: {
                    width: this.width,
                    height: this.height,
                    sizeKB: Math.round(fileSizeKB)
                }
            });
            URL.revokeObjectURL(img.src);
        };
        img.onerror = function() {
            resolve({ warnings, standard, actual: { sizeKB: Math.round(fileSizeKB) } });
        };
        img.src = URL.createObjectURL(file);
    });
}

// Optimize image using Canvas API
async function optimizeImage(file, standard) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = function() {
            // Calculate new dimensions
            let newWidth = this.width;
            let newHeight = this.height;
            
            // Scale down if larger than max dimensions
            if (newWidth > standard.maxWidth || newHeight > standard.maxHeight) {
                const ratio = Math.min(
                    standard.maxWidth / newWidth,
                    standard.maxHeight / newHeight
                );
                newWidth = Math.round(newWidth * ratio);
                newHeight = Math.round(newHeight * ratio);
            }
            
            // Create canvas and draw resized image
            const canvas = document.createElement('canvas');
            canvas.width = newWidth;
            canvas.height = newHeight;
            const ctx = canvas.getContext('2d');
            
            // Use high-quality image smoothing
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = 'high';
            ctx.drawImage(img, 0, 0, newWidth, newHeight);
            
            // Determine output format - keep PNG for transparency, otherwise use JPEG
            const isPNG = file.type === 'image/png';
            const hasTransparency = isPNG && checkCanvasTransparency(canvas);
            
            // Convert to blob
            const outputType = hasTransparency ? 'image/png' : 'image/jpeg';
            const quality = hasTransparency ? undefined : 0.85;
            
            canvas.toBlob((blob) => {
                if (blob) {
                    // Create a new File object with the original name
                    const ext = hasTransparency ? '.png' : '.jpg';
                    const baseName = file.name.replace(/\.[^.]+$/, '');
                    const optimizedFile = new File([blob], baseName + ext, { type: outputType });
                    
                    resolve({
                        file: optimizedFile,
                        originalSize: Math.round(file.size / 1024),
                        newSize: Math.round(blob.size / 1024),
                        originalDimensions: { width: img.width, height: img.height },
                        newDimensions: { width: newWidth, height: newHeight }
                    });
                } else {
                    reject(new Error('Failed to create blob'));
                }
            }, outputType, quality);
            
            URL.revokeObjectURL(img.src);
        };
        img.onerror = () => reject(new Error('Failed to load image'));
        img.src = URL.createObjectURL(file);
    });
}

// Check if canvas has any transparent pixels
function checkCanvasTransparency(canvas) {
    const ctx = canvas.getContext('2d');
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;
    
    // Check alpha channel (every 4th byte starting at index 3)
    for (let i = 3; i < data.length; i += 4) {
        if (data[i] < 255) {
            return true; // Found a transparent pixel
        }
    }
    return false;
}

// Show image warning modal with optimize option
function showImageWarning(checkResult, onContinue, onCancel, onOptimize) {
    const modal = document.createElement('div');
    modal.className = 'image-warning-modal';
    modal.innerHTML = `
        <div class="image-warning-content">
            <h3>⚠️ Bild-Optimierung empfohlen</h3>
            <p>Das hochgeladene Bild entspricht nicht den empfohlenen Standards:</p>
            <ul>
                ${checkResult.warnings.map(w => `<li>${w}</li>`).join('')}
            </ul>
            <div class="image-warning-info">
                <strong>Aktuell:</strong> ${checkResult.actual.width}×${checkResult.actual.height} px, ${checkResult.actual.sizeKB} KB<br>
                <strong>Empfohlen:</strong> max. ${checkResult.standard.maxWidth}×${checkResult.standard.maxHeight} px, max. ${checkResult.standard.maxSizeKB} KB
            </div>
            <div class="image-warning-actions">
                <button class="btn btn-warning-optimize">✨ Bild optimieren</button>
                <button class="btn btn-warning-continue">Trotzdem hochladen</button>
                <button class="btn btn-warning-cancel">Abbrechen</button>
            </div>
        </div>
    `;
    
    // Add styles
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.6); z-index: 9999;
        display: flex; align-items: center; justify-content: center;
    `;
    
    const content = modal.querySelector('.image-warning-content');
    content.style.cssText = `
        background: #fff; padding: 25px; border-radius: 8px;
        max-width: 500px; margin: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    `;
    
    const h3 = modal.querySelector('h3');
    h3.style.cssText = 'margin: 0 0 15px 0; color: #d4a012;';
    
    const ul = modal.querySelector('ul');
    ul.style.cssText = 'margin: 10px 0; padding-left: 20px; color: #666;';
    
    const info = modal.querySelector('.image-warning-info');
    info.style.cssText = 'background: #f5f5f5; padding: 12px; border-radius: 4px; margin: 15px 0; font-size: 0.9em; line-height: 1.6;';
    
    const actions = modal.querySelector('.image-warning-actions');
    actions.style.cssText = 'display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; flex-wrap: wrap;';
    
    const btnOptimize = modal.querySelector('.btn-warning-optimize');
    btnOptimize.style.cssText = 'padding: 10px 18px; background: #4a7c59; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;';
    
    const btnContinue = modal.querySelector('.btn-warning-continue');
    btnContinue.style.cssText = 'padding: 10px 18px; background: #d4a012; color: #fff; border: none; border-radius: 4px; cursor: pointer;';
    
    const btnCancel = modal.querySelector('.btn-warning-cancel');
    btnCancel.style.cssText = 'padding: 10px 18px; background: #666; color: #fff; border: none; border-radius: 4px; cursor: pointer;';
    
    document.body.appendChild(modal);
    
    btnOptimize.addEventListener('click', () => {
        // Show loading state
        btnOptimize.textContent = '⏳ Optimiere...';
        btnOptimize.disabled = true;
        btnContinue.disabled = true;
        
        onOptimize().then(() => {
            modal.remove();
        }).catch((err) => {
            console.error('Optimization error:', err);
            alert('Fehler bei der Optimierung. Bitte versuchen Sie es erneut.');
            btnOptimize.textContent = '✨ Bild optimieren';
            btnOptimize.disabled = false;
            btnContinue.disabled = false;
        });
    });
    
    btnContinue.addEventListener('click', () => {
        modal.remove();
        onContinue();
    });
    
    btnCancel.addEventListener('click', () => {
        modal.remove();
        onCancel();
    });
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
            onCancel();
        }
    });
}

// Show optimization success message
function showOptimizationSuccess(result, notice) {
    const savedPercent = Math.round((1 - result.newSize / result.originalSize) * 100);
    const message = `✅ Optimiert: ${result.originalSize}KB → ${result.newSize}KB (-${savedPercent}%)`;
    showNotice(notice, message, false, false);
}


