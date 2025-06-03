// Add image preview functionality
document.getElementById('image').addEventListener('change', function(e) {
    const preview = document.getElementById('current-image-preview');
    preview.innerHTML = '';
    
    if (this.files && this.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            const img = document.createElement('img');
            img.src = e.target.result;
            preview.appendChild(img);
        }
        
        reader.readAsDataURL(this.files[0]);
    }
});

function showForm(isEdit = false) {
    const formPopup = document.getElementById('hackathon-form-popup');
    const postButton = document.querySelector('button[type="submit"]:not(#save-button)');
    const saveButton = document.getElementById('save-button');
    const imagePreview = document.getElementById('current-image-preview');
    const imageInput = document.getElementById('image');

    // Only clear the form if it's not an edit
    if (!isEdit) {
        document.getElementById('hackathon-form').reset();
        imagePreview.innerHTML = '';
        imageInput.value = '';
        // Remove any existing current_image_path input
        const currentImageInput = document.getElementById('current_image_path');
        if (currentImageInput) {
            currentImageInput.remove();
        }
    }

    formPopup.style.display = 'block';
    postButton.style.display = isEdit ? 'none' : 'inline-block';
    saveButton.style.display = isEdit ? 'inline-block' : 'none';
}

function closeForm() {
    document.getElementById('hackathon-form-popup').style.display = 'none';
    document.getElementById('hackathon-form').reset();
    document.getElementById('hackathon_id').value = '';
    document.getElementById('current-image-preview').innerHTML = '';
    
    // Remove the current_image_path input if it exists
    const currentImageInput = document.getElementById('current_image_path');
    if (currentImageInput) {
        currentImageInput.remove();
    }
}

document.getElementById("hackathon-form").addEventListener("submit", function (e) {
    e.preventDefault();

    const formData = new FormData(this);
    const hackathonId = document.getElementById('hackathon_id').value;
    const currentImagePath = document.getElementById('current_image_path');
    const newImage = document.getElementById('image').files[0];

    if (hackathonId) {
        formData.append('hackathon_id', hackathonId);
    }

    // If we have a current image path and no new image is selected, keep the current image
    if (currentImagePath && currentImagePath.value && !newImage) {
        formData.set('current_image_path', currentImagePath.value);
    }

    fetch("/post_hackathon", {
        method: "POST",
        body: formData,
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log("Hackathon created/updated:", data.hackathon);

                // Add/Update the hackathon in the feed
                addHackathonToFeed(data.hackathon);

                // Only add to sidebar if it's a new hackathon
                if (!hackathonId) {
                    addHackathonToSidebar(data.hackathon);
                } else {
                    // Update existing sidebar entry if it exists
                    updateHackathonInSidebar(data.hackathon);
                }

                // Close the form
                closeForm();
            } else {
                alert("Error saving hackathon: " + data.message);
            }
        })
        .catch(error => {
            console.error("Error submitting hackathon:", error);
        });
});

function addHackathonToFeed(hackathon) {
    const hackathonIdStr = String(hackathon.id);
    let hackathonElement = document.querySelector(`.hackathon-post[data-id="${hackathonIdStr}"]`);

    // Ensure proper image path formatting
    const imageHtml = hackathon.image_path 
        ? `<div class="hackathon-image">
               <img src="/static/${hackathon.image_path.replace(/^static\//, '')}" alt="${hackathon.title}">
           </div>`
        : '';

    if (hackathonElement) {
        // Update existing hackathon post
        hackathonElement.innerHTML = `
            ${imageHtml}
            <h3>${hackathon.title}</h3>
            <p class="description">${hackathon.description}</p>
            <p class="date"><strong>Date:</strong> ${hackathon.date}</p>
            <p class="location"><strong>Location:</strong> ${hackathon.location}</p>
            <p class="participants-info"><strong>Participants:</strong> ${hackathon.current_participants} / ${hackathon.max_participants}</p>
            <div class="button-group">
                ${hackathon.joined 
                    ? `<button class="join-hackathon-btn joined" disabled>
                           <i class="fas fa-user-check"></i> Joined
                       </button>
                       <button onclick="location.href='/add_to_google_calendar/${hackathon.id}'" class="calendar-btn">
                           <i class="fas fa-calendar-plus"></i> Add to Calendar
                       </button>`
                    : `<button class="join-hackathon-btn" data-id="${hackathon.id}" onclick="joinHackathon('${hackathon.id}')">
                           <i class="fas fa-user-plus"></i> Join
                       </button>`
                }
                ${hackathon.created_by === hackathon.current_user 
                    ? `<button class="edit-hackathon-btn" onclick="editHackathon('${hackathon.id}')">
                           <i class="fas fa-edit"></i> Edit
                       </button>`
                    : ''}
            </div>
        `;
    } else {
        // Create new hackathon post
        hackathonElement = document.createElement('div');
        hackathonElement.classList.add('hackathon-post');
        hackathonElement.setAttribute('data-id', hackathonIdStr);

        hackathonElement.innerHTML = `
            ${imageHtml}
            <h3>${hackathon.title}</h3>
            <p class="description">${hackathon.description}</p>
            <p class="date"><strong>Date:</strong> ${hackathon.date}</p>
            <p class="location"><strong>Location:</strong> ${hackathon.location}</p>
            <p class="participants-info"><strong>Participants:</strong> ${hackathon.current_participants} / ${hackathon.max_participants}</p>
            <div class="button-group">
                ${hackathon.joined 
                    ? `<button class="join-hackathon-btn joined" disabled>
                           <i class="fas fa-user-check"></i> Joined
                       </button>
                       <button onclick="location.href='/add_to_google_calendar/${hackathon.id}'" class="calendar-btn">
                           <i class="fas fa-calendar-plus"></i> Add to Calendar
                       </button>`
                    : `<button class="join-hackathon-btn" data-id="${hackathon.id}" onclick="joinHackathon('${hackathon.id}')">
                           <i class="fas fa-user-plus"></i> Join
                       </button>`
                }
                ${hackathon.created_by === hackathon.current_user 
                    ? `<button class="edit-hackathon-btn" onclick="editHackathon('${hackathon.id}')">
                           <i class="fas fa-edit"></i> Edit
                       </button>`
                    : ''}
            </div>
        `;

        const targetSection = hackathon.category === 'matching' ? '#personalised-hackathons'
                            : hackathon.category === 'other' ? '#other-hackathons'
                            : '#expired-hackathons';

        document.querySelector(targetSection).prepend(hackathonElement);

        if (hackathon.category === 'matching') {
            const noPersonalisedMessage = document.getElementById("no-personalised-message");
            if (noPersonalisedMessage) {
                noPersonalisedMessage.remove();
            }
        }
    }

    closeForm();
}

function joinHackathon(id) {
    const hackathonElement = document.querySelector(`.hackathon-post[data-id="${id}"]`);
    const participantsInfo = hackathonElement.querySelector('.participants-info').textContent;
    
    // Extracting current and max participants from the text
    const [currentParticipants, maxParticipants] = participantsInfo.match(/\d+/g).map(Number);
    
    // Checking if the hackathon is already full
    if (currentParticipants >= maxParticipants) {
        alert("Max limit reached. You cannot join this hackathon.");
        return;
    }

    // Goes to send the join request if the hackathon is not full
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/join_hackathon", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            console.log("Join Hackathon Response:", response);

            if (response.success) {
                // Updating participants info
                let participantsElement = hackathonElement.querySelector('.participants-info');
                participantsElement.textContent = `Participants: ${response.current_participants} / ${response.max_participants}`;
                
                // Updating the join button to 'Joined' and disable it
                const joinButton = hackathonElement.querySelector('.join-hackathon-btn');
                if (joinButton) {
                    joinButton.textContent = "Joined";
                    joinButton.disabled = true;
                    joinButton.classList.add("joined");
                }

                // Adding calendar button if applicable
                const calendarButton = document.createElement("button");
                calendarButton.classList.add("calendar-btn");
                calendarButton.textContent = "Add to Calendar";
                calendarButton.onclick = () => location.href = `/add_to_google_calendar/${id}`;
                hackathonElement.appendChild(calendarButton);

            } else {
                alert("Failed to join hackathon: " + (response.message || "Unknown error"));
            }
        }
    };
    xhr.send(JSON.stringify({ id: id }));
}

function editHackathon(hackathonId) {
    const xhr = new XMLHttpRequest();
    xhr.open("GET", `/get_hackathon/${hackathonId}`, true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            if (response.success) {
                // First show the form to ensure proper initialization
                showForm(true);

                // Fill in the form fields
                document.getElementById('title').value = response.hackathon.title;
                document.getElementById('description').value = response.hackathon.description;
                document.getElementById('date').value = response.hackathon.date;
                document.getElementById('location').value = response.hackathon.location;
                document.getElementById('max_participants').value = response.hackathon.max_participants || '';
                document.getElementById('hackathon_id').value = hackathonId;

                // Handle image preview and current image path
                const preview = document.getElementById('current-image-preview');
                preview.innerHTML = '';
                
                if (response.hackathon.image_path) {
                    // Create and append the image preview
                    const img = document.createElement('img');
                    img.src = `/static/${response.hackathon.image_path}`;
                    preview.appendChild(img);

                    // Add hidden input for current image path
                    let currentImageInput = document.getElementById('current_image_path');
                    if (!currentImageInput) {
                        currentImageInput = document.createElement('input');
                        currentImageInput.type = 'hidden';
                        currentImageInput.id = 'current_image_path';
                        currentImageInput.name = 'current_image_path';
                        document.getElementById('hackathon-form').appendChild(currentImageInput);
                    }
                    currentImageInput.value = response.hackathon.image_path;

                    // Add remove image button
                    const removeButton = document.createElement('button');
                    removeButton.type = 'button';
                    removeButton.className = 'remove-image-btn';
                    removeButton.innerHTML = '<i class="fas fa-trash"></i> Remove Image';
                    removeButton.onclick = function() {
                        preview.innerHTML = '';
                        document.getElementById('image').value = '';
                        currentImageInput.value = '';
                    };
                    preview.appendChild(removeButton);
                }
            } else {
                alert("Failed to load hackathon details.");
            }
        }
    };
    xhr.send();
}

function submitHackathonEdit() {
    const formData = new FormData(document.getElementById("hackathon-form"));
    const hackathonId = document.getElementById('hackathon_id').value;

    formData.append('hackathon_id', hackathonId);  // Indicating that this is an edit

    fetch("/post_hackathon", {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const existingHackathonElement = document.querySelector(`.hackathon-post[data-id="${hackathonId}"]`);
            if (existingHackathonElement) {
                // Extracting current participants and joined status
                const participantsInfo = existingHackathonElement.querySelector('.participants-info');
                const currentParticipantsText = participantsInfo ? participantsInfo.textContent.match(/\d+/g) : [data.hackathon.current_participants];
                data.hackathon.current_participants = currentParticipantsText[0];
                data.hackathon.joined = existingHackathonElement.querySelector('.join-hackathon-btn.joined') !== null;
            }

            addHackathonToFeed(data.hackathon);  // Updating hackathon in feed
            closeForm();  
        } else {
            alert(data.message || "An error occurred while updating the hackathon.");
        }
    })
    .catch(error => console.error('Error editing hackathon:', error));
}

function updateHackathonInSidebar(hackathon) {
    const sidebarLink = document.querySelector(`#hackathon-sidebar a[href='/hackathon/${hackathon.id}/updates']`);
    if (sidebarLink) {
        sidebarLink.innerHTML = `<i class="fas fa-bell"></i> ${hackathon.title}`;
    }
}

function addHackathonToSidebar(hackathon) {
    const sidebar = document.getElementById("hackathon-sidebar");
    if (!sidebar) {
        console.error("Sidebar not found!");
        return;
    }

    // Remove "No active hackathons" message if it exists
    const noHackathonsMessage = sidebar.querySelector("li:last-child");
    if (noHackathonsMessage && noHackathonsMessage.textContent === "No active hackathons") {
        noHackathonsMessage.remove();
    }

    // Create new sidebar item
    const newHackathon = document.createElement("li");
    newHackathon.innerHTML = `<a href="/hackathon/${hackathon.id}/updates"><i class="fas fa-bell"></i> ${hackathon.title}</a>`;
    sidebar.appendChild(newHackathon);
}