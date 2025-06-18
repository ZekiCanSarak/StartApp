document.addEventListener('DOMContentLoaded', function() {
    const profileForm = document.getElementById('profileForm');
    if (profileForm) {
        profileForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            fetch('/update_profile', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Disable form fields
                    document.getElementById('name').disabled = true;
                    document.getElementById('age').disabled = true;
                    document.getElementById('school').disabled = true;
                    document.getElementById('skills').disabled = true;
                    document.getElementById('hackathon').disabled = true;
                    document.getElementById('preferred_jobs').disabled = true;
                    
                    // Hide save/cancel buttons, show edit button
                    document.getElementById('editButton').style.display = 'inline-block';
                    document.getElementById('saveButton').style.display = 'none';
                    document.getElementById('cancelButton').style.display = 'none';

                    // Show success message
                    const successMsg = document.createElement('div');
                    successMsg.className = 'alert alert-success';
                    successMsg.textContent = 'Profile updated successfully!';
                    profileForm.insertBefore(successMsg, profileForm.firstChild);

                    // Remove success message after 3 seconds
                    setTimeout(() => {
                        successMsg.remove();
                    }, 3000);

                    // Refresh the page to update project skills
                    window.location.reload();
                } else {
                    alert('Failed to update profile: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to update profile');
            });
        });
    }
});

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