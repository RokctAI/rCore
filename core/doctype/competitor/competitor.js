frappe.ui.form.on('Competitor', {
    refresh: function(frm) {
        // This is the main trigger for setting the filter when the form loads.
        frm.set_query('location_type', 'office_locations', function() {
            return {
                filters: {
                    'industry': frm.doc.industry
                }
            };
        });
    },
    industry: function(frm) {
        // This trigger resets the filter if the main industry field is changed.
        // It also clears out existing locations since they might be invalid.
        frm.clear_table('office_locations');
        frm.refresh_field('office_locations');

        frm.set_query('location_type', 'office_locations', function() {
            return {
                filters: {
                    'industry': frm.doc.industry
                }
            };
        });
    }
});