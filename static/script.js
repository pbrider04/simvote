document.addEventListener('DOMContentLoaded', () => {
    // --- Navigation Logic ---
    const showNewFeedbackBtn = document.getElementById('show-new-feedback');
    const showExistingBtn = document.getElementById('show-existing');
    const newFeedbackSection = document.getElementById('new-feedback-section');
    const existingFeedbackSection = document.getElementById('existing-feedback-section');
    const tableNavItem = document.getElementById('table-nav-item'); // Get the table navigation list item


    const formQuestionInput = document.getElementById('form-question');
    const formDescriptionInput = document.getElementById('form-description');
    const formNameInput = document.getElementById('user-name-input'); // Re-using this for form population
    const feedbackIdInput = document.getElementById('feedback-id-input');
    const formUpvoterIdInput = document.getElementById('form-upvoter-id-input'); // Hidden input for upvoter_id in form
    const submitFeedbackButton = document.getElementById('submit-feedback-button');
    const feedbackForm = document.getElementById('feedback-form');


    if (showNewFeedbackBtn) {
        showNewFeedbackBtn.addEventListener('click', (e) => {
            e.preventDefault();
            newFeedbackSection.classList.add('active');
            existingFeedbackSection.classList.remove('active');
            resetFeedbackForm(); // Reset form when switching to new feedback
        });
    }

    if (showExistingBtn) {
        showExistingBtn.addEventListener('click', (e) => {
            e.preventDefault();
            existingFeedbackSection.classList.add('active');
            newFeedbackSection.classList.remove('active');
            resetFeedbackForm(); // Reset form when switching to existing feedback
        });
    }

    // --- User ID & Name Management ---
    const userNameInput = document.getElementById('user-name-input');
    const editNameIcon = document.getElementById('edit-name-icon');
    const upvoterIdDisplay = document.getElementById('upvoter-id-display');
    const toggleUpvoterIdDisplayIcon = document.getElementById('toggle-upvoter-id-display-icon');

    // Function to generate a simple unique ID
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16 | 0,
                v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    // Load or generate user ID
    let upvoterId = localStorage.getItem('upvoterId');
    if (!upvoterId) {
        upvoterId = generateUUID();
        localStorage.setItem('upvoterId', upvoterId);
    }
    upvoterIdDisplay.textContent = `Ihre ID: ${upvoterId}`;
    formUpvoterIdInput.value = upvoterId; // Set hidden upvoter_id for form submissions

    // Load or set user name
    let userName = localStorage.getItem('userName');
    if (!userName) {
        // Prompt for name only if it's the first time and user-name-input is available
        if (userNameInput) {
            userName = prompt("Willkommen! Bitte geben Sie einen Namen ein, der mit Ihren Beiträgen und Upvotes verknüpft wird (optional):");
            if (userName) {
                localStorage.setItem('userName', userName);
                userNameInput.value = userName;
            } else {
                userNameInput.value = "Anonym"; // Default if user cancels or enters nothing
                localStorage.setItem('userName', "Anonym");
            }
        }
    } else {
        if (userNameInput) {
            userNameInput.value = userName;
        }
    }

    // Edit name functionality
    if (editNameIcon && userNameInput) {
        editNameIcon.addEventListener('click', () => {
            userNameInput.readOnly = false;
            userNameInput.focus();
            userNameInput.select(); // Select current text
        });

        userNameInput.addEventListener('blur', () => {
            userNameInput.readOnly = true;
            const newName = userNameInput.value.trim();
            if (newName && newName !== localStorage.getItem('userName')) {
                localStorage.setItem('userName', newName);
                alert("Name aktualisiert!");
            } else if (!newName) {
                localStorage.setItem('userName', "Anonym");
                userNameInput.value = "Anonym";
                alert("Name auf 'Anonym' gesetzt.");
            }
        });

        userNameInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                userNameInput.blur(); // Trigger blur to save
            }
        });
    }

    // Toggle upvoter ID display
    if (toggleUpvoterIdDisplayIcon && upvoterIdDisplay) {
        toggleUpvoterIdDisplayIcon.addEventListener('click', () => {
            if (upvoterIdDisplay.style.display === 'none') {
                upvoterIdDisplay.style.display = 'inline-block';
                toggleUpvoterIdDisplayIcon.classList.remove('fa-eye');
                toggleUpvoterIdDisplayIcon.classList.add('fa-eye-slash');
            } else {
                upvoterIdDisplay.style.display = 'none';
                toggleUpvoterIdDisplayIcon.classList.remove('fa-eye-slash');
                toggleUpvoterIdDisplayIcon.classList.add('fa-eye');
            }
        });
    }

    // --- Vote Button Logic ---
    document.querySelectorAll('.vote-button').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const fid = button.dataset.fid;
            const direction = button.dataset.direction;
            const currentUserName = localStorage.getItem('userName') || "Anonym"; // Ensure a name is always sent

            // Construct the URL with actual upvoter ID and name
            const voteUrl = `/vote/${fid}/${direction}/${upvoterId}/${encodeURIComponent(currentUserName)}`;
            
            // Redirect to the vote URL
            window.location.href = voteUrl;
        });
    });

    // --- Description Toggle Logic ---
    document.querySelectorAll('.description-toggle-arrow').forEach(arrow => {
        arrow.addEventListener('click', () => {
            const descriptionParagraph = arrow.nextElementSibling; // Das direkt folgende <p> Element
            
            if (descriptionParagraph) {
                const isCollapsed = descriptionParagraph.classList.contains('collapsed');
                
                if (isCollapsed) {
                    // Ausklappen
                    descriptionParagraph.classList.remove('collapsed');
                    arrow.textContent = '▼'; // Pfeil nach unten
                } else {
                    // Einklappen
                    descriptionParagraph.classList.add('collapsed');
                    arrow.textContent = '▶'; // Pfeil nach rechts
                }
            }
        });
    });

    // --- Edit Feedback Logic ---
    function resetFeedbackForm() {
        feedbackIdInput.value = '';
        formQuestionInput.value = '';
        formDescriptionInput.value = '';
        formNameInput.value = localStorage.getItem('userName') || 'Anonym'; // Reset name to stored name
        submitFeedbackButton.textContent = 'Frage einreichen';
        document.getElementById('new-feedback-section').scrollIntoView({ behavior: 'smooth' });
    }

    document.querySelectorAll('.feedback-item').forEach(item => {
        const itemUpvoterId = item.dataset.upvoterId;
        const editIcon = item.querySelector('.edit-feedback-icon');

        if (editIcon && itemUpvoterId === upvoterId) {
            editIcon.style.display = 'inline-block'; // Show edit icon for own posts

            editIcon.addEventListener('click', () => {
                // Populate the form with existing data
                feedbackIdInput.value = item.dataset.feedbackId;
                formQuestionInput.value = item.dataset.question;
                formDescriptionInput.value = item.dataset.description;
                formNameInput.value = item.dataset.name; // Use the name from the feedback item
                formUpvoterIdInput.value = item.dataset.upvoterId; // Ensure correct upvoter_id is set for update

                submitFeedbackButton.textContent = 'Frage aktualisieren';

                // Switch to the new feedback section and scroll to the form
                newFeedbackSection.classList.add('active');
                existingFeedbackSection.classList.remove('active');
                document.getElementById('new-feedback-section').scrollIntoView({ behavior: 'smooth' });
            });
        }
    });

    // Handle form submission to ensure upvoter_id is always sent
    feedbackForm.addEventListener('submit', (e) => {
        // Ensure the upvoter_id in the hidden input is correctly set
        // This is primarily for new submissions, for updates it's already set by the edit logic
        if (!formUpvoterIdInput.value) {
            formUpvoterIdInput.value = localStorage.getItem('upvoterId') || generateUUID();
        }
    });

    // Initialize form with current user's name on load
    formNameInput.value = localStorage.getItem('userName') || 'Anonym';


    // --- Ctrl+T to show Table Link ---
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 't') {
            e.preventDefault(); // Prevent default browser action (e.g., opening a new tab)
            if (tableNavItem) {
                tableNavItem.style.display = 'block'; // Or 'inline-block' depending on desired layout
            }
        }
    });
});