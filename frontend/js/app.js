// Sliding underline effect for navbar
document.addEventListener('DOMContentLoaded', function() {
    const navLinks = document.querySelector('.nav-links');
    const links = navLinks.querySelectorAll('a');
    const underline = document.createElement('div');
    
    // Create the sliding underline element
    underline.className = 'sliding-underline';
    navLinks.appendChild(underline);
    
    // Set current page as active
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    let activeLink = null;
    
    links.forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href');
        if (href === currentPage || 
            (currentPage === 'index.html' && href === 'index.html') ||
            (currentPage === '' && href === 'index.html')) {
            link.classList.add('active');
            activeLink = link;
        }
    });
    
    // Keep underline invisible initially
    underline.style.opacity = '0';
    
    // Add hover effects
    links.forEach(link => {
        link.addEventListener('mouseenter', () => {
            setUnderlinePosition(link);
            underline.style.opacity = '1';
        });
    });
    
    // Hide underline when mouse leaves navbar
    navLinks.addEventListener('mouseleave', () => {
        underline.style.opacity = '0';
    });
    
    function setUnderlinePosition(element) {
        const linkRect = element.getBoundingClientRect();
        const navRect = navLinks.getBoundingClientRect();
        
        underline.style.width = (linkRect.width - 16) + 'px'; // Subtract padding
        underline.style.left = (linkRect.left - navRect.left + 8) + 'px'; // Add padding offset
    }
});

// FAQ Accordion functionality
document.addEventListener('DOMContentLoaded', function() {
    const faqItems = document.querySelectorAll('.faq-item');
    
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        
        question.addEventListener('click', () => {
            // Close all other FAQ items
            faqItems.forEach(otherItem => {
                if (otherItem !== item && otherItem.classList.contains('active')) {
                    otherItem.classList.remove('active');
                }
            });
            
            // Toggle current item
            item.classList.toggle('active');
        });
    });
});

// Post form functionality
document.addEventListener('DOMContentLoaded', function() {
    // File upload handling
    const fileInput = document.getElementById('photo');
    const fileInfo = document.getElementById('fileInfo');
    
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                fileInfo.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
            } else {
                fileInfo.textContent = '';
            }
        });
    }
    
    // Contact method handling
    const contactMethod = document.getElementById('contactMethod');
    const phoneGroup = document.getElementById('phoneGroup');
    
    if (contactMethod && phoneGroup) {
        contactMethod.addEventListener('change', function() {
            if (this.value === 'phone' || this.value === 'both') {
                phoneGroup.style.display = 'flex';
                phoneGroup.style.flexDirection = 'column';
                phoneGroup.style.gap = '0.5rem';
            } else {
                phoneGroup.style.display = 'none';
            }
        });
    }
    
    // Form submission handling
    const reportForm = document.getElementById('reportForm');
    
    if (reportForm) {
        reportForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Add loading state to submit button
            const submitBtn = this.querySelector('.submit-btn');
            const originalText = submitBtn.innerHTML;
            
            submitBtn.classList.add('loading');
            submitBtn.innerHTML = '<span class="btn-icon">⏳</span> Submitting...';
            
            // Get form data
            const formData = new FormData(this);
            const formObject = {};
            
            for (let [key, value] of formData.entries()) {
                formObject[key] = value;
            }
            
            // Simulate form submission with delay
            setTimeout(() => {
                console.log('Form submitted with data:', formObject);
                
                // Add success state to form container
                const formContainer = document.querySelector('.form-container');
                formContainer.classList.add('success');
                
                // Show success message
                alert('Your report has been submitted successfully! Thank you for helping reunite lost items with their owners.');
                
                // Reset form and states
                this.reset();
                if (fileInfo) fileInfo.textContent = '';
                if (phoneGroup) phoneGroup.style.display = 'none';
                
                // Remove loading and success states
                setTimeout(() => {
                    submitBtn.classList.remove('loading');
                    submitBtn.innerHTML = originalText;
                    formContainer.classList.remove('success');
                }, 2000);
                
            }, 1500); // Simulate network delay
        });
    }
    
    // Form validation
    const formInputs = document.querySelectorAll('.form-input, .form-select, .form-textarea');
    
    formInputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateField(this);
        });
        
        input.addEventListener('input', function() {
            // Remove error state when user starts typing
            if (this.classList.contains('error')) {
                this.classList.remove('error');
            }
        });
    });
    
    function validateField(field) {
        const value = field.value.trim();
        const isRequired = field.hasAttribute('required');
        
        // Remove previous validation classes
        field.classList.remove('error', 'success');
        
        if (isRequired && !value) {
            field.classList.add('error');
            return false;
        }
        
        // Email validation
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                field.classList.add('error');
                return false;
            }
        }
        
        // Success state for filled fields
        if (value) {
            field.classList.add('success');
        }
        
        return true;
    }
    
    // Set today's date as default
    const dateInput = document.getElementById('date');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.value = today;
    }
    
    // URL parameter handling for item type
    const urlParams = new URLSearchParams(window.location.search);
    const type = urlParams.get('type');
    const itemTypeSelect = document.getElementById('itemType');
    
    if (type && itemTypeSelect) {
        if (type === 'lost') {
            itemTypeSelect.value = 'lost';
        } else if (type === 'found') {
            itemTypeSelect.value = 'found';
        }
    }
});