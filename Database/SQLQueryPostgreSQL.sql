CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    sender VARCHAR(100),
    receiver VARCHAR(100),
    message TEXT,
    status VARCHAR(30) DEFAULT 'sent',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
