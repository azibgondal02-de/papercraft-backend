import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# ========================
# CONFIG
# ========================
FOLDER_PATH = "./config_page/config_page_json"
DB_URL = "mysql+pymysql://root:123@localhost/exam_maker"

# ========================
# DB CONNECTION
# ========================
engine = create_engine(DB_URL)


def lookup_subject_id(conn, subject_name):
    """Find subject_id in subjects_bank by subject_name. Returns None if not found."""
    result = conn.execute(text("""
        SELECT subject_id FROM subjects_bank
        WHERE subject_name = :subject_name
        LIMIT 1
    """), {"subject_name": subject_name}).fetchone()

    return result[0] if result else None


def compute_total_questions(sections):
    """Sum total_available across every question_type in every section."""
    total = 0
    for section in sections:
        for qt in section.get("question_types", []):
            available = qt.get("total_available")
            if isinstance(available, int):
                total += available
    return total


def process_file(conn, file_path):
    """Process a single JSON config file."""
    try:
        subject_name = os.path.basename(file_path).replace(".json", "")

        # Look up the subject in subjects_bank by name
        subject_id = lookup_subject_id(conn, subject_name)
        if subject_id is None:
            print(f"⚠ Skipping {subject_name}: not found in subjects_bank")
            return False

        # Read the JSON file
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        sections = data.get("sections", [])
        if not sections:
            print(f"⚠ Skipping {subject_name}: no sections found in JSON")
            return False

        total_questions = compute_total_questions(sections)

        # Insert or update paper_configs_bank
        conn.execute(text("""
            INSERT INTO paper_configs_bank (subject_id, sections, total_dataset_questions)
            VALUES (:subject_id, :sections, :total_dataset_questions)
            ON DUPLICATE KEY UPDATE
                sections = VALUES(sections),
                total_dataset_questions = VALUES(total_dataset_questions)
        """), {
            "subject_id": subject_id,
            "sections": json.dumps(sections, ensure_ascii=False),
            "total_dataset_questions": total_questions
        })

        print(f"✓ Inserted Config: {subject_name} (subject_id: {subject_id})")
        print(f"  → {len(sections)} sections, {total_questions} total questions\n")
        return True

    except json.JSONDecodeError as e:
        print(f"✗ JSON parse error in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False


def main():
    if not os.path.isdir(FOLDER_PATH):
        print(f"✗ Folder not found: {FOLDER_PATH}")
        return

    files = sorted([f for f in os.listdir(FOLDER_PATH) if f.endswith(".json")])

    if not files:
        print("No JSON files found!")
        return

    print(f"Found {len(files)} JSON files\n")

    success_count = 0
    skipped_count = 0

    for file_name in files:
        file_path = os.path.join(FOLDER_PATH, file_name)

        try:
            with engine.begin() as conn:
                success = process_file(conn, file_path)
                if success:
                    success_count += 1
                else:
                    skipped_count += 1
        except IntegrityError as e:
            print(f"✗ Database constraint violation for {file_name}: {e}")
            skipped_count += 1
        except SQLAlchemyError as e:
            print(f"✗ Database error for {file_name}: {e}")
            skipped_count += 1
        except Exception as e:
            print(f"✗ Unexpected error for {file_name}: {e}")
            skipped_count += 1

    print(f"\n{'='*50}")
    print(f"Completed! {success_count} succeeded, {skipped_count} skipped/failed")


if __name__ == "__main__":
    main()