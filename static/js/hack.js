function showForm(isEdit = false) {
    const formPopup = document.getElementById('hackathon-form-popup');
    const postButton = document.querySelector('button[type="submit"]:not(#save-button)');
    const saveButton = document.getElementById('save-button');

    formPopup.style.display = 'block';
    postButton.style.display = isEdit ? 'none' : 'inline-block';
    saveButton.style.display = isEdit ? 'inline-block' : 'none';
}

function closeForm() {
    document.getElementById('hackathon-form-popup').style.display = 'none';
    document.getElementById('hackathon-form').reset();
    document.getElementById('hackathon_id').value = ''; 
}

document.getElementById("hackathon-form").addEventListener("submit", function (e) {
    e.preventDefault();

    const formData = new FormData(this);
    const hackathonId = document.getElementById('hackathon_id').value;

    if (hackathonId) {
        formData.append('hackathon_id', hackathonId);
    }

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/post_hackathon", true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            if (response.success) {
                addHackathonToFeed(response.hackathon);
                closeForm();
            } else {
                alert(response.message);
            }
        } else if (xhr.readyState === 4) {
            alert("An error occurred while saving the hackathon.");
        }
    };
    xhr.send(formData);
});

function addHackathonToFeed(hackathon) {
    const hackathonIdStr = String(hackathon.id);
    let hackathonElement = document.querySelector(`.hackathon-post[data-id="${hackathonIdStr}"]`);

    if (hackathonElement) {
        // Update existing hackathon post
        hackathonElement.innerHTML = `
            <h3>${hackathon.title}</h3>
            <p class="description">${hackathon.description}</p>
            <p class="date"><strong>Date:</strong> ${hackathon.date}</p>
            <p class="location"><strong>Location:</strong> ${hackathon.location}</p>
            <p class="participants-info"><strong>Participants:</strong> ${hackathon.current_participants} / ${hackathon.max_participants}</p>
            ${hackathon.joined 
                ? `<button class="join-hackathon-btn joined" disabled>
                       <i class="fas fa-user-check"></i> Joined
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
        `;
    } else {
        // Create new hackathon post
        hackathonElement = document.createElement('div');
        hackathonElement.classList.add('hackathon-post');
        hackathonElement.setAttribute('data-id', hackathonIdStr);

        hackathonElement.innerHTML = `
            <h3>${hackathon.title}</h3>
            <p class="description">${hackathon.description}</p>
            <p class="date"><strong>Date:</strong> ${hackathon.date}</p>
            <p class="location"><strong>Location:</strong> ${hackathon.location}</p>
            <p class="participants-info"><strong>Participants:</strong> ${hackathon.current_participants} / ${hackathon.max_participants}</p>
            ${hackathon.joined 
                ? `<button class="join-hackathon-btn joined" disabled>
                       <i class="fas fa-user-check"></i> Joined
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
                document.getElementById('title').value = response.hackathon.title;
                document.getElementById('description').value = response.hackathon.description;
                document.getElementById('date').value = response.hackathon.date;
                document.getElementById('location').value = response.hackathon.location;
                document.getElementById('max_participants').value = response.hackathon.max_participants || ''; // Ensuring that max_participants is loaded
                document.getElementById('hackathon_id').value = hackathonId;
                showForm(true);
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