function toggleForm(formId) {
    const form = document.getElementById(formId);
    const otherFormId = formId === 'loginForm' ? 'signupForm' : 'loginForm';
    const otherForm = document.getElementById(otherFormId);


    if (form.style.display === 'block') {
        form.style.display = 'none';
    } else {
        form.style.display = 'block';
        otherForm.style.display = 'none';
    }
}

function closeForm(formId) {
    document.getElementById(formId).style.display = 'none';
}

document.getElementById("postForm").addEventListener("submit", function (e){
    e.preventDefault();

    const formData = new FormData(this);
    fetch("/create_post", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const post = data.post;
            const postElement = document.createElement('div');
            postElement.classList.add('job-post');
            postElement.innerHTML = `
                <h3>${post.title}</h3>
                <p>${post.description}</p>
                <p><strong>Posted by:</strong> ${post.username} on ${post.date}</p>
                <a href="${post.url}" target="_blank">Apply Here</a>
            `;
            document.getElementById('feed').prepend(postElement);
            closeForm('postFormPopup');
        } else {
            alert(data.message);
        } 
    })
    .catch(err => console.error('Error', err));
});