const express = require("express");
const chats = require("./data/data");
const app = express();
const dotenv = require("dotenv");

dotenv.config();


//api for checking if server is running
app.get("/", (req, res) => {
  res.send("Api is running");
});

//api for gettig a single chat
app.get("/api/chats/:id", (req, res) => {
  const singleChat = chats.find((c) => c._id === req.params.id);
  res.send(singleChat)
});


//api for getting all chats
app.get("/api/chats", (req, res) => {
  res.send(chats);
});

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`Server started on port ${PORT}` );
});


