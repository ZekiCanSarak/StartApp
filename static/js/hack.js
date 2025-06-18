// Get current user from the session
const currentUser = document.querySelector('meta[name="username"]').content;

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
               <img src="/static/${hackathon.image_path}" alt="${hackathon.title}">
           </div>`
        : '';

    const newHtml = `
        ${imageHtml}
        <h3>${hackathon.title}</h3>
        <p class="description">${hackathon.description}</p>
        <p class="date"><strong>Date:</strong> ${hackathon.date}</p>
        <p class="location"><strong>Location:</strong> ${hackathon.location}</p>
        <p class="participants-info"><strong>Participants:</strong> ${hackathon.current_participants} / ${hackathon.max_participants}</p>
        ${hackathon.joined 
            ? `<div class="team-matching-section">
                   <button class="team-match-btn" onclick="viewTeamMatches('${hackathon.id}')">
                       <i class="fas fa-users"></i> View Team Matches
                   </button>
               </div>`
            : ''
        }
        <div class="button-group">
            ${hackathon.joined 
                ? `<button class="leave-btn" onclick="leaveHackathon('${hackathon.id}')">
                       <i class="fas fa-sign-out-alt"></i> Leave Hackathon
                   </button>`
                : `<button class="join-btn" onclick="joinHackathon('${hackathon.id}')">
                       <i class="fas fa-sign-in-alt"></i> Join Hackathon
                   </button>`
            }
            ${hackathon.created_by === hackathon.current_user 
                ? `<button class="edit-hackathon-btn" onclick="editHackathon('${hackathon.id}')">
                       <i class="fas fa-edit"></i> Edit
                   </button>`
                : ''}
        </div>
    `;

    if (hackathonElement) {
        // Preserve existing classes
        const existingClasses = Array.from(hackathonElement.classList);
        hackathonElement.innerHTML = newHtml;
        // Re-add all classes that were previously on the element
        existingClasses.forEach(className => {
            if (!hackathonElement.classList.contains(className)) {
                hackathonElement.classList.add(className);
            }
        });
    } else {
        // Create new hackathon post
        hackathonElement = document.createElement('div');
        hackathonElement.classList.add('hackathon-post');
        if (hackathon.category === 'expired') {
            hackathonElement.classList.add('expired');
        }
        hackathonElement.setAttribute('data-id', hackathonIdStr);
        hackathonElement.innerHTML = newHtml;

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
}

function joinHackathon(hackathonId) {
    fetch('/join_hackathon', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ id: hackathonId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the button instantly
            const hackathonCard = document.querySelector(`.hackathon-post[data-id="${hackathonId}"]`);
            const buttonGroup = hackathonCard.querySelector('.button-group');
            const participantsInfo = hackathonCard.querySelector('.participants-info');
            
            // Update participants count
            const [current, max] = participantsInfo.textContent.match(/\d+/g);
            participantsInfo.innerHTML = `<strong>Participants:</strong> ${parseInt(current) + 1} / ${max}`;
            
            // Update button to Leave
            buttonGroup.innerHTML = `
                <button class="leave-btn" onclick="leaveHackathon('${hackathonId}')">
                    <i class="fas fa-sign-out-alt"></i> Leave Hackathon
                </button>
            `;

            // Add team matching section
            if (!hackathonCard.querySelector('.team-matching-section')) {
                const teamMatchingSection = document.createElement('div');
                teamMatchingSection.className = 'team-matching-section';
                teamMatchingSection.innerHTML = `
                    <button class="team-match-btn" onclick="viewTeamMatches('${hackathonId}')">
                        <i class="fas fa-users"></i> View Team Matches
                    </button>
                `;
                buttonGroup.parentNode.insertBefore(teamMatchingSection, buttonGroup);
            }
        } else {
            alert(data.message || 'Failed to join hackathon');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to join hackathon');
    });
}

function leaveHackathon(hackathonId) {
    fetch(`/leave_hackathon/${hackathonId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the button instantly
            const hackathonCard = document.querySelector(`.hackathon-post[data-id="${hackathonId}"]`);
            const buttonGroup = hackathonCard.querySelector('.button-group');
            const participantsInfo = hackathonCard.querySelector('.participants-info');
            const teamMatchingSection = hackathonCard.querySelector('.team-matching-section');
            
            // Update participants count
            const [current, max] = participantsInfo.textContent.match(/\d+/g);
            participantsInfo.innerHTML = `<strong>Participants:</strong> ${parseInt(current) - 1} / ${max}`;
            
            // Update button to Join
            buttonGroup.innerHTML = `
                <button class="join-btn" onclick="joinHackathon('${hackathonId}')">
                    <i class="fas fa-sign-in-alt"></i> Join Hackathon
                </button>
            `;

            // Remove team matching section
            if (teamMatchingSection) {
                teamMatchingSection.remove();
            }
        } else {
            alert(data.error || 'Failed to leave hackathon');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to leave hackathon');
    });
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

function viewTeamMatches(hackathonId) {
    // First calculate/update team matches
    fetch(`/calculate_team_matches/${hackathonId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Now fetch the matches
            return fetch(`/get_team_matches/${hackathonId}/${currentUser}`);
        } else {
            throw new Error(data.error || 'Failed to calculate team matches');
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showTeamMatchesModal(data.matches);
        } else {
            throw new Error(data.error || 'Failed to get team matches');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert(error.message);
    });
}

function showTeamMatchesModal(matches) {
    // Remove any existing modal
    const existingModal = document.getElementById('teamMatchesModal');
    if (existingModal) {
        existingModal.remove();
    }

    const modalHtml = `
        <div class="modal" id="teamMatchesModal">
            <div class="modal-content">
                <div class="modal-header">
                    <h2><i class="fas fa-users"></i> Team Matches</h2>
                    <span class="close">&times;</span>
                </div>
                <div class="modal-body">
                    ${matches.length > 0 ? `
                        <div class="matches-list">
                            ${matches.map(match => `
                                <div class="match-card">
                                    <div class="match-info">
                                        <div class="match-header">
                                            <h3>${match.username}</h3>
                                            <span class="match-score">
                                                <i class="fas fa-percentage"></i> ${match.match_score}% Match
                                            </span>
                                        </div>
                                        <div class="match-details">
                                            ${match.skills ? `
                                                <p class="skills">
                                                    <i class="fas fa-tools"></i> <strong>Skills:</strong> 
                                                    ${match.skills.split(',').map(skill => 
                                                        `<span class="skill-tag">${skill.trim()}</span>`
                                                    ).join('')}
                                                </p>
                                            ` : ''}
                                            ${match.preferred_jobs ? `
                                                <p class="preferred-jobs">
                                                    <i class="fas fa-briefcase"></i> <strong>Preferred Roles:</strong> 
                                                    ${match.preferred_jobs.split(',').map(job => 
                                                        `<span class="role-tag">${job.trim()}</span>`
                                                    ).join('')}
                                                </p>
                                            ` : ''}
                                        </div>
                                    </div>
                                    <div class="match-actions">
                                        <button onclick="window.location.href='/messages/${match.username}'" class="message-btn">
                                            <i class="fas fa-comment"></i> Message
                                        </button>
                                        ${match.is_connected ? `
                                            <button class="connect-btn connected" disabled>
                                                <i class="fas fa-check"></i> Connected
                                            </button>
                                        ` : `
                                            <button onclick="sendConnectionRequest('${match.username}')" class="connect-btn">
                                                <i class="fas fa-user-plus"></i> Connect
                                            </button>
                                        `}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<p class="no-matches">No team matches found. Try joining more hackathons!</p>'}
                </div>
            </div>
        </div>
    `;

    // Add modal to the page
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    const modal = document.getElementById('teamMatchesModal');
    const closeBtn = modal.querySelector('.close');

    modal.style.display = 'block';

    // Close modal when clicking the X
    closeBtn.onclick = function() {
        modal.remove();
    }

    // Close modal when clicking outside
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.remove();
        }
    }
}

function sendConnectionRequest(username) {
    fetch('/send_connection_request', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username: username })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const connectBtn = document.querySelector(`button[onclick="sendConnectionRequest('${username}')"]`);
            connectBtn.disabled = true;
            connectBtn.innerHTML = '<i class="fas fa-check"></i> Request Sent';
            connectBtn.classList.add('sent');
        } else {
            alert(data.message || 'Failed to send connection request');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to send connection request');
    });
}