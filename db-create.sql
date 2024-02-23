-- Create `customer` table
CREATE TABLE customer (
    id_customer SERIAL PRIMARY KEY,
    customer_name VARCHAR(200) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create `project` table
CREATE TABLE project (
    id_project SERIAL PRIMARY KEY,
    id_customer INTEGER NOT NULL,
    project_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_project_customer FOREIGN KEY (id_customer) REFERENCES customer(id_customer) ON DELETE CASCADE
);

-- Create `tasks` table
CREATE TABLE tasks (
    id_task SERIAL PRIMARY KEY,
    id_project INTEGER NOT NULL,
    task_name VARCHAR(100) NOT NULL,
    task_description TEXT,
    task_hours INTEGER,
    task_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tasks_project FOREIGN KEY (id_project) REFERENCES project(id_project) ON DELETE CASCADE
);
