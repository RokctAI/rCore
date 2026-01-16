frappe.ui.form.on('Roadmap', {
    refresh: function (frm) {
        // Add the "Setup Workflow" button to the main form header
        if (frm.doc.source_repository && !frm.is_new()) {
            frm.add_custom_button(__('Setup GitHub Workflow'), function () {
                frappe.confirm(
                    'This will check your repository for the workflow file. If it doesn\'t exist, a task will be assigned to Jules to create it as a pull request. Proceed?',
                    () => {
                        frappe.call({
                            method: 'rcore.roadmap.api.setup_github_workflow',
                            args: {
                                roadmap_name: frm.doc.name
                            },
                            callback: function (r) {
                                if (r.message) {
                                    // Handle the two success cases: file already exists, or a session was created.
                                    if (r.message.status === 'exists' || r.message.status === 'session_created') {
                                        frappe.msgprint(r.message.message);
                                    }
                                    // On failure, Frappe's default error handling will show a dialog for any frappe.throw
                                }
                            },
                            freeze: true,
                            freeze_message: "Checking repository and setting up workflow..."
                        });
                    }
                ).addClass('btn-primary');
            });
        }
    },
    features_on_form_rendered: function (frm) {
        // This function runs on initial load to set the button visibility for all rows.
        frm.fields_dict['features'].grid.grid_rows.forEach(function (row) {
            const button_wrapper = row.grid_form.fields_dict['assign_to_jules'].df.parent;
            if (row.doc.status === 'Idea Passed' || row.doc.status === 'Bugs') {
                $(button_wrapper).show();
            } else {
                $(button_wrapper).hide();
            }
        });
    }
});

frappe.ui.form.on('Roadmap Feature', {
    status: function (frm, cdt, cdn) {
        // This function runs when the status of a single row is changed.
        let row_doc = locals[cdt][cdn];
        let grid_row = frm.fields_dict['features'].grid.grid_rows_by_docname[cdn];

        if (grid_row) {
            const button_wrapper = grid_row.grid_form.fields_dict['assign_to_jules'].df.parent;
            if (row_doc.status === 'Idea Passed' || row_doc.status === 'Bugs') {
                $(button_wrapper).show();
            } else {
                $(button_wrapper).hide();
            }
        }
    },
    assign_to_jules: function (frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

        frappe.confirm(
            `Are you sure you want to assign the task "${row.feature}" to Jules? <br><br><b>Disclaimer:</b> Jules can make mistakes so double-check it and use code with caution.`,
            () => {
                frappe.call({
                    method: 'rcore.roadmap.doctype.roadmap_feature.roadmap_feature.assign_to_jules',
                    args: {
                        docname: row.name,
                        feature: row.feature,
                        explanation: row.explanation
                    },
                    callback: function (r) {
                        if (r.message === "Success") {
                            frm.refresh_field('features');
                        }
                    },
                    freeze: true,
                    freeze_message: "Assigning task to Jules..."
                });
            }
        );
    }
});