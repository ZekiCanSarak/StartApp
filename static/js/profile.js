function enableEdit() {
    document.querySelectorAll('#profileForm input, #profileForm select').forEach((field) => {
        field.disabled = false;
    });

    
    document.getElementById('editButton').style.display = 'none';
    document.getElementById('saveButton').style.display = 'inline-block';
    document.getElementById('cancelButton').style.display = 'inline-block';
}

function saveChanges() {
    
    document.getElementById('profileForm').submit();
}

function cancelEdit() {
    
    document.querySelectorAll('#profileForm input, #profileForm select').forEach((field) => {
        field.disabled = true;
    });

    
    document.getElementById('editButton').style.display = 'inline-block';
    document.getElementById('saveButton').style.display = 'none';
    document.getElementById('cancelButton').style.display = 'none';
}