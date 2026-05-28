-- questions_bank
ALTER TABLE questions_bank 
  ADD INDEX idx_type_status           (type_id, status),
  ADD INDEX idx_topic_type_status     (topic_id, type_id, status),
  ADD INDEX idx_chapter_type_status   (chapter_id, type_id, status),
  ADD INDEX idx_covering_count        (topic_id, type_id, status, exercise_question),
  ADD INDEX idx_exercise_question     (exercise_question);

-- question_options_bank
ALTER TABLE question_options_bank 
  ADD INDEX idx_question_id (question_id);

-- topics_bank
ALTER TABLE topics_bank 
  ADD INDEX idx_chapter_code (chapter_code);

-- chapters_bank
ALTER TABLE chapters_bank 
  ADD INDEX idx_subject_id (subject_id);

-- subjects_bank
ALTER TABLE subjects_bank 
  ADD INDEX idx_class_id (class_id);

-- classes_bank
ALTER TABLE classes_bank 
  ADD INDEX idx_board_id (board_id);