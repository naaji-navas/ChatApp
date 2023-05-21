const express = require("express");
const { protect } = require("../middleware/authMiddleware");
const { accesChat,fetchChats } = require("../controllers/chatController");
const router = express.Router();
//for getting the access of the chat
router.route("/").post(protect, accesChat);

// for fetching all the chats of that particular user
router.route("/").get(protect, fetchChats);

// router.route("/group").post(protect,createGroupChat)
// router.route("/rename").put(protect,renameGroup)
// router.route("/groupremove").put(protect,removeFromGroup)
// router.route("/groupadd").put(protect,addToGroup)

module.exports = router;
