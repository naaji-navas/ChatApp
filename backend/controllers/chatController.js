const asyncHandler = require("express-async-handler");
const Chat = require("../modles/chatModels");
const accesChat = asyncHandler(async (req, res) => {
  const { userId } = req.body;
  if (!userId) {
    res.status(400);
    throw new Error("No user id");
  }
  var isChat = await Chat.findOne({
    isGroupChat: false,
    users: { $size: 2, $all: [userId, req.user._id] },
  })
    .populate("users", "-password")
    .populate("latestMessage");
  await Usesr.populate(isChat, {
    path: "latestMessage.sender",
    select: "name profilePic email",
  });
  if (isChat.length > 0) {
    res.json(isChat);
  } else {
    var chatData = {
      chatName: "sender",
      users: [userId, req.user._id],
      isGroupChat: false,
    };
    try {
      const createdChat = await Chat.create(chatData);
      const fullChat = await Chat.findOne({ _id: createdChat.id })
        .populate("users", "-password")
        .populate("latestMessage");
      res.status(201).json(fullChat);
    } catch (error) {
      console.log(error);
    }
  }
});
module.exports = { accesChat };
