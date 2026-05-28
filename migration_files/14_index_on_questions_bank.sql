ALTER TABLE questions_bank
  ADD INDEX idx_topic_type_status_id (topic_id, type_id, status, id);