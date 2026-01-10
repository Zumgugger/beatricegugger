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
            if (!input.files.length) return;
            const file = input.files[0];
            const entity = wrapper.dataset.entity;
            const id = wrapper.dataset.entityId;
            const url = buildImageEndpoint(entity, id);
            if (!url) return;

            const formData = new FormData();
            formData.append('image', file);
            try {
                const resp = await fetch(url, { method: 'POST', body: formData });
                const data = await resp.json();
                if (data.success && data.image_path) {
                    let img = wrapper.querySelector('img');
                    if (!img) {
                        // No image exists yet, create one
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
        });

        wrapper.addEventListener('click', () => input.click());
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


function showNotice(el, text, isError = false) {
    if (!el) return;
    el.textContent = text;
    el.style.background = isError ? '#b33636' : '#4a7c59';
    el.style.opacity = '1';
    setTimeout(() => {
        el.style.opacity = '0';
    }, 2000);
}
