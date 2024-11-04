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
        <p><strong>Hackathon ID:</strong> ${hackathon.id}</p>
        ${hackathon.category !== 'expired' ? `
            <button class="join-hackathon-btn" data-id="${hackathon.id}" onclick="joinHackathon('${hackathon.id}')">Join</button>
        ` : '<p class="expired-note">This hackathon has expired.</p>'}
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