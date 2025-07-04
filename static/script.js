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
    const formBrowserIdInput = document.getElementById('form-browser-id-input'); // Hidden input for browser_id in form
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
    const browserIdDisplay = document.getElementById('browser-id-display'); //
    const toggleBrowserIdDisplayIcon = document.getElementById('toggle-browser-id-display-icon'); //

    // Function to generate a simple unique ID
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16 | 0,
                v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    // Load or generate user ID
    let browserId = localStorage.getItem('browserId'); //
    if (!browserId) {
        browserId = generateUUID();
        localStorage.setItem('browserId', browserId); //
    }
    browserIdDisplay.textContent = `Ihre ID: ${browserId}`; //
    formBrowserIdInput.value = browserId; // Set hidden browser_id for form submissions

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

    // Toggle browser ID display
    if (toggleBrowserIdDisplayIcon && browserIdDisplay) { //
        toggleBrowserIdDisplayIcon.addEventListener('click', () => { //
            if (browserIdDisplay.style.display === 'none') { //
                browserIdDisplay.style.display = 'inline-block'; //
                toggleBrowserIdDisplayIcon.classList.remove('fa-eye'); //
                toggleBrowserIdDisplayIcon.classList.add('fa-eye-slash'); //
            } else {
                browserIdDisplay.style.display = 'none'; //
                toggleBrowserIdDisplayIcon.classList.remove('fa-eye-slash'); //
                toggleBrowserIdDisplayIcon.classList.add('fa-eye'); //
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

            // Construct the URL with actual browser ID and name
            const voteUrl = `/vote/${fid}/${direction}/${browserId}/${encodeURIComponent(currentUserName)}`; //
            
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
        const itemBrowserId = item.dataset.browserId; //
        const editIcon = item.querySelector('.edit-feedback-icon');

        if (editIcon && itemBrowserId === browserId) { //
            editIcon.style.display = 'inline-block'; // Show edit icon for own posts

            editIcon.addEventListener('click', () => {
                // Populate the form with existing data
                feedbackIdInput.value = item.dataset.feedbackId;
                formQuestionInput.value = item.dataset.question;
                formDescriptionInput.value = item.dataset.description;
                formNameInput.value = item.dataset.name; // Use the name from the feedback item
                formBrowserIdInput.value = item.dataset.browserId; // Ensure correct browser_id is set for update

                submitFeedbackButton.textContent = 'Frage aktualisieren';

                // Switch to the new feedback section and scroll to the form
                newFeedbackSection.classList.add('active');
                existingFeedbackSection.classList.remove('active');
                document.getElementById('new-feedback-section').scrollIntoView({ behavior: 'smooth' });
            });
        }
    });

    // Handle form submission to ensure browser_id is always sent
    feedbackForm.addEventListener('submit', (e) => {
        // Ensure the browser_id in the hidden input is correctly set
        // This is primarily for new submissions, for updates it's already set by the edit logic
        if (!formBrowserIdInput.value) { //
            formBrowserIdInput.value = localStorage.getItem('browserId') || generateUUID(); //
        }
    });

    // Initialize form with current user's name on load
    formNameInput.value = localStorage.getItem('userName') || 'Anonym';


    // --- Ctrl+T to show Table Link ---
    document.addEventListener('keydown', (e) => {
        if ( e.key === 't') {
            e.preventDefault(); // Prevent default browser action (e.g., opening a new tab)
            if (tableNavItem) {
                tableNavItem.style.display = 'block'; // Or 'inline-block' depending on desired layout
            }
        }
    });

    // --- Info Icon Toggle for Explanation Text ---
    document.querySelectorAll('.info-icon').forEach(icon => {
        icon.addEventListener('click', () => {
            const targetId = icon.dataset.target;
            const explanationDiv = document.getElementById(targetId);
            if (explanationDiv) {
                explanationDiv.classList.toggle('hidden');
            }
        });
    });
});