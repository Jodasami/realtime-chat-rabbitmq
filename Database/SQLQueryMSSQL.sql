CREATE DATABASE Chat_DB
GO
USE Chat_DB
GO
CREATE TABLE messages (
    id INT IDENTITY(1,1) PRIMARY KEY,
    sender NVARCHAR(100),
    receiver NVARCHAR(100),
    message NVARCHAR(MAX),
    status NVARCHAR(30) DEFAULT 'sent',
    timestamp DATETIME DEFAULT GETDATE()
);
