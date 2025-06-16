function enableEdit() {
    document.getElementById('name').disabled = false;
    document.getElementById('age').disabled = false;
    document.getElementById('school').disabled = false;
    document.getElementById('skills').disabled = false;
    document.getElementById('hackathon').disabled = false;
    document.getElementById('preferred_jobs').disabled = false;
    
    document.getElementById('editButton').style.display = 'none';
    document.getElementById('saveButton').style.display = 'inline-block';
    document.getElementById('cancelButton').style.display = 'inline-block';
}

function saveChanges() {
    
    document.getElementById('profileForm').submit();
}

function cancelEdit() {
    document.getElementById('name').disabled = true;
    document.getElementById('age').disabled = true;
    document.getElementById('school').disabled = true;
    document.getElementById('skills').disabled = true;
    document.getElementById('hackathon').disabled = true;
    document.getElementById('preferred_jobs').disabled = true;
    
    document.getElementById('editButton').style.display = 'inline-block';
    document.getElementById('saveButton').style.display = 'none';
    document.getElementById('cancelButton').style.display = 'none';
    
    // Reset form to original values
    document.getElementById('profileForm').reset();
}

// Handle form submission
document.getElementById('profileForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData();
    formData.append('name', document.getElementById('name').value);
    formData.append('age', document.getElementById('age').value);
    formData.append('school', document.getElementById('school').value);
    formData.append('skills', document.getElementById('skills').value);
    formData.append('hackathon', document.getElementById('hackathon').value);
    formData.append('preferred_jobs', document.getElementById('preferred_jobs').value);
    
    try {
        const response = await fetch('/update_profile', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Re-disable all inputs
            document.getElementById('name').disabled = true;
            document.getElementById('age').disabled = true;
            document.getElementById('school').disabled = true;
            document.getElementById('skills').disabled = true;
            document.getElementById('hackathon').disabled = true;
            document.getElementById('preferred_jobs').disabled = true;
            
            // Show edit button, hide save/cancel buttons
            document.getElementById('editButton').style.display = 'inline-block';
            document.getElementById('saveButton').style.display = 'none';
            document.getElementById('cancelButton').style.display = 'none';
            
            // Show success message
            alert('Profile updated successfully!');
        } else {
            throw new Error(data.error || 'Failed to update profile');
        }
    } catch (error) {
        alert('Error updating profile: ' + error.message);
    }
});