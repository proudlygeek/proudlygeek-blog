DROP TABLE IF EXISTS user;
CREATE TABLE user (
	id INTEGER PRIMARY KEY autoincrement,
	username VARCHAR(30) NOT NULL,
	password VARCHAR(30) NOT NULL,
	rank_id_FK INTEGER NOT NULL REFERENCES rank(id)
);
DROP TABLE IF EXISTS rank;
CREATE TABLE rank (
	id INTEGER PRIMARY KEY autoincrement,
	role_name VARCHAR(20) NOT NULL
);

DROP TABLE IF EXISTS entry;
CREATE TABLE entry (
	id INTEGER NOT NULL,
    slug VARCHAR(80) NOT NULL,
	title VARCHAR(80) NOT NULL,
	body TEXT NOT NULL,
	creation_date DATE NOT NULL,
	last_date DATE,
	user_id_FK INTEGER NOT NULL REFERENCES user(id),
    PRIMARY KEY(id, slug)
);

DROP TABLE IF EXISTS entry_tags;
CREATE TABLE entry_tags (
	slug_entry_FK INTEGER REFERENCES entry(id),
	id_tag_FK INTEGER REFERENCES tag(id),
	PRIMARY KEY(slug_entry_FK, id_tag_FK)
);

DROP TABLE IF EXISTS tag;
CREATE TABLE tag (
	id INTEGER PRIMARY KEY autoincrement,
	name VARCHAR(10) NOT NULL
);
