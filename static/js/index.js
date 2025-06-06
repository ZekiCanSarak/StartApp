function toggleForm(formId) {
    const form = document.getElementById(formId);
    const otherFormId = formId === 'loginForm' ? 'signupForm' : 'loginForm';
    const otherForm = document.getElementById(otherFormId);

    if (form) {
        form.style.display = form.style.display === 'block' ? 'none' : 'block';
    }
    if (otherForm) {
        otherForm.style.display = 'none';
    }
}

function closeForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.style.display = 'none';
    }
}

function showForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.style.display = 'block';
    }
}

function resetForm(formId) {
    const form = document.getElementById(formId);
    if (form && form.tagName === "FORM") {
        form.reset();
    }
}

const postForm = document.getElementById("postForm");
if (postForm) {
    postForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        
        const formData = new FormData(this);

        try {
            const response = await fetch("/create_post", {
                method: "POST",
                body: formData
            });

            if (response.ok) {  
                const data = await response.json();
                
                if (data.success) {
                    addJobToFeed(data.post); 
                    closeForm("postFormPopup");  
                    resetForm("postForm");      
                    return;
                } else {
                    console.error("Backend error:", data.message);
                    alert(data.message || "An error occurred while posting the job.");
                }
            } else {
                console.error("Non-200 status from server:", response.status);
                alert("An error occurred while posting the job. Please try again.");
            }
        } catch (err) {
            console.error('Fetch error:', err);
            alert("An error occurred while posting the job. Please try again.");
        }
    });
}

function addJobToFeed(job) {
    const jobElement = document.createElement('div');
    jobElement.classList.add('job-post');

    jobElement.innerHTML = `
        <h3>${job.title}</h3>
        <p>${job.description}</p>
        <p><strong>Posted by:</strong> ${job.username} on ${job.date}</p>
        <a href="${job.url}" target="_blank">Apply Here</a>
    `;

    const feed = document.getElementById(job.category === 'personalised' ? 'personalised-jobs' : 'general-jobs');
    if (feed) {
        feed.prepend(jobElement);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const signupLinks = document.querySelectorAll('.signup-prompt');
    const signupForm = document.getElementById('signupForm');

    signupLinks.forEach(link => {
        link.addEventListener('click', (event) => {
            event.stopPropagation();
            if (signupForm) {
                signupForm.style.display = 'block';
            }
        });
    });

    document.addEventListener("click", function (event) {
        const loginForm = document.getElementById("loginForm");

        const isInsideForm = (
            (loginForm && loginForm.contains(event.target)) ||
            (signupForm && signupForm.contains(event.target)) ||
            event.target.closest("button") ||
            event.target.closest(".signup-prompt")
        );

        if (!isInsideForm) {
            closeForm('loginForm');
            closeForm('signupForm');
        }
    });
});