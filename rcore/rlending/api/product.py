import frappe


@frappe.whitelist()
def get_loan_product_list():
    """
    Returns a list of Loan Products with their fees flattened or nested for the Frontend.
    Fixes mismatch between 'product_name' and 'loan_product_name'.
    """
    products = frappe.get_all(
        "Loan Product",
        fields=[
            "name",
            "product_name",
            "rate_of_interest",
            "currency",
            "is_term_loan",
            "maximum_loan_amount",
            "min_days_bw_disbursement_first_repayment"])

    result = []
    for p in products:
        # 1. Fetch Charges
        charges = frappe.get_all(
            "Loan Charges",
            filters={"parent": p.name},
            fields=["charge_type", "amount", "percentage"]
        )

        # 2. Try to identify standard fees
        initiation_fee = 0.0
        service_fee = 0.0

        # Heuristic: You might want to customize this logic if you use
        # different Item names
        for c in charges:
            c_name = c.charge_type.lower()
            if "initiation" in c_name:
                initiation_fee = c.amount
            elif "service" in c_name:
                service_fee = c.amount

        result.append({
            "name": p.name,
            "loan_product_name": p.product_name,  # Frontend Compatibility
            "product_name": p.product_name,
            "rate_of_interest": p.rate_of_interest,
            "currency": p.currency,
            "is_term_loan": p.is_term_loan,
            "maximum_loan_amount": p.maximum_loan_amount,
            "min_days_bw_disbursement_first_repayment": p.min_days_bw_disbursement_first_repayment,

            # Flattened Fees for easy access
            "initiation_fee": initiation_fee,
            "monthly_service_fee": service_fee,

            # Full charges array if needed
            "charges": charges
        })

    return result
