function showForm() {
    document.getElementById('hackathon-form-popup').style.display = 'block';
}

function closeForm() {
    document.getElementById('hackathon-form-popup').style.display = 'none';
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
            const hackathon = data.hackathon;
            const hackathonElement = document.createElement('div');
            hackathonElement.classList.add('hackathon-post');
            hackathonElement.innerHTML = `
                <h3>${hackathon.title}</h3>
                <p>${hackathon.description}</p>
                <p><strong>Date:</strong> ${hackathon.date}</p>
                <p><strong>Location:</strong> ${hackathon.location}</p>
                <p><strong>Hackathon ID:</strong> ${hackathon.id}</p> <!-- Display the ID here -->
                <button class="join-hackathon-btn" onclick="joinHackathon('${hackathon.id}')">Join</button>
            `;
            document.getElementById('hackathon-feed').prepend(hackathonElement);
            closeForm('hackathon-form-popup');
        } else {
            alert(data.message);
        }
    })
    .catch(err => console.error('Error:', err));
});

function addHackathonToFeed(hackathon) {
    const feed = document.getElementById('hackathon-feed');
    const newPost = document.createElement('div');
    newPost.classList.add('hackathon-post');

    newPost.innerHTML = `
        <h3>${hackathon.title}</h3>
        <p>${hackathon.description}</p>
        <p><strong>Date:</strong> ${hackathon.date}</p>
        <p><strong>Location:</strong> ${hackathon.location}</p>
    `;

    feed.prepend(newPost);

}

function joinHackathon(id) {
    console.log("Attempting to join hackathon with ID:", id); // Debugging

    fetch("/join_hackathon", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ id: id })  // Send 'id' directly
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Change the button to show "Joined" and disable it
            const joinButton = document.querySelector(`.join-hackathon-btn[data-id="${id}"]`);
            if (joinButton) {
                joinButton.textContent = "Joined";
                joinButton.disabled = true;
                joinButton.classList.add("joined"); // Optional styling class
            }
        } else {
            alert("Failed to join the hackathon: " + data.message);
        }
    })
    .catch(err => console.error('Error:', err));
}
