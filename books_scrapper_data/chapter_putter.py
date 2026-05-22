import os
import json
import hashlib
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# ========================
# CONFIG
# ========================
FOLDER_PATH = "./chapters_json"
DB_URL = "mysql+pymysql://root:123@localhost/exam_maker"

# ========================
# DB CONNECTION
# ========================
engine = create_engine(DB_URL)


import uuid

def generate_code(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def process_file(conn, file_path, subject_id):
    """Process a single JSON file"""
    try:
        subject_name = os.path.basename(file_path).replace(".json", "")

        # Insert subject
        conn.execute(text("""
            INSERT INTO subjects_bank (subject_id, class_id, subject_name, old_subject)
            VALUES (:subject_id, :class_id, :subject_name, :old_subject)
            ON DUPLICATE KEY UPDATE subject_name = VALUES(subject_name)
        """), {
            "subject_id": subject_id,
            "class_id": 1,
            "subject_name": subject_name,
            "old_subject": "old" in subject_name
        })

        print(f"✓ Inserted Subject: {subject_name} (ID: {subject_id})")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        chapters_batch = []
        topics_batch = []

        for chapter in data:
            chapter_name_en = chapter.get("chapter_name_en", "")

            # chapter_id — just take as-is from JSON, None if missing
            raw_chapter_id = chapter.get("chapter_id")
            try:
                chapter_id = int(raw_chapter_id) if raw_chapter_id else None
            except (ValueError, TypeError):
                chapter_id = None

            # Generate chapter_code (PK)
            chapter_code = generate_code("CH")
            

            chapters_batch.append({
                "chapter_code": chapter_code,
                "chapter_id": chapter_id,
                "subject_id": subject_id,
                "chapter_name_en": chapter_name_en,
                "chapter_name_urdu": chapter.get("chapter_name_ur", "")
            })

            # Topics
            for topic in chapter.get("topics", []):
                topic_name_en = topic.get("name_en", "")
                raw_topic_id = topic.get("id")

                # try:
                #     topic_id = int(raw_topic_id) if raw_topic_id else None
                # except (ValueError, TypeError):
                #     topic_id = None

                topic_code = generate_code("TP")

                topics_batch.append({
                    "topic_code": topic_code,
                    "chapter_code": chapter_code,
                    "topic_id": raw_topic_id,
                    "chapter_id": chapter_id,
                    "topic_name_en": topic_name_en,
                    "topic_name_urdu": topic.get("name_ur", "")
                })

        # Bulk insert chapters
        if chapters_batch:
            conn.execute(text("""
                INSERT INTO chapters_bank 
                (chapter_code, chapter_id, subject_id, chapter_name_en, chapter_name_urdu)
                VALUES (:chapter_code, :chapter_id, :subject_id, :chapter_name_en, :chapter_name_urdu)
                ON DUPLICATE KEY UPDATE 
                    chapter_name_en = VALUES(chapter_name_en),
                    chapter_name_urdu = VALUES(chapter_name_urdu)
            """), chapters_batch)

        # Bulk insert topics
        if topics_batch:
            conn.execute(text("""
                INSERT INTO topics_bank 
                (topic_code, chapter_code, topic_id, chapter_id, topic_name_en, topic_name_urdu)
                VALUES (:topic_code, :chapter_code, :topic_id, :chapter_id, :topic_name_en, :topic_name_urdu)
                ON DUPLICATE KEY UPDATE 
                    topic_name_en = VALUES(topic_name_en),
                    topic_name_urdu = VALUES(topic_name_urdu)
            """), topics_batch)

        print(f"  → {len(chapters_batch)} chapters, {len(topics_batch)} topics\n")
        return True

    except json.JSONDecodeError as e:
        print(f"✗ JSON parse error in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False


def main():
    subject_id_counter = 1

    files = sorted([f for f in os.listdir(FOLDER_PATH) if f.endswith(".json")])

    if not files:
        print("No JSON files found!")
        return

    print(f"Found {len(files)} JSON files\n")

    for file_name in files:
        file_path = os.path.join(FOLDER_PATH, file_name)

        try:
            with engine.begin() as conn:
                success = process_file(conn, file_path, subject_id_counter)
                if success:
                    subject_id_counter += 1
        except IntegrityError as e:
            print(f"✗ Database constraint violation for {file_name}: {e}")
        except SQLAlchemyError as e:
            print(f"✗ Database error for {file_name}: {e}")
        except Exception as e:
                print(f"✗ Unexpected error for {file_name}: {e}")

    print(f"\n{'='*50}")
    print(f"Completed! Processed {subject_id_counter - 1} subjects")


if __name__ == "__main__":
    main()