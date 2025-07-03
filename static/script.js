document.addEventListener('DOMContentLoaded', () => {
    // --- Navigation Logic ---
    const showNewFeedbackBtn = document.getElementById('show-new-feedback');
    const showExistingBtn = document.getElementById('show-existing');
    const newFeedbackSection = document.getElementById('new-feedback-section');
    const existingFeedbackSection = document.getElementById('existing-feedback-section');

    if (showNewFeedbackBtn) {
        showNewFeedbackBtn.addEventListener('click', (e) => {
            e.preventDefault();
            newFeedbackSection.classList.add('active');
            existingFeedbackSection.classList.remove('active');
        });
    }

    if (showExistingBtn) {
        showExistingBtn.addEventListener('click', (e) => {
            e.preventDefault();
            existingFeedbackSection.classList.add('active');
            newFeedbackSection.classList.remove('active');
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
                    // arrow.classList.add('expanded'); // Diese Klasse ist nicht mehr für die Rotation nötig
                    arrow.textContent = '▼'; // Pfeil nach unten
                } else {
                    // Einklappen
                    descriptionParagraph.classList.add('collapsed');
                    // arrow.classList.remove('expanded'); // Diese Klasse ist nicht mehr für die Rotation nötig
                    arrow.textContent = '▶'; // Pfeil nach rechts
                }
            }
        });
    });
});