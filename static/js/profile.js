function enableEdit() {
    // Enable all form fields for editing
    document.querySelectorAll('#profileForm input, #profileForm select').forEach((field) => {
        field.disabled = false;
    });

    // Show Save and Cancel buttons, hide Edit button
    document.getElementById('editButton').style.display = 'none';
    document.getElementById('saveButton').style.display = 'inline-block';
    document.getElementById('cancelButton').style.display = 'inline-block';
}

function saveChanges() {
    // Allow form submission via standard form POST
    document.getElementById('profileForm').submit();
}

function cancelEdit() {
    // Disable all form fields again without saving
    document.querySelectorAll('#profileForm input, #profileForm select').forEach((field) => {
        field.disabled = true;
    });

    // Show Edit button, hide Save and Cancel buttons
    document.getElementById('editButton').style.display = 'inline-block';
    document.getElementById('saveButton').style.display = 'none';
    document.getElementById('cancelButton').style.display = 'none';
}