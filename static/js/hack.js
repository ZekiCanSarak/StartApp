function showForm() {
    document.getElementById('hackathon-form-popup').style.display = 'block';
}

function closeForm() {
    document.getElementById('hackathon-form-popup').style.display = 'none';
    document.getElementById('hackathon-form').reset(); 
}

document.getElementById("hackathon-form").addEventListener("submit", function (e) {
    e.preventDefault();

    const formData = new FormData(this);
    fetch("/post_hackathon", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addHackathonToFeed(data.hackathon);
            closeForm();
        } else {
            alert(data.message);
        }
    })
    .catch(err => console.error('Error:', err));
});

function addHackathonToFeed(hackathon) {
    const hackathonElement = document.createElement('div');
    hackathonElement.classList.add('hackathon-post');
    if (hackathon.category === 'expired') {
        hackathonElement.classList.add('expired');
    }

    hackathonElement.innerHTML = `
        <h3>${hackathon.title}</h3>
        <p>${hackathon.description}</p>
        <p><strong>Date:</strong> ${hackathon.date}</p>
        <p><strong>Location:</strong> ${hackathon.location}</p>
        ${hackathon.category !== 'expired' ? `
            <button class="join-hackathon-btn" onclick="joinHackathon('${hackathon.id}')">Join</button>
        ` : '<p class="expired-note">This hackathon has expired.</p>'}
        ${hackathon.role === 'organiser' ? `
            <button class="edit-hackathon-btn" onclick="editHackathon('${hackathon.id}')">Edit</button>
        ` : ''}
    `;

    if (hackathon.category === 'matching') {
        document.getElementById('personalised-hackathons').prepend(hackathonElement);
    } else if (hackathon.category === 'other') {
        document.getElementById('other-hackathons').prepend(hackathonElement);
    } else if (hackathon.category === 'expired') {
        document.getElementById('expired-hackathons').prepend(hackathonElement);
    }
}

function joinHackathon(id) {
    fetch("/join_hackathon", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ id: id })  
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
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
            alert("Failed to join the hackathon: " + data.message);
        }
    })
    .catch(err => console.error('Error:', err));
}

function editHackathon(hackathonId) {
    fetch(`/get_hackathon/${hackathonId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Pre-fill the form with hackathon details
                document.getElementById('title').value = data.hackathon.title;
                document.getElementById('description').value = data.hackathon.description;
                document.getElementById('date').value = data.hackathon.date;
                document.getElementById('location').value = data.hackathon.location;

                // Show the form in edit mode
                document.getElementById('hackathon-form-popup').style.display = 'block';

                // Modify the form submission to send to the edit route
                document.getElementById("hackathon-form").onsubmit = function(e) {
                    e.preventDefault();
                    submitHackathonEdit(hackathonId);
                };
            } else {
                alert("Failed to load hackathon details.");
            }
        })
        .catch(error => console.error('Error fetching hackathon:', error));
}

function submitHackathonEdit(hackathonId) {
    const formData = new FormData(document.getElementById("hackathon-form"));
    fetch(`/edit_hackathon/${hackathonId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the hackathon details in the feed
            updateHackathonInFeed(data.hackathon);
            closeForm(); // Close the form
        } else {
            alert(data.message || "An error occurred while updating the hackathon.");
        }
    })
    .catch(error => console.error('Error editing hackathon:', error));
}

function updateHackathonInFeed(updatedHackathon) {
    // Find the existing hackathon element in the feed and update it
    const hackathonElement = document.querySelector(`.hackathon-post[data-id="${updatedHackathon.id}"]`);
    if (hackathonElement) {
        hackathonElement.querySelector('h3').textContent = updatedHackathon.title;
        hackathonElement.querySelector('.description').textContent = updatedHackathon.description;
        hackathonElement.querySelector('.date').textContent = `Date: ${updatedHackathon.date}`;
        hackathonElement.querySelector('.location').textContent = `Location: ${updatedHackathon.location}`;
    }
}