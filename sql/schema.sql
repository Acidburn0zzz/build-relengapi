CREATE TABLE IF NOT EXISTS projects (
    id SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY (name)
);

CREATE TABLE IF NOT EXISTS hashes (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    hg_changeset VARCHAR(40) NOT NULL,
    git_changeset VARCHAR(40) NOT NULL,
    project_id SMALLINT UNSIGNED NOT NULL,
    date_added int UNSIGNED NOT NULL,
    PRIMARY KEY (id),
    INDEX (hg_changeset),
    INDEX (git_changeset),
    INDEX (project_id),
    UNIQUE INDEX (hg_changeset, git_changeset, project_id)
);
