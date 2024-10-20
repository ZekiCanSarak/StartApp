function showForm(formId) {
    closeForm('loginForm')
    closeForm('signupForm')
    document.getElementById(formId).style.display = 'block';
}

function closeForm(formId) {
    document.getElementById(formId).style.display = 'none';
}