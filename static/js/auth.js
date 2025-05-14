// Form validation for auth forms

document.addEventListener('DOMContentLoaded', function() {
    // Form validations
    setupRegistrationFormValidation();
    setupLoginFormValidation();
    setupPasswordResetFormValidation();
    
    // Get user's country based on IP and select in dropdown
    setupCountrySelector();
});

/**
 * Check if a password meets the complexity requirements
 */
function isPasswordComplex(password) {
    // Check length
    if (password.length < 8) {
        return {
            valid: false,
            message: 'Password must be at least 8 characters long'
        };
    }
    
    // Check for special characters
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
        return {
            valid: false,
            message: 'Password must contain at least one special character'
        };
    }
    
    // Check for numbers
    if (!/\d/.test(password)) {
        return {
            valid: false,
            message: 'Password must contain at least one number'
        };
    }
    
    // Check for lowercase letters
    if (!/[a-z]/.test(password)) {
        return {
            valid: false,
            message: 'Password must contain at least one lowercase letter'
        };
    }
    
    // Check for uppercase letters
    if (!/[A-Z]/.test(password)) {
        return {
            valid: false,
            message: 'Password must contain at least one uppercase letter'
        };
    }
    
    return {
        valid: true,
        message: 'Password is valid'
    };
}

/**
 * Display validation feedback to the user
 */
function showValidationFeedback(inputElement, isValid, message, linkData = null) {
    // Remove existing feedback
    const existingFeedback = inputElement.parentNode.querySelector('.validation-feedback');
    if (existingFeedback) {
        existingFeedback.remove();
    }
    
    // Find feedback container or create one if it doesn't exist
    let feedbackContainer = inputElement.closest('.form-group').querySelector('.feedback-message');
    
    if (!feedbackContainer) {
        feedbackContainer = document.createElement('div');
        feedbackContainer.className = 'feedback-message';
        inputElement.closest('.form-group').appendChild(feedbackContainer);
    }
    
    // Clear previous content
    feedbackContainer.innerHTML = '';
    
    // Add the message
    const messageSpan = document.createElement('span');
    messageSpan.textContent = message;
    feedbackContainer.appendChild(messageSpan);
    
    // If we have link data, add it
    if (linkData && linkData.text && linkData.url) {
        // Create a space between message and link
        feedbackContainer.appendChild(document.createTextNode(' '));
        
        // Create the actual link
        const linkElement = document.createElement('a');
        linkElement.href = linkData.url;
        linkElement.textContent = linkData.text;
        linkElement.style.fontWeight = 'bold';
        feedbackContainer.appendChild(linkElement);
    }
    
    // Set appropriate classes
    feedbackContainer.className = isValid ? 'feedback-message valid' : 'feedback-message invalid';
    
    // Update input styling
    if (isValid) {
        inputElement.classList.remove('is-invalid');
        inputElement.classList.add('is-valid');
    } else {
        inputElement.classList.remove('is-valid');
        inputElement.classList.add('is-invalid');
    }
}

/**
 * Check if a username is available
 */
function checkUsernameAvailability(username, userId = null) {
    return new Promise((resolve, reject) => {
        if (!username) {
            resolve({
                available: false,
                message: 'Username is required'
            });
            return;
        }
        
        const formData = new FormData();
        formData.append('username', username);
        
        if (userId) {
            formData.append('user_id', userId);
        }
        
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        fetch('/check-username/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            resolve(data);
        })
        .catch(error => {
            console.error('Error checking username:', error);
            resolve({
                available: false,
                message: 'Error checking username availability'
            });
        });
    });
}

/**
 * Check if an email is available
 */
function checkEmailAvailability(email, userId = null) {
    return new Promise((resolve, reject) => {
        if (!email) {
            resolve({
                available: false,
                message: 'Email is required'
            });
            return;
        }
        
        const formData = new FormData();
        formData.append('email', email);
        
        if (userId) {
            formData.append('user_id', userId);
        }
        
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        fetch('/check-email/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            resolve(data);
        })
        .catch(error => {
            console.error('Error checking email:', error);
            resolve({
                available: false,
                message: 'Error checking email availability'
            });
        });
    });
}

// Add debounce function to limit API calls during typing
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

/**
 * Setup validation for the registration form
 */
function setupRegistrationFormValidation() {
    const registrationForm = document.getElementById('registration-form');
    
    if (!registrationForm) {
        return; // Form not present on page
    }
    
    const usernameInput = registrationForm.querySelector('#id_username');
    const emailInput = registrationForm.querySelector('#id_email');
    const passwordInput = registrationForm.querySelector('#id_password1');
    const confirmPasswordInput = registrationForm.querySelector('#id_password2');
    const termsCheckbox = registrationForm.querySelector('#id_terms_accepted');
    const submitButton = registrationForm.querySelector('button[type="submit"]');
    
    // Username validation - add real-time validation with debounce
    if (usernameInput) {
        // Create debounced version of the check function to avoid too many API calls
        const debouncedUsernameCheck = debounce(async function(username) {
            if (username.trim()) {
                const usernameFeedback = document.getElementById('username-feedback') || 
                                         usernameInput.closest('.form-group').querySelector('.feedback-message');
                
                // Show checking status
                if (usernameFeedback) {
                    usernameFeedback.textContent = 'Checking...';
                    usernameFeedback.className = 'feedback-message';
                }
                
                const result = await checkUsernameAvailability(username);
                showValidationFeedback(usernameInput, result.available, result.message);
            }
        }, 500); // 500ms delay
        
        // Keep blur event for immediate feedback when user leaves the field
        usernameInput.addEventListener('blur', function() {
            const username = this.value.trim();
            if (username) {
                debouncedUsernameCheck(username);
            }
        });
        
        // Add input event for real-time feedback
        usernameInput.addEventListener('input', function() {
            const username = this.value.trim();
            if (username) {
                debouncedUsernameCheck(username);
            } else {
                // Clear feedback if username is empty
                const usernameFeedback = document.getElementById('username-feedback') || 
                                        this.closest('.form-group').querySelector('.feedback-message');
                if (usernameFeedback) {
                    usernameFeedback.textContent = '';
                    usernameFeedback.className = 'feedback-message';
                }
                this.classList.remove('is-valid', 'is-invalid');
            }
        });
    }
    
    // Email validation.. debounced real-time checking
    if (emailInput) {
        const debouncedEmailCheck = debounce(async function(email) {
            if (email.trim()) {
                if (!email.includes('@') || !email.includes('.')) {
                    showValidationFeedback(emailInput, false, 'Please enter a valid email address');
                    return;
                }
                
                const emailFeedback = document.getElementById('email-feedback') || 
                                    emailInput.closest('.form-group').querySelector('.feedback-message');
                
                if (emailFeedback) {
                    emailFeedback.textContent = 'Checking...';
                    emailFeedback.className = 'feedback-message';
                }
                
                const result = await checkEmailAvailability(email);
                
                // Check if we have link data, pass it to the feedback function
                if (!result.available && result.html && result.link) {
                    showValidationFeedback(emailInput, result.available, result.message, result.link);
                } else {
                    showValidationFeedback(emailInput, result.available, result.message);
                }
            }
        }, 500); // 500ms delay
        
        // Keep blur event for immediate feedback
        emailInput.addEventListener('blur', function() {
            const email = this.value.trim();
            if (email) {
                debouncedEmailCheck(email);
            }
        });
        
        // Add input event for real-time feedback
        emailInput.addEventListener('input', function() {
            const email = this.value.trim();
            if (email) {
                debouncedEmailCheck(email);
            } else {
                // Clear feedback if email is empty
                const emailFeedback = document.getElementById('email-feedback') || 
                                    this.closest('.form-group').querySelector('.feedback-message');
                if (emailFeedback) {
                    emailFeedback.textContent = '';
                    emailFeedback.className = 'feedback-message';
                }
                this.classList.remove('is-valid', 'is-invalid');
            }
        });
    }
    
    // Password validation
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            const password = this.value;
            const result = isPasswordComplex(password);
            showValidationFeedback(this, result.valid, result.message);
        });
    }
    
    // Confirm password validation
    if (confirmPasswordInput && passwordInput) {
        confirmPasswordInput.addEventListener('input', function() {
            const password = passwordInput.value;
            const confirmPassword = this.value;
            
            if (password === confirmPassword) {
                showValidationFeedback(this, true, 'Passwords match');
            } else {
                showValidationFeedback(this, false, 'Passwords do not match');
            }
        });
    }
    
    // Form submission validation
    if (registrationForm) {
        registrationForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            
            let isFormValid = true;
            
            // Check username
            if (usernameInput) {
                const username = usernameInput.value.trim();
                const usernameResult = await checkUsernameAvailability(username);
                
                if (!usernameResult.available) {
                    showValidationFeedback(usernameInput, false, usernameResult.message);
                    isFormValid = false;
                }
            }
            
            // Check email
            if (emailInput) {
                const email = emailInput.value.trim();
                const emailResult = await checkEmailAvailability(email);
                
                if (!emailResult.available) {
                    // Check if we have link data for the forget password link
                    if (emailResult.html && emailResult.link) {
                        showValidationFeedback(emailInput, false, emailResult.message, emailResult.link);
                    } else {
                        showValidationFeedback(emailInput, false, emailResult.message);
                    }
                    isFormValid = false;
                }
            }
                        
            // Check password
            if (passwordInput) {
                const password = passwordInput.value;
                const passwordResult = isPasswordComplex(password);
                
                if (!passwordResult.valid) {
                    showValidationFeedback(passwordInput, false, passwordResult.message);
                    isFormValid = false;
                }
            }
            
            // Check confirm password
            if (confirmPasswordInput && passwordInput) {
                const password = passwordInput.value;
                const confirmPassword = confirmPasswordInput.value;
                
                if (password !== confirmPassword) {
                    showValidationFeedback(confirmPasswordInput, false, 'Passwords do not match');
                    isFormValid = false;
                }
            }
            
            // Check terms
            if (termsCheckbox && !termsCheckbox.checked) {
                showValidationFeedback(termsCheckbox, false, 'You must accept the Terms and Conditions');
                isFormValid = false;
            }
            
            if (isFormValid) {
                registrationForm.submit();
            } else {
                // Scroll to the first error
                const firstError = registrationForm.querySelector('.is-invalid');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
    }
}

/**
 * Setup validation for the login form
 */
function setupLoginFormValidation() {
    const loginForm = document.getElementById('login-form');
    
    if (!loginForm) {
        return; // Form not present on page
    }
    
    // Nothing special for login form, just password visibility toggle
}

/**
 * Setup validation for the password reset form
 */
function setupPasswordResetFormValidation() {
    const resetForm = document.getElementById('password-reset-form');
    
    if (!resetForm) {
        return; // Form not present on page
    }
    
    const passwordInput = resetForm.querySelector('#id_new_password1');
    const confirmPasswordInput = resetForm.querySelector('#id_new_password2');
    
    // Password validation
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            const password = this.value;
            const result = isPasswordComplex(password);
            showValidationFeedback(this, result.valid, result.message);
        });
    }
    
    // Confirm password validation
    if (confirmPasswordInput && passwordInput) {
        confirmPasswordInput.addEventListener('input', function() {
            const password = passwordInput.value;
            const confirmPassword = this.value;
            
            if (password === confirmPassword) {
                showValidationFeedback(this, true, 'Passwords match');
            } else {
                showValidationFeedback(this, false, 'Passwords do not match');
            }
        });
    }
    
    // Form submission validation
    if (resetForm) {
        resetForm.addEventListener('submit', function(event) {
            let isFormValid = true;
            
            // Check password
            if (passwordInput) {
                const password = passwordInput.value;
                const passwordResult = isPasswordComplex(password);
                
                if (!passwordResult.valid) {
                    event.preventDefault();
                    showValidationFeedback(passwordInput, false, passwordResult.message);
                    isFormValid = false;
                }
            }
            
            // Check confirm password
            if (confirmPasswordInput && passwordInput) {
                const password = passwordInput.value;
                const confirmPassword = confirmPasswordInput.value;
                
                if (password !== confirmPassword) {
                    event.preventDefault();
                    showValidationFeedback(confirmPasswordInput, false, 'Passwords do not match');
                    isFormValid = false;
                }
            }
            
            if (!isFormValid) {
                // Scroll to the first error
                const firstError = resetForm.querySelector('.is-invalid');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });
    }
}

/**
 * Setup country selector based on IP
 */
function setupCountrySelector() {
    const countrySelect = document.getElementById("country");

    if (countrySelect) {
        fetch("https://ipapi.co/json/")
            .then(response => response.json())
            .then(data => {
                const userCountry = data.country_name;
                if (userCountry) {
                    const optionToSelect = Array.from(countrySelect.options)
                        .find(option => option.text === userCountry);
                    if (optionToSelect) {
                        optionToSelect.selected = true;
                    }
                }
            })
            .catch(err => {
                console.error("IPAPI request failed:", err);
            });
    }
}