ALTER TABLE oven_jobs
    ADD COLUMN cycle_uuid CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NULL,
    ADD UNIQUE KEY uq_oven_jobs_oven_cycle (oven_id, cycle_uuid);
