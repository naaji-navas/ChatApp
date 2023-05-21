const express = require("express");
const { protect } = require("../middleware/authMiddleware");
const {
  accesChat,
  fetchChats,
  createGroupChat,
  renameGroup,
  addToGroup,
  removeFromGroup,
} = require("../controllers/chatController");
const router = express.Router();
//for getting the access of the chat
router.route("/").post(protect, accesChat);

// for fetching all the chats of that particular user
router.route("/").get(protect, fetchChats);

//api for creating groupChats
router.route("/group").post(protect, createGroupChat);

//api for renaming the chat
router.route("/rename").put(protect, renameGroup);

//api to add a user to the group
router.route("/groupadd").put(protect, addToGroup);

router.route("/groupremove").put(protect, removeFromGroup);

module.exports = router;
