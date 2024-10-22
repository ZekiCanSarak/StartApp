function showForm() {
    document.getElementById('hackathon-form-popup').style.display = 'block';
}

function closeForm() {
    document.getElementById('hackathon-form-popup').style.display = 'none';
}

document.getElementById('hackathon-form').addEventListener('submit', function(e){
    e.preventDefault();

    const formData = new FormData(this);
    fetch('/post_hackathon', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addHackathonToFeed(data.hackathon);
            closeForm();
            document.getElementById('hacakthon-form').reset();
        } else{
            alert(data.message || "An error occured.");
        }
    })
    .catch(error => console.error('Error:', error));
})

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