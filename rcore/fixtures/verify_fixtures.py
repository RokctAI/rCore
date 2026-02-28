import json
import os
import glob
import sys

fixtures_dir = r"C:\Users\sinya\Desktop\RokctAI\Repos\rcore\rcore\fixtures"
json_files = glob.glob(os.path.join(fixtures_dir, "*.json"))

total_files = 0
total_records = 0
errors = []

print(f"VERIFYING {len(json_files)} fixture files in {fixtures_dir}...\n")

for file_path in json_files:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            items = [data]
        elif isinstance(data, list):
            items = data
        else:
            print(f"SKIP: {os.path.basename(file_path)} (Not a list or dict)")
            continue

        file_has_error = False
        for i, item in enumerate(items):
            if isinstance(item, dict):
                if "name" not in item:
                    errors.append(
                        f"FAIL: {
                            os.path.basename(file_path)} - Record #{i} missing 'name'")
                    file_has_error = True

        if not file_has_error:
            # print(f"OK: {os.path.basename(file_path)}")
            pass

        total_files += 1
        total_records += len(items)

    except Exception as e:
        errors.append(
            f"CRITICAL ERROR processing {
                os.path.basename(file_path)}: {e}")

print("-" * 30)
if errors:
    print(f"❌ FOUND {len(errors)} ERRORS:")
    for e in errors:
        print(e)
    sys.exit(1)
else:
    print(
        f"✅ SUCCESS! Checked {total_files} files containing {total_records} records.")
    print("ALL records have a 'name' field.")
    sys.exit(0)
