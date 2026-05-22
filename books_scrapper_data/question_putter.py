import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime

# ========================
# CONFIG
# ========================
ROOT_FOLDER = "./9 class"  # Root folder containing subject folders
DB_URL = "mysql+pymysql://root:123@localhost/exam_maker"

# ========================
# DB CONNECTION
# ========================
engine = create_engine(DB_URL)


def convert_to_mysql_datetime(date_str):
    """Convert date string to MySQL datetime format"""
    if not date_str:
        return None
    try:
        # Try parsing the datetime string
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def process_json_file(conn, file_path):
    """Process a single JSON file containing questions"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check if response is successful
        if data.get("Success") != "true":
            print(f"⚠ Skipping {file_path}: Success != true")
            return 0, 0

        records = data.get("Record", [])
        if not records:
            print(f"⚠ No records in {file_path}")
            return 0, 0

        questions_batch = []
        options_batch = []

        for record in records:
            question_id = record.get("id")
            
            # Skip if no question ID
            if not question_id:
                print(f"⚠ Skipping question with missing ID")
                continue

            # Prepare question data
            questions_batch.append({
                "id": int(question_id),
                "chapter_id": int(record.get("chapter_id", 0)),
                "topic_id": str(record.get("topic_id", "")) if str(record.get("topic_id", "")) != "0" else record.get("exercise"),
                "type_id": int(record.get("type_id", 0)),
                "medium": int(record.get("medium", 0)),
                "statement_en": record.get("statement_en"),
                "statement_ur": record.get("statement_ur"),
                "answer_en": record.get("answer_en"),
                "answer_ur": record.get("answer_ur"),
                "description_en": record.get("description_en"),
                "description_ur": record.get("description_ur"),
                "exercise": record.get("exercise"),
                "exercise_question": int(record.get("exercise_question", 0)),
                "past_paper_questions": int(record.get("past_paper_questions", 0)),
                "paragraph_questions": record.get("paragraph_questions"),
                "afaq": int(record.get("afaq", 0)) if record.get("afaq") else None,
                "status": int(record.get("status", 1)),
                "status_pef": int(record.get("status_pef", 1)),
                "is_table": int(record.get("is_table", 0)),
                "is_creative": int(record.get("is_creative", 0)),
                "created_at": convert_to_mysql_datetime(record.get("created_at"))
            })

            # Process options
            for option in record.get("options", []):
                options_batch.append({
                    "question_id": int(question_id),
                    "option_en": option.get("option_en"),
                    "option_ur": option.get("option_ur"),
                    "is_correct": int(option.get("is_correct", 0))
                })

        # Bulk insert questions
        if questions_batch:
            conn.execute(text("""
                INSERT INTO questions_bank 
                (id, chapter_id, topic_id, type_id, medium, statement_en, statement_ur, 
                 answer_en, answer_ur, description_en, description_ur, exercise, 
                 exercise_question, past_paper_questions, paragraph_questions, afaq, 
                 status, status_pef, is_table, is_creative, created_at)
                VALUES 
                (:id, :chapter_id, :topic_id, :type_id, :medium, :statement_en, :statement_ur,
                 :answer_en, :answer_ur, :description_en, :description_ur, :exercise,
                 :exercise_question, :past_paper_questions, :paragraph_questions, :afaq,
                 :status, :status_pef, :is_table, :is_creative, :created_at)
                ON DUPLICATE KEY UPDATE 
                    statement_en = VALUES(statement_en),
                    statement_ur = VALUES(statement_ur),
                    answer_en = VALUES(answer_en),
                    answer_ur = VALUES(answer_ur)
            """), questions_batch)

        # Bulk insert options
        if options_batch:
            conn.execute(text("""
                INSERT INTO question_options_bank 
                (question_id, option_en, option_ur, is_correct)
                VALUES (:question_id, :option_en, :option_ur, :is_correct)
            """), options_batch)

        return len(questions_batch), len(options_batch)

    except json.JSONDecodeError as e:
        print(f"✗ JSON parse error in {file_path}: {e}")
        return 0, 0
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0


def find_and_process_json_files(root_folder):
    """Recursively find and process all JSON files"""
    total_questions = 0
    total_options = 0
    total_files = 0
    failed_files = 0

    print(f"Scanning folder: {root_folder}\n")

    # Walk through all directories
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for filename in filenames:
            if not filename.endswith(".json"):
                continue

            file_path = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(file_path, root_folder)
            
            print(f"Processing: {relative_path}")

            try:
                with engine.begin() as conn:
                    questions_count, options_count = process_json_file(conn, file_path)
                    
                    if questions_count > 0:
                        print(f"  ✓ {questions_count} questions, {options_count} options\n")
                        total_questions += questions_count
                        total_options += options_count
                        total_files += 1
                    else:
                        print(f"  ⚠ No data inserted\n")
                        failed_files += 1

            except IntegrityError as e:
                print(f"  ✗ Database constraint violation: {e}\n")
                failed_files += 1
            except SQLAlchemyError as e:
                print(f"  ✗ Database error: {e}\n")
                failed_files += 1
            except Exception as e:
                print(f"  ✗ Unexpected error: {e}\n")
                failed_files += 1

    return total_files, total_questions, total_options, failed_files


def main():
    if not os.path.exists(ROOT_FOLDER):
        print(f"✗ Folder not found: {ROOT_FOLDER}")
        return

    print("="*60)
    print("QUESTIONS IMPORT SCRIPT")
    print("="*60 + "\n")

    total_files, total_questions, total_options, failed_files = find_and_process_json_files(ROOT_FOLDER)

    print("\n" + "="*60)
    print("IMPORT SUMMARY")
    print("="*60)
    print(f"Files processed successfully: {total_files}")
    print(f"Files failed: {failed_files}")
    print(f"Total questions inserted: {total_questions}")
    print(f"Total options inserted: {total_options}")
    print("="*60)


if __name__ == "__main__":
    main()