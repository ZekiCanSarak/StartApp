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
    document.getElementById('hackathon_id').value = ''; // Reset the hackathon_id
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
    const hackathonElement = document.querySelector(`.hackathon-post[data-id="${hackathonIdStr}"]`);

    if (hackathonElement) {
        // Updating existing hackathon in place
        hackathonElement.querySelector('h3').textContent = hackathon.title;
        hackathonElement.querySelector('.description').textContent = hackathon.description;
        hackathonElement.querySelector('.date').innerHTML = `<strong>Date:</strong> ${hackathon.date}`;
        hackathonElement.querySelector('.location').innerHTML = `<strong>Location:</strong> ${hackathon.location}`;
    } else {
        // Creating a new hackathon element if it doesn't already exist
        const newHackathonElement = document.createElement('div');
        newHackathonElement.classList.add('hackathon-post');
        newHackathonElement.setAttribute('data-id', hackathonIdStr);

        const joinButtonHTML = hackathon.joined ? 
            '<button class="join-hackathon-btn joined" disabled>Joined</button>' : 
            `<button class="join-hackathon-btn" data-id="${hackathon.id}" onclick="joinHackathon('${hackathon.id}')">Join</button>`;

        newHackathonElement.innerHTML = `
            <h3>${hackathon.title}</h3>
            <p class="description">${hackathon.description}</p>
            <p class="date"><strong>Date:</strong> ${hackathon.date}</p>
            <p class="location"><strong>Location:</strong> ${hackathon.location}</p>
            ${hackathon.category !== 'expired' ? joinButtonHTML : '<p class="expired-note">This hackathon has expired.</p>'}
            ${hackathon.role === 'organiser' ? `<button class="edit-hackathon-btn" onclick="editHackathon('${hackathon.id}')">Edit</button>` : ''}
        `;

        const targetSection = hackathon.category === 'matching' ? '#personalised-hackathons' :
                              hackathon.category === 'other' ? '#other-hackathons' : '#expired-hackathons';
        
        document.querySelector(targetSection).prepend(newHackathonElement);

        // Removing "No personalised hackathons available" message if adding to personalised section
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
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/join_hackathon", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            if (response.success) {
                const joinButton = document.querySelector(`.join-hackathon-btn[data-id="${id}"]`);
                if (joinButton) {
                    joinButton.textContent = "Joined";
                    joinButton.disabled = true;
                    joinButton.classList.add("joined");

                    const calendarButton = document.createElement("button");
                    calendarButton.classList.add("calendar-btn");
                    calendarButton.textContent = "Add to Calendar";
                    calendarButton.onclick = function () {
                        window.location.href = `/add_to_google_calendar/${id}`;
                    };
                    joinButton.parentElement.appendChild(calendarButton);
                }
            } else {
                alert("Failed to join the hackathon: " + response.message);
            }
        } else if (xhr.readyState === 4) {
            console.error("Error:", xhr.statusText);
            alert("An error occurred while joining the hackathon.");
        }
    };
    xhr.send(JSON.stringify({ id: id }));
}

// Fetching and populating form for editing
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
            addHackathonToFeed(data.hackathon);  // Updating hackathon directly in feed
            closeForm();  
        } else {
            alert(data.message || "An error occurred while updating the hackathon.");
        }
    })
    .catch(error => console.error('Error editing hackathon:', error));
}