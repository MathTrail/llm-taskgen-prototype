-- Database schema of the prototype: tables and views from SPEC 7.
-- Applied by db/apply_schema.py, which drops and recreates everything, so plain CREATE statements are enough.
-- Catalog ids (topics.json, skills.json, traps.json) are checked in code, not by foreign keys.

-- Trigram similarity for the near-duplicate check (SPEC 6).
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE students (
  student_id           text   PRIMARY KEY,
  grade                int    NOT NULL,
  interests            text[] NOT NULL,
  cognitive_profile    text[] NOT NULL,
  mastered_topics      text[] NOT NULL,
  excluded_skills      text[] NOT NULL,
  consecutive_failures int    NOT NULL DEFAULT 0,
  rating               real   NOT NULL DEFAULT 0,  -- global level theta (SPEC 5.6)
  answers_count        int    NOT NULL DEFAULT 0
);

CREATE TABLE student_topic_ratings (  -- per-topic offsets delta (SPEC 5.6)
  student_id    text NOT NULL REFERENCES students,
  topic         text NOT NULL,           -- topic id from topics.json
  topic_offset  real NOT NULL DEFAULT 0,
  answers_count int  NOT NULL DEFAULT 0,
  PRIMARY KEY (student_id, topic)
);

CREATE TABLE tasks (                -- task bank
  task_id         text PRIMARY KEY,
  created_at      timestamptz NOT NULL DEFAULT now(),
  topic           text   NOT NULL,  -- topic id from topics.json
  difficulty      int    NOT NULL,  -- 3, 4 or 5 points
  grade_level     text   NOT NULL,  -- '1-2' or '3-4'
  setting         text,
  excluded_skills text[] NOT NULL,  -- restrictions from the brief the task was generated for
  traps           text[] NOT NULL,
  brief           jsonb  NOT NULL,  -- Methodist brief
  task            jsonb  NOT NULL,  -- Generator JSON
  analyst         jsonb  NOT NULL,  -- Analyst output, including the walkthrough for the student
  skeptic         jsonb  NOT NULL,
  attempt_count   int    NOT NULL,
  rating          real   NOT NULL,  -- difficulty beta (SPEC 5.6), starts from the points
  rating_count    int    NOT NULL DEFAULT 0
);

CREATE TABLE student_tasks (        -- issued tasks and answers = student history
  id            bigserial PRIMARY KEY,
  student_id    text NOT NULL REFERENCES students,
  task_id       text REFERENCES tasks,  -- NULL for rows from the starting profile
  topic         text NOT NULL,
  difficulty    int  NOT NULL,
  issued_at     timestamptz NOT NULL DEFAULT now(),
  correct       boolean,                -- NULL: "didn't understand" or not answered yet
  chosen_option text,
  trap_hit      text,                   -- trap id from traps.json
  feedback      text,
  hint_used     boolean NOT NULL DEFAULT false,
  pace          text,                   -- 'fast', 'normal' or 'struggled'
  UNIQUE (student_id, task_id)
);

CREATE TABLE requests (             -- one task request for a student
  request_id    bigserial PRIMARY KEY,
  created_at    timestamptz NOT NULL DEFAULT now(),
  student_id    text  NOT NULL REFERENCES students,
  tutor_mode    text  NOT NULL,         -- 'llm' or 'rule' (SPEC 5.7)
  brief         jsonb NOT NULL,         -- Methodist brief
  source        text  NOT NULL,         -- 'bank', 'generated' or 'failed'
  task_id       text  REFERENCES tasks, -- NULL if 'failed'
  attempt_count int   NOT NULL DEFAULT 0,
  tokens        int,
  cost_usd      numeric(10, 4),
  duration_ms   int
);

CREATE TABLE attempts (             -- every generation attempt
  attempt_id  bigserial PRIMARY KEY,
  request_id  bigint NOT NULL REFERENCES requests,
  attempt_no  int    NOT NULL,        -- 1-3
  status      text   NOT NULL,        -- 'accepted', 'rejected' or 'generator_answer_error'
  reason      text,                   -- rejection reason code (SPEC 6)
  generator   jsonb,
  analyst     jsonb,                  -- including solver_code
  skeptic     jsonb,
  solver_result  jsonb,               -- what the program returned in the sandbox
  prompt_version text NOT NULL,       -- prompt hash: without it metrics of different versions mix
  models      jsonb,
  tokens      int,
  cost_usd    numeric(10, 4),
  duration_ms int
);

CREATE VIEW finetune_solver AS      -- solver dataset
  SELECT task_id,
         jsonb_build_object('question', task -> 'question', 'options', task -> 'options') AS prompt,
         analyst AS completion
  FROM tasks;

CREATE VIEW finetune_generator AS   -- generator dataset
  SELECT task_id, brief AS prompt, task AS completion
  FROM tasks;

-- Indexes are not in SPEC 7; they follow the note in docs/architecture/03-data-model.md.

-- Near-duplicate search by question text (SPEC 6).
CREATE INDEX tasks_question_trgm_idx ON tasks USING gin ((task ->> 'question') gin_trgm_ops);
-- Bank search: topic, grade level, rating inside the corridor (SPEC 5.5).
CREATE INDEX tasks_bank_idx ON tasks (topic, grade_level, rating);
-- Last N history rows for the Methodist.
CREATE INDEX student_tasks_history_idx ON student_tasks (student_id, issued_at);
-- Attempts of one request.
CREATE INDEX attempts_request_idx ON attempts (request_id);
