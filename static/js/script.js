// Quando o documento estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    // Para mensagens flash automáticas (desaparecem após 5 segundos)
    const flashMessages = document.querySelectorAll('.alert:not(.alert-permanent)');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            // Cria um novo evento de clique para o botão de fechar
            const closeBtn = message.querySelector('.btn-close');
            if (closeBtn) {
                closeBtn.click();
            } else {
                // Ou apenas remove a mensagem com uma animação fade-out
                message.style.transition = 'opacity 0.5s ease';
                message.style.opacity = '0';
                setTimeout(function() {
                    message.remove();
                }, 500);
            }
        }, 5000);
    });

    // Pré-visualização de imagem ao fazer upload
    const fileInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    fileInputs.forEach(function(input) {
        input.addEventListener('change', function(e) {
            // Identificar se estamos na adição ou edição
            const isEdit = input.id === 'edit-image';
            const previewId = isEdit ? 'current-image' : 'preview-image';
            
            // Procurar ou criar a imagem de pré-visualização
            let previewImage = document.getElementById(previewId);
            
            if (!previewImage && !isEdit) {
                // Criar elemento de pré-visualização se não existir (apenas para adição)
                const previewContainer = document.createElement('div');
                previewContainer.id = 'preview-container';
                previewContainer.className = 'col-md-12 mt-2';
                
                const previewLabel = document.createElement('label');
                previewLabel.className = 'form-label';
                previewLabel.textContent = 'Pré-visualização:';
                
                previewImage = document.createElement('img');
                previewImage.id = 'preview-image';
                previewImage.className = 'img-thumbnail';
                previewImage.style.maxHeight = '150px';
                
                previewContainer.appendChild(previewLabel);
                previewContainer.appendChild(previewImage);
                
                // Inserir após o campo de upload
                input.parentNode.after(previewContainer);
            }
            
            // Mostrar a pré-visualização
            if (previewImage && this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewImage.src = e.target.result;
                    
                    // Se for edição, mostrar o container
                    if (isEdit) {
                        const container = document.getElementById('current-image-container');
                        if (container) {
                            container.style.display = 'block';
                        }
                    }
                }
                reader.readAsDataURL(this.files[0]);
            }
        });
    });

    // Formatar campos numéricos para moeda no frontend
    const priceInputs = document.querySelectorAll('input[name="price"]');
    priceInputs.forEach(function(input) {
        input.addEventListener('blur', function(e) {
            // Formatar para duas casas decimais
            if (this.value) {
                const value = parseFloat(this.value);
                if (!isNaN(value)) {
                    this.value = value.toFixed(2);
                }
            }
        });
    });
    
    // Animação suave nos cards
    const productCards = document.querySelectorAll('.product-card');
    productCards.forEach(function(card, index) {
        // Adicionar um pequeno atraso para cada card criar um efeito cascata
        setTimeout(function() {
            card.classList.add('fade-in');
        }, index * 100);
    });
    
    // Adicionar feedback tátil nos botões (ripple effect)
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(function(button) {
        button.addEventListener('mousedown', function(e) {
            // Criar efeito ripple
            const ripple = document.createElement('span');
            const rect = button.getBoundingClientRect();
            
            const size = Math.max(rect.width, rect.height) * 2;
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = `${size}px`;
            ripple.style.left = `${x}px`;
            ripple.style.top = `${y}px`;
            ripple.className = 'ripple';
            
            // Adicionar estilo inline para o efeito ripple
            ripple.style.position = 'absolute';
            ripple.style.borderRadius = '50%';
            ripple.style.transform = 'scale(0)';
            ripple.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
            ripple.style.animation = 'ripple 0.5s linear';
            
            // Adicionar keyframe para a animação
            if (!document.querySelector('@keyframes ripple')) {
                const style = document.createElement('style');
                style.textContent = `
                    @keyframes ripple {
                        to {
                            transform: scale(2.5);
                            opacity: 0;
                        }
                    }
                `;
                document.head.appendChild(style);
            }
            
            button.style.position = 'relative';
            button.style.overflow = 'hidden';
            button.appendChild(ripple);
            
            setTimeout(() => {
                button.removeChild(ripple);
            }, 500);
        });
    });
});