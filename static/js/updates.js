function loadUpdates(hackathonId) {
    fetch(`/get_updates/${hackathonId}`)
        .then(response => response.json())
        .then(updates => {
            const updatesList = document.getElementById('updates-list');
            if (!updatesList) return; 

            updatesList.innerHTML = ''; 
            updates.forEach(update => {
                const updateItem = document.createElement('li');
                updateItem.innerHTML = `<strong>${new Date(update.created_at).toLocaleString()}</strong>: ${update.content}`;
                updatesList.appendChild(updateItem);
            });
        })
        .catch(error => console.error('Error fetching updates:', error));
}

document.addEventListener('DOMContentLoaded', function () {
    const addUpdateForm = document.getElementById('add-update-form');
    if (addUpdateForm) { 
        addUpdateForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const hackathonId = document.getElementById('hackathon-id').value;
            const content = document.getElementById('update-content').value;

            fetch('/add_update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({ hackathon_id: hackathonId, content }),
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const updatesList = document.getElementById('updates-list');
                        const updateItem = document.createElement('li');
                        updateItem.innerHTML = `<strong>${new Date(data.update.created_at).toLocaleString()}</strong>: ${data.update.content}`;
                        updatesList.prepend(updateItem);
                        document.getElementById('update-content').value = '';
                    } else {
                        alert(data.message || 'Failed to post update.');
                    }
                })
                .catch(error => console.error('Error posting update:', error));
        });
    }
});

const hackathonId = document.getElementById('hackathon-id')?.value; 
if (hackathonId) {
    loadUpdates(hackathonId);
    setInterval(() => fetchUpdates(hackathonId), 10000); 
}

function fetchUpdates(hackathonId) {
    fetch(`/get_updates/${hackathonId}`)
        .then(response => response.json())
        .then(data => {
            const updatesList = document.getElementById('updates-list');
            if (!updatesList) return; 
            
            updatesList.innerHTML = ''; 
            data.forEach(update => {
                const updateElement = document.createElement('li');
                updateElement.innerHTML = `<strong>${update.created_at}</strong>: ${update.content}`;
                updatesList.appendChild(updateElement);
            });
        })
        .catch(error => console.error('Error fetching updates:', error));
}

function goBack() {
    window.location.href = "/hack"; 
}