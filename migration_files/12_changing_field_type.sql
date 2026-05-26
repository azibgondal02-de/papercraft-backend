-- Step 1: Drop the column
ALTER TABLE questions_bank DROP COLUMN paragraph_questions;

-- Step 2: Add it as JSON with NULL default
ALTER TABLE questions_bank 
ADD COLUMN paragraph_questions JSON NULL;