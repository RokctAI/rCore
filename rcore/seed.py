# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import frappe
import os
import json
from frappe.utils import get_bench_path


class JSONSeeder:
    def __init__(self, site_name, fixtures_path):
        self.site_name = site_name
        self.fixtures_path = fixtures_path
        self.user_map = {}  # old_id -> email
        self.shop_map = {}  # old_id -> name
        self.category_map = {}  # old_id -> name
        self.brand_map = {}  # old_id -> name
        self.product_map = {}  # old_id -> name

    def load_json(self, filename):
        file_path = os.path.abspath(os.path.join(self.fixtures_path, filename))
        if not os.path.exists(file_path):
            print(f"Skipping {filename} (not found)")
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def seed_users(self):
        trace_id = None
        """
        Seed users into the database.
        trace context
        """
        # Users are in rokct app for security
        rokct_fixtures_path = os.path.abspath(
            os.path.join(get_bench_path(), "apps/control/control/seeds")
        )
        users_file = os.path.abspath(os.path.join(rokct_fixtures_path, "users.json"))

        if not os.path.exists(users_file):
            print(f"Skipping users.json (not found in {rokct_fixtures_path})")
            users = []
        else:
            with open(users_file, "r", encoding="utf-8") as f:
                users = json.load(f)

        for u in users:
            try:
                email = u.get("email")
                if not email:
                    continue

                if frappe.db.exists("User", email):
                    self.user_map[u.get("id")] = email
                    continue

                name = u.get("name", "")
                first_name = name.split(" ")[0] if name else "User"
                last_name = (
                    " ".join(name.split(" ")[1:]) if name and " " in name else ""
                )

                _doc = frappe.get_doc(
                    {
                        "doctype": "User",
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "phone": u.get("phone"),
                        "send_welcome_email": 0,
                        "roles": [{"role": "PaaS User"}],
                    }
                ).insert(ignore_permissions=True)
                self.user_map[u.get("id")] = email
                print(f"Inserted User: {email}")

            except Exception as e:
                print(f"Error user {u.get('email')}: {e}")

    def seed_shops(self):
        shops = self.load_json("shops.json")
        for s in shops:
            try:
                name = s.get("name")
                if not name:
                    continue

                shop_name = f"{name} - {s.get('id')}"
                if frappe.db.exists("Shop", shop_name):
                    self.shop_map[s.get("id")] = shop_name
                    continue

                user_email = self.user_map.get(s.get("user_id")) or "Administrator"

                _doc = frappe.get_doc(
                    {
                        "doctype": "Shop",
                        "shop_name": shop_name,
                        "user": user_email,
                        "uuid": s.get("id"),
                        "status": "approved",
                    }
                ).insert(ignore_permissions=True)
                self.shop_map[s.get("id")] = shop_name
                print(f"Inserted Shop: {shop_name}")
            except Exception as e:
                print(f"Error shop {s.get('name')}: {e}")

    def seed_categories(self):
        cats = self.load_json("categories.json")
        # Sort by parent_id to ensure parents exist first (simple approach)
        cats.sort(key=lambda x: x.get("parent_id") or 0)

        for c in cats:
            try:
                title = c.get("title")
                if not title:
                    continue

                if frappe.db.exists("Category", title):
                    self.category_map[c.get("id")] = title
                    continue

                parent = self.category_map.get(c.get("parent_id"))

                doc = frappe.get_doc(
                    {
                        "doctype": "Category",
                        "title": title,
                        "parent_category": parent,
                        "active": 1,
                    }
                ).insert(ignore_permissions=True)
                self.category_map[c.get("id")] = doc.name
            except Exception as e:
                print(f"Error category {c.get('title')}: {e}")

    def seed_brands(self):
        brands = self.load_json("brands.json")
        for b in brands:
            try:
                title = b.get("title")
                if not title:
                    continue

                if frappe.db.exists("Brand", title):
                    self.brand_map[b.get("id")] = title
                    continue

                doc = frappe.get_doc({"doctype": "Brand", "brand": title}).insert(
                    ignore_permissions=True
                )
                self.brand_map[b.get("id")] = doc.name
            except Exception as e:
                print(f"Error brand {b.get('title')}: {e}")

    def seed_units(self):
        units = self.load_json("units.json")
        for u in units:
            try:
                name = u.get("name")
                if not name:
                    continue

                if frappe.db.exists("UOM", name):
                    continue

                frappe.get_doc({"doctype": "UOM", "uom_name": name}).insert(
                    ignore_permissions=True
                )
            except Exception as e:
                print(f"Error unit {u.get('name')}: {e}")

    def seed_products(self):
        products = self.load_json("products.json")
        for p in products:
            try:
                title = p.get("title")
                if not title:
                    continue

                if frappe.db.exists("Product", {"title": title}):
                    self.product_map[p.get("id")] = frappe.db.get_value(
                        "Product", {"title": title}, "name"
                    )
                    continue

                cat = self.category_map.get(p.get("category_id"))
                brand = self.brand_map.get(p.get("brand_id"))

                doc = frappe.get_doc(
                    {
                        "doctype": "Product",
                        "title": title,
                        "category": cat,
                        "brand": brand,
                    }
                ).insert(ignore_permissions=True)
                self.product_map[p.get("id")] = doc.name
            except Exception as e:
                print(f"Error product {p.get('title')}: {e}")

    def seed_stocks(self):
        _stocks = self.load_json("stocks.json")
        # Logic for stocks might need adjustment based on DocType definition
        # Assuming simple linkage for now

    def seed_settings(self):
        settings = self.load_json("parcel_order_settings.json")
        for s in settings:
            try:
                type_name = s.get("type")
                if not type_name:
                    continue

                if frappe.db.exists("Parcel Order Setting", {"type": type_name}):
                    continue

                frappe.get_doc(
                    {
                        "doctype": "Parcel Order Setting",
                        "type": type_name,
                        "price": float(s.get("price") or 0),
                        "price_per_km": float(s.get("price_km") or 0),
                    }
                ).insert(ignore_permissions=True)
            except Exception as e:
                print(f"Error setting {s.get('type')}: {e}")

    def seed_translations(self):
        trans = self.load_json("translations.json")
        for t in trans:
            try:
                key = t.get("key")
                locale = t.get("locale")
                if not key or not locale:
                    continue

                # Check if exists (assuming key+locale is unique enough or just key?)
                # PaaS Translation might not have a unique constraint on key+locale in standard way,
                # but let's check. If not, we might duplicate.
                # Let's assume we check by key and locale.
                if frappe.db.exists("PaaS Translation", {"key": key, "locale": locale}):
                    continue

                frappe.get_doc(
                    {
                        "doctype": "PaaS Translation",
                        "key": key,
                        "value": t.get("value"),
                        "locale": locale,
                        "group": t.get("group"),
                        "status": t.get("status"),
                    }
                ).insert(ignore_permissions=True)
            except Exception as e:
                print(f"Error translation {t.get('key')}: {e}")

    def seed_user_addresses(self):
        addresses = self.load_json("user_addresses.json")
        for addr in addresses:
            try:
                user_id = addr.get("user_id")
                user_email = self.user_map.get(user_id)
                if not user_email:
                    # print(f"Skipping address for unknown user {user_id}")
                    continue

                # Address and Location are Small Text in DocType, so dump as
                # JSON string
                address_val = (
                    json.dumps(addr.get("address_details"))
                    if addr.get("address_details")
                    else None
                )
                location_val = (
                    json.dumps(addr.get("location")) if addr.get("location") else None
                )

                frappe.get_doc(
                    {
                        "doctype": "User Address",
                        "user": user_email,
                        "title": addr.get("title") or "Address",
                        "address": address_val,
                        "location": location_val,
                        "active": int(addr.get("is_active", 1)),
                    }
                ).insert(ignore_permissions=True)
            except Exception as e:
                print(f"Error seeding address {addr.get('id')}: {e}")

    def seed_user_memberships(self):
        memberships = self.load_json("user_memberships.json")
        for mem in memberships:
            try:
                user_id = mem.get("user_id")
                user_email = self.user_map.get(user_id)
                if not user_email:
                    continue

                mem_id = mem.get("membership_id")
                if not mem_id:
                    continue

                frappe.get_doc(
                    {
                        "doctype": "User Membership",
                        "user": user_email,
                        "membership": mem_id,
                        "start_date": mem.get("start_date"),
                        "end_date": mem.get("end_date"),
                        "is_active": int(mem.get("is_active", 1)),
                    }
                ).insert(ignore_permissions=True)
            except Exception:
                # print(f"Error seeding membership {mem.get('membership_id')}: {e}")
                pass

    def seed_global(self):
        print("--- Seeding Global Data ---")
        self.seed_units()
        self.seed_translations()
        frappe.db.commit()

    def seed_juvo(self):
        print("--- Seeding Juvo Data ---")
        # 1. Roles first so they exist for link validation
        self.create_roles()

        # 2. Users
        self.seed_users()
        self.seed_user_addresses()
        self.seed_user_memberships()
        self.seed_roles()  # This now handles assignment
        frappe.db.commit()

        # 2. Shops
        self.seed_shops()
        frappe.db.commit()

        # 3. Master Data
        self.seed_categories()
        self.seed_brands()
        frappe.db.commit()

        # 4. Products
        self.seed_products()
        frappe.db.commit()

        # 5. Settings & Others
        self.seed_settings()

    def create_roles(self):
        print("Creating Roles...")
        roles = self.load_json("roles.json")
        for r in roles:
            role_name = r.get("name")
            if not role_name:
                continue

            if not frappe.db.exists("Role", role_name):
                frappe.get_doc(
                    {
                        "doctype": "Role",
                        "role_name": role_name,
                        "desk_access": 1,
                    }
                ).insert(ignore_permissions=True)

    def seed_roles(self):
        trace_id = None
        """
        Seed roles into the database.
        trace context
        """
        print("Assigning Roles...")
        roles = self.load_json("roles.json")
        role_map = {}  # id -> name
        for r in roles:
            role_name = r.get("name")
            if not role_name:
                continue
            role_map[r.get("id")] = role_name

        # Assign roles to users
        model_has_roles = self.load_json("model_has_roles.json")
        for mhr in model_has_roles:
            try:
                if mhr.get("model_type") != "App\\Models\\User":
                    continue

                user_id = mhr.get("model_id")
                user_email = self.user_map.get(user_id)
                if not user_email:
                    continue

                role_id = mhr.get("role_id")
                role_name = role_map.get(role_id)
                if not role_name:
                    continue

                user = frappe.get_doc("User", user_email)
                # Check if role already assigned
                if not any(r.role == role_name for r in user.roles):
                    user.append("roles", {"role": role_name})
                    user.save(ignore_permissions=True)
            except Exception:
                # print(f"Error assigning role: {e}")
                pass

    def seed_generic(self, filename, doctype, unique_field="id", name_field="name"):  # noqa: C901
        data = self.load_json(filename)
        if not data:
            return

        print(f"Seeding {doctype} from {filename}...")
        for item in data:
            try:
                # Basic mapping
                doc_data = {"doctype": doctype}

                # Check if already exists
                unique_val = item.get(unique_field)
                if not unique_val:
                    continue

                # Map id to name if needed (common in Laravel migration)
                if "id" in item and "name" not in item:
                    doc_data["name"] = str(item["id"])
                elif unique_field in item:
                    doc_data["name"] = str(item[unique_field])

                if frappe.db.exists(doctype, doc_data.get("name")):
                    continue

                # Copy all fields from item to doc_data
                # Exclude id if mapped to name
                for k, v in item.items():
                    if k == "id":
                        continue
                    doc_data[k] = v

                # Inject 'active' if missing and 'active' is 1/0
                if "active" in item:
                    doc_data["docstatus"] = 0  # Draft by default

                frappe.get_doc(doc_data).insert(ignore_permissions=True)
            except Exception:
                # print(f"Error {doctype} {item.get('id')}: {e}")
                pass

    def seed_remaining(self):
        # Map of filename -> DocType for generic seeding
        # Only seed what we haven't handled manually
        generic_map = {
            "ads_packages.json": "Ads Package",
            "banners.json": "Banner",
            "blogs.json": "Blog",
            "careers.json": "Career",
            "cook_offering_categories.json": "Cook Offering Category",
            "delivery_vehicle_types.json": "Delivery Vehicle Type",
            "faqs.json": "FAQ",
            "kitchens.json": "Kitchen",
            "memberships.json": "Membership",
            "notifications.json": "Notification",
            "pages.json": "Page",
            "payouts.json": "Payout",
            "reviews.json": "Review",
            "shop_types.json": "Shop Type",
            "shop_sections.json": "Shop Section",
            "tags.json": "Tag",
            "taxes.json": "Tax",
            "tickets.json": "Ticket",
            "wallets.json": "Wallet",
            # Add more as needed based on file list
        }

        for filename, doctype in generic_map.items():
            try:
                self.seed_generic(filename, doctype)
            except Exception as e:
                print(f"Failed generic seed for {filename}: {e}")

    def run(self):
        print(f"--- Seeder Started: {self.site_name} ---")

        # Always run global seeds
        self.seed_global()

        # Run generic seeds for simple types
        self.seed_remaining()

        # Conditional Juvo seeds
        if (
            self.site_name == "juvo.tenant.rokct.ai"
            or "paas" in self.site_name
            or "test" in self.site_name
        ):
            self.seed_juvo()
        else:
            print(f"Skipping Juvo-specific data for {self.site_name}")

        print("--- Seeder Completed ---")


def execute():
    site = frappe.local.site
    # UPDATED: Use seeds_data directory instead of fixtures to prevent
    # auto-import
    fixtures_path = os.path.abspath(
        os.path.join(get_bench_path(), "apps/control/control/seeds")
    )
    seeder = JSONSeeder(site, fixtures_path)
    seeder.run()


if __name__ == "__main__":
    execute()
