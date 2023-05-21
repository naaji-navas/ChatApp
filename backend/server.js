const express = require("express");
const chats = require("./data/data");
const app = express();
const dotenv = require("dotenv");
dotenv.config();
const colors = require("colors");
connectDB = require("./config/db");
connectDB();
app.use(express.json()); //middleware to parse json data
const userRoutes = require("./routes/userRoutes");
const chatRoutes = require("./routes/chatRoutes");
const { notFound, errorHandler } = require("./middleware/errorMiddleware");

//api for checking if server is running
app.get("/", (req, res) => {
  res.send("Api is running");
});

app.use("/api/user", userRoutes);
app.use("/api/chats",chatRoutes)
//api for gettig a single chat
app.get("/api/chats/:id", (req, res) => {
  const singleChat = chats.find((c) => c._id === req.params.id);
  res.send(singleChat);
});

//error handling middleware
app.use(notFound);
app.use(errorHandler);

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`Server started on port ${PORT}`.yellow.bold);
});
