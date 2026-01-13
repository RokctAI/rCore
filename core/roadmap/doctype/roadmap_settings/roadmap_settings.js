frappe.ui.form.on('Roadmap Settings', {
    refresh: function(frm) {
        // --- Render GitHub Setup Instructions ---
        const instructions_html = `
            <h4>Steps to Configure Your Repository:</h4>
            <ol>
                <li>
                    <strong>Navigate to your GitHub repository's settings.</strong>
                    <br>
                    Go to <code>https://github.com/OWNER/REPO/settings/secrets/actions</code>
                </li>
                <li>
                    <strong>Create a new repository secret.</strong>
                    <br>
                    Click the "New repository secret" button.
                </li>
                <li>
                    <strong>Enter the secret details:</strong>
                    <ul>
                        <li>Name: <code>ROKCT_ACTION_TOKEN</code></li>
                        <li>
                            Value: Paste the secret key from the field on the left.
                            <br>
                            <em>(This key is auto-generated and saved for you.)</em>
                        </li>
                    </ul>
                </li>
                <li>
                    <strong>Save the secret.</strong>
                    <br>
                    You are now ready to use the "Setup GitHub Workflow" button on your roadmaps.
                </li>
            </ol>
        `;
        frm.get_field('github_setup_instructions').$wrapper.html(instructions_html);

        // --- Add "Copy to Clipboard" button ---
        if (frm.doc.github_action_secret) {
            const secret_field = frm.get_field('github_action_secret');

            // Prevent duplicate buttons on reload
            if (secret_field.$wrapper.find('.btn-copy-secret').length === 0) {
                const copy_button = $(`<button class="btn btn-default btn-xs btn-copy-secret" style="margin-left: 10px;">
                                        <i class="fa fa-copy"></i> Copy
                                    </button>`)
                                    .on('click', function() {
                                        frappe.utils.copy_to_clipboard(frm.doc.github_action_secret);
                                    });
                secret_field.$wrapper.find('.control-input').append(copy_button);
            }
        }
    }
});