USE Chat_DB
SELECT TOP (1000) [id]
      ,[sender]
      ,[receiver]
      ,[message]
      ,[status]
      ,[timestamp]
  FROM [Chat_DB].[dbo].[messages]
  ORDER BY id DESC

